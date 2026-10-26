"""Discrete face consistency, projection identities and coupled climate checks."""
import numpy as np
import pytest
from rotclimate.column_mass import ColumnMassProjection


def explicit_divergence(projector, u, v):
    east = projector.xmass*.5*(u[:, 1:]+u[:, :-1])
    north = projector.ymass*.5*(v[1:, :]+v[:-1, :])
    return east[1:-1, 1:]-east[1:-1, :-1]+north[:-1, 1:-1]-north[1:, 1:-1]


def test_discrete_operator_matches_actual_terrain_mass_and_northward_face_sign():
    rng = np.random.default_rng(815)
    projector = ColumnMassProjection(rng.uniform(0, 5000, (8, 9)), 56000)
    u, v = rng.normal(size=(2, 8, 9))
    actual = projector.divergence@np.r_[u.ravel(), v.ravel()]
    np.testing.assert_allclose(actual.reshape(6, 7), explicit_divergence(projector, u, v), atol=1e-15)
    flat = ColumnMassProjection(np.zeros((8, 9)), 56000)
    y, x = np.mgrid[:8, :9]
    # u=x increases eastward; v=y decreases northward: the two cancel.
    np.testing.assert_allclose(explicit_divergence(flat, x, y), 0, atol=1e-15)


@pytest.mark.parametrize('shape', [(5, 6), (8, 9), (9, 8)])
def test_minimum_mass_weighted_change_is_idempotent_orthogonal_and_nonenergizing(shape):
    rng = np.random.default_rng(916)
    projector = ColumnMassProjection(rng.uniform(0, 4500, shape), 56000)
    u, v = rng.normal(size=(2,)+shape)*10
    east, north, info = projector.project(u, v)
    np.testing.assert_allclose(explicit_divergence(projector, east, north), 0, atol=1e-13)
    ue, vn, second = projector.project(east, north)
    np.testing.assert_allclose(ue, east, atol=1e-12); np.testing.assert_allclose(vn, north, atol=1e-12)
    mass = projector.mass
    original_energy = np.sum(mass*(u*u+v*v))
    output_energy = np.sum(mass*(east*east+north*north))
    correction_energy = np.sum(mass*((east-u)**2+(north-v)**2))
    assert output_energy <= original_energy
    assert original_energy == pytest.approx(output_energy+correction_energy, rel=1e-12)
    assert info['max_scaled_mass_divergence'] < 1e-13 and second['velocity_correction_max_ms'] < 1e-11
    assert abs(info['boundary_net_dry_air_kg_s']) < .05  # cancellation of very large opposing flows


def test_constant_flat_wind_is_unchanged_but_terrain_flow_must_adjust():
    u, v = np.full((7, 9), 5.), np.full((7, 9), -2.)
    flat = ColumnMassProjection(np.zeros_like(u), 56000)
    east, north, info = flat.project(u, v)
    np.testing.assert_array_equal(east, u); np.testing.assert_array_equal(north, v)
    terrain = ColumnMassProjection(np.tile(np.arange(9.)*400, (7, 1)), 56000)
    east, north, info = terrain.project(u, v)
    assert info['original_max_mass_divergence_kgm2s'] > 0
    assert info['velocity_correction_max_ms'] > .1


@pytest.mark.parametrize('updates', [dict(moisture_mass_balance='true'),
    dict(moisture_mass_balance=True),
    dict(moisture_mass_balance=True, moisture_transport_form='flux', flux_convergence=0, moisture_wind_factor=2),
    dict(moisture_mass_balance=True, moisture_transport_form='flux', flux_convergence=0, wind_cap=10)])
def test_ambiguous_or_unsupported_profile_fails_before_building_grid(updates):
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError):
        ClimateModel(Params(**updates))


def test_disabled_path_never_builds_projector_and_enabled_path_keeps_both_ledgers(monkeypatch):
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth, column_mass
    from rotclimate.model import ClimateModel
    case = _toy_case()
    p = earth.earth_params(strict_params().replace(moisture_transport_form='flux', flux_convergence=0,
        eddy_moisture_scheme='conservative', subsidence_drying=.05), case)
    original = column_mass.ColumnMassProjection
    monkeypatch.setattr(column_mass, 'ColumnMassProjection', lambda *a: pytest.fail('Default constructed projection'))
    a = ClimateModel(p, grid=case.grid).run()
    assert 'column_mass_balance' not in a.numerics
    monkeypatch.setattr(column_mass, 'ColumnMassProjection', original)
    model = ClimateModel(p.replace(moisture_mass_balance=True), grid=case.grid)
    b = model.run(diagnose_moisture=True)
    assert b.numerics['all_checks_passed']
    assert b.numerics['column_mass_balance']['max_scaled_mass_divergence'] < 1e-12
    assert b.numerics['vapor_flux_budget']['horizontal_transport_conservative']
    assert b.numerics['vapor_flux_budget']['max_relative_transport_cancellation'] < 1e-12
    assert b.numerics['vapor_flux_budget']['max_scaled_equation_residual'] <= p.moisture_residual_tol
    assert np.max(np.abs(a.P-b.P)) > 1e-4
