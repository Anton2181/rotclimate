import numpy as np
import pytest
from scripts.propose_momentum_balance import solve_hull


def test_feasible_weights_stay_inside_convex_physical_neighborhood():
    result=solve_hull([1,.8,.9],[[1,1.2,.8],[1,.8,1.1]],[1,1])
    assert result['feasible']
    w=np.array(result['weights'])
    assert (w>=0).all() and w.sum()==pytest.approx(1)
    assert np.max(np.array([[1,1.2,.8],[1,.8,1.1]])@w)<=1+1e-9
    assert result['predicted_S']<1


def test_conflicting_protections_return_no_proposal_weights():
    result=solve_hull([.9,.8],[[1,2],[2,1]],[1.2,1.2])
    assert result['feasible'] is False and 'weights' not in result


@pytest.mark.parametrize('objective,a,b',[([np.nan],[[1]],[1]),([1],[[np.inf]],[1]),
    ([1,2],[[1]],[1]),([],[],[])])
def test_invalid_response_archive_cannot_propose_parameters(objective,a,b):
    with pytest.raises(ValueError):solve_hull(objective,a,b)
