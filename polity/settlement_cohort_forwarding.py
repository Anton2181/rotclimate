"""Market forwarding that leaves a cohort-capable town its cohort.

Same people, grain, links and losses as the market hierarchy. Only the amount
a town passes up changes: a town that can hold the existing cohort keeps the
floor (cohort plus civilian minimum) and passes from what is above it.
"""
import numpy as np

from harvest.food_stocks import periodic_food_year
from .settlement_hierarchy import MarketHierarchy, cohorts

RULES = ('excess', 'capped')


def passed_fraction(held, capable, *, share, floor, rule):
    """Fraction of its people AND grain one town passes to its market.

    A town with no residents has no proportion of people to follow: under the
    flat and capped rules its collected grain moves up at the flat share, as in
    the published scenarios; under the excess rule nothing is above the floor,
    so nothing moves.
    """
    if rule not in RULES:
        raise ValueError('Unknown passing rule')
    if not capable or floor == 0:
        return share
    if rule == 'excess':
        return share * (held - floor) / held if held > floor else 0.
    return min(share, (held - floor) / held) if held >= floor else share


def forward_with_floor(people, grain, parent, budget, capable, *, share, retention, delay_bins, floor, rule):
    """Pass people and grain up each chain in the same proportion; return what stays at every town."""
    held = np.asarray(people, float).copy(); food = np.asarray(grain, float).copy()
    parent = np.asarray(parent); n = len(held); retention = np.broadcast_to(np.asarray(retention, float), (n,))
    capable = np.asarray(capable, bool)
    if food.shape != (12, n) or parent.shape != (n,) or capable.shape != (n,) or not 0 <= share < 1:
        raise ValueError('Twelve grain bins by town, a parent and capability per town and a share in [0,1) required')
    if np.any((retention <= 0) | (retention > 1)) or not np.isfinite(floor) or floor < 0:
        raise ValueError('Retention in (0,1] and a finite nonnegative floor required')
    passed = np.zeros(n); sent = np.zeros((12, n)); lost = np.zeros(n); fraction = np.zeros(n)
    for a in np.argsort(np.asarray(budget, float), kind='stable'):       # children always precede their parent
        if parent[a] < 0 or share == 0:
            continue
        fraction[a] = passed_fraction(held[a], capable[a], share=share, floor=floor, rule=rule)
        amount = held[a] * fraction[a]
        passed[a] = amount; sent[:, a] = food[:, a] * fraction[a]
        held[a] -= amount; food[:, a] -= sent[:, a]
        held[parent[a]] += amount
        food[:, parent[a]] += np.roll(sent[:, a], delay_bins) * retention[a]
        lost[a] = sent[:, a].sum() * (1 - retention[a])
    return dict(residents=held, grain=food, passed_people=passed, sent_grain=sent, leg_loss=lost, passed_fraction=fraction)


class CohortProtectedHierarchy(MarketHierarchy):
    """Identical solver and feasibility test; only the split between a town and its market differs."""

    def __init__(self, inputs, parent, depth, *, rule, floor=None, **options):
        super().__init__(inputs, parent, depth, **options)
        if rule not in RULES:
            raise ValueError('Unknown passing rule')
        self.rule = rule
        self.floor = self.institutional_request + self.minimum_community if floor is None else float(floor)
        self.capable = np.asarray(self.x.affiliated, bool) & (np.asarray(self.x.civilian_request, float) >= self.minimum_community)

    def distribute(self, final):
        x = self.x; draw = final['total']
        flow = forward_with_floor(draw, final['flow']['arrivals'], self.parent, self.budget, self.capable, share=self.share,
            retention=self.leg_retention, delay_bins=self.leg_delay, floor=self.floor, rule=self.rule)
        residents = flow['residents']
        need = np.broadcast_to(residents * self.kcal_day * self.year_days / 12, (12, len(residents)))
        food = periodic_food_year(flow['grain'], need, residents * self.kcal_day * self.destination_store_days,
            loss_fraction_year=self.loss_fraction_year, step_days=self.year_days / 12, record=True)
        if np.any(food.unmet > 1e-8 * np.maximum(1, food.needed)):
            raise RuntimeError('Pooled town grain does not feed the residents left after forwarding')
        if abs(residents.sum() - draw.sum()) > 1e-9 * max(1, draw.sum()):
            raise RuntimeError('Forwarding changed the number of residents')
        active, staff, civil = cohorts(residents, x.civilian_request, x.affiliated,
            institutional_request=self.institutional_request, minimum_community=self.minimum_community)
        return dict(flow, draw=draw.copy(), town_food=food, active=active, staff=staff, civil=civil,
            community_viable=civil >= self.minimum_community)
