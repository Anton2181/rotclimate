import numpy as np
import pytest

from polity.earth_fixed_food import fixed_request_food,KCAL


def run(produced,boundary,*,rural=None,request=.5,blocked=False):
    produced=np.asarray(produced,float)*KCAL;boundary=np.asarray(boundary,int);n=produced.shape[1]
    rural=np.ones(n) if rural is None else np.asarray(rural,float)
    owner=np.full((4,n),-1 if blocked else 0,int)
    retention=np.full((4,n),0. if blocked else .8)
    return fixed_request_food(produced,boundary,rural,np.array([request]),owner,retention,
                              np.zeros((4,1,1)),marketed_share=.5)


def test_distinct_component_harvests_add_without_copying_the_physical_grain():
    result=run([[2.],[1.]],[[0],[6]])
    np.testing.assert_array_equal(result['harvest'][:,0]/KCAL,[2,0,0,0,0,0,1,0,0,0,0,0])
    assert result['rural_food'].harvested[0]==3*KCAL
    assert result['rural_food'].periodic_converged.all()


def test_coincident_component_pulses_sum_once_at_the_same_boundary():
    result=run([[2.],[1.]],[[3],[3]])
    assert result['harvest'][3,0]==3*KCAL and np.count_nonzero(result['harvest'])==1


def test_hungry_origins_cannot_export_while_a_separate_rich_origin_can():
    result=run([[.5,3.]],[[0,0]])
    assert result['rural_food'].unmet[0]>0
    assert np.all(result['marketed'][:,0]==0) and np.all(result['departures'][:,0]==0)
    assert result['departures'][:,1].sum()>0


def test_blocked_routes_do_not_teleport_stored_export_grain_to_town():
    result=run([[3.]],[[0]],blocked=True)
    assert result['marketed'].sum()>0 and result['departures'].sum()==0
    assert result['direct'].sum()==0 and result['town_food'].consumed.sum()==0
    assert result['town_food'].unmet[0]==pytest.approx(.5*KCAL)


def test_source_arrivals_have_one_bin_delay_including_cyclic_december_departure():
    result=run([[3.]],[[0]])
    expected=np.roll(result['departures'][:,0]*.8,1)
    np.testing.assert_array_equal(result['direct'][:,0],expected)


def test_zero_harvest_has_no_hidden_initial_food_or_exports():
    result=run([[0.]],[[ -1]])
    assert result['rural_food'].initial_stock[0]==0
    assert result['marketed'].sum()==result['departures'].sum()==result['town_food'].consumed.sum()==0


def test_positive_grain_with_no_calendar_is_rejected():
    with pytest.raises(ValueError):run([[1.]],[[ -1]])
