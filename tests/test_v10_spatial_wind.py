"""Analytic interpolation, manufactured transport and bounded-run tests."""
from dataclasses import replace
import numpy as np
import pytest
from experiments import v10_spatial_wind as m, v10_forcing_audit as atmosphere
from scripts import check_v10_spatial_wind as runner, review_v10_storm_delivery as review
from tests.test_v10_mass_projection import fixture
from rotclimate_v10.core import DAY, CENTERS


def field_fixture():
    lat = np.array([40., 35., 30.])
    lon = np.array([0., 5., 350., 355.])
    pressure = np.array([1000., 700., 300.])
    unwrapped = (lon+180)%360-180
    values = np.arange(12.)[:, None, None, None]+4*np.log(pressure)[None, :, None, None]+3*lat[None, None, :, None]+2*unwrapped[None, None, None, :]
    return atmosphere.Field(values, pressure, lat, lon, np.arange(12.))


def test_bilinear_log_pressure_sampling_recovers_affine_field_across_meridian():
    field = field_fixture()
    lon = np.array([[-7., -1., 2.], [-6., 0., 4.]])
    lat = np.array([[31., 32., 33.], [36., 37., 38.]])
    p = np.array([[400., 500., 600.], [700., 800., 900.]])
    expected = np.arange(12.)[:, None, None]+4*np.log(p)+3*lat+2*lon
    np.testing.assert_allclose(m.sample_bilinear(field, lon, lat, p), expected, atol=1e-12)


def test_sampling_preserves_exact_native_edges_and_rejects_extrapolation():
    field = field_fixture()
    np.testing.assert_allclose(m.sample_bilinear(field, np.array([[-10., 5.]]), np.array([[30., 40.]]), np.array([[300., 1000.]])),
        np.stack([field.values[:, -1, -1, 2], field.values[:, 0, 0, 1]], axis=1)[:, None, :])
    for lon, lat, pressure in ((6., 35., 700.), (0., 41., 700.), (0., 35., 1100.)):
        with pytest.raises(ValueError, match='cover'):
            m.sample_bilinear(field, np.array([[lon]]), np.array([[lat]]), pressure)


@pytest.mark.parametrize('terrain', ['shallow', 'deep', 'none'])
def test_uniform_spatial_wind_exactly_matches_frozen_flow_with_active_storm(terrain):
    case, p, s, g, air = fixture()
    s = replace(s, terrain=terrain, storm_rate_month=1.)
    events = m.nested_events(case.domain, s, 41, None)
    wind = np.broadcast_to(np.stack([p.eastward, p.northward], axis=1)[:, :, :, None, None], (12, 2, 4)+case.domain.land.shape).copy()
    t = events[0].day*DAY
    actual = m.flow_at(case.domain, p, s, events, t, g, wind)
    expected = m.mass_model.flow_at(case.domain, p, s, events, t, g)
    for name in ('x', 'y', 'vertical'):
        np.testing.assert_allclose(getattr(actual, name), getattr(expected, name), atol=1e-10)


def test_spatial_wind_preserves_uniform_tracer_and_closes_saturated_step():
    case, p, s, g, air = fixture()
    wind = np.zeros((12, 2, 4)+case.domain.land.shape)
    y, x = np.indices(case.domain.land.shape)
    wind[:, 0] = (2+x)[None, None];wind[:, 1] = (1-y)[None, None]
    flow = m.flow_at(case.domain, p, s, [], 0., g, wind)
    dt = min(300., m.base.stable_step(flow, g.mass, case.domain))
    moved, exported = m.base.transport(g.mass*.003, g.mass, flow, np.full_like(g.mass, .003), dt, case.domain)
    np.testing.assert_allclose(moved, g.mass*.003, atol=1e-12)
    assert abs(exported) < 1e-10 and flow.continuity < 1e-10
    state = m.initial_state(case.domain, p, s, g, air)
    state.water += g.mass*.02;state.energy += m.base.LV*g.mass*.02
    result = m.advance(state, case.domain, p, s, flow, dt, 0., air, geometry=g)
    assert result[0].water.min() >= 0 and result[1].max() > 0
    assert abs(result[4]['water_error_mm']) < 1e-9
    assert abs(result[4]['energy_error_j_m2']) < 1e-5 and result[-1] < 1e-9


