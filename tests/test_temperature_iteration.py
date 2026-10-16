import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate.model import ClimateModel, temperature_update


def test_damping_stabilises_an_oscillating_coupled_fixed_point():
    # Fixed point x=1, full iteration derivative -2: raising its iteration cap
    # makes the undamped error larger. Quarter updates converge to the same root.
    x = np.array([0.])
    for _ in range(40):
        x, error = temperature_update(x, 3 - 2 * x, 0.25)
    np.testing.assert_allclose(x, 1., atol=1e-8)
    assert error.max() < 1e-8


def test_small_damped_step_cannot_hide_large_fixed_point_error():
    x, error = temperature_update(np.array([0.]), np.array([4.]), 0.01)
    assert x[0] < 0.05
    assert error[0] == 4.


def test_default_preserves_full_update_and_existing_profiles():
    solved = np.array([12., 20.])
    state, _ = temperature_update(np.array([1., 2.]), solved, Params().t_relaxation)
    assert state is solved
    assert Params.from_json('calibration/round20_retrograde_selected.json').t_relaxation == 1.


@pytest.mark.parametrize('fraction', [0, -1, 1.1, float('nan')])
def test_invalid_relaxation_rejected_before_building_a_grid(fraction):
    with pytest.raises(ValueError, match='t_relaxation'):
        ClimateModel(Params(t_relaxation=fraction))
