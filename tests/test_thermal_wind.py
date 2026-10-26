import numpy as np
import pytest
from rotclimate.winds import thermal_shear


def test_poleward_cooling_produces_westerly_shear_and_reversed_spin_flips_it():
    y, x = np.mgrid[:7, :8]
    # Exact affine log(T), warmer to the south (larger row) and east.
    temperature = 280*np.exp(.001*y+.002*x)-273.15
    u, v = thermal_shear(temperature, 100000, 8e-5, 2)
    inverse_f = 8e-5/((8e-5)**2+(2*7.292e-5*np.sin(np.radians(10)))**2)
    np.testing.assert_allclose(u, 9.80665*2000*inverse_f*.001/100000, rtol=1e-11)
    np.testing.assert_allclose(v, 9.80665*2000*inverse_f*.002/100000, rtol=1e-11)
    ur, vr = thermal_shear(temperature, 100000, -8e-5, 2)
    np.testing.assert_allclose(ur, -u); np.testing.assert_allclose(vr, -v)
    u2, v2 = thermal_shear(temperature, 100000, 8e-5, 1)
    np.testing.assert_allclose(u2, .5*u); np.testing.assert_allclose(v2, .5*v)


def test_balanced_f_plane_increment_is_nondivergent_and_equator_is_finite():
    y, x = np.mgrid[:9, :10]
    temperature = 280*np.exp(.001*x*y+.002*x*x+.001*y*y)-273.15
    u, v = thermal_shear(temperature, 56000, 1e-4, 2)
    divergence = (np.gradient(u, axis=1)-np.gradient(v, axis=0))/56000
    np.testing.assert_allclose(divergence, 0, atol=1e-16)
    a, b = thermal_shear(temperature, 56000, 0, 2)
    np.testing.assert_array_equal(a, 0); np.testing.assert_array_equal(b, 0)
    a, b = thermal_shear(temperature, 56000, 1e-4, 0)
    np.testing.assert_array_equal(a, 0); np.testing.assert_array_equal(b, 0)


@pytest.mark.parametrize('updates', [dict(moisture_thermal_height_km=-1),
    dict(moisture_thermal_height_km=5), dict(moisture_thermal_height_km=np.nan),
    dict(moisture_thermal_height_km=2, moisture_wind_factor=2),
    dict(moisture_thermal_height_km=2, wind_cap=20)])
def test_ambiguous_height_profiles_fail_before_grid_construction(updates):
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError):
        ClimateModel(Params(**updates))


def test_opt_in_changes_column_wind_and_keeps_a_conservative_coupled_ledger(monkeypatch):
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth, winds
    from rotclimate.model import ClimateModel
    case = _toy_case()
    p = earth.earth_params(strict_params().replace(moisture_transport_form='flux', flux_convergence=0,
        eddy_moisture_scheme='conservative', subsidence_drying=.05), case)
    original = winds.thermal_shear
    monkeypatch.setattr(winds, 'thermal_shear', lambda *a: pytest.fail('Default called thermal shear'))
    a = ClimateModel(p, grid=case.grid).run()
    monkeypatch.setattr(winds, 'thermal_shear', original)
    model = ClimateModel(p.replace(moisture_thermal_height_km=2), grid=case.grid)
    model.trace_cells = np.nonzero(case.grid.inmap)
    b = model.run(diagnose_moisture=True)
    assert a.numerics['all_checks_passed'] and b.numerics['all_checks_passed']
    assert max(np.max(np.abs(t['moisture_u']-t['u'])) for t in model.trace) > 0
    assert np.max(np.abs(a.P-b.P)) > 1e-4
    budget = b.numerics['vapor_flux_budget']
    assert budget['horizontal_transport_conservative']
    assert budget['max_relative_transport_cancellation'] < 1e-12
    assert budget['max_scaled_equation_residual'] <= p.moisture_residual_tol
