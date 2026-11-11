import copy
import pytest
from polity.institution_scope import group_scopes


def row(a=None,b=None,**flags):return dict(year_from=a,year_to=b,**flags)


def test_documented_single_undated_scope_retains_raw_dates_without_value_imputation():
    rows=[row(value_from='P')];before=copy.deepcopy(rows)
    explicit=group_scopes(rows,100,300,'explicit_only')[0]
    scoped=group_scopes(rows,100,300,'documented_parent_scope')[0]
    assert not explicit['eligible'] and scoped['scope']=='documented_parent_scope'
    assert scoped['raw_from'] is None and scoped['effective_from']==100 and scoped['compatible_with_positive_year200']
    assert rows==before and not scoped['calendar_harmonized']


def test_disputed_alternatives_stay_separate_and_unflagged_multiples_fail():
    rows=[row(is_disputed=True),row(is_disputed=True)]
    assert len(group_scopes(rows,100,300,'documented_parent_scope'))==2
    assert all(r['eligible'] for r in group_scopes(rows,100,300,'documented_parent_scope'))
    assert all(r['review_reason']=='ambiguous_multiple_undated' for r in group_scopes([row(),row()],100,300,'documented_parent_scope'))
    assert not group_scopes([row(is_disputed='False'),row()],100,300,'documented_parent_scope')[0]['eligible']


def test_mixed_group_rejected_by_documented_policy_without_losing_explicit_comparator():
    rows=[row(100,300),row()]
    assert group_scopes(rows,100,300,'explicit_only')[0]['eligible']
    assert all(r['review_reason']=='mixed_time_scope_review' for r in group_scopes(rows,100,300,'documented_parent_scope'))


def test_partial_invalid_reversed_or_outside_dates_are_not_clipped_or_rescued():
    rows=[row(100,None),row(300,100),row(50,300),row('100',300)]
    states=[r['review_reason'] for r in group_scopes(rows,100,300,'explicit_only')]
    assert states==['partial_date_review','reversed_time_bounds','outside_parent_interval','invalid_time_bounds']
    assert group_scopes([row()],300,100,'documented_parent_scope')[0]['review_reason']=='invalid_parent_interval'


def test_explicit_point_is_a_point_not_a_polity_wide_interpolation():
    r=group_scopes([row(150,150)],100,300,'documented_parent_scope')[0]
    assert r['scope']=='explicit_interval' and not r['compatible_with_positive_year200']
    with pytest.raises(ValueError):group_scopes([],100,300,'nearest_date')
