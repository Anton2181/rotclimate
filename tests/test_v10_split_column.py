"""Controlled split flow, matched water, regression and five-layer resume."""
from dataclasses import replace
import json
import numpy as np
import pytest
from experiments import v10_split_column as m
from scripts import check_v10_split_column as runner
from tests.test_v10_mass_projection import fixture
from rotclimate_v10.core import DAY
from rotclimate_v10.earth import atomic_json, sha256


def five_fixture(hill=True):
    case, p, s, old_g, old_air = fixture(hill)
    edges = np.concatenate([old_g.interfaces_pa[:4], np.full((1,)+case.domain.land.shape, 30000.), np.zeros((1,)+case.domain.land.shape)])
    mass = -np.diff(edges, axis=0)/m.base.G;pressure = .5*(edges[:-1]+edges[1:])
    height = np.concatenate([old_g.height_m[:3], -8400*np.log(pressure[3:]/m.coordinates.P0)])
    g = m.coordinates.Geometry(mass, old_g.surface_pressure.copy(), pressure, height, edges, 'hybrid_split300')
    air = np.concatenate([old_air[:, :3], old_air[:, 3:]+12., old_air[:, 3:]-25.], axis=1)
    mixing = np.concatenate([p.mixing_ratio[:, :3], np.full((12, 1), .001), np.full((12, 1), .00001)], axis=1)
    profile = m.Profile(np.zeros((12, 5)), mixing,
        np.concatenate([p.eastward[:, :3], np.repeat(p.eastward[:, 3:], 2, axis=1)], axis=1),
        np.concatenate([p.northward[:, :3], np.repeat(p.northward[:, 3:], 2, axis=1)], axis=1), height.mean(axis=(1, 2)))
    wind = np.full((12, 2, 4)+case.domain.land.shape, 2.)
    return case, profile, s, g, air, (old_g, p, old_air, wind)


@pytest.mark.parametrize('mode', ['uniform', 'spatial'])
def test_split_flow_preserves_lower_and_aggregate_upper_face_flux(mode):
    case, p, s, g, air, circulation = five_fixture()
    old_g, old_p, old_air, wind = circulation
    coarse = m.core.flow_at(case.domain, old_p, s, [], 0., old_g, wind, wind_mode=mode)
    split = m.flow_at(case.domain, p, s, [], 0., g, wind, wind_mode=mode, circulation=circulation)
    assert split.continuity < 1e-10
    for name in ('x', 'y'):
        a,b = getattr(split, name),getattr(coarse, name)
        np.testing.assert_array_equal(a[:3], b[:3])
        np.testing.assert_allclose(a[3:].sum(0), b[3], atol=1e-10)
    np.testing.assert_array_equal(split.vertical[:3], coarse.vertical)
    np.testing.assert_allclose(g.mass.sum(0), old_g.mass.sum(0), atol=1e-10)


def test_column_matched_boundary_preserves_original_local_water_after_caps():
    case, p, s, g, air, circulation = five_fixture()
    old_g, old_p, old_air, wind = circulation
    r = m.boundary_ratio(case.domain, p, s, g, air, 0., 'column_matched', circulation)
    old = m.boundary_ratio(case.domain, old_p, s, old_g, old_air, 0.)
    np.testing.assert_allclose((g.mass*r).sum(0), (old_g.mass*old).sum(0), atol=1e-12)
    assert (r <= .95*m.base.saturation(air[0], g.pressure)+1e-15).all()
    p.mixing_ratio[:] = 0.
    with pytest.raises(ValueError, match='upward scaling'):
        m.boundary_ratio(case.domain, p, s, g, air, 0., 'column_matched', circulation)


def test_four_layer_step_is_exact_frozen_regression():
    case, p, s, g, air = fixture()
    state = m.initial_state(case.domain, p, s, g, air)
    expected_state = m.core.initial_state(case.domain, p, s, g, air)
    for name in ('water', 'energy', 'soil'):
        np.testing.assert_array_equal(getattr(state, name), getattr(expected_state, name))
    wind = np.ones((12, 2, 4)+case.domain.land.shape)
    flow = m.flow_at(case.domain, p, s, [], 0., g, wind)
    dt = min(300., m.base.stable_step(flow, g.mass, case.domain))
    new = m.advance(state, case.domain, p, s, flow, dt, 0., air, geometry=g)
    old = m.core.advance(state, case.domain, p, s, flow, dt, 0., air, geometry=g)
    for name in ('water', 'energy', 'soil'):
        np.testing.assert_array_equal(getattr(new[0], name), getattr(old[0], name))
    for a,b in zip(new[1:4], old[1:4]):
        np.testing.assert_array_equal(a,b)
    assert new[4] == old[4]


