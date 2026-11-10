import numpy as np
import pytest
from scipy.spatial.distance import pdist, squareform

from polity.settlement_intensity import adaptive_count_sites,intensity_fields


def test_intensity_budget_and_scale_invariance():
    score=np.arange(1,2501,dtype=float).reshape(50,50)
    mask=np.ones(score.shape,bool);mask[:4]=False
    history=np.exp(-np.indices(score.shape)[1]/15.)
    a,r=intensity_fields(score,mask,70,3,history=history)
    b,s=intensity_fields(score*100,mask,70,3,history=history*.001)
    assert a.sum()*9==pytest.approx(70)
    np.testing.assert_allclose(a,b,rtol=1e-13)
    np.testing.assert_allclose(r,s,rtol=1e-13)
    assert np.all(a[~mask]==0) and np.all(r[~mask]==0)


def test_symmetric_pair_constraints_and_count_are_preserved():
    score=np.ones((60,90));score[:,:45]=30
    mask=np.ones(score.shape,bool)
    intensity,spacing=intensity_fields(score,mask,100,2,coefficient=.35)
    placed=adaptive_count_sites(score,mask,100,2,coefficient=.35,seed=7,stochastic=True)
    assert len(placed.towns)==100 and placed.shortfall==0
    points=np.array(placed.towns);r=spacing[points[:,0],points[:,1]]
    distances=squareform(pdist(points*2));threshold=.5*(r[:,None]+r[None,:])
    assert np.all(distances[~np.eye(len(points),dtype=bool)]>threshold[~np.eye(len(points),dtype=bool)]-1e-10)
    assert spacing[30,10]<spacing[30,70]


def test_zero_budget_zero_support_and_infeasible_request():
    score=np.ones((8,8));mask=score.astype(bool)
    assert not adaptive_count_sites(score,mask,0,1).towns
    assert adaptive_count_sites(score,mask,5,1,history=np.zeros_like(score)).shortfall==5
    one=np.zeros_like(mask);one[4,4]=True
    assert adaptive_count_sites(score,one,10,1).shortfall==9


def test_no_artificial_grid_spacing_floor_and_no_input_mutation():
    score=np.ones((20,20));mask=score.astype(bool);before=score.copy()
    p=adaptive_count_sites(score,mask,50,9,coefficient=0,stochastic=False)
    assert len(p.towns)==50 and pdist(np.array(p.towns)*9).min()==9.
    np.testing.assert_array_equal(score,before)
    assert p==adaptive_count_sites(score,mask,50,9,coefficient=0,stochastic=False)


def test_seed_replay_and_location_prior_without_population_change():
    score=np.ones((60,60));mask=score.astype(bool)
    history=np.exp(-np.indices(score.shape)[1]/12)
    p=adaptive_count_sites(score,mask,80,3,history=history,stochastic=True,seed=43)
    assert len(p.towns)==80
    assert p==adaptive_count_sites(score,mask,80,3,history=history,stochastic=True,seed=43)
    assert np.mean(np.array(p.towns)[:,1])<25


@pytest.mark.parametrize('kw',[{'count':-1},{'count':True},{'cell_km':0},{'coefficient':-1},{'maximum_spacing_km':np.inf}])
def test_invalid_request_rejected(kw):
    args=dict(count=5,cell_km=1);args.update(kw)
    with pytest.raises(ValueError):intensity_fields(np.ones((8,8)),np.ones((8,8),bool),**args)
