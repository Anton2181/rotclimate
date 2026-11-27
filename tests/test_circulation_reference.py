"""Known-answer projection, partial-column, vector and footprint diagnostics."""
import numpy as np
import pytest
from scripts.circulation_reference import (column_targets, geographic_wind,
    native_aggregation, projection_jacobian, vector_scores)
from experiments.v10_forcing_audit import Field


@pytest.mark.parametrize('latitude', [37., -29.])
def test_center_east_north_and_southern_reflection(latitude):
    geometry = projection_jacobian(np.array([[latitude]]), np.array([[151.]]), latitude, 151.)
    east, north = geographic_wind(np.array([[5.]]), np.array([[3.]]), geometry, mirrored=latitude < 0)
    np.testing.assert_allclose(east, 5, atol=1e-8)
    np.testing.assert_allclose(north, -3 if latitude < 0 else 3, atol=1e-8)


def test_off_center_metric_and_rotation_recover_known_geographic_vector():
    geometry = projection_jacobian(np.array([[55., 24.]]), np.array([[15., -22.]]), 37.1, -3.45)
    ex, ey, nx, ny, determinant = geometry
    assert np.max(np.abs(determinant-1)) > .01  # normalization would be wrong
    east, north = geographic_wind(4*ex-7*nx, 4*ey-7*ny, geometry)
    np.testing.assert_allclose(east, 4, atol=1e-12)
    np.testing.assert_allclose(north, -7, atol=1e-12)


def fixture():
    pressure = np.array([1000., 925., 850., 700., 600., 500., 400., 300.])
    axes = (pressure, np.array([35.]), np.array([0.]), np.arange(12.))
    q = np.broadcast_to(np.linspace(.02, .001, 8)[None, :, None, None], (12, 8, 1, 1))
    u = np.broadcast_to(np.arange(8.)[None, :, None, None], q.shape)
    return dict(shum=Field(q/(1-q), *axes), uwnd=Field(u, *axes),
                vwnd=Field(2*u, *axes), hgt=Field(np.full_like(u, 750), *axes)), q, u


def test_partial_column_uses_specific_humidity_and_positive_pressure_integral():
    fields, q, u = fixture()
    targets, water, height = column_targets(fields)
    # Independent manual trapezoids; no mixing-ratio weighting or whole column.
    dp = -np.diff(fields['shum'].pressure_hpa[1:])*100
    qa = q[0, 1:, 0, 0]; ua = u[0, 1:, 0, 0]
    mass = np.sum(.5*(qa[:-1]+qa[1:])*dp)
    flux = np.sum(.5*(qa[:-1]*ua[:-1]+qa[1:]*ua[1:])*dp)
    np.testing.assert_allclose(water, mass/9.80665)
    np.testing.assert_allclose(targets['q925_300'][:, 0], flux/mass)
    np.testing.assert_allclose(targets['q925_300'][:, 1], 2*flux/mass)
    np.testing.assert_array_equal(targets['850'][:, 0], 2)
    np.testing.assert_array_equal(height, 750)


def test_reference_coordinate_mismatch_is_rejected():
    fields, _, _ = fixture()
    fields['vwnd'].latitude = np.array([37.5])
    with pytest.raises(ValueError, match='unmatched'):
        column_targets(fields)


def test_monthly_vector_error_distinguishes_reversed_equal_speed_winds():
    reference = np.zeros((12, 2, 2)); reference[:, 0] = 5
    model = -reference
    scores = vector_scores(model, reference, np.array([1., 3.]), np.ones(12)*30)
    assert scores['vector_rmse_ms'] == pytest.approx(10)
    assert scores['direction_cosine'] == pytest.approx(-1)
    assert scores['model_mean_vector_speed_ms'] == scores['reference_mean_vector_speed_ms'] == 5


def test_native_footprint_area_coverage_and_terrain_exclusions():
    fields, _, _ = fixture()
    field = fields['shum']
    # Entire2.5-degree cell represented by four equal-area samples.
    from rotclimate.earth import R_EARTH_KM
    total = R_EARTH_KM**2*np.radians(2.5)*(np.sin(np.radians(36.25))-np.sin(np.radians(33.75)))
    lat = np.array([[35.5, 35.5], [34.5, 34.5]])
    lon = np.array([[-.5, .5], [-.5, .5]])
    area = np.full((2, 2), total/4)
    inmap = np.ones((2, 2), bool)
    land = np.ones((2, 2), bool)
    terrain = np.zeros((2, 2))
    h = np.full((12, 1, 1), 750)
    aggregate, masks, _, diagnostic = native_aggregation(lat, lon, area, inmap, land, terrain, field, h)
    assert diagnostic['land_cells'] == 1
    np.testing.assert_allclose(aggregate(np.array([[1., 3.], [5., 7.]])), [4])
    inmap[0, 0] = False
    assert not native_aggregation(lat, lon, area, inmap, land, terrain, field, h)[1]['land'].any()
    inmap[:] = True; terrain[1, 0] = 800
    assert not native_aggregation(lat, lon, area, inmap, land, terrain, field, h)[1]['land'].any()
    terrain[:] = 0; land[0] = False
    assert native_aggregation(lat, lon, area, inmap, land, terrain, field, h)[3]['mixed_excluded'] == 1
