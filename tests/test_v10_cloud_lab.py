"""Analytic limits and conservative cloud-process comparisons; manufactured only."""
from types import SimpleNamespace
import numpy as np
import pytest
from experiments import v10_cloud_lab as lab
from experiments import v10_cloud_column_lab as column
from scripts import audit_v10_cloud_lab as audit


def rain(result):
    return result['cumulative_rain_kg_per_kg_initial_dry_air'][-1]


@pytest.mark.parametrize('intervals', [1, 7, 256])
def test_dry_path_matches_poisson_and_explicit_pressure_work(intervals):
    initial = lab.Air(20., 0.)
    result = lab.ascend(initial, 100000., 60000., intervals)
    expected = (initial.temperature_c+273.15)*.6**lab.KAPPA-273.15
    assert result['temperature_c'][-1, 0] == pytest.approx(expected, abs=1e-10)
    assert rain(result) == 0.
    assert result['pressure_work_j_per_kg_initial_dry_air'] == pytest.approx(lab.base.CP*(expected-20.), abs=1e-7)
    returned = lab.dry_descent(lab.Air(expected, 0.), 60000., 100000.)
    assert returned.temperature_c == pytest.approx(20., abs=1e-10)


@pytest.mark.parametrize('case', audit.LIFTS, ids=lambda case: case.key)
def test_refined_path_matches_independently_integrated_thermodynamics(case):
    air = case.air()
    reference = lab.continuous_reference(air, case.start_pa, case.end_pa)
    fine = lab.ascend(air, case.start_pa, case.end_pa, 256)
    assert rain(fine) == pytest.approx(reference['rain_kg_per_kg_dry_air'], abs=5e-6)
    assert fine['temperature_c'][-1, 0] == pytest.approx(reference['temperature_c'], abs=.02)
    assert abs(fine['water_error_kg_per_kg_dry_air']) < 1e-11
    assert abs(fine['enthalpy_error_j_per_kg_dry_air']) < 1e-6


def test_saturated_start_reference_does_not_need_a_sign_changing_root():
    air = lab.Air(25., lab.saturation(25., 100000.))
    reference = lab.continuous_reference(air, 100000., 60000.)
    assert reference['first_saturation_pressure_pa'] == 100000.
    assert reference['rain_kg_per_kg_dry_air'] > 0.
    fine = lab.ascend(air, 100000., 60000., 256)
    assert rain(fine) == pytest.approx(reference['rain_kg_per_kg_dry_air'], abs=5e-6)
    with pytest.raises(ValueError, match='supersaturated'):
        lab.continuous_reference(lab.Air(25., air.vapor_ratio*1.01), 100000., 60000.)


def test_exchange_conserves_finite_populations_and_does_not_mutate_inputs():
    t = np.array([20., -10.]); q = np.array([.012, .001]); m = np.array([.2, .8])
    original = (t.copy(), q.copy(), m.copy())
    after_t, after_q = lab.exchange(t, q, m, .6)
    assert np.dot(m, after_q) == pytest.approx(np.dot(m, q), abs=1e-16)
    assert np.dot(m, lab.enthalpy(after_t, after_q)) == pytest.approx(np.dot(m, lab.enthalpy(t, q)), abs=1e-9)
    for actual, before in zip((t, q, m), original):
        np.testing.assert_array_equal(actual, before)
    mixed_t, mixed_q = lab.exchange(t, q, m, 1.)
    np.testing.assert_allclose(mixed_t, np.dot(m, t), atol=1e-14, rtol=0)
    np.testing.assert_allclose(mixed_q, np.dot(m, q), atol=1e-16, rtol=0)


@pytest.mark.parametrize('intervals', [1, 7, 256])
def test_total_mixing_exposure_is_independent_of_pressure_substeps(intervals):
    # Unsaturated, isobaric: the exact population anomaly decays by 1-chi.
    fraction = .2; chi = .7
    result = lab.ascend_pair(lab.Air(20., .001), lab.Air(25., .002), fraction, 100000., 100000., intervals, chi)
    expected_q = .001*fraction+.002*(1-fraction)
    expected_t = 20.*fraction+25.*(1-fraction)
    np.testing.assert_allclose(result['vapor_ratio'][-1], expected_q+(1-chi)*(np.array([.001, .002])-expected_q), atol=1e-15, rtol=0)
    np.testing.assert_allclose(result['temperature_c'][-1], expected_t+(1-chi)*(np.array([20., 25.])-expected_t), atol=1e-10, rtol=0)
    assert rain(result) == 0.


