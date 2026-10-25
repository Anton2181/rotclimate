from copy import deepcopy
import pytest
from scripts.check_column_wind import compare


def records(factor=1.):
    return [dict(region=name,status='passed',case_identity='fixed-'+name,
        temperature=dict(monthly_mae_C=2.*factor),rain=dict(loss=.5*factor),
        diagnosis=dict(july_lowland_mae_mm=50.*factor,annual_plateau_mae_mm=100.*factor))
        for name in ['north_india','japan']]


def test_fine_limit_does_not_apply_coarse_selection_criteria():
    ref=records();candidate=records(1.005)
    assert not compare(ref,candidate)['passed']
    fine=compare(ref,candidate,coarse=False)
    assert fine['passed'] and fine['failures']==[]


def test_fine_score_above_allowance_fails():
    result=compare(records(),records(1.011),coarse=False)
    assert result['failures']==['Fine S exceeds 1.01']


def test_failed_numerics_never_pass_even_with_better_other_errors():
    rows=records(.9);rows[0]['status']='failed'
    assert not compare(records(),rows,coarse=False)['passed']


def test_changed_case_is_not_an_admissible_pair():
    rows=deepcopy(records());rows[1]['case_identity']='different-observations'
    with pytest.raises(ValueError,match='Unpaired'):compare(records(),rows)


def test_coarse_rainfall_gain_cannot_pay_for_worse_foothill_error():
    candidate=records(.98);candidate[0]['diagnosis']['july_lowland_mae_mm']=51.
    result=compare(records(),candidate)
    assert result['S']<.995 and not result['passed']
