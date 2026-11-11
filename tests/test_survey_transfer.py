import numpy as np
import pytest
from polity.survey_transfer import relative_ranks, capture_fraction, sphere_distance


def test_tied_zero_opportunity_is_preserved_in_reference():
    np.testing.assert_allclose(relative_ranks([0, 1, 2, 3], [0, 0, 2, 2]), [.25, .5, .75, 1])
    with pytest.raises(ValueError):
        relative_ranks([1], [])


def test_capture_deduplicates_cells_and_keeps_unmatched_sites():
    assert capture_fraction([0, 0, 9], [(0, 0)], 5, 3., 5.) == .5
    assert capture_fraction([0], [], 5, 3., 5.) == 0
    assert capture_fraction([], [], 5, 3., 5.) is None
    assert sphere_distance(0., 1., 0., 0.) == pytest.approx(111.1949266)