@pytest.mark.parametrize('chi', [0., 1.])
def test_pair_endpoints_recover_independent_or_homogeneous_ascent(chi):
    a = lab.Air(20., .7*lab.saturation(20., 100000.)); b = lab.Air(30., .001)
    fraction = .2
    result = lab.ascend_pair(a, b, fraction, 100000., 80000., 64, chi)
    if chi == 0:
        first = lab.ascend(a, 100000., 80000., 64)
        second = lab.ascend(b, 100000., 80000., 64)
        expected = fraction*rain(first)+(1-fraction)*rain(second)
    else:
        mixed = lab.Air(fraction*a.temperature_c+(1-fraction)*b.temperature_c, fraction*a.vapor_ratio+(1-fraction)*b.vapor_ratio)
        first = lab.ascend(mixed, 100000., 80000., 64)
        expected = rain(first)
        np.testing.assert_allclose(result['temperature_c'][-1], first['temperature_c'][-1, 0], atol=1e-9, rtol=0)
    assert rain(result) == pytest.approx(expected, abs=1e-11)


def test_saturated_warm_cold_mixing_creates_condensate_without_ascent():
    a = lab.Air(20., lab.saturation(20., 90000.)); b = lab.Air(0., lab.saturation(0., 90000.))
    separate = lab.ascend_pair(a, b, .5, 90000., 90000., 1, 0.)
    mixed = lab.ascend_pair(a, b, .5, 90000., 90000., 1, 1.)
    assert rain(separate) < 1e-12
    assert rain(mixed) > .0007
    assert mixed['pressure_work_j_per_kg_initial_dry_air'] == 0.
    assert abs(mixed['enthalpy_error_j_per_kg_dry_air']) < 1e-6


def test_endpoint_law_recovers_frozen_parcel_dose_without_relaxation():
    # Five-layer artificial column, no real-region fixture or integration.
    p = np.array([100000., 80000., 65000., 50000., 35000.])[:, None, None]
    t = np.array([25., 10., -5., -20., -40.])[:, None, None]
    q = .8*lab.base.saturation(t, p); mass = np.full_like(p, 1000.); z = np.zeros_like(p)
    state = lab.base.State(mass*q, mass*lab.enthalpy(t, q), np.zeros((1, 1)))
    geometry = SimpleNamespace(mass=mass, pressure=p, height_m=z)
    settings = SimpleNamespace(relaxation_lower_days=np.inf, relaxation_upper_days=np.inf)
    vertical = np.full((4, 1, 1), .1)
    actual = lab.frozen.ascending_condensate(state, settings, SimpleNamespace(vertical=vertical), 60., geometry, t, 'parcel_all')
    for k in range(4):
        result = lab.ascend(lab.Air(float(t[k, 0, 0]), float(q[k, 0, 0])), float(p[k, 0, 0]), float(p[k+1, 0, 0]), 1)
        assert actual[k+1, 0, 0] == pytest.approx(6.*rain(result), abs=1e-10)


@pytest.mark.parametrize('args', [(100000., 110000., 1), (0., 10000., 1), (100000., 80000., True), (100000., 80000., 1.5)])
def test_bad_pressure_path_rejected(args):
    with pytest.raises(ValueError):
        lab.pressure_path(*args)


def test_bad_water_and_mixing_rejected():
    with pytest.raises(ValueError):
        lab.ascend(lab.Air(20., -.01), 100000., 80000., 1)
    with pytest.raises(ValueError):
        lab.ascend_pair(lab.Air(20., .001), lab.Air(20., .001), .2, 100000., 80000., 1, np.nan)


