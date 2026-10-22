"""Scientific invariants for the experimental annual-climate target crosswalk."""
import numpy as np
import pytest

from rotclimate import biome_targets as B


def test_representative_target_climates_have_perfect_strict_fit():
    # Source polygon interiors, ordered by painted-zone ID (not polygon ID).
    indices = {'MAT': np.array([2., 10., 10., 18., 27., 27., 27.]),
               'MAP': np.array([900., 300., 2200., 650., 3000., 1400., 100.])}
    r = B.evaluate(indices, np.arange(1, 8), np.ones(7, bool))
    assert r['macro_hard'] == r['macro_soft'] == r['score'] == 1


def test_soft_credit_decreases_toward_impossible_rainfall_without_reclassifying_it():
    d = B.envelope_distance([27., 27., 27.], [3000., 6000., 12000.], [4])
    assert d[0] == 0 and 0 < d[1] < d[2]
    r = B.evaluate({'MAT': np.array([27.]), 'MAP': np.array([12000.])},
                   np.array([5]), np.array([True]))
    assert r['macro_hard'] == 0 and r['outside_share'] == 1
    assert 0 <= r['score'] < .01


def test_target_zones_are_equally_weighted_and_invalid_climates_do_not_disappear():
    r = B.evaluate({'MAT': np.array([2.]*100 + [np.nan]),
                    'MAP': np.array([900.]*101)},
                   np.array([1]*100 + [7]), np.ones(101, bool))
    assert r['macro_hard'] == r['macro_soft'] == .5
    assert r['score'] == .5


def test_unpainted_and_ocean_cells_do_not_affect_fit():
    r = B.evaluate({'MAT': np.array([27., 100., 100.]), 'MAP': np.array([100., -1., -1.])},
                   np.array([7, 0, 7]), np.array([True, True, False]))
    assert r['score'] == 1 and r['outside_share'] == 0
    with pytest.raises(ValueError, match='No painted'):
        B.evaluate({'MAT': np.array([10.]), 'MAP': np.array([100.])},
                   np.array([0]), np.array([True]))


def test_broad_profile_is_a_superset_and_layout_averaging_does_not_vote_on_ids():
    ix = {'MAT': np.array([10., 27.]), 'MAP': np.array([1100., 1400.])}
    target = np.array([1, 5]);valid = np.ones(2, bool)
    strict = B.evaluate(ix, target, valid)
    broad = B.evaluate(ix, target, valid, 'broad')
    assert broad['score'] >= strict['score'] and broad['score'] == 1
    mean = B.average([strict, strict])
    assert mean['score'] == strict['score'] and mean['layouts'] == 2
    with pytest.raises(ValueError):B.average([strict, broad])
