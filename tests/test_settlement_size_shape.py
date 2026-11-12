"""Analytic checks of the scale-free size metrics and the catalogue gates."""
import math

import numpy as np
import pytest

from polity.settlement_size_shape import (basis_group, date_blockers, largest, refused, relative_sizes,
                                          shape_metrics)


def brute_gini(x):
    x = np.asarray(x, float)
    return np.abs(x[:, None] - x[None, :]).sum() / (2 * len(x) ** 2 * x.mean())


def test_equal_towns_have_no_inequality():
    m = shape_metrics([250.] * 200)
    assert m['gini'] == pytest.approx(0, abs=1e-12) and m['log10_sd'] == pytest.approx(0, abs=1e-12)
    assert m['largest_over_median'] == 1 and m['share_largest_1_percent'] == pytest.approx(.01)
    assert m['share_largest_10_percent'] == pytest.approx(.1) and m['rank_size_slope_top100'] == pytest.approx(0, abs=1e-12)


def test_metrics_do_not_depend_on_scale_or_order():
    rng = np.random.default_rng(3); x = rng.lognormal(5, 1, 400)
    a, b = shape_metrics(x), shape_metrics(rng.permutation(x) * 7.3)
    for key, value in a.items():
        assert b[key] == pytest.approx(value, rel=1e-12)
    assert a['gini'] == pytest.approx(brute_gini(x), rel=1e-12)


def test_zipf_sizes_have_slope_minus_one_and_known_shares():
    x = 1 / np.arange(1, 1001)
    m = shape_metrics(x)
    assert m['rank_size_slope_top100'] == pytest.approx(-1, abs=1e-12) and m['rank_size_places'] == 100
    assert m['share_largest_1_percent'] == pytest.approx(x[:10].sum() / x.sum())
    assert m['largest_over_median'] == pytest.approx(1 / np.median(x))


def test_tail_keeps_the_largest_places_only():
    x = np.arange(1., 102)
    assert list(largest(x, .25)) == list(np.arange(101., 75, -1)) and shape_metrics(x, .25)['places'] == 26
    assert shape_metrics(np.concatenate([x, np.zeros(50)]))['places'] == 101
    for bad in (0, 1.5, True):
        with pytest.raises(ValueError):
            largest(x, bad)
    for bad in ([], [0, 0], [1, -1], [1, float('nan')]):
        with pytest.raises(ValueError):
            shape_metrics(bad)


def test_density_exponent_raises_inequality_without_a_scale():
    area = np.array([1., 10, 100, 1000])
    assert list(relative_sizes(area, 0)) == list(area)
    assert shape_metrics(relative_sizes(area, .5))['gini'] > shape_metrics(relative_sizes(area, 0))['gini']
    assert shape_metrics(relative_sizes(area * 5, .2))['gini'] == pytest.approx(shape_metrics(relative_sizes(area, .2))['gini'])
    for bad in (-.1, float('inf'), True):
        with pytest.raises(ValueError):
            relative_sizes(area, bad)
    with pytest.raises(ValueError):
        relative_sizes([10, 0], 0)


def test_whole_site_dates_refuse_but_never_certify():
    assert date_blockers(150, -600, 79) == ('place_ended_before_year',) and refused(150, -600, 79)
    assert date_blockers(150, 200, 'NULL') == ('place_not_yet_founded', 'catalogue_end_unrecorded') and refused(150, 200, 'NULL')
    assert date_blockers(150, -700, 'NULL') == ('catalogue_end_unrecorded',) and not refused(150, -700, 'NULL')
    assert date_blockers(150, -200, 270) == () and not refused(150, -200, 270)
    assert refused(150, None, 300) and refused(150, 'NULL', 'NULL')
    with pytest.raises(ValueError):
        date_blockers(150.0, 1, 2)


@pytest.mark.parametrize('text,group', [('Walls', 'walls'), ('walls (Augustan)', 'walls'), ('Ramparts', 'walls'),
    ('Inhabited area, 150 or 160', 'inhabited_area'), ('Urban grid and walls', 'urban_grid'),
    ('Unspecified', 'other_or_unspecified'), ('Colonia and cannabae', 'other_or_unspecified'),
    (None, 'other_or_unspecified'), ('Lower town, 1,500 by 400 m', 'other_or_unspecified')])
def test_extent_basis_groups_follow_first_words(text, group):
    assert basis_group(text) == group