@pytest.mark.parametrize('layers', [8, 32, 128, 256])
def test_column_refinement_preserves_initial_integrals_and_nested_fluxes(layers):
    _, old_g, old, old_flow = column.fixture(4)
    _, g, initial, flow = column.fixture(layers)
    ratio = layers//4
    for fine, coarse, atol in ((g.mass, old_g.mass, 1e-10), (initial.water, old.water, 1e-10), (initial.energy, old.energy, 1e-5), (flow.x, old_flow.x, 1e-10)):
        np.testing.assert_allclose(fine.reshape((4, ratio)+fine.shape[1:]).sum(1), coarse, atol=atol, rtol=0)
    np.testing.assert_allclose(flow.vertical[ratio-1::ratio], old_flow.vertical, atol=1e-14, rtol=0)
    # Closed columns carry equal/opposite ascent and have no exterior flux.
    np.testing.assert_allclose(flow.vertical[:, 0, 0], -flow.vertical[:, 0, 1], atol=1e-15, rtol=0)
    assert not flow.x[:, :, [0, -1]].any() and not flow.y.any()


def test_dry_neutral_column_is_stationary_in_potential_temperature():
    result = column.run(32, 'bulk', vapor=False, physics=False)
    g = result['geometry']; state = result['state']
    t = lab.base.temperature(state.energy, g.mass, state.water, g.height_m)
    theta = (t+273.15)*(100000./g.pressure)**lab.KAPPA
    np.testing.assert_allclose(theta, 300., atol=1e-9, rtol=0)
    assert result['rain_mm'] == result['remaining_vapor_mm'] == 0.
    assert abs(result['energy_error_j_m2']) < 1e-3


@pytest.mark.parametrize('mode', ['bulk', 'unmixed'])
@pytest.mark.parametrize('factor', [1., .5])
def test_wet_closed_column_conserves_water_heat_and_signed_tendencies(mode, factor):
    result = column.run(32, mode, time_factor=factor)
    assert 0. < result['rain_mm'] < result['initial_vapor_mm']
    assert result['rain_mm']+result['remaining_vapor_mm'] == pytest.approx(result['initial_vapor_mm'], abs=1e-9)
    assert abs(result['energy_error_j_m2']) < 1e-3
    assert result['maximum_step_temperature_ledger_error_c'] < 1e-9
    assert (np.diff(result['rain_history_mm']) >= 0).all()
    assert result['duration_seconds'] == column.TURNOVER_S
    if mode == 'bulk':
        assert result['parcel_rain_mm'] == 0.


@pytest.mark.parametrize('dt', [np.nan, np.inf, 0., -1., 1e10])
def test_column_bad_step_rejected(dt):
    domain, geometry, state, flow = column.fixture(4)
    with pytest.raises(ValueError):
        column.advance(state, domain, geometry, flow, dt, 'bulk')


@pytest.mark.parametrize('cells', [16, 64, 256])
def test_periodic_contact_exact_shift_has_no_cloud_and_recovers_initial_state(cells):
    result = column.advect_contact(cells, 1.)
    assert result['rain_g_per_kg_initial_dry_air'] == 0.
    np.testing.assert_array_equal(result['initial_vapor_ratio'], result['final_vapor_ratio'])
    np.testing.assert_array_equal(result['initial_enthalpy_j_per_kg'], result['final_enthalpy_j_per_kg'])


def test_periodic_upwind_diffusion_can_create_false_rain_while_conserving():
    result = column.advect_contact(32, .5)
    assert result['rain_g_per_kg_initial_dry_air'] > 0.
    assert result['exact_inviscid_rain_g_per_kg'] == 0.
    assert abs(result['water_error_kg_per_kg']) < 1e-11
    assert abs(result['enthalpy_error_j_per_kg']) < 1e-6


def test_audit_default_writes_nothing_and_protected_write_fails_before_work(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(audit, 'analyse', lambda: ({}, {}))
    monkeypatch.setattr(audit, 'markdown', lambda _: 'toy audit')
    monkeypatch.setattr(audit, 'plot', lambda *a: pytest.fail('Read-only invocation'))
    out = tmp_path/'absent'
    assert audit.main(['--out', str(out)]) == 0
    assert not out.exists()
    monkeypatch.setattr(audit, 'analyse', lambda: pytest.fail('Protected path must reject before work'))
    for path in ('output/v10_cloud_geometry', 'output/v10_cloud_geometry/nested', 'output'):
        with pytest.raises(ValueError, match='Preserve'):
            audit.main(['--write', '--out', str(audit.ROOT/path)])