def test_five_layer_dry_constant_theta_preserves_pressure_law():
    case, p, s, g, air, circulation = five_fixture()
    p.mixing_ratio[:] = 0.
    theta = 320.
    t = theta*m.core.exner(g.pressure)-273.15
    air = np.broadcast_to(t, (12,)+t.shape).copy()
    state = m.base.State(np.zeros_like(g.mass), g.mass*(m.base.CP*(t+273.15)+m.base.G*g.height_m), np.zeros(case.domain.land.shape))
    flow = m.flow_at(case.domain, p, s, [], 0., g, circulation[3], circulation=circulation)
    dt = min(60., m.base.stable_step(flow, g.mass, case.domain))
    result = m.advance(state, case.domain, p, s, flow, dt, 0., air, physics=False, geometry=g)
    np.testing.assert_allclose(result[2], t, atol=1e-10)
    assert abs(result[4]['theta_transport_error_kg_k_m2']) < 1e-7
    assert abs(result[4]['energy_error_j_m2']) < 1e-5


def test_five_layer_moist_step_closes_ledgers_and_shapes():
    case, p, s, g, air, circulation = five_fixture()
    state = m.initial_state(case.domain, p, s, g, air)
    state.water += g.mass*.02;state.energy += m.base.LV*g.mass*.02
    flow = m.flow_at(case.domain, p, s, [], 0., g, circulation[3], circulation=circulation)
    result = m.advance(state, case.domain, p, s, flow, 60., 0., air, geometry=g)
    assert result[0].water.min() >= 0 and result[1].max() > 0
    assert result[5].shape == g.mass.shape and result[6].shape == (6,)+g.mass.shape
    assert abs(result[4]['water_error_mm']) < 1e-9
    assert abs(result[4]['energy_error_j_m2']) < 1e-5 and result[-1] < 1e-9
    assert result[4]['boundary_export_gross_mm']-result[4]['boundary_import_gross_mm'] == pytest.approx(result[4]['boundary_export_mm'], abs=1e-12)
    with pytest.raises(ValueError, match='thermal shape'):
        m.advance(state, case.domain, p, s, flow, 60., 0., air[:, :4], geometry=g)


@pytest.mark.parametrize('count', [4, 5])
def test_manufactured_year_regression_and_five_layer_serialized_resume(tmp_path, monkeypatch, count):
    if count == 4:
        case, p, s, g, air = fixture(False);circulation = None
        wind = np.full((12, 2, 4)+case.domain.land.shape, 2.)
    else:
        case, p, s, g, air, circulation = five_fixture(False);wind = circulation[3]
    edges = np.arange(13, dtype=float)*DAY
    monkeypatch.setattr(m, 'EDGES', edges);monkeypatch.setattr(m.core, 'EDGES', edges)
    initial = m.initial_state(case.domain, p, s, g, air)
    full = m.year(case.domain, p, s, 41, initial, air, case.score_mask, g, wind, circulation=circulation)
    if count == 4:
        old = m.core.year(case.domain, p, s, 41, initial, air, case.score_mask, g, wind)
        for name in ('water', 'energy', 'soil'):
            np.testing.assert_array_equal(getattr(old[0], name), getattr(full[0], name))
        for a,b in zip(old[1:4], full[1:4]):
            np.testing.assert_array_equal(a,b)
        assert full[-1] == old[-1]
    stopped = [False]
    def save(*record):
        runner.write_checkpoint(tmp_path, 1, record)
        if record[-1]['month'] == 4:
            stopped[0] = True
    with pytest.raises(m.base.BudgetStop):
        m.year(case.domain, p, s, 41, initial, air, case.score_mask, g, wind,
            circulation=circulation, save_month=save, should_stop=lambda: stopped[0])
    partial = runner.read_checkpoint(tmp_path, 1, case.domain.land.shape, count=count)
    assert partial[-1]['month'] == 4
    result = m.year(case.domain, p, s, 41, initial, air, case.score_mask, g, wind, checkpoint=partial, circulation=circulation)
    for name in ('water', 'energy', 'soil'):
        np.testing.assert_array_equal(getattr(result[0], name), getattr(full[0], name))
    for a,b in zip(result[1:4], full[1:4]):
        np.testing.assert_array_equal(a,b)
    assert result[-1] == full[-1]
    runner.write_checkpoint(tmp_path, 1, result, completed=True)
    loaded = runner.read_checkpoint(tmp_path, 1, case.domain.land.shape, count=count, completed=True)
    np.testing.assert_array_equal(loaded[0].water, full[0].water)
    (tmp_path/'year1.npz').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='integrity'):
        runner.read_checkpoint(tmp_path, 1, case.domain.land.shape, count=count, completed=True)


