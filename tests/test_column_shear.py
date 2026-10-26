import numpy as np
import pytest

from rotclimate.winds import frictional_response, pressure_shear


@pytest.mark.parametrize('latitude_sign', [-1, 0, 1])
def test_pressure_response_solves_the_force_balance_and_dissipates_energy(latitude_sign):
    rng = np.random.default_rng(92)
    px, py = rng.normal(size=(2, 5, 6))*.002
    drag = rng.uniform(2e-5, 1e-4, (5, 6))
    f = latitude_sign*8e-5
    u, v = frictional_response(px, py, f, drag)
    np.testing.assert_allclose(drag*u-f*v, -px/1.2, atol=1e-17)
    np.testing.assert_allclose(f*u+drag*v, -py/1.2, atol=1e-17)
    np.testing.assert_allclose(-(px*u+py*v)/1.2, drag*(u*u+v*v), atol=1e-15)
    assert np.isfinite(u).all() and np.isfinite(v).all()


def test_less_drag_turns_the_pressure_flow_toward_geostrophic_not_just_faster():
    u, v = frictional_response(.001, 0, 1e-4, 1e-4)
    uc, vc = frictional_response(.001, 0, 1e-4, .5e-4)
    assert abs(vc/uc) > abs(v/u)
    assert uc*v != vc*u


def test_row_sign_rotation_and_zero_shear_endpoint():
    y, x = np.mgrid[:5, :6]
    pressure = 2*x-3*y
    du, dv = pressure_shear(pressure, 1000, 8e-5, np.full((5,6), 1e-4), .5)
    us, vs = frictional_response(.002, .003, 8e-5, 1e-4)
    uc, vc = frictional_response(.002, .003, 8e-5, .5e-4)
    np.testing.assert_allclose(du, uc-us)
    np.testing.assert_allclose(dv, vc-vs)
    a, b = pressure_shear(pressure, 1000, 8e-5, 1e-4, 1)
    np.testing.assert_array_equal(a, 0)
    np.testing.assert_array_equal(b, 0)


@pytest.mark.parametrize('changes', [dict(moisture_pressure_drag_ratio=.1),
    dict(moisture_pressure_drag_ratio=np.nan), dict(moisture_pressure_drag_ratio=1.1),
    dict(moisture_pressure_drag_ratio=.5),
    dict(moisture_pressure_drag_ratio=.5, slp_large=1, moisture_wind_factor=2),
    dict(moisture_pressure_drag_ratio=.5, slp_large=1, wind_cap=10)])
def test_invalid_or_ambiguous_column_profiles_fail_before_building_grid(changes):
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError):
        ClimateModel(Params(**changes))


def test_legacy_never_calls_shear_and_opt_in_preserves_water_residual(monkeypatch):
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth, winds
    from rotclimate.model import ClimateModel
    case = _toy_case()
    p = earth.earth_params(strict_params().replace(slp_large=1.2, slp_local=.2,
                          flux_convergence=.5, flux_scale_km=800), case)
    original = winds.pressure_shear
    monkeypatch.setattr(winds, 'pressure_shear', lambda *a:pytest.fail('Default called opt-in shear'))
    a = ClimateModel(p, grid=case.grid).run()
    monkeypatch.setattr(winds, 'pressure_shear', original)
    model = ClimateModel(p.replace(moisture_pressure_drag_ratio=.5), grid=case.grid)
    model.trace_cells = np.nonzero(case.grid.inmap & case.grid.land)
    b = model.run(diagnose_moisture=True)
    assert a.numerics['all_checks_passed'] and b.numerics['all_checks_passed']
    assert np.max(np.abs(a.P-b.P)) > 1e-4
    assert max(np.max(np.abs(t['u']-t['moisture_u'])) for t in model.trace) > 0
    sl = (slice(None),)+case.grid.map_slice()
    residual = b.moisture_budget['absolute_residual']/np.maximum(b.P[sl]+np.abs(b.E[sl]), .1)
    # Numerical criterion uses net evaporation including import/drying.
    net = sum(b.moisture_budget[key] for key in ['evaporation', 'column_drying', 'convergence_import'])
    scaled = b.moisture_budget['absolute_residual']/np.maximum(b.P[sl]+np.abs(net), .1)
    assert np.isfinite(residual).all() and scaled.max() <= p.moisture_residual_tol*1.001
