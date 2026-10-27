"""Environmental capacity shape is distinct from terrain cooling and solved water."""
import numpy as np
import pytest

from rotclimate import earth
from rotclimate.config import Params
from rotclimate.model import ClimateModel
from test_earth import _toy_case
from test_transient_orography import strict_params


def reservoir_params(case, **changes):
    return earth.earth_params(strict_params().replace(
        moisture_transport_form='flux', flux_convergence=0,
        eddy_moisture_scheme='conservative', moisture_mass_balance=True,
        moisture_two_layer=True, moisture_mass_tracer=True, moisture_reservoirs=True,
        moisture_relaxation=.1, picard_iters=1024).replace(**changes), case)


@pytest.mark.parametrize('changes,match', [
    ({'moisture_reservoir_temperature_profile': 'unknown'}, 'temperature_profile'),
    ({'moisture_reservoir_temperature_profile': 'environmental'}, 'independent moisture reservoirs'),
    *[({'moisture_reservoir_lapse_k_km': value}, 'moisture_reservoir_lapse_k_km')
      for value in [np.nan, np.inf, -np.inf, 1.99, 9.81]],
])
def test_invalid_environmental_partition_rejected_before_grid_build(changes, match):
    with pytest.raises(ValueError, match=match):
        ClimateModel(Params(**changes))


def test_partition_parameters_are_shared_physics():
    from rotclimate.joint import SHARED_FIELDS, validate_partition
    validate_partition()
    assert {'moisture_reservoir_temperature_profile',
            'moisture_reservoir_lapse_k_km'} <= SHARED_FIELDS


@pytest.mark.parametrize('scheme', ['legacy', 'pressure-lapse', 'pressure-moist'])
def test_environmental_shape_keeps_surface_anchors_and_separate_total_scheme(monkeypatch, scheme):
    from rotclimate import column_thermodynamics as thermo, reservoir_moisture
    case = _toy_case()
    p = reservoir_params(case, column_saturation_scheme=scheme, lapse_rate=4.,
        lapse_seasonal=.25, seasonal_column_lapse=True,
        moisture_reservoir_lapse_k_km=8.)
    original = thermo.saturation_column
    calls = []
    captured = []

    def record_column(temperature, pressure, **kwargs):
        result = original(temperature, pressure, **kwargs)
        calls.append((np.array(temperature), np.array(pressure), kwargs, result))
        return result

    class FirstWaterEquation(Exception):
        pass

    def capture_equation(*args, **kwargs):
        captured.append((args[5].copy(), args[7].copy(), kwargs))
        raise FirstWaterEquation

    monkeypatch.setattr(thermo, 'saturation_column', record_column)
    monkeypatch.setattr(reservoir_moisture, 'solve_reservoir_moisture', capture_equation)
    for profile in ['moist', 'environmental']:
        with pytest.raises(FirstWaterEquation):
            ClimateModel(p.replace(moisture_reservoir_temperature_profile=profile),
                         grid=case.grid).run()
        if profile == 'moist':
            moist_calls = list(calls)
            calls.clear()

    # All comparisons use the same initial coupled state: later climate
    # responses may legitimately change total capacity and ocean equilibrium.
    for previous, environmental in zip(captured[0][:2], captured[1][:2]):
        np.testing.assert_array_equal(previous, environmental)
    environmental_calls = calls[-2:]
    for old, new in zip(moist_calls[-2:], environmental_calls):
        np.testing.assert_array_equal(old[0], new[0])
        np.testing.assert_array_equal(old[1], new[1])
        assert new[2] == {'profile': 'lapse', 'lapse_k_km': 8.}
        # Independent hydrostatic solution at the lower/upper interface.
        expected = np.maximum((new[0]+273.15)*.75**(thermo.RD*.008/thermo.G),
                              np.minimum(new[0]+273.15, 200.))
        np.testing.assert_allclose(new[3].interface_temperature_k[1], expected, rtol=1e-10)
        np.testing.assert_array_equal(new[1], 101325.*np.exp(-case.grid.elev/8000.))
    capacity, ocean = environmental_calls
    np.testing.assert_array_equal(captured[1][2]['lower_capacity_fraction'],
                                  capacity[3].lower_water_fraction)
    np.testing.assert_array_equal(captured[1][2]['ocean_lower_fraction'],
                                  ocean[3].lower_water_fraction)
    assert not np.allclose(captured[0][2]['lower_capacity_fraction'],
                           captured[1][2]['lower_capacity_fraction'])
    if scheme != 'legacy':
        assert len(calls) == 4  # total profiles plus independent partition profiles
        assert calls[0][2]['lapse_k_km'] != 8.


