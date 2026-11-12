import numpy as np
import pytest
from scipy import ndimage as ndi

from polity.settlement_joint import density_score, history_prior, variants


def test_exponent_changes_only_density_factor_preserving_source_dtype_and_inputs():
    density = np.arange(1, 21, dtype=np.float32).reshape(4, 5)
    land = np.ones_like(density, bool); land[0, 0] = False
    eligible = land.copy(); eligible[-1, -1] = False
    smooth = ndi.gaussian_filter(np.where(land, density, 0.), 1.)
    environment = np.linspace(1, 2, 20).reshape(4, 5)
    score = smooth * environment
    before = density.copy(), score.copy(), eligible.copy()
    for power in (.5, .7, 1.):
        result = density_score(score, density, land, eligible, power)
        # Match the declared float32 transformation, then verify its algebra.
        np.testing.assert_array_equal(result[eligible], score[eligible] * smooth[eligible] ** (power - 1))
        np.testing.assert_allclose(result[eligible], (smooth ** power * environment)[eligible], rtol=2e-7)
        assert np.all(result[~eligible] == 0)
    for actual, expected in zip((density, score, eligible), before):
        np.testing.assert_array_equal(actual, expected)


def test_history_mixture_limits_and_deduplicated_grid():
    distance = np.array([0., 450., 800., np.inf])
    np.testing.assert_allclose(history_prior(distance, 450, 0), np.exp(-distance / 450))
    np.testing.assert_array_equal(history_prior(distance, 450, 1), np.ones(4))
    mixture = history_prior(distance, 800, .3)
    assert mixture[0] == 1 and mixture[-1] == .3
    assert np.all(np.diff(mixture) < 0)
    grid = list(variants())
    assert len(grid) == len({v['variant'] for v in grid}) == 21
    assert sum(v['floor'] == 1 for v in grid) == 3


@pytest.mark.parametrize('scale,floor,distance', [(0, 0, [1]), (450, -1, [1]), (450, 2, [1]),
                                               (450, 0, [-1]), (450, 0, [np.nan])])
def test_invalid_prior_is_rejected(scale, floor, distance):
    with pytest.raises(ValueError):
        history_prior(distance, scale, floor)


def test_zero_density_cannot_be_rescued_by_negative_exponent():
    with pytest.raises(ValueError, match='positive smoothed density'):
        density_score(np.ones((3, 3)), np.zeros((3, 3)), np.ones((3, 3), bool), np.ones((3, 3), bool), .5)
