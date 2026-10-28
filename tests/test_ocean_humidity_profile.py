"""Hydrostatic RH integrals, actual equation inputs and independent water."""
import numpy as np
import pytest
from scipy.integrate import quad
from rotclimate.column_thermodynamics import humidity_column, saturation_column, specific_saturation, G
from rotclimate.config import Params
from rotclimate.model import ClimateModel
from test_earth import _toy_case
from test_environmental_partition import reservoir_params


@pytest.mark.parametrize('thermal', ['moist', 'lapse'])
def test_uniform_hydrostatic_target_recovers_saturation_bit_exact(thermal):
    t = np.array([-5., 15., 29.]); p = np.array([101325., 95000., 90000.])
    a = saturation_column(t, p, profile=thermal, lapse_k_km=6.)
    b = humidity_column(t, p, profile=thermal, lapse_k_km=6., rh_taper=0.)
    np.testing.assert_array_equal(a.water_mm, b.water_mm)
    np.testing.assert_array_equal(a.interface_temperature_k, b.interface_temperature_k)
    np.testing.assert_array_equal(a.air_mass_kg_m2, b.air_mass_kg_m2)


def test_isothermal_weighted_column_matches_independent_pressure_quadrature():
    ts, ps, taper = 283.15, 101325., .5
    result = humidity_column(ts - 273.15, ps, profile='isothermal', rh_taper=taper, steps=128)
    weight = lambda p: (1 - taper) + taper * max((p / ps - .02) / .98, 0.)
    f = lambda p: float(specific_saturation(ts, p)) * weight(p) / G
    expected = [quad(f, .75 * ps, ps, epsabs=1e-10)[0], quad(f, 10000., .75 * ps, epsabs=1e-10)[0]]
    np.testing.assert_allclose(result.water_mm, expected, rtol=1e-8, atol=1e-9)


def test_rh_interpolation_is_linear_in_water_with_unchanged_thermal_profile():
    results = [humidity_column(22., 101325., profile='lapse', rh_taper=a) for a in [0., .5, 1.]]
    np.testing.assert_allclose(results[1].water_mm, .5 * (results[0].water_mm + results[2].water_mm), rtol=1e-14)
    for result in results[1:]:
        np.testing.assert_array_equal(result.interface_temperature_k, results[0].interface_temperature_k)
        assert result.total_mm < results[0].total_mm
        assert result.lower_water_fraction > results[0].lower_water_fraction
        assert (result.water_mm > 0).all()


@pytest.mark.parametrize('changes,match', [
    ({'moisture_ocean_hydrostatic': 1}, 'must be boolean'),
    ({'moisture_ocean_rh_taper': .5}, 'requires moisture_ocean_hydrostatic'),
    ({'moisture_ocean_hydrostatic': True}, 'requires independent moisture reservoirs'),
    *[({'moisture_ocean_rh_taper': x}, 'moisture_ocean_rh_taper') for x in [np.nan, -.1, 1.1]],
])
def test_invalid_ocean_modes_rejected_before_grid_build(changes, match):
    with pytest.raises(ValueError, match=match):
        ClimateModel(Params(**changes))


def test_new_ocean_modes_are_shared_physics():
    from rotclimate.joint import SHARED_FIELDS, validate_partition
    validate_partition()
    assert {'moisture_ocean_hydrostatic', 'moisture_ocean_rh_taper'} <= SHARED_FIELDS


def test_actual_ocean_equation_gets_the_same_profile_total_and_layer_fraction(monkeypatch):
    from rotclimate import column_thermodynamics as thermo, reservoir_moisture
    case = _toy_case()
    p = reservoir_params(case, moisture_reservoir_temperature_profile='environmental',
                         moisture_reservoir_lapse_k_km=6., ocean_rh=.75, ocean_rh_warm=.1)
    columns, inputs = [], []
    original = thermo.humidity_column

    def column(t, pressure, **kwargs):
        result = original(t, pressure, **kwargs)
        columns.append((t.copy(), result))
        return result

    class FirstWaterEquation(Exception):
        pass

    def capture(*args, **kwargs):
        inputs.append((args[5].copy(), args[7].copy(), kwargs['ocean_lower_fraction'].copy()))
        raise FirstWaterEquation

    monkeypatch.setattr(thermo, 'humidity_column', column)
    monkeypatch.setattr(reservoir_moisture, 'solve_reservoir_moisture', capture)
    with pytest.raises(FirstWaterEquation):
        ClimateModel(p, grid=case.grid).run()
    assert not columns
    with pytest.raises(FirstWaterEquation):
        ClimateModel(p.replace(moisture_ocean_hydrostatic=True, moisture_ocean_rh_taper=.5), grid=case.grid).run()
    t, target = columns[-1]
    rh = .75 + .1 * np.clip((t - 25.) / 4., 0., 1.)
    np.testing.assert_array_equal(inputs[1][0], rh * target.total_mm)
    np.testing.assert_array_equal(inputs[1][2], target.lower_water_fraction)
    np.testing.assert_array_equal(inputs[0][1], inputs[1][1])  # land rain capacity at the matched initial state


def test_half_taper_keeps_independent_layer_equations_and_certifies_every_step():
    case = _toy_case()
    p = reservoir_params(case, moisture_reservoir_mixing_days=0.,
        moisture_reservoir_temperature_profile='environmental', moisture_reservoir_lapse_k_km=6.,
        moisture_reservoir_rain_scheme='column-convection', moisture_ocean_hydrostatic=True,
        moisture_ocean_rh_taper=.5)
    result = ClimateModel(p, grid=case.grid).run(diagnose_moisture=True)
    assert result.layer_water is not None and result.numerics['all_checks_passed']
    certificate = result.numerics['moisture_reservoirs']
    assert certificate['all_layer_checks_passed']
    for step in certificate['steps']:
        assert step['ocean_target_scheme'] == 'hydrostatic-rh'
        assert step['ocean_rh_taper'] == .5
        assert step['ocean_target_thermal_profile'] == 'environmental'
        assert step['ocean_target_lapse_k_km'] == 6.
        assert step['ocean_target_cells'] == int((~case.grid.land).sum())
        assert 0 < step['minimum_ocean_surface_rh'] <= step['maximum_ocean_surface_rh'] <= 1
        assert 0 < step['minimum_ocean_target_water_mm'] <= step['maximum_ocean_target_water_mm']
        assert step['max_scaled_layer_residual'] <= p.moisture_residual_tol
        assert step['max_scaled_column_residual'] <= p.moisture_residual_tol
