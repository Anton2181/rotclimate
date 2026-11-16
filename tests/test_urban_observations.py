import itertools

import numpy as np
import pytest
from scipy.stats import ks_2samp

from polity.urban_observations import interval_ks_lower_bound


def test_exact_observations_reduce_to_two_sample_ks():
    for a,b in [([1,2,2],[2,3]),([0,0],[0,0,1]),([5],[1,2,3])]:
        assert interval_ks_lower_bound(a,b,b)==pytest.approx(ks_2samp(a,b).statistic)


def test_open_class_does_not_invent_model_ceiling():
    assert interval_ks_lower_bound([3000,4000],[201,201],[np.inf,np.inf])==0
    assert interval_ks_lower_bound([3000,4000],[201,201],[1783,1783])==1


def test_disjoint_support_forces_complete_gap():
    assert interval_ks_lower_bound([1,2],[4,5],[6,np.inf])==1


def test_bound_never_exceeds_any_feasible_discrete_imputation():
    # Exhaust independent integer assignments, with ties and overlapping intervals.
    for lo,hi in [([0,2],[2,4]),([1,1,3],[1,3,4]),([0,0],[1,2])]:
        for sample in [[0,2,4],[1,1],[3,4,4]]:
            bound=interval_ks_lower_bound(sample,lo,hi)
            oracle=min(ks_2samp(sample,values).statistic for values in itertools.product(*(range(a,b+1) for a,b in zip(lo,hi))))
            assert bound<=oracle+1e-14


@pytest.mark.parametrize('a,lo,hi',[
    ([],[1],[2]),([1],[],[]),([1],[2],[1]),([np.nan],[1],[2]),
    ([1],[1],[np.nan]),([1],[-1],[2]),([1],[1],[-np.inf]),([1],[1,2],[3]),
])
def test_invalid_observation_definitions_rejected(a,lo,hi):
    with pytest.raises(ValueError):interval_ks_lower_bound(a,lo,hi)
