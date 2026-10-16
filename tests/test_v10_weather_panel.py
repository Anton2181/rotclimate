"""Fixed paired design, seeded adapter regression, bounded resume and evidence."""
from dataclasses import dataclass, replace
import json
import numpy as np
import pytest
from experiments import v10_weather_panel as weather
from scripts import afternoon_v10_delivery as run
from tests.test_v10_event_forcing import calendar_fixture
from tests.test_v10_split_column import five_fixture
from tests.test_v10_delivery_diagnostics import fake_case
from rotclimate_v10.earth import atomic_json


@dataclass
class TinySettings:
    test: bool = True


def test_plan_has_fixed_pairs_and_diagnostic_prerequisites(monkeypatch):
    old = {'jobs':[{'key':f'old{i}'} for i in range(4)],'inputs':{'california':'a','iberia':'b'}}
    monkeypatch.setattr(run.replay,'prepare',lambda:(old,{'california':None,'iberia':None},TinySettings(),{}, {},{}))
    protocol,*_ = run.prepare();jobs = protocol['jobs']
    assert len(jobs) == 100 and len({job['key'] for job in jobs}) == 100
    assert [sum(j['phase'] == p for j in jobs) for p in ('reference','climate','diagnostic')] == [4,64,32]
    assert all(j['phase'] == 'reference' for j in jobs[:4])
    earlier = set()
    for job in jobs:
        if job['phase'] == 'diagnostic':assert job['source_case'] in earlier
        earlier.add(job['key'])
    assert protocol['seeds'] == [67,103,149,211,307,401,503,607]
    assert not protocol['atlas_publication'] and not protocol['downloads']


def test_seed_adapter_exact_original_and_repeatable_new_catalogue(monkeypatch):
    case,p,s,g,air,c = five_fixture();s = replace(s,storm_rate_month=4.)
    _,_,_,_,_,_,a,_ = calendar_fixture()
    # Only Driver's native-flow path is examined here; use a matching tiny mask.
    a = dict(a,boundary_mask=weather.core.boundary_mask(case.domain.land.shape))
    for amplitude,timing in run.CONDITIONS:
        a['boundary_'+weather.core.variant_key(amplitude,timing)] = np.zeros((len(a['times']),5,int(a['boundary_mask'].sum())))
        old = weather.core.Driver(a,case,p,s,g,air,c,amplitude,timing)
        same = weather.Driver(a,case,p,s,g,air,c,amplitude,timing,41)
        fresh = weather.Driver(a,case,p,s,g,air,c,amplitude,timing,67)
        repeat = weather.Driver(a,case,p,s,g,air,c,amplitude,timing,67)
        assert same.events == old.events and fresh.events == repeat.events
        assert fresh.events != same.events
        # Make mean faces compatible with this geometry; they need not describe
        # a climatology for this direct adapter regression.
        a['mean_convergence_x'] = np.zeros((12,5,4,6));a['mean_convergence_y'] = np.zeros((12,5,5,5))
        for t in (0.,10800.,86400.):
            for left,right in ((old,same),(fresh,repeat)):
                f,q,end = left.at(t);other,other_q,other_end = right.at(t)
                for name in ('x','y','vertical'):np.testing.assert_array_equal(getattr(f,name),getattr(other,name))
                np.testing.assert_array_equal(q,other_q);assert end == other_end


def test_seeded_calendar_matches_original_builder_and_passive_toy_year(monkeypatch):
    case,p,s,g,air,c = five_fixture(False);s = replace(s,storm_rate_month=2.)
    distance = np.broadcast_to(np.array([50.,100.,200.,400.,500.]),case.domain.land.shape).copy()
    case = replace(case,coast_distance_km=distance)
    edges = np.arange(13,dtype=float)*12*3600.
    original_builder = weather.core.build_calendar
    monkeypatch.setattr(weather.core,'build_calendar',lambda *a,**kw:original_builder(*a,**kw,edges=edges))
    a,_ = weather.core.prepare_calendar(case,p,s,g,air,c)
    b,stats = weather.prepare_calendar(case,p,s,g,air,c,41)
    for name in a:np.testing.assert_array_equal(a[name],b[name])
    assert stats['seed'] == 41 and stats['maximum_monthly_import_error_mm'] < 1e-10
    monkeypatch.setattr(weather.core,'EDGES',edges);monkeypatch.setattr(run.replay.model,'EDGES',edges)
    initial = weather.core.core.initial_state(case.domain,p,s,g,air)
    old_driver = weather.core.Driver(a,case,p,s,g,air,c,16.,'aligned')
    new_driver = weather.Driver(b,case,p,s,g,air,c,16.,'aligned',41)
    expected = weather.core.year(case.domain,p,s,initial,air,case.score_mask,g,old_driver)
    collector = run.replay.model.Collector(case.domain,g,case.score_mask,case.coast_distance_km)
    actual = run.replay.model.year(case.domain,p,s,initial,air,case.score_mask,g,new_driver,collector=collector)
    run.replay.verify_physical(actual,expected)
    collector.validate_months(12)


