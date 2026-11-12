"""Forwarding conserves people and grain, loses grain on every leg and never invents links."""
import numpy as np
import pytest

from polity.settlement_hierarchy import band_state, cohorts, forward, market_forest, year_round_links


def test_links_require_all_twelve_bins_and_exclude_self():
    landnodes = np.array([10, 20, 30, 40]); nodes = np.array([10, 30, 40])
    keys, covered, offsets = [], [], [0]
    for month in range(12):
        for site, cells in ((0, [0, 2]), (1, [0, 2, 3] if month != 5 else [2])):      # site 1 loses node 10 and 40 in one bin
            keys.append((month, site)); covered += cells; offsets.append(len(covered))
    links = year_round_links(np.array(keys), np.array(offsets), np.array(covered), landnodes, nodes)
    assert links.tolist() == [[False, True, False], [False, False, False], [False, False, False]]
    with pytest.raises(ValueError):
        year_round_links(np.array(keys), np.array(offsets), np.array(covered), landnodes, np.array([10, 25, 40]))


def test_parent_is_largest_strictly_larger_same_actor_link():
    budget = np.array([5., 9., 9., 3., 20.]); actor = np.array([0, 0, 0, 0, 1])
    links = np.ones((5, 5), bool); np.fill_diagonal(links, False)
    parent, depth = market_forest(budget, actor, links)
    assert parent.tolist() == [1, -1, -1, 1, -1]            # tie between 1 and 2 goes to the lower index; actor 1 is separate
    assert depth.tolist() == [1, 0, 0, 1, 0]
    parent, _ = market_forest(budget, np.array([0, 0, 0, -1, 1]), links)
    assert parent[3] == -1                                    # no actor: no link, missing evidence


def test_forwarding_conserves_people_and_charges_every_leg():
    people = np.array([100., 200., 400.]); budget = people.copy(); parent = np.array([1, 2, -1])
    grain = np.zeros((12, 3)); grain[0] = [120., 0., 0.]
    out = forward(people, grain, parent, budget, share=.5, retention=np.array([.9, .8, 1.]), delay_bins=1)
    assert out['residents'].tolist() == [50., 125., 525.] and out['residents'].sum() == people.sum()
    assert out['grain'][0, 0] == 60 and out['grain'][1, 1] == pytest.approx(27) and out['grain'][2, 2] == pytest.approx(21.6)
    assert out['leg_loss'].tolist() == pytest.approx([6., 5.4, 0.])
    assert grain.sum() == pytest.approx(out['grain'].sum() + out['leg_loss'].sum())


def test_zero_share_and_roots_change_nothing():
    people = np.array([10., 20.]); grain = np.arange(24.).reshape(12, 2)
    for share, parent in ((0., np.array([1, -1])), (.5, np.array([-1, -1]))):
        out = forward(people, grain, parent, people, share=share, retention=.95, delay_bins=1)
        assert np.array_equal(out['residents'], people) and np.array_equal(out['grain'], grain) and not out['leg_loss'].any()


@pytest.mark.parametrize('share,retention', [(1., .95), (-.1, .95), (.5, 0.), (.5, 1.2)])
def test_invalid_forwarding_parameters_refused(share, retention):
    with pytest.raises(ValueError):
        forward(np.ones(2), np.ones((12, 2)), np.array([1, -1]), np.array([1., 2.]), share=share, retention=retention, delay_bins=1)


def test_cohort_follows_people_actually_present():
    active, staff, civil = cohorts(np.array([149., 150., 400., 400.]), np.array([500., 500., 40., 500.]),
        np.array([True, True, True, False]), institutional_request=100., minimum_community=50.)
    assert active.tolist() == [False, True, False, False] and staff.tolist() == [0., 100., 0., 0.]
    assert civil.tolist() == [149., 50., 400., 400.]


def test_band_states():
    assert band_state(.5, .4, .6) == 'within_reference_band' and band_state(.4, .4, .6) == 'within_reference_band'
    assert band_state(.3, .4, .6) == 'more_equal_than_every_reference' and band_state(.7, .4, .6) == 'more_unequal_than_every_reference'
