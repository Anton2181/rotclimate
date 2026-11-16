import numpy as np
import pytest
from polity.urban_hierarchy_trial import closed_pairs,member_order,generate,fit_fold,ensemble_scores
from polity.settlement_sizes import draws


def fixture():
    rng=np.random.default_rng(9);fold=np.repeat(np.arange(4),20);n=len(fold)
    capital=np.zeros(n,bool);capital[[0,20,40,60]]=True
    centre=np.full(n,-1)
    for i in np.flatnonzero(~capital):centre[i]=(i//20)*20
    centre[1]=20;centre[22]=0
    lnH=rng.uniform(5,12,n);y=1+.2*lnH+.8*capital+rng.normal(size=n)
    return lnH,y,fold,capital,centre


def test_outer_responses_cannot_change_selection_or_predictions():
    H,y,f,c,owner=fixture();args=dict(phis=(0,.5,1),shifts=(0,.4,.8))
    a=fit_fold(H,y,f,c,owner,0,**args);y[f==0]+=40
    b=fit_fold(H,y,f,c,owner,0,**args)
    np.testing.assert_array_equal(a[0],b[0]);np.testing.assert_array_equal(a[1],b[1]);assert a[2:]==b[2:]


def test_closed_pair_masks_do_not_read_cross_fold_centre_labels():
    _,_,fold,_,owner=fixture()
    train=closed_pairs(owner,fold,0,True);test=closed_pairs(owner,fold,0)
    assert not train[1] and not train[22] and not test[1] and not test[22]
    for i in np.flatnonzero(train):assert fold[i]!=0 and fold[owner[i]]!=0
    for i in np.flatnonzero(test):assert fold[i]==fold[owner[i]]==0


def test_residual_selection_preserves_draw_multiset_and_bounds():
    H,_,_,c,owner=fixture();order=member_order(owner,c)
    area,e=generate(H,1.,c,order,1.,.8,7,(1.,1783.),True)
    np.testing.assert_array_equal(np.sort(e),np.sort(draws(len(H),7)))
    for centre,members in order.items():assert e[centre]>=max(e[members])
    assert (area>=1).all() and (area<=1783).all()


def test_ensemble_crps_by_hand_and_identity():
    score=ensemble_scores(np.exp([[0.],[2.]]),np.exp([1.]))
    assert score['log_area_crps']==pytest.approx(.5) and score['median_log_area_mae']==pytest.approx(0)
    assert ensemble_scores(np.array([[5.],[5.]]),np.array([5.]))['log_area_crps']==0
