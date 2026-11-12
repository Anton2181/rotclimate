"""A cohort-capable town keeps its floor; people and grain still move in one proportion and are conserved."""
import numpy as np
import pytest

from polity.settlement_cohort_forwarding import forward_with_floor, passed_fraction
from polity.settlement_hierarchy import forward


def chain():
    people = np.array([100., 200., 400., 1000.]); parent = np.array([3, 3, 3, -1])
    grain = np.zeros((12, 4)); grain[0] = [50., 80., 160., 400.]
    return people, grain, parent, people.copy()


@pytest.mark.parametrize('held,capable,rule,expected', [
    (400., True, 'excess', .5 * 250 / 400), (150., True, 'excess', 0.), (100., True, 'excess', 0.), (0., True, 'excess', 0.),
    (400., True, 'capped', .5), (200., True, 'capped', .25), (150., True, 'capped', 0.), (100., True, 'capped', .5),
    (0., True, 'capped', .5), (400., False, 'excess', .5), (100., False, 'capped', .5)])
def test_passing_fraction_rules(held, capable, rule, expected):
    assert passed_fraction(held, capable, share=.5, floor=150., rule=rule) == pytest.approx(expected)


@pytest.mark.parametrize('rule', ['excess', 'capped'])
def test_zero_floor_is_the_published_flat_share(rule):
    people, grain, parent, budget = chain()
    old = forward(people, grain, parent, budget, share=.5, retention=.9, delay_bins=1)
    new = forward_with_floor(people, grain, parent, budget, np.ones(4, bool), share=.5, retention=.9, delay_bins=1, floor=0., rule=rule)
    for key in ('residents', 'grain', 'passed_people', 'leg_loss'):
        assert np.array_equal(old[key], new[key])


@pytest.mark.parametrize('rule,residents', [('excess', [100., 175., 275., 1150.]), ('capped', [50., 150., 200., 1300.])])
def test_floor_protects_capable_towns_and_conserves(rule, residents):
    people, grain, parent, budget = chain()
    out = forward_with_floor(people, grain, parent, budget, np.ones(4, bool), share=.5, retention=.9, delay_bins=1, floor=150., rule=rule)
    assert out['residents'].tolist() == pytest.approx(residents) and out['residents'].sum() == pytest.approx(people.sum())
    assert grain.sum() == pytest.approx(out['grain'].sum() + out['leg_loss'].sum())
    held = out['residents'] + out['passed_people']
    assert np.all(out['residents'][(held >= 150) & (parent >= 0)] >= 150 - 1e-12)
    # People and grain leave each town in the same proportion.
    assert out['sent_grain'][0] == pytest.approx(grain[0] * out['passed_fraction'])


def test_incapable_towns_pass_the_flat_share():
    people, grain, parent, budget = chain()
    out = forward_with_floor(people, grain, parent, budget, np.array([True, False, True, True]), share=.5, retention=.9,
        delay_bins=1, floor=150., rule='capped')
    assert out['residents'][1] == 100. and out['passed_fraction'][1] == .5


def test_invalid_inputs_refused():
    people, grain, parent, budget = chain(); ok = np.ones(4, bool)
    for kwargs in (dict(share=1., retention=.9, floor=150., rule='capped'), dict(share=.5, retention=0., floor=150., rule='capped'),
                   dict(share=.5, retention=.9, floor=-1., rule='capped'), dict(share=.5, retention=.9, floor=150., rule='other')):
        with pytest.raises(ValueError):
            forward_with_floor(people, grain, parent, budget, ok, delay_bins=1, **kwargs)
