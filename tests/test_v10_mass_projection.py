"""Manufactured mass-projection and paired-weather tests, no regional runs."""
from dataclasses import replace
import numpy as np
import pytest
from experiments import v10_mass_projection as m, v10_coordinates as c
from scripts import check_v10_storm_delivery as runner, overnight_v10 as night
from rotclimate_v10.core import Domain, DAY, CENTERS, MONTH_DAYS
from rotclimate_v10.earth import EarthCase


def fixture(hill=True):
    h = np.zeros((4, 5))
    if hill:
        h[1:3, 2] = 2000.
    ps = c.P0*np.exp(-h/8400)
    mass, pressure, edges = c.pressure_grid(ps, 'hybrid')
    g = c.Geometry(mass, ps, pressure, -8400*np.log(pressure/c.P0), edges, 'hybrid')
    land = np.ones(h.shape, bool)
    d = Domain('california', land, h, np.full(h.shape, 37.), np.full((12,)+h.shape, 15.), 60000., 60000.)
    p = m.base.Profile(np.tile([-3., -10., -20., -45.], (12, 1)),
        np.tile([.006, .004, .002, .0004], (12, 1)),
        np.tile([4., 6., 8., 12.], (12, 1)), np.zeros((12, 4)), -8400*np.log(m.base.SIGMA))
    s = m.base.Settings(storm_rate_month=0)
    air = np.stack([m.base.targets(d, p, s, t)[0] for t in CENTERS])
    case = EarthCase(d, np.full(h.shape, -125.), np.full((12,)+h.shape, 20.),
        land.copy(), np.zeros(h.shape), np.zeros(h.shape, bool))
    return case, p, s, g, air


def test_projection_removes_known_gradient_with_open_boundary_half_cells():
    case, p, s, g, air = fixture()
    projector = m.ColumnProjection(case.domain, g)
    potential = np.random.default_rng(7).normal(0, 200000., case.domain.land.shape)
    gx, gy = projector.gradient(potential)
    result = projector.project(projector.mx*gx, projector.my*gy)
    np.testing.assert_allclose(result.x, 0, atol=1e-10)
    np.testing.assert_allclose(result.y, 0, atol=1e-10)


def test_divergence_free_projection_is_idempotent_and_preserves_face_shear():
    case, p, s, g, air = fixture()
    projector = m.ColumnProjection(case.domain, g)
    vx = np.array([3., 6., 9., 12.])[:, None, None]
    vy = np.array([1., -2., 3., -4.])[:, None, None]
    result = projector.project(projector.mx*vx, projector.my*vy)
    assert result.continuity < 1e-10
    rx = result.x/projector.mx;ry = result.y/projector.my
    for layer in range(1, 4):
        np.testing.assert_allclose(rx[layer]-rx[0], (vx[layer]-vx[0]).item(), atol=1e-12)
        np.testing.assert_allclose(ry[layer]-ry[0], (vy[layer]-vy[0]).item(), atol=1e-12)
    second = projector.project(result.x, result.y)
    np.testing.assert_allclose(second.x, result.x, atol=1e-10)
    np.testing.assert_allclose(second.y, result.y, atol=1e-10)


def test_projected_layer_continuity_preserves_constant_tracer_and_mse():
    case, p, s, g, air = fixture()
    flow = m.flow_at(case.domain, p, s, [], 0., g)
    dt = m.base.stable_step(flow, g.mass, case.domain)
    for value in (.002, 330000.):
        store = g.mass*value
        moved, exported = m.base.transport(store, g.mass, flow, np.full_like(store, value), dt, case.domain)
        np.testing.assert_allclose(moved, store, rtol=1e-14, atol=1e-6 if value > 1 else 1e-12)
        assert abs(exported) < 1e-5
    rng = np.random.default_rng(8)
    water = g.mass*rng.uniform(.001, .01, g.mass.shape)
    moved, exported = m.base.transport(water, g.mass, flow, np.full_like(water, .003), dt, case.domain)
    assert moved.min() >= 0
    assert abs((moved-water).sum(0).mean()+exported) < 1e-10


def test_sea_level_uniform_mass_preserves_old_forcing():
    case, p, s, g, air = fixture(False)
    s = replace(s, storm_rate_month=1.)
    storms = m.nested_events(case.domain, s, 41, None)
    expected = m.base.flow_at(case.domain, p, s, storms, float(CENTERS[0]))
    actual = m.flow_at(case.domain, p, s, storms, float(CENTERS[0]), g)
    np.testing.assert_allclose(actual.x, expected.x, atol=1e-9)
    np.testing.assert_allclose(actual.y, expected.y, atol=1e-9)
    np.testing.assert_allclose(actual.vertical, expected.vertical, atol=1e-14)


def test_projection_does_not_accelerate_thin_layers_like_fixed_flux():
    case, p, s, g, air = fixture()
    projector = m.ColumnProjection(case.domain, g)
    old = m.base.flow_at(case.domain, p, s, [], 0.)
    new = m.flow_at(case.domain, p, s, [], 0., g, projector)
    ou, ov = m.cell_velocity(old, projector);nu, nv = m.cell_velocity(new, projector)
    assert np.hypot(nu[1:3], nv[1:3]).max() < np.hypot(ou[1:3], ov[1:3]).max()
    assert projector.last_info['projected_column_divergence_max_kg_m2_s'] < 1e-10


