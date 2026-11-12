"""Prevent unit, date, detection and overflow errors entering resident fitting."""
from dataclasses import replace
import pytest
from polity.settlement_size_evidence import HousingSample


def sample():
    return HousingSample('one-place', 4, .25, 45., 'dated excavation')


def test_partial_housing_sample_is_not_automatically_city_census():
    x=sample()
    assert x.reference(5)['people']==3600
    assert x.reference(5)['sampled_fraction']==.25/45
    assert not x.reference(5)['direct_census']
    with pytest.raises(ValueError, match='sample_phase_unresolved'):x.for_calibration(150,5)
    # Even observing the entire mapped extent does not establish dates or completeness.
    with pytest.raises(ValueError):replace(x,sample_area_ha=45).for_calibration(150,5)


def test_year_and_measurement_certifications_are_all_required():
    x=replace(sample(),phase_start=100,phase_end=200,representative_sample=True)
    with pytest.raises(ValueError,match='contemporaneous_extent'):x.for_calibration(150,5)
    x=replace(x,extent_matches_phase=True)
    assert x.for_calibration(150,5)['qualification']=='dated_conditional_housing_reference'
    with pytest.raises(ValueError,match='outside_sample_phase'):x.for_calibration(300,5)
    with pytest.raises(ValueError,match='excludes_year'):replace(x,excluded_years=(150,)).for_calibration(150,5)


def test_missing_one_phase_endpoint_is_not_continuous_occupation():
    x=replace(sample(),phase_start=50,representative_sample=True,extent_matches_phase=True)
    with pytest.raises(ValueError,match='sample_phase_unresolved'):x.for_calibration(150,5)


@pytest.mark.parametrize('changes',[dict(properties=0),dict(properties=2.5),dict(properties=True),
    dict(sample_area_ha=46),dict(sample_area_ha=0),dict(site_area_ha=float('nan')),
    dict(phase_start=200,phase_end=100),dict(provenance=''),dict(representative_sample='yes')])
def test_invalid_measurements_refused(changes):
    with pytest.raises(ValueError):replace(sample(),**changes)


@pytest.mark.parametrize('household',[0,-1,float('inf'),float('nan'),True])
def test_invalid_household_assumptions_refused(household):
    with pytest.raises(ValueError):sample().reference(household)


def test_overflow_cannot_become_an_infinite_size_target():
    with pytest.raises(ValueError,match='overflow'):
        HousingSample('tiny',4,1e-300,1e100,'synthetic').reference(5)