def test_settling_checks_fifth_water_layer():
    case, p, s, g, air, circulation = five_fixture()
    old = m.initial_state(case.domain, p, s, g, air)
    new = m.base.State(old.water.copy(), old.energy.copy(), old.soil.copy())
    new.water[4] += 2.;new.energy[4] += 2*m.base.LV
    rain = np.zeros((12,)+case.domain.land.shape)
    a = (old, rain, air, air, {});b = (new, rain, air, air, {})
    check = runner.settling(a,b,case,g)
    assert check['changes']['water_store_p95_mm'] == 2. and not check['passed']


def test_default_is_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *a: pytest.fail('Unexpected seasonal run'))
    assert runner.main(['--out', str(tmp_path/'absent')]) == 0
    assert not (tmp_path/'absent').exists()


def mock_batch(monkeypatch):
    case, p, s, g, air, circulation = five_fixture()
    inputs = {'california_dry': (case,p,g,air,circulation), 'california_rh300': (case,p,g,air,circulation)}
    jobs = [{'key': f'california_uniform_{variant}', 'region': 'california', 'wind': 'uniform', 'variant': variant, 'seed': 41}
        for variant in ('split_dry', 'split_rh300')]
    protocol = {'code_sha256': runner.source_id(), 'jobs': jobs,
        'inputs': {key: runner.geometry_rules.array_id(runner.input_arrays(g,air,p,circulation)) for key in inputs}}
    baselines = {'california_uniform': {'score': 30., 'annual_rain_ratio': .1}}
    monkeypatch.setattr(runner, 'prepare', lambda: (protocol, inputs, {'uniform':s}, baselines))
    return protocol


def test_batch_monthly_budget_resume_and_changed_evidence_rejected(tmp_path, monkeypatch):
    protocol = mock_batch(monkeypatch);calls=[]
    def fake(folder, job, *args):
        calls.append(job['key'])
        if len(calls) == 2:
            raise m.base.BudgetStop()
        folder.mkdir(parents=True, exist_ok=True);(folder/'year1.npz').write_bytes(b'manufactured evidence')
        row = {'score': 29., 'annual_rain_ratio': .2, 'response': {'coast_winter_mm': 20.},
            'settling': {'passed': True}, 'eligible': False, 'evidence_sha256': {'year1.npz':sha256(folder/'year1.npz')}}
        atomic_json(folder/'summary.json', row)
        return row
    out=tmp_path/'out'
    assert runner.run(out, case_runner=fake)['status'] == 'budget_reached'
    assert runner.run(out, case_runner=fake)['status'] == 'complete'
    assert calls.count('california_uniform_split_dry') == 1
    (out/'cases/california_uniform_split_dry/year1.npz').write_bytes(b'corrupted')
    assert runner.run(out, case_runner=fake)['status'] == 'needs_diagnosis'
    assert len(calls) == 3
    protocol['changed'] = True
    with pytest.raises(ValueError, match='protocol changed'):
        runner.run(out, case_runner=fake)


def test_global_budget_prevents_starting_a_case(tmp_path, monkeypatch):
    mock_batch(monkeypatch)
    times=iter([0.,1.5*3600+1])
    state=runner.run(tmp_path/'out',case_runner=lambda *a:pytest.fail('Already out of time'),clock=lambda:next(times))
    assert state['status'] == 'budget_reached' and not state['cases']
