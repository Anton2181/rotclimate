import numpy as np
import pytest

from experiments.descent_continuity_20261102.closure import net_descent_rate


def test_divergent_air_keeps_existing_descent_and_ascent_reduces_it():
    requested = np.full(4, 3e-6)
    convergence = np.array([-5e-6, 0, 1e-6, 4e-6])
    assert np.allclose(net_descent_rate(requested, convergence), [3e-6, 3e-6, 2e-6, 0], atol=1e-20)


def test_disabled_path_preserves_existing_array_and_half_strength_uses_same_units():
    requested = np.array([3e-6])
    assert net_descent_rate(requested, [2e-6], 0) is requested
    assert net_descent_rate(requested, [2e-6], .5)[0] == pytest.approx(2e-6)


@pytest.mark.parametrize('strength', [-.1, 1.1, np.nan])
def test_invalid_strength_is_rejected(strength):
    with pytest.raises(ValueError):
        net_descent_rate([1e-6], [0], strength)
