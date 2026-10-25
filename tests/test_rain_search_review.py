import copy
import pytest
from scripts.gate_calibrate import score
from scripts.review_rain_structure_search import review_rows


GROUPS={'training':['a'],'holdout':['b'],'midlatitude':['c'],'dev12':['d']}
REF={n:(2.,.5) for names in GROUPS.values() for n in names}


def row(n,errors):
    cost,info=score(errors,REF,GROUPS)
    return dict(n=n,cost=cost,regions=errors,**info)


def test_better_average_cannot_pay_for_worse_protected_group():
    errors={n:(1.9,.475) for n in REF};errors['b']=(2.002,.5005)
    candidate=row(1,errors);assert candidate['S']<.995
    result=review_rows([row(0,REF),candidate],REF,GROUPS,2)
    assert result['selected_indices']==[]
    assert 'holdout: group worsened' in result['checks'][1]['failures']


def test_better_rain_cannot_pay_for_temperature_beyond_component_limit():
    candidate=row(1,{n:(2.04,.48) for n in REF});assert candidate['S']<.995
    result=review_rows([row(0,REF),candidate],REF,GROUPS,2)
    assert not result['checks'][1]['eligible']
    assert 'Temperature error exceeds 1% allowance' in result['checks'][1]['failures']


def test_finalists_are_the_first_three_eligible_in_score_order():
    rows=[row(0,REF)]+[row(i,{n:(2.*f,.5*f) for n in REF}) for i,f in enumerate([.99,.97,.98,.96],1)]
    result=review_rows(rows,REF,GROUPS,5)
    assert result['eligible_count']==4
    assert result['selected_indices']==[4,2,3]


def test_incomplete_budget_and_changed_score_are_rejected():
    rows=[row(0,REF),row(1,{n:(1.98,.495) for n in REF})]
    with pytest.raises(ValueError,match='budget'):review_rows(rows,REF,GROUPS,3)
    changed=copy.deepcopy(rows);changed[1]['S']-=.01
    with pytest.raises(ValueError,match='does not reproduce'):review_rows(changed,REF,GROUPS,2)
    changed=copy.deepcopy(rows);changed[1]['S']=float('nan')
    with pytest.raises(ValueError,match='does not reproduce'):review_rows(changed,REF,GROUPS,2)


def test_failed_solve_is_never_selected():
    errors={**REF,'b':None}
    result=review_rows([row(0,REF),dict(n=1,cost=99.,regions=errors)],REF,GROUPS,2)
    assert result['selected_indices']==[]
    assert result['checks'][1]['failures']==['Unverified regional solve']