def test_nested_weather_retains_old_anchor_and_gives_paired_event_sets():
    case, p, s, g, air = fixture()
    catalogues = {rate: m.nested_events(case.domain, replace(s, storm_rate_month=rate), 41, 300000.) for rate in (0, 1, 4, 8)}
    assert catalogues[0] == []
    assert catalogues[1] == m.base.events(case.domain, replace(s, storm_rate_month=1.), 41, 300000.)
    assert set(catalogues[1]) <= set(catalogues[4]) <= set(catalogues[8])
    assert catalogues[4] == m.nested_events(case.domain, replace(s, humidity_scale=.8, storm_rate_month=4.), 41, 300000.)
    assert catalogues[4] != m.nested_events(case.domain, replace(s, storm_rate_month=4.), 73, 300000.)


def test_nested_catalogue_has_correct_mean_event_rates():
    case, p, s, g, air = fixture()
    multiplier = float(np.sum((1+.75*np.cos(2*np.pi*(CENTERS/DAY-15)/365))*MONTH_DAYS/30))
    for rate in (1, 4, 8):
        counts = [len(m.nested_events(case.domain, replace(s, storm_rate_month=rate), seed, 300000.)) for seed in range(200)]
        expected = multiplier*rate
        assert abs(np.mean(counts)-expected) < 6*np.sqrt(expected/200)


def test_nested_weather_rejects_undeclared_rates():
    case, p, s, g, air = fixture()
    for rate in (-1., .5, 9.):
        with pytest.raises(ValueError):
            m.nested_events(case.domain, replace(s, storm_rate_month=rate), 41, None)


def test_projected_saturated_step_closes_water_energy_and_temperature():
    case, p, s, g, air = fixture()
    state = m.initial_state(case.domain, p, s, g, air)
    state.water += g.mass*.02;state.energy += m.base.LV*g.mass*.02
    flow = m.flow_at(case.domain, p, s, [], 0., g)
    dt = min(300., m.base.stable_step(flow, g.mass, case.domain))
    result = m.advance(state, case.domain, p, s, flow, dt, 0., air, geometry=g)
    assert result[1].max() > 0 and result[0].water.min() >= 0
    assert abs(result[4]['water_error_mm']) < 1e-9
    assert abs(result[4]['energy_error_j_m2']) < 1e-5
    assert result[-1] < 1e-9


def test_projected_year_monthly_resume_includes_projection_diagnostics(tmp_path, monkeypatch):
    case, p, s, g, air = fixture()
    p.eastward[:] = 0;p.northward[:] = 0
    monkeypatch.setattr(m.base, 'stable_step', lambda *a: DAY)
    t = m.interpolate_months(air, 0.)
    state = m.base.State(np.zeros_like(g.mass), g.mass*(m.base.CP*(t+273.15)+m.base.G*g.height_m), np.zeros(case.domain.land.shape))
    full = m.year(case.domain, p, s, 41, state, air, case.score_mask, g)
    stopped = [False]
    def save(*record):
        night.write_checkpoint(tmp_path, 1, record)
        if record[-1]['month'] == 2:
            stopped[0] = True
    with pytest.raises(m.base.BudgetStop):
        m.year(case.domain, p, s, 41, state, air, case.score_mask, g, save_month=save, should_stop=lambda: stopped[0])
    resumed = m.year(case.domain, p, s, 41, state, air, case.score_mask, g,
        checkpoint=night.read_checkpoint(tmp_path, 1, case.domain.land.shape))
    for name in ('water', 'energy', 'soil'):
        np.testing.assert_allclose(getattr(resumed[0], name), getattr(full[0], name), atol=1e-9)
    for key in ('max_projection_adjustment_m_s', 'max_raw_column_divergence_kg_m2_s'):
        assert resumed[-1]['diagnostics'][key] == full[-1]['diagnostics'][key]


def test_runner_read_only_default_and_declared_control_design(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *a: pytest.fail('Unexpected model launch'))
    out = tmp_path/'no_write'
    assert runner.main(['--out', str(out)]) == 0
    assert not out.exists()
    _, _, settings, _, _ = fixture()
    settings = replace(settings, humidity_scale=.8, storm_rate_month=1.)
    design = runner.design(settings)
    assert design['anchor'] == settings
    assert [v.storm_rate_month for k, v in design.items() if k != 'anchor'] == [0., 1., 4., 8.]
    assert all(v.humidity_scale == 1. for k, v in design.items() if k != 'anchor')


def test_ten_case_runner_resumes_completed_cases_and_refuses_changes(tmp_path, monkeypatch):
    case, p, s, g, air = fixture()
    settings = runner.design(replace(s, humidity_scale=.8, storm_rate_month=1.))
    names = ('california', 'iberia')
    inputs = dict.fromkeys(names, (case, p, g, air))
    expected = {'code_sha256': runner.source_id(), 'inputs': {r: runner.old.array_id(runner.old.geometry_arrays(g, air)) for r in names},
        'winds': {r: {'old_face_velocity_max_m_s_by_layer': [10]*4, 'new_face_velocity_max_m_s_by_layer': [8]*4} for r in names}}
    monkeypatch.setattr(runner, 'prepare', lambda *a: (expected, inputs, settings, {}))
    calls = []
    def fake(folder, *args):
        calls.append(folder.name)
        if len(calls) == 2:
            raise m.base.BudgetStop()
        return {'score': 1., 'annual_rain_ratio': 1., 'wet_reference_coverage': 1.,
            'eligible': True, 'settling': {'passed': True}, 'evidence_sha256': {}}
    out = tmp_path/'batch'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'budget_reached'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'complete'
    assert calls.count('california_anchor') == 1
    assert len(set(calls)) == 10
    expected['change'] = 'new scheme'
    with pytest.raises(ValueError, match='changed'):
        runner.run(out, tmp_path, case_runner=fake)
