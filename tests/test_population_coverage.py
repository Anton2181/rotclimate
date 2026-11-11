import numpy as np
import pytest
from polity.population_coverage import population_coverage,require_population_coverage


def test_missing_eastern_input_cannot_pass_as_zero_population():
    covered=population_coverage([40,40],[124.9,125.1],[40.05,39.95],[124.85,124.95])
    assert covered.tolist()==[True,False]
    with pytest.raises(ValueError,match='unknown is not zero'):
        require_population_coverage(covered,[True,True])
    require_population_coverage(covered,[True,False])
    assert not population_coverage(np.nan,124.9,[40.05,39.95],[124.85,124.95])


def test_nonregular_axes_are_rejected():
    with pytest.raises(ValueError):population_coverage(0,0,[1,0,-2],[0,1,2])
