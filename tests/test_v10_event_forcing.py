"""Manufactured forcing invariants, physical regression, restart and run guards."""
from dataclasses import replace
import json
import numpy as np
import pytest
from experiments import v10_event_forcing as m
from scripts import check_v10_event_forcing as run, audit_v10_event_fronts as fronts
from tests.test_v10_split_column import five_fixture
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def calendar_fixture():
    domain,p,s,g = fronts.manufactured_inputs()
    t = np.broadcast_to(np.array([15.,8.,-3.,-25.,-55.])[:,None,None],g.mass.shape)
    air = np.broadcast_to(t,(12,)+t.shape).copy()
    x = np.broadcast_to(g.mass[...,:1]*2.,(5,3,9)).copy();y = np.zeros((5,4,8))
    def flows(time_s):
        cx = np.zeros_like(x);cy = np.zeros_like(y)
        cx[0] = 300.*np.sin(2*np.pi*time_s/(12*3600.))*np.linspace(1.,-1.,9)[None]
        cx[4] = -cx[0]
        return m.base.balanced(x+cx,y,domain.dx,domain.dy),m.base.balanced(cx,cy,domain.dx,domain.dy),{}
    q = .15*m.base.saturation(t,g.pressure);q[4] = 0.
    caps = .95*m.base.saturation(t,g.pressure)
    edges = np.arange(13,dtype=float)*12*3600.
    arrays,stats = m.build_calendar(domain,g,flows,lambda t:q,lambda a,b:caps,domain.land,edges=edges)
    return domain,p,s,g,air,flows,arrays,stats


def test_boundary_corner_coefficients_match_actual_gross_transport():
    domain,p,s,g,air,flows,a,stats = calendar_fixture()
    f = flows(10800.)[0];q = np.random.default_rng(4).uniform(0,.005,g.mass.shape)
    state = m.base.State(g.mass*.002,g.mass*300000.,np.zeros(domain.land.shape))
    expected,_ = m.core.gross_boundary_transfers(state,f,60.,domain,g,q)
    actual = (m.incoming_coefficients(f,domain)*q[:,m.boundary_mask(domain.land.shape)]).sum()*60.
    assert actual == pytest.approx(expected,abs=1e-12)
    assert m.boundary_mask((3,8)).sum() == 18


def test_all_variants_match_monthly_gross_import_and_preserve_mean_flow():
    domain,p,s,g,air,flows,a,stats = calendar_fixture()
    assert stats['maximum_monthly_mean_face_velocity_change_m_s'] < 1e-12
    assert stats['maximum_monthly_import_error_mm'] < 1e-10
    for amplitude in m.AMPLITUDES:
        for timing in m.TIMINGS:
            values = a['boundary_'+m.variant_key(amplitude,timing)]
            assert not values[:,4].any()
            for month in range(12):
                indices = np.flatnonzero((a['times'] >= a['edges'][month]) & (a['times'] < a['edges'][month+1]))
                total = 0.
                for i in indices:
                    full,conv,_ = flows(a['times'][i])
                    f = m.centered_flow(full,conv,a['mean_convergence_x'][month],a['mean_convergence_y'][month],amplitude,domain)
                    total += np.sum(m.incoming_coefficients(f,domain)*values[i])*m.INTERVAL
                assert total == pytest.approx(a['monthly_import_target_mm'][month],abs=1e-10)
    # Actual humidity statistics need not match despite the matched water dose.
    assert not np.allclose(a['boundary_lift1_aligned'],a['boundary_lift1_shifted'])


def test_pulse_shift_preserves_nominal_distribution_within_month():
    a,b = m.pulse_pair([0.,1.,0.,0.,.3,0.])
    np.testing.assert_array_equal(np.sort(a),np.sort(b))
    assert a.mean() == pytest.approx(1.) and a.min() >= .6 and a.max() <= 1.4
    quiet,_ = m.pulse_pair(np.zeros(8));np.testing.assert_array_equal(quiet,1.)
    sectors = np.array([[0.,1.,0.],[1.,0.,0.],[0.,0.,0.],[0.,.3,0.]])
    a,b = m.pulse_pair(sectors)
    np.testing.assert_array_equal(np.sort(a,axis=0),np.sort(b,axis=0))
    np.testing.assert_allclose(a.mean(axis=0),1.)
    np.testing.assert_array_equal(a[:,2],1.)


def test_capped_dose_normalization_accounts_for_nonuniform_inflow():
    raw = np.array([1.,2.,3.]);caps = np.array([.5,1.,2.]);weight = np.array([10.,1.,.1])
    q,scale = m.match_import(raw,caps,weight,2.,8.)
    assert (q <= caps).all() and scale > 0
    assert np.dot(weight,q)*2. == pytest.approx(8.,abs=1e-10)
    with pytest.raises(ValueError,match='infeasible'):
        m.match_import(raw,caps,weight,2.,100.)
    with pytest.raises(ValueError,match='infeasible'):
        m.match_import(np.zeros(3),caps,weight,2.,1.)


