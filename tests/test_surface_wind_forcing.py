"""Known vectors and calendar edge cases for diagnostic prescribed winds."""
import numpy as np
import pytest
from scripts.circulation_reference import geographic_wind, projection_jacobian
from scripts.surface_wind_forcing import at_day, project_monthly


def test_projection_preserves_off_center_geographic_vectors_and_metric():
    geometry = projection_jacobian(np.array([[52., 15.]]), np.array([[55., 20.]]), 30., 35.)
    east = np.broadcast_to(np.arange(12.)[:, None, None], (12, 1, 2))
    north = np.full_like(east, -7.)
    projected = project_monthly(east, north, geometry)
    assert np.max(np.abs(geometry[-1] - 1)) > .01
    restored = geographic_wind(projected[:, 0], projected[:, 1], geometry)
    np.testing.assert_allclose(restored[0], east, atol=2e-14, rtol=0)
    np.testing.assert_allclose(restored[1], north, atol=2e-14, rtol=0)


def test_calendar_centers_seam_and_negative_primer_days():
    months = np.arange(12., dtype=float)
    for month in range(12):
        assert at_day(months, (month + .5) * 365 / 12) == pytest.approx(month)
    assert at_day(months, 0.) == 5.5
    assert at_day(months, 365.) == 5.5
    assert at_day(months, -365 / 24) == 11.
    assert at_day(months, 365 / 12) == pytest.approx(.5)


def test_projection_rejects_invalid_geometry_and_field_shape():
    geometry = tuple(np.ones((1, 2)) for _ in range(5))
    with pytest.raises(ValueError):
        project_monthly(np.ones((12, 2)), np.ones((12, 2)), geometry)
    with pytest.raises(ValueError):
        project_monthly(np.ones((12, 1, 2)), np.ones((12, 1, 2)), (*geometry[:-1], -geometry[-1]))
    with pytest.raises(ValueError):
        at_day(np.arange(12.), 1., 0.)
