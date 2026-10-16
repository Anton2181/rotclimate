"""Passive regional budgets, stage reconstruction, exact replay and resume."""
from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
from experiments import v10_delivery_diagnostics as m
from scripts import replay_v10_delivery as replay,review_v10_event_forcing as review
from tests.test_v10_event_forcing import calendar_fixture,ToyDriver
from rotclimate_v10.core import divergence
from rotclimate_v10.earth import atomic_json,sha256


def toy():
    d,p,s,g,air,flows,a,stats = calendar_fixture()
    distance = np.broadcast_to(np.array([50.,50.,100.,200.,250.,400.,450.,500.]),d.land.shape).copy()
    case = SimpleNamespace(domain=d,score_mask=d.land,coast_distance_km=distance)
    return case,p,s,g,air,flows,a


def test_regional_gross_transfers_close_divergence_and_count_internal_edges_once():
    rng = np.random.default_rng(6);fx = rng.normal(size=(5,3,9));fy = rng.normal(size=(5,4,8))
    mask = np.zeros((3,8),bool);mask[0:2,2:5] = True;mask[2,7] = True
    incoming,outgoing = m.masked_transfers(fx,fy,mask,60000.,60000.)
    expected = -divergence(fx,fy,60000.,60000.).sum(0)[mask].mean()
    assert incoming-outgoing == pytest.approx(expected,abs=1e-18)
    assert incoming >= 0 and outgoing >= 0


def test_joint_bins_include_saturated_and_extreme_values_without_losing_weight():
    w = np.array([-.2,-.01,0.,.01,.3]);rh = np.array([0.,.9,1.,1.05,3.])
    bins = m.joint_bins(w,rh)
    assert bins.min() >= 0 and bins.max() < (len(m.W_EDGES)-1)*(len(m.RH_EDGES)-1)
    assert len(np.bincount(bins)) <= 72
    with pytest.raises(ValueError,match='Invalid'):
        m.joint_bins(w,rh+np.nan)


def test_passive_stages_do_not_change_physics_and_rain_is_not_dt_weighted_twice():
    case,p,s,g,air,flows,a = toy();d = case.domain
    t = air[0];water = 1.2*g.mass*m.base.saturation(t,g.pressure)
    state = m.base.State(water,g.mass*(m.base.CP*(t+273.15)+m.base.G*g.height_m)+m.base.LV*water,np.zeros(d.land.shape))
    f = m.base.balanced(np.zeros((5,3,9)),np.zeros((5,4,8)),d.dx,d.dy)
    rain_totals = []
    for dt in (10.,20.):
        result = m.advance(state,d,p,s,f,dt,0.,air,geometry=g,boundary=np.zeros_like(g.mass))
        physical = deepcopy(result)
        c = m.Collector(d,g,case.score_mask,case.coast_distance_km)
        c.add(state,result[0],result[5],result[6],f,np.zeros_like(g.mass),result[4],dt,0.)
        np.testing.assert_array_equal(result[0].water,physical[0].water)
        np.testing.assert_array_equal(result[0].energy,physical[0].energy)
        assert c.arrays['joint_layer_rain_cell_mm'][:,0].sum() == pytest.approx(result[5][1:].sum(),abs=1e-10)
        assert c.arrays['time_cell_seconds'][0,0] == dt*d.land.size
        rain_totals.append(c.arrays['actual_layer_rain_cell_mm'][:,0].sum())
        assert c.arrays['maximum_reconstruction_errors'].max() < 1e-9
    assert rain_totals[0] == pytest.approx(rain_totals[1],abs=1e-10)


def test_manufactured_replay_exact_physics_and_binary_diagnostic_resume(tmp_path,monkeypatch):
    case,p,s,g,air,flows,a = toy();d = case.domain
    monkeypatch.setattr(m,'EDGES',a['edges']);monkeypatch.setattr(m.physics,'EDGES',a['edges'])
    state = m.physics.core.initial_state(d,p,s,g,air);driver = ToyDriver(d,flows,a)
    expected = m.physics.year(d,p,s,state,air,case.score_mask,g,driver)
    c = m.Collector(d,g,case.score_mask,case.coast_distance_km)
    full = m.year(d,p,s,state,air,case.score_mask,g,driver,collector=c)
    replay.verify_physical(full,expected);c.validate_months(12)
    interrupted = [False];partial_collector = m.Collector(d,g,case.score_mask,case.coast_distance_km)
    def save(*record):
        replay.write_checkpoint(tmp_path,record,partial_collector)
        if record[-1]['month'] == 2:interrupted[0] = True
    with pytest.raises(m.base.BudgetStop):
        m.year(d,p,s,state,air,case.score_mask,g,driver,save_month=save,should_stop=lambda:interrupted[0],collector=partial_collector)
    partial,restored = replay.read_checkpoint(tmp_path,case,g)
    resumed = m.year(d,p,s,state,air,case.score_mask,g,driver,checkpoint=partial,collector=restored)
    replay.verify_physical(resumed,expected)
    for key in c.arrays:np.testing.assert_array_equal(c.arrays[key],restored.arrays[key])
    replay.write_checkpoint(tmp_path,resumed,restored,completed=True)
    loaded,loaded_collector = replay.read_checkpoint(tmp_path,case,g,completed=True)
    replay.verify_physical(loaded,expected)
    assert loaded_collector.summary() == restored.summary()
    (tmp_path/'year1.npz').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='integrity'):
        replay.read_checkpoint(tmp_path,case,g,completed=True)