@pytest.mark.parametrize('interval,target',[(np.nan,1.),(0.,1.),(1.,np.nan),(1.,-1.)])
def test_dose_normalization_rejects_invalid_targets_and_clock(interval,target):
    with pytest.raises(ValueError):
        m.match_import(np.ones(3),np.ones(3),np.ones(3),interval,target)


def test_explicit_boundary_step_exactly_reproduces_frozen_physics():
    case,p,s,g,air,c = five_fixture();state = m.core.initial_state(case.domain,p,s,g,air)
    f = m.core.flow_at(case.domain,p,s,[],0.,g,c[3],wind_mode='spatial',circulation=c)
    q = m.core.boundary_ratio(case.domain,p,s,g,air,0.)
    new = m.advance(state,case.domain,p,s,f,60.,0.,air,geometry=g,boundary=q)
    old = m.core.advance(state,case.domain,p,s,f,60.,0.,air,geometry=g)
    for name in ('water','energy','soil'):
        np.testing.assert_array_equal(getattr(new[0],name),getattr(old[0],name))
    for i in (1,2,3,5,6):
        np.testing.assert_array_equal(new[i],old[i])
    assert new[4] == old[4] and new[-1] == old[-1]
    with pytest.raises(ValueError,match='saturation cap'):
        m.advance(state,case.domain,p,s,f,60.,0.,air,geometry=g,boundary=q+.1)


def test_manufactured_front_and_saturated_ascent_limits():
    data = fronts.probes()
    assert data['unsaturated_front']['total_rain_mm'] == 0.
    assert data['saturated_pressure_transfer']['condensation_error_mm'] < 1e-10
    assert data['regional_climate_integrations'] == 0


class ToyDriver:
    def __init__(self,domain,flows,arrays,amplitude=None,timing='aligned'):
        self.domain = domain;self.flows = flows;self.arrays = arrays
        self.amplitude = m.AMPLITUDES[1] if amplitude is None else amplitude;self.timing = timing
        self.monthly_targets = arrays['monthly_import_target_mm']
        self.last_info = dict(barotropic_velocity_adjustment_max_m_s=0.,raw_column_divergence_max_kg_m2_s=0.)
    def at(self,time_s):
        index = int(np.floor((time_s+1e-6)/m.INTERVAL));tick = self.arrays['times'][index]
        month = np.searchsorted(self.arrays['edges'][1:],tick,side='right')
        full,conv,_ = self.flows(tick)
        f = m.centered_flow(full,conv,self.arrays['mean_convergence_x'][month],self.arrays['mean_convergence_y'][month],self.amplitude,self.domain)
        boundary = np.zeros((5,)+self.domain.land.shape)
        boundary[:,self.arrays['boundary_mask']] = self.arrays['boundary_'+m.variant_key(self.amplitude,self.timing)][index]
        return f,boundary,tick+m.INTERVAL


def test_manufactured_year_preserves_dose_and_resumes_exactly(tmp_path,monkeypatch):
    domain,p,s,g,air,flows,a,_ = calendar_fixture();monkeypatch.setattr(m,'EDGES',a['edges'])
    driver = ToyDriver(domain,flows,a);state = m.core.initial_state(domain,p,s,g,air)
    full = m.year(domain,p,s,state,air,domain.land,g,driver)
    stopped = [False]
    def save(*record):
        run.parent.write_checkpoint(tmp_path,1,record)
        if record[-1]['month'] == 2:
            stopped[0] = True
    with pytest.raises(m.base.BudgetStop):
        m.year(domain,p,s,state,air,domain.land,g,driver,save_month=save,should_stop=lambda:stopped[0])
    partial = run.parent.read_checkpoint(tmp_path,1,domain.land.shape)
    run.validate_control_record(partial,driver.monthly_targets)
    result = m.year(domain,p,s,state,air,domain.land,g,driver,checkpoint=partial)
    for name in ('water','energy','soil'):
        np.testing.assert_array_equal(getattr(full[0],name),getattr(result[0],name))
    for x,y in zip(full[1:4],result[1:4]):
        np.testing.assert_array_equal(x,y)
    assert full[-1] == result[-1]
    run.validate_control_record(result,driver.monthly_targets)
    result[-1]['diagnostics']['monthly_boundary_import_gross_mm'][0] += 1.
    with pytest.raises(ValueError,match='import control'):
        run.validate_control_record(result,driver.monthly_targets)


def test_read_only_default_does_not_prepare_or_launch(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'run',lambda *a:pytest.fail('Unexpected climate integration'))
    monkeypatch.setattr(run,'prepare',lambda *a:pytest.fail('Unexpected preparation'))
    assert run.main(['--out',str(tmp_path/'absent')]) == 0
    assert not (tmp_path/'absent').exists()


