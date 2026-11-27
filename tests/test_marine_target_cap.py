"""Physical bounds and source geometry for the private candidate; no runs."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

path = Path(__file__).resolve().parents[1] / 'calibration/marine_target_cap_20261127/marine_target.py'
spec = importlib.util.spec_from_file_location('marine_target_candidate', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cap = module.capped_marine_target


def fields():
    ocean = np.array([[True, False, False], [True, False, False]])
    target = np.array([[10., 999., 999.], [20., 999., 999.]])
    saturation = np.array([[1., 100., 5.], [1., 100., 5.]])
    nearest = (np.array([[0, 0, 0], [1, 1, 1]]), np.zeros((2, 3), dtype=int))
    return target, saturation, ocean, nearest


def test_source_equilibrium_caps_warm_receiving_columns():
    target, sat, ocean, nearest = fields()
    rate = np.full(ocean.shape, .01)
    bounded, returned_rate = cap(target, sat, ocean, nearest, .8, rate)
    np.testing.assert_array_equal(bounded, [[10., 10., 4.], [20., 20., 4.]])
    np.testing.assert_array_equal(bounded[ocean], target[ocean])
    assert returned_rate is rate, 'Actual warm/onshore/distance rates are untouched'


def test_all_land_never_invents_sea_source_or_drying():
    shape = (2, 3)
    invalid = (np.full(shape, -1), np.zeros(shape, int))
    target, rate = cap(np.ones(shape), np.ones(shape), np.zeros(shape, bool), invalid, .8, np.ones(shape))
    assert not target.any() and not rate.any()


def test_all_sea_retains_equilibrium_bytes():
    a = np.array([[0., -0.], [3., 4.]])
    got, _ = cap(a, np.ones_like(a), np.ones_like(a, bool), None, .8, np.zeros_like(a))
    assert got.tobytes() == a.tobytes()


def test_nearest_source_must_be_real_sea():
    a, s, o, nearest = fields()
    with pytest.raises(ValueError, match='actual sea'):
        cap(a, s, o, (nearest[0], np.ones_like(nearest[1])), .8, np.ones_like(a))


def test_negative_indices_cannot_wrap_to_fake_source():
    a, s, o, nearest = fields()
    with pytest.raises(ValueError, match='outside'):
        cap(a, s, o, (nearest[0] - 1, nearest[1]), .8, np.ones_like(a))


@pytest.mark.parametrize('value', [float('nan'), -1.])
def test_invalid_marine_equilibrium_is_rejected(value):
    a, s, o, n = fields()
    a[0, 0] = value
    with pytest.raises(ValueError, match='Invalid marine'):
        cap(a, s, o, n, .8, np.ones_like(a))