@pytest.mark.parametrize('rain_scheme,mixing_days', [('layer', 0.), ('column-convection', 5.)])
def test_actual_environmental_reservoir_equations_conserve_water(rain_scheme, mixing_days):
    case = _toy_case()
    p = reservoir_params(case, moisture_reservoir_temperature_profile='environmental',
        moisture_reservoir_lapse_k_km=6.5, moisture_reservoir_rain_scheme=rain_scheme,
        moisture_reservoir_mixing_days=mixing_days)
    result = ClimateModel(p, grid=case.grid).run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    checks = result.numerics['moisture_reservoirs']
    assert checks['partition_temperature_profile'] == 'environmental'
    assert checks['partition_lapse_k_km'] == 6.5
    assert checks['all_layer_checks_passed']
    assert checks['max_scaled_layer_residual'] <= p.moisture_residual_tol
    assert checks['max_scaled_column_residual'] <= p.moisture_residual_tol
    assert result.numerics['vapor_flux_budget']['max_scaled_equation_residual'] <= p.moisture_residual_tol
    primer = max(8, int(round(117./(p.year_days/p.steps_per_year))))
    assert len(checks['steps']) == primer+p.steps_per_year
    for step in checks['steps']:
        assert step['partition_temperature_profile'] == 'environmental'
        assert step['partition_lapse_k_km'] == 6.5
        assert 0 < step['minimum_lower_capacity_fraction'] <= step['maximum_lower_capacity_fraction'] < 1
        assert 0 < step['minimum_ocean_lower_fraction'] <= step['maximum_ocean_lower_fraction'] < 1
        assert 170 < step['minimum_partition_temperature_k'] <= step['maximum_partition_temperature_k'] < 330
        assert step['maximum_internal_precipitation_transfer_residual_mm_day'] == 0
    np.testing.assert_allclose(result.layer_water.sum(1), result.W, rtol=2*np.finfo(np.float32).eps)
    assert np.isfinite(result.layer_water).all() and result.layer_water.min() >= 0
    # The capacity profile must not restore the old imposed humidity ratio.
    other = ClimateModel(p.replace(moisture_upper_q_ratio=.8), grid=case.grid).run()
    np.testing.assert_array_equal(result.P, other.P)
    np.testing.assert_array_equal(result.layer_water, other.layer_water)


@pytest.mark.parametrize('scheme', ['legacy', 'pressure-moist'])
def test_default_moist_partition_ignores_environmental_lapse_exactly(scheme):
    case = _toy_case()
    p = reservoir_params(case, column_saturation_scheme=scheme)
    default = ClimateModel(p, grid=case.grid).run()
    explicit = ClimateModel(p.replace(moisture_reservoir_temperature_profile='moist',
        moisture_reservoir_lapse_k_km=9.8), grid=case.grid).run()
    assert default.numerics['all_checks_passed'] and explicit.numerics['all_checks_passed']
    for key in ['T', 'Tsl', 'P', 'W', 'u', 'v', 'E', 'snow', 'layer_water']:
        np.testing.assert_array_equal(getattr(default, key), getattr(explicit, key))
    checks = default.numerics['moisture_reservoirs']
    assert checks['partition_temperature_profile'] == 'moist'
    assert checks['partition_lapse_k_km'] is None
    assert all(step['partition_temperature_profile'] == 'moist'
               and step['partition_lapse_k_km'] is None for step in checks['steps'])