def test_manufactured_year_matches_frozen_driver_and_resumes_months(tmp_path, monkeypatch):
    case, p, s, g, air = fixture()
    p.eastward[:] = 0.;p.northward[:] = 0.
    wind = np.zeros((12, 2, 4)+case.domain.land.shape)
    monkeypatch.setattr(m.base, 'stable_step', lambda *a: DAY)
    state = m.initial_state(case.domain, p, s, g, air)
    expected = m.mass_model.year(case.domain, p, s, 41, state, air, case.score_mask, g)
    stopped = [False]
    def save(*record):
        runner.night.write_checkpoint(tmp_path, 1, record)
        if record[-1]['month'] == 2:
            stopped[0] = True
    with pytest.raises(m.base.BudgetStop):
        m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind,
            save_month=save, should_stop=lambda: stopped[0])
    result = m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind,
        checkpoint=runner.night.read_checkpoint(tmp_path, 1, case.domain.land.shape))
    for field in ('water', 'energy', 'soil'):
        np.testing.assert_allclose(getattr(result[0], field), getattr(expected[0], field), atol=1e-9)
    for i in (1, 2, 3):
        np.testing.assert_allclose(result[i], expected[i], atol=1e-10)
    assert result[-1]['diagnostics'] == expected[-1]['diagnostics']


def test_paired_rain_vectors_keep_coastal_and_interior_seasonal_responses_separate():
    case, p, s, g, air = fixture(False)
    case.coast_distance_km[:] = 200.;case.coast_distance_km[:, :2] = 50.;case.coast_distance_km[:, 3:] = 400.
    reference = review.rain_vector(case, case.observed_rain_mm)
    dry = review.rain_vector(case, np.zeros_like(case.observed_rain_mm))
    assert reference['skill_vs_zero_rain'] == 1. and dry['skill_vs_zero_rain'] == 0.
    assert dry['wettest_five_percent_rain_share'] == 0.
    rain = case.observed_rain_mm.copy()
    rain[review.WINTER, :, :2] += 10.
    changed = review.rain_vector(case, rain)
    assert changed['coast_winter_mm']-reference['coast_winter_mm'] == 60.
    assert changed['interior_winter_mm'] == reference['interior_winter_mm']
    assert changed['coast_summer_mm'] == reference['coast_summer_mm']


def test_default_never_launches_or_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *a: pytest.fail('Unexpected seasonal integration'))
    out = tmp_path/'not_created'
    assert runner.main(['--out', str(out)]) == 0
    assert not out.exists()


def test_four_case_resume_reuses_baselines_and_refuses_protocol_change(tmp_path, monkeypatch):
    case, profile, s, g, air = fixture()
    wind = np.zeros((12, 2, 4)+case.domain.land.shape)
    inputs = dict.fromkeys(('california', 'iberia'), (case, profile, g, air, wind))
    settings = {'humidity_08': replace(s, humidity_scale=.8), 'humidity_10': s}
    summary = {'score': 2., 'annual_rain_ratio': 1., 'wet_reference_coverage': 1.,
        'settling': {'passed': True}, 'eligible': True, 'evidence_sha256': {}}
    baselines = {r+'_'+k: summary for r in inputs for k in settings}
    expected = {'code_sha256': runner.source_id(), 'inputs': {r: runner.old.old.array_id(runner.input_arrays(g, air, wind)) for r in inputs}}
    monkeypatch.setattr(runner, 'prepare', lambda *a: (expected, inputs, settings, baselines))
    calls = []
    def fake(folder, *args):
        calls.append(folder.name)
        if len(calls) == 2:
            raise m.base.BudgetStop()
        return summary.copy()
    out = tmp_path/'batch'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'budget_reached'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'complete'
    assert calls.count('california_humidity_08') == 1 and len(set(calls)) == 4
    expected['change'] = 'new protocol'
    with pytest.raises(ValueError, match='changed'):
        runner.run(out, tmp_path, case_runner=fake)
