import numpy as np
import pytest
from polity.settlement_counts import count_exposure,fit_scale,poisson_deviance


def test_zero_population_mismatch_is_not_floored_or_dropped():
    assert count_exposure([2,3],[0,0],0).tolist()==[2,3]
    assert count_exposure([2,3],[0,0],.7).tolist()==[0,0]
    assert fit_scale([0,0],[0,1]) is None
    assert np.isinf(poisson_deviance([1,0],[0,2]))
    assert poisson_deviance([0,0],[0,2])==4


def test_partition_invariance_and_held_target_cannot_set_scale():
    unsplit=count_exposure([20],[100],.7)
    split=count_exposure([5,15],[25,75],.7)
    assert split.sum()==pytest.approx(unsplit.sum())
    scale=fit_scale(split,[1,3])
    np.testing.assert_allclose(scale*split,[1,3])
    assert poisson_deviance([1,3],scale*split)==pytest.approx(0,abs=1e-12)
    with pytest.raises(ValueError):count_exposure([0],[1],.7)
