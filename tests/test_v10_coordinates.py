"""Manufactured coordinate/transport/checkpoint tests; no regional integrations."""
from dataclasses import replace
import numpy as np
import pytest
from experiments import v10_coordinates as m, v10_column as base, v10_upper_air as old
from scripts import check_v10_coordinates as runner, overnight_v10 as night
from scripts.diagnose_v10_upper_air import ridge_probe
from rotclimate_v10.core import Domain, CENTERS, DAY
from rotclimate_v10.earth import EarthCase


def fixture(mode='sigma'):
    h = np.zeros((3, 4))
    h[1, 1:3] = 1500
    ps = m.P0*np.exp(-h/8400)
    mass, pressure, edges = m.pressure_grid(ps, mode)
    z = -8400*np.log(pressure/m.P0)
    g = m.Geometry(mass, ps, pressure, z, edges, mode)
    land = np.ones(h.shape, bool)
    d = Domain('california', land, h, np.full(h.shape, 37.), np.full((12,)+h.shape, 15.), 60000., 60000.)
    p = base.Profile(np.tile([-3., -10., -20., -45.], (12, 1)),
        np.tile([.006, .004, .002, .0004], (12, 1)),
        np.tile([4., 6., 8., 12.], (12, 1)), np.zeros((12, 4)),
        -8400*np.log(base.SIGMA))
    s = base.Settings(storm_rate_month=0)
    air = np.stack([base.targets(d, p, s, t)[0] for t in CENTERS])
    case = EarthCase(d, np.full(h.shape, -125.), np.full((12,)+h.shape, 20.),
        land.copy(), np.zeros(h.shape), np.zeros(h.shape, bool))
    return case, p, s, g, air


def test_sea_level_pressure_grids_match_exactly():
    ps = np.full((2, 3), m.P0)
    sigma = m.pressure_grid(ps, 'sigma')
    hybrid = m.pressure_grid(ps, 'hybrid')
    for a, b in zip(sigma, hybrid):
        np.testing.assert_allclose(a, b, rtol=1e-15)


@pytest.mark.parametrize('mode', ['sigma', 'hybrid'])
def test_mass_pressure_order_and_column_sum(mode):
    ps = np.array([[68000., 80000.], [95000., 102000.]])
    mass, pressure, edges = m.pressure_grid(ps, mode)
    assert (mass > 0).all()
    assert (np.diff(pressure, axis=0) < 0).all()
    np.testing.assert_allclose(mass.sum(0), ps/base.G)
    assert (pressure < ps).all()
    if mode == 'hybrid':
        np.testing.assert_array_equal(edges[-2], m.TRANSITION_PA)
        np.testing.assert_array_equal(pressure[-1], .5*m.TRANSITION_PA)


def test_hybrid_rejects_ground_intersecting_upper_interface():
    with pytest.raises(ValueError, match='Ground'):
        m.pressure_grid(np.array([[m.TRANSITION_PA]]), 'hybrid')


def test_hydrostatic_surface_pressure_inversion_and_lowest_interval_extrapolation():
    p = np.array([100000., 92500., 85000., 70000., 50000.])
    heights = -8400*np.log(p/m.P0)[:, None, None]*np.ones((1, 2, 2))
    ground = np.array([[-20., 0.], [1500., 3000.]])
    inferred = m.surface_pressure_from_heights(ground, p, heights)
    np.testing.assert_allclose(inferred, m.P0*np.exp(-ground/8400), rtol=1e-14)
    with pytest.raises(ValueError, match='increase'):
        m.surface_pressure_from_heights(ground, p, heights[::-1])


def test_dry_ridge_isolates_imposed_upper_path_without_vertical_exchange():
    for mode in ('sigma', 'hybrid'):
        flat = ridge_probe(mode, False)
        assert flat['layer_absolute_change_max_c'][-1] < 1e-10
    sigma = ridge_probe('sigma')
    hybrid = ridge_probe('hybrid')
    assert sigma['upper_interface_vertical_flux_max'] == 0
    assert hybrid['upper_interface_vertical_flux_max'] == 0
    assert sigma['layer_cooling_max_c'][-1] > .05
    assert hybrid['layer_cooling_max_c'][-1] < 1e-10
    assert abs(sigma['energy_budget_error_j_m2']) < 1e-5
    assert abs(hybrid['energy_budget_error_j_m2']) < 1e-5


@pytest.mark.parametrize('wet', [False, True])
def test_sigma_backend_matches_frozen_step_with_identical_geometry_and_targets(wet):
    case, p, s, g, air = fixture()
    d = case.domain
    # Factory geometry here uses the exact frozen isothermal height relation.
    state = base.initial_state(d, p, s)
    if wet:
        state.water += g.mass*.02
        state.energy += base.LV*g.mass*.02
    flow = base.flow_at(d, p, s, [], 0.)
    dt = min(300., base.stable_step(flow, g.mass, d))
    expected = old.advance(state, d, p, s, flow, dt, 0., air)
    actual = m.advance(state, d, p, s, flow, dt, 0., air, geometry=g)
    for name in ('water', 'energy', 'soil'):
        np.testing.assert_allclose(getattr(actual[0], name), getattr(expected[0], name), rtol=1e-12, atol=1e-6)
    np.testing.assert_allclose(actual[1], expected[1], atol=1e-10)
    np.testing.assert_allclose(actual[2], expected[2], atol=1e-10)
    assert actual[-1] < 1e-9