def test_prepared_forcing_rejects_changed_source_identity_or_calendar(tmp_path,monkeypatch):
    domain,p,s,g,air,flows,a,stats = calendar_fixture();monkeypatch.setattr(m,'EDGES',a['edges'])
    identity = {'code_sha256':run.source_id()}
    inputs = {'california':(None,p,g,air,None)}
    monkeypatch.setattr(run,'load_inputs',lambda:(identity,inputs,s,{},{}))
    atomic_npz(tmp_path/'california.npz',**a)
    ready = {'identity':identity.copy(),'verified':True,
        'forcing_file_sha256':{'california':sha256(tmp_path/'california.npz')},
        'forcing_array_sha256':{'california':run.parent.geometry_rules.array_id(a)}}
    atomic_json(tmp_path/'manifest.json',ready)
    assert len(run.prepare(tmp_path)[0]['jobs']) == 6
    identity['code_sha256'] = 'changed'
    with pytest.raises(ValueError,match='stale'):
        run.prepare(tmp_path)
    identity['code_sha256'] = ready['identity']['code_sha256']
    (tmp_path/'california.npz').write_bytes(b'corrupted')
    with pytest.raises(ValueError,match='hash changed'):
        run.prepare(tmp_path)


def mocked_batch(monkeypatch):
    jobs = [dict(key='california_lift1_steady',region='california',amplitude=1.,timing='steady',anchor=True),
        dict(key='california_lift16_aligned',region='california',amplitude=16.,timing='aligned',anchor=False)]
    protocol = {'code_sha256':run.source_id(),'jobs':jobs}
    monkeypatch.setattr(run,'prepare',lambda *a:(protocol,{},None,{'california':None},{'california':None},{'california':None}))
    return protocol


def fake_row(folder,anchor_passed=True):
    folder.mkdir(parents=True,exist_ok=True);(folder/'year1.npz').write_bytes(b'manufactured evidence')
    atomic_json(folder/'config.json',{'manufactured':True})
    row = {'score':2.,'response':dict(coast_winter_mm=3.,coast_winter_reference_mm=4.,interior_winter_mm=1.),
        'koppen_fixed_surface_temperature':{'target_mediterranean_to_arid':.5},
        'settling':{'passed':True},'maximum_monthly_import_error_mm':0.,'anchor_check':{'passed':anchor_passed},
        'case_config_sha256':sha256(folder/'config.json'),
        'evidence_sha256':{'year1.npz':sha256(folder/'year1.npz')}}
    atomic_json(folder/'summary.json',row);return row


def test_batch_resumes_and_rejects_changed_evidence(tmp_path,monkeypatch):
    protocol = mocked_batch(monkeypatch);calls = []
    def case_runner(folder,job,*args):
        calls.append(job['key'])
        if len(calls) == 2:
            raise m.base.BudgetStop()
        return fake_row(folder)
    out = tmp_path/'run';preflight = tmp_path/'prepared'
    assert run.run(out,preflight,case_runner=case_runner)['status'] == 'budget_reached'
    assert run.run(out,preflight,case_runner=case_runner)['status'] == 'complete'
    assert calls.count('california_lift1_steady') == 1
    (out/'cases/california_lift1_steady/year1.npz').write_bytes(b'changed')
    assert run.run(out,preflight,case_runner=case_runner)['status'] == 'needs_diagnosis'
    protocol['changed'] = True
    with pytest.raises(ValueError,match='protocol changed'):
        run.run(out,preflight,case_runner=case_runner)


def test_failed_anchor_stops_before_mechanism_cases(tmp_path,monkeypatch):
    mocked_batch(monkeypatch);calls = []
    def case_runner(folder,job,*args):
        calls.append(job['key']);return fake_row(folder,anchor_passed=False)
    state = run.run(tmp_path/'run',tmp_path/'prepared',case_runner=case_runner)
    assert state['status'] == 'needs_diagnosis'
    assert calls == ['california_lift1_steady']


def test_completed_config_change_stops_before_more_work(tmp_path,monkeypatch):
    mocked_batch(monkeypatch)
    assert run.run(tmp_path/'run',tmp_path/'prepared',case_runner=lambda folder,*a:fake_row(folder))['status'] == 'complete'
    atomic_json(tmp_path/'run/cases/california_lift1_steady/config.json',{'changed':True})
    state = run.run(tmp_path/'run',tmp_path/'prepared',case_runner=lambda *a:pytest.fail('Must not run'))
    assert state['status'] == 'needs_diagnosis'


def test_time_budget_prevents_starting_a_case(tmp_path,monkeypatch):
    mocked_batch(monkeypatch);times = iter([0.,run.BUDGET_HOURS*3600+1])
    state = run.run(tmp_path/'run',tmp_path/'prepared',case_runner=lambda *a:pytest.fail('No time'),clock=lambda:next(times))
    assert state['status'] == 'budget_reached' and not state['cases']
