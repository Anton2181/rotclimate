import numpy as np
import pytest
from polity import wide_supply as W


def test_delivered_share_bounds():
    assert np.allclose(W.delivered_share([0, 135, 270, 400, np.inf]), [1, .5, 0, 0, 0])


def test_hinterland_conserves_and_splits_seasons():
    owner = np.array([[0, 0, 1, -1], [1, 0, 1, -1]]); share = np.array([[1., .5, .2, .9], [.5, .5, 0., .9]])
    grain = np.array([8., 4., 10., 100.])
    delivered, sent = W.hinterland_delivery(owner, share, grain, 2)
    assert np.allclose(delivered, [4 + 1 + 1, 1 + 2]) and np.allclose(sent, [4 + 2 + 2, 5 + 4])
    assert sent.sum() <= grain.sum()


def test_ship_cheapest_first_and_conservation():
    excess = np.array([10., 0., 6.]); deficit = np.array([0., 9., 0.])
    share = np.array([[0, .5, 0], [0, 0, 0], [0, .9, 0]])
    sent, received = W.ship(excess, deficit, share)
    assert sent[2, 1] == 6 and np.isclose(sent[0, 1], (9 - 5.4) / .5) and np.isclose(received[1], 9)
    assert all(v <= e + 1e-12 for (i, _), v in sent.items() for e in [excess[i]])


def test_ship_shortage_and_no_reshipment():
    sent, received = W.ship(np.array([2., 0.]), np.array([0., 5.]), np.array([[0, .5], [0, 0]]))
    assert sent == {(0, 1): 2.0} and np.isclose(received[1], 1.0)
    with pytest.raises(ValueError):
        W.ship(np.array([1.]), np.array([1.]), np.array([[.5]]))