def test_physical_reproduction_refuses_changed_rain_or_budget():
    state = m.base.State(np.ones((5,2,2)),np.ones((5,2,2)),np.zeros((2,2)))
    record = (state,np.zeros((12,2,2)),np.zeros((12,5,2,2)),np.zeros((12,5,2,2)),{'budget':{'rain_mm':0.},'elapsed_seconds':1.})
    changed = deepcopy(record);changed[-1]['elapsed_seconds'] = 500.
    replay.verify_physical(changed,record)
    changed[1][0,0,0] = 1.
    with pytest.raises(ValueError,match='rain'):replay.verify_physical(changed,record)
    changed = deepcopy(record);changed[-1]['budget']['rain_mm'] = 1.
    with pytest.raises(ValueError,match='ledger'):replay.verify_physical(changed,record)


def test_diagnostic_resume_refuses_negative_weight_or_missing_array():
    case,p,s,g,air,flows,a = toy()
    c = m.Collector(case.domain,g,case.score_mask,case.coast_distance_km)
    arrays = deepcopy(c.arrays);arrays['time_cell_seconds'][0,0] = -1.
    with pytest.raises(ValueError,match='Negative'):
        m.Collector(case.domain,g,case.score_mask,case.coast_distance_km,saved=arrays)
    arrays = deepcopy(c.arrays);arrays.pop('joint_time_cell_seconds')
    with pytest.raises(ValueError,match='shape'):
        m.Collector(case.domain,g,case.score_mask,case.coast_distance_km,saved=arrays)


def test_budget_differences_keep_recycling_and_storage_separate_from_source_fractions():
    a = dict(boundary_import_gross_mm=100.,boundary_export_gross_mm=90.,ocean_evaporation_mm=10.,land_evaporation_mm=5.,rain_mm=20.,roundoff_correction_mm=0.)
    b = dict(a,boundary_export_gross_mm=92.,ocean_evaporation_mm=14.,land_evaporation_mm=8.,rain_mm=24.)
    row = review.atmospheric_budget_difference(a,b)
    assert row['signed_ledger_terms_mm']['boundary_import'] == 0.
    assert row['signed_ledger_terms_mm']['reduced_export'] == -2.
    assert row['signed_ledger_terms_mm']['land_recycling'] == 3.
    assert row['implied_atmospheric_storage_change_difference_mm'] == 1.


def test_default_does_not_prepare_or_replay(tmp_path,monkeypatch):
    monkeypatch.setattr(replay,'prepare',lambda:pytest.fail('Unexpected preparation'))
    monkeypatch.setattr(replay,'replay',lambda *a:pytest.fail('Unexpected replay'))
    assert replay.main(['--out',str(tmp_path/'absent')]) == 0
    assert not (tmp_path/'absent').exists()


def mock_batch(tmp_path,monkeypatch):
    jobs = [{'key':'california_lift1_steady','source_year':4},{'key':'iberia_lift16_aligned','source_year':4}]
    protocol = {'code_sha256':replay.source_id(),'jobs':jobs}
    monkeypatch.setattr(replay,'prepare',lambda:(protocol,{},None,{}, {},{}))
    prepared = tmp_path/'prepared';atomic_json(prepared/'manifest.json',{'protocol':protocol})
    return protocol,prepared


def fake_case(folder):
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'config.json',{'toy':True});(folder/'year1.npz').write_bytes(b'toy evidence')
    row = {'physical_reproduction_exact':True,'regions':{'coast':{
        'mean_relative_humidity_by_stage_layer':np.full((3,5),.5).tolist(),'annual_layer_rain_mm':[1.]*5,
        'recipient_moist_fraction_when_upward_exchange_ge_001_pa_s':[.2]*4}},
        'case_config_sha256':sha256(folder/'config.json'),'evidence_sha256':{'year1.npz':sha256(folder/'year1.npz')}}
    atomic_json(folder/'summary.json',row);return row


def test_replay_batch_resumes_and_refuses_changed_evidence(tmp_path,monkeypatch):
    protocol,prepared = mock_batch(tmp_path,monkeypatch);calls = []
    def fake(folder,job,*args):
        calls.append(job['key'])
        if len(calls) == 2:raise m.base.BudgetStop()
        return fake_case(folder)
    out = tmp_path/'replay'
    assert replay.replay(out,prepared,case_runner=fake)['status'] == 'budget_reached'
    assert replay.replay(out,prepared,case_runner=fake)['status'] == 'complete'
    assert calls.count('california_lift1_steady') == 1
    (out/'cases/california_lift1_steady/year1.npz').write_bytes(b'changed')
    assert replay.replay(out,prepared,case_runner=fake)['status'] == 'needs_diagnosis'


def test_budget_prevents_start_and_stale_preflight_stops(tmp_path,monkeypatch):
    protocol,prepared = mock_batch(tmp_path,monkeypatch);times = iter([0.,replay.BUDGET_SECONDS+1])
    state = replay.replay(tmp_path/'replay',prepared,case_runner=lambda *a:pytest.fail('No time'),clock=lambda:next(times))
    assert state['status'] == 'budget_reached' and not state['cases']
    protocol['changed'] = True
    with pytest.raises(ValueError,match='stale'):replay.replay(tmp_path/'replay',prepared)
