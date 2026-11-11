from polity.institution_evidence import value_evidence,time_evidence


def test_unknown_missing_and_inference_never_turn_into_observed_absence():
    states={code:value_evidence(code,None)['state'] for code in ['P','A','IP','IA','SU','U','SA','A~P']}
    assert states==dict(P='coded_present',A='coded_absent',IP='inferred_present',IA='inferred_absent',
        SU='suspected_unknown',U='expert_unknown',SA='unresolved_code',**{'A~P':'unresolved_code'})
    assert value_evidence(None,None)['state']=='missing_export_value'


def test_numeric_intervals_and_unresolved_shapes_are_not_point_estimates():
    r=value_evidence(2,4);assert r==dict(raw_from=2,raw_to=4,state='numeric_interval')
    assert value_evidence(4,2)['state']=='reversed_numeric_bounds'
    assert value_evidence(2,None)['state']=='unresolved_value_shape'
    assert value_evidence(True,True)['state']=='unresolved_value_shape'


def test_dates_keep_unknowns_and_signed_bounds_without_nearest_date_matching():
    r=time_evidence(-100,300);assert r['raw_from']==-100 and r['compatible_with_positive_year200'] is True and not r['calendar_harmonized']
    assert time_evidence(300,100)['state']=='reversed_time_bounds'
    assert time_evidence(None,300)['compatible_with_positive_year200'] is None
    assert time_evidence('100',300)['state']=='invalid_time_bounds'
    assert time_evidence(0,100)['zero_year_present'] and time_evidence(0,100)['compatible_with_positive_year200'] is False
