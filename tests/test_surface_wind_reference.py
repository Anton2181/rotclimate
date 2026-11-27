"""Reference orientation, periodic longitude and momentum-unit contracts."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from circulation_components import bilinear_monthly, pressure_velocity


def test_bilinear_reference_retains_latitude_sign_and_months():
    field = np.broadcast_to((90 - 2.5*np.arange(73))[None, :, None], (12, 73, 144)).copy()
    field += np.arange(12)[:, None, None]
    got = bilinear_monthly(field, np.array([35.4, -20.2, 90., -90.]), np.array([41.2, 21., 1., 359.]))
    np.testing.assert_allclose(got, np.array([35.4, -20.2, 90., -90.])[None] + np.arange(12)[:, None], atol=1e-12, rtol=0)


def test_longitude_seam_uses_both_global_edges():
    field = np.zeros((12, 73, 144))
    field[:, :, -1] = 2
    field[:, :, 0] = 10
    got = bilinear_monthly(field, np.array([0., 0.]), np.array([358.75, -1.25]))
    np.testing.assert_array_equal(got, np.full((12, 2), 6.))


def test_invalid_geographic_coordinate_is_not_silently_clipped():
    with pytest.raises(ValueError):
        bilinear_monthly(np.zeros((12, 73, 144)), np.array([91.]), np.array([0.]))


def test_equatorial_momentum_is_regular_and_uses_pa_per_metre():
    pressure = np.broadcast_to(np.arange(5.)[None] * 100., (4, 5))
    lat, friction = np.zeros_like(pressure), np.full_like(pressure, 1e-4)
    u, v = pressure_velocity(pressure, lat, friction, 1e5, 7.292e-5, 1.2)
    np.testing.assert_allclose(u, -100 / (1e5 * 1.2 * 1e-4))
    np.testing.assert_array_equal(v, np.zeros_like(v))


def test_hemisphere_reverses_geostrophic_turning():
    pressure = np.broadcast_to(np.arange(5.)[None] * 100., (4, 5))
    drag = np.full_like(pressure, 1e-5)
    north = pressure_velocity(pressure, np.full_like(pressure, 30.), drag, 1e5, 7.292e-5, 1.2)
    south = pressure_velocity(pressure, np.full_like(pressure, -30.), drag, 1e5, 7.292e-5, 1.2)
    np.testing.assert_array_equal(north[0], south[0])
    np.testing.assert_array_equal(north[1], -south[1])
