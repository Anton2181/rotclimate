from polity.survey_observations import yes_no_evidence,north_east_evidence


def test_phase_flag_unknown_and_missing_are_not_negative_evidence():
    assert yes_no_evidence(' YES ')['state']=='recorded_yes'
    assert yes_no_evidence('No')['state']=='recorded_no'
    assert yes_no_evidence(None)['state']=='missing'
    assert yes_no_evidence('?')['state']=='unresolved'
    assert yes_no_evidence('1')['state']=='unresolved'


def test_documented_coordinate_order_is_not_automatically_swapped_or_rescued():
    assert north_east_evidence('21.1','78.2')['inside_declared_vidarbha_envelope']
    swapped=north_east_evidence('78.2','21.1')
    assert swapped['documented_latitude_longitude_valid'] and not swapped['inside_declared_vidarbha_envelope']
    assert not swapped['coordinate_swap_applied']
    assert not north_east_evidence('21 degrees','78.2')['numeric_pair']
    assert not north_east_evidence('nan','78.2')['numeric_pair']