def test_forcing_cache_refuses_damage_and_wrong_source(tmp_path):
    _,_,_,_,_,_,a,stats = calendar_fixture();identity = {'seed':67,'source':'frozen'}
    path = tmp_path/'forcing/s67_toy';run.write_calendar(path,identity,a,stats)
    saved,_ = run.read_calendar(path,identity)
    for key in a:np.testing.assert_array_equal(saved[key],a[key])
    with pytest.raises(ValueError,match='identity'):run.read_calendar(path,dict(identity,seed=41))
    path.with_suffix('.npz').write_bytes(b'damaged')
    with pytest.raises(ValueError,match='integrity'):run.read_calendar(path,identity)


def mock_batch(tmp_path,monkeypatch):
    jobs = [{'key':'first','phase':'reference'},{'key':'second','phase':'reference'}]
    protocol = {'code_sha256':run.source_id(),'jobs':jobs}
    monkeypatch.setattr(run,'prepare',lambda:(protocol,{},None,{}, {},{}))
    prepared = tmp_path/'prepared';atomic_json(prepared/'manifest.json',{'protocol':protocol})
    monkeypatch.setattr(run,'PREFLIGHT',prepared)
    return protocol


def test_batch_resumes_and_verifies_prior_evidence(tmp_path,monkeypatch):
    mock_batch(tmp_path,monkeypatch);calls = []
    def fake(folder,job):
        calls.append(job['key'])
        if len(calls) == 2:raise run.run.model.base.BudgetStop()
        return fake_case(folder)
    out = tmp_path/'result'
    assert run.batch(out,case_runner=fake)['status'] == 'budget_reached'
    state = run.batch(out,case_runner=fake)
    assert state['status'] == 'complete' and len(state['invocations']) == 2
    assert calls == ['first','second','second']
    (out/'cases/first/year1.npz').write_bytes(b'changed')
    assert run.batch(out,case_runner=fake)['status'] == 'needs_diagnosis'
    with pytest.raises(ValueError,match='inspection'):run.batch(out,case_runner=fake)


def test_budget_blocks_start_and_stale_preflight_is_rejected(tmp_path,monkeypatch):
    protocol = mock_batch(tmp_path,monkeypatch);ticks = [0.]
    def clock():
        result = ticks[0];ticks[0] = 15000.;return result
    state = run.batch(tmp_path/'result',case_runner=lambda *a:pytest.fail('Out of time'),clock=clock)
    assert state['status'] == 'budget_reached' and not state['cases']
    protocol['changed'] = True
    with pytest.raises(ValueError,match='stale'):run.batch(tmp_path/'other')


@pytest.mark.parametrize('hours',[0.,-1.,4.01,np.inf,np.nan])
def test_invalid_budget_rejected_before_preparation(hours,tmp_path,monkeypatch):
    monkeypatch.setattr(run,'prepare',lambda:pytest.fail('Invalid budget'))
    with pytest.raises(ValueError,match='budget'):run.batch(tmp_path,hours)


def test_read_only_default_does_not_prepare_or_integrate(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'prepare',lambda:pytest.fail('Unexpected preparation'))
    monkeypatch.setattr(run,'batch',lambda *a:pytest.fail('Unexpected climate'))
    assert run.main(['--out',str(tmp_path/'absent')]) == 0
    assert not (tmp_path/'absent').exists()


def test_pairing_keeps_signed_contrasts_and_unsettled_label():
    state = {'cases':{}}
    for (amplitude,timing),rain,mae in zip(run.CONDITIONS,(20.,50.,55.,53.),(30.,28.,27.,28.)):
        key = 's67_california_'+run.run.model.variant_key(amplitude,timing)
        state['cases'][key] = {'settling':{'passed':timing != 'shifted'},'response':{
            'coast_winter_mm':rain,'monthly_mae_mm':mae,'coast_winter_reference_mm':500.}}
    paired = run.paired_results(state)
    assert list(paired) == ['s67_california']
    row = paired['s67_california']
    assert row['lifting_coastal_winter_gain_mm'] == 30.
    assert row['combined_coastal_winter_gain_mm'] == 35.
    assert row['timing_coastal_winter_gain_mm'] == 2.
    assert row['combined_monthly_mae_change_mm'] == -3.
    assert not row['all_settled']