def test_hybrid_saturated_step_closes_budgets_and_temperature_ledger():
    case, p, s, g, air = fixture('hybrid')
    state = m.initial_state(case.domain, p, s, g, air)
    state.water += g.mass*.02
    state.energy += base.LV*g.mass*.02
    flow = base.flow_at(case.domain, p, s, [], 0.)
    dt = min(300., base.stable_step(flow, g.mass, case.domain))
    result = m.advance(state, case.domain, p, s, flow, dt, 0., air, geometry=g)
    assert result[0].water.min() >= 0 and result[1].max() > 0
    assert abs(result[4]['water_error_mm']) < 1e-9
    assert abs(result[4]['energy_error_j_m2']) < 1e-5
    assert result[-1] < 1e-9
    with pytest.raises(ValueError, match='CFL'):
        m.advance(state, case.domain, p, s, flow, base.stable_step(flow, g.mass, case.domain)*1.1, 0., air, geometry=g)


def test_hybrid_diagnostic_checkpoint_resume(tmp_path, monkeypatch):
    case, p, s, g, air = fixture('hybrid')
    p.eastward[:] = 0
    p.northward[:] = 0
    s = replace(s, terrain='none')
    monkeypatch.setattr(base, 'stable_step', lambda *args: DAY)
    t = m.interpolate_months(air, 0.)
    initial = base.State(np.zeros_like(g.mass), g.mass*(base.CP*(t+273.15)+base.G*g.height_m), np.zeros(case.domain.land.shape))
    complete = m.year(case.domain, p, s, 41, initial, air, case.score_mask, g)
    interrupted = [False]
    def save(*record):
        night.write_checkpoint(tmp_path, 1, record)
        if record[-1]['month'] == 2:
            interrupted[0] = True
    with pytest.raises(base.BudgetStop):
        m.year(case.domain, p, s, 41, initial, air, case.score_mask, g,
            save_month=save, should_stop=lambda: interrupted[0])
    partial = night.read_checkpoint(tmp_path, 1, case.domain.land.shape)
    resumed = m.year(case.domain, p, s, 41, initial, air, case.score_mask, g, checkpoint=partial)
    for name in ('water', 'energy', 'soil'):
        np.testing.assert_allclose(getattr(resumed[0], name), getattr(complete[0], name), atol=1e-9)
    np.testing.assert_allclose(resumed[-1]['diagnostics']['temperature_changes_scored_land_c'],
        complete[-1]['diagnostics']['temperature_changes_scored_land_c'], atol=1e-9)
    assert abs(resumed[-1]['budget']['annual_water_error_mm']) < 1e-6


def test_input_array_hash_detects_geometry_and_shape_changes():
    case, p, s, g, air = fixture()
    arrays = runner.geometry_arrays(g, air)
    before = runner.array_id(arrays)
    arrays['height_m'] = arrays['height_m'].copy()
    arrays['height_m'][0, 0, 0] += 1
    assert runner.array_id(arrays) != before
    arrays['height_m'] = arrays['height_m'].reshape(4, 2, 6)
    assert runner.array_id(arrays) != before


def test_runner_default_never_launches_or_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *a: pytest.fail('Unexpected run'))
    out = tmp_path/'no_write'
    assert runner.main(['--out', str(out)]) == 0
    assert not out.exists()


def test_four_case_batch_resumes_and_refuses_changed_manifest(tmp_path, monkeypatch):
    case, p, s, g, air = fixture()
    keys = ['california_sigma', 'california_hybrid', 'iberia_sigma', 'iberia_hybrid']
    expected = {'code_sha256': runner.source_id(), 'cases': {key: {'array_sha256': runner.array_id(runner.geometry_arrays(g, air)), 'wind': {'no_storm_speed_max_m_s_by_layer': [10]*4}} for key in keys}}
    monkeypatch.setattr(runner, 'prepare', lambda *a: (expected, {key: (case, p, g, air) for key in keys}, s))
    calls = []
    stop_once = [True]
    def fake(folder, *args):
        calls.append(folder.name)
        if len(calls) == 2 and stop_once[0]:
            stop_once[0] = False
            raise base.BudgetStop()
        return {'score': 1., 'annual_rain_ratio': 1., 'wet_reference_coverage': 1., 'eligible': True,
            'settling': {'passed': True}, 'evidence_sha256': {}}
    out = tmp_path/'batch'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'budget_reached'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'complete'
    assert calls.count(keys[0]) == 1
    expected['change'] = 'new physics'
    with pytest.raises(ValueError, match='changed'):
        runner.run(out, tmp_path, case_runner=fake)
