import pytest

from polity.settlement_phase_evidence import change_evidence,review_blocks


def test_ordered_changes_do_not_date_roles_or_create_continuous_occupation():
    result=change_evidence(50,450,70,150)
    assert result.usable_for_change_order and result.recorded_changes==(70,150)
    assert result.status=='consistent_changes' and not result.role_intervals_assigned


@pytest.mark.parametrize('values,flag', [((50,400,450,''),'change_outside_recorded_span'),
    ((50,400,300,150),'reversed_change_order'),((50,400,'',150),'second_change_without_first'),
    ((50,400,'?',150),'nonnumeric_change_date'),((0,400,150,''),'ambiguous_zero_site_endpoint'),
    ((50,400,0,''),'ambiguous_zero_change_date'),(('',400,150,''),'unknown_site_span')])
def test_problem_dates_require_review_without_repair(values,flag):
    result=change_evidence(*values)
    assert flag in result.flags and not result.usable_for_change_order
    assert result.status=='changes_require_review' and not result.role_intervals_assigned


def test_missing_changes_and_coincident_changes_are_not_fabricated_intervals():
    missing=change_evidence(-100,400,'','')
    assert missing.status=='no_recorded_changes' and missing.recorded_changes==()
    same=change_evidence(50,400,150,150)
    assert 'coincident_change_dates' in same.flags and same.recorded_changes==(150,150)
    assert not same.role_intervals_assigned


def test_negative_dates_are_source_years_not_missing_sentinels():
    result=change_evidence(-100,60,-50,'')
    assert result.usable_for_change_order and result.recorded_changes==(-50,)


def test_same_point_and_same_name_block_folds_without_merging_observations():
    core=[('a','One','Place',100,200),('b','One','Other',100,200),
        ('c','One','Place',900,900),('d','Two','Place',1000,1000),
        ('e','Two','Unlocated','',''),('f','Two','Different','','')]
    forward=review_blocks(core,[])
    assert forward==review_blocks(list(reversed(core)),[])
    assert forward['a']==forward['b']==forward['c']
    assert len(forward)==6 and len({forward[i] for i in ['a','d','e','f']})==4


def test_source_namespace_links_remain_and_duplicate_record_keys_fail():
    core=[('a','One','A',1,2),('b','Two','B',3,4)]
    groups=review_blocks(core,[('a','HERMON','One','17'),('b','HERMON','One','17')])
    assert groups['a']==groups['b']
    with pytest.raises(ValueError,match='Unique'):
        review_blocks([core[0],core[0]],[])
