"""Lower-order towns pass a share of residents and collected grain to a larger linked centre.

One finite ledger: people leave origin cells once, grain is collected once,
and every forwarding leg loses grain. Nothing here adds people or food.
"""
import numpy as np

from harvest.food_stocks import periodic_food_year
from .settlement_feedback import CerealFeedback


def year_round_links(keys, offsets, covered, landnodes, nodes):
    """links[a, b]: town b lies inside town a's two-way footprint in all twelve bins."""
    landnodes = np.asarray(landnodes); nodes = np.asarray(nodes)
    position = np.searchsorted(landnodes, nodes)
    if np.any(position >= len(landnodes)) or not np.array_equal(landnodes[position], nodes):
        raise ValueError('Every town node must be a land node of the footprint grid')
    months = np.zeros((len(nodes), len(nodes)), np.int16); seen = set()
    for k, (month, site) in enumerate(np.asarray(keys)):
        if (int(month), int(site)) in seen or not 0 <= month < 12:
            raise ValueError('One footprint per site and monthly bin required')
        seen.add((int(month), int(site)))
        months[site] += np.isin(position, covered[offsets[k]:offsets[k + 1]])
    links = months == 12
    np.fill_diagonal(links, False)
    return links


def market_forest(budget, actor, links):
    """Parent = linked same-actor town with the largest strictly larger budget; -1 for roots."""
    budget = np.asarray(budget, float); actor = np.asarray(actor); links = np.asarray(links, bool)
    n = len(budget)
    if links.shape != (n, n) or actor.shape != (n,) or not np.isfinite(budget).all() or np.any(budget < 0):
        raise ValueError('Aligned finite budgets, actors and links required')
    parent = np.full(n, -1, int)
    for a in range(n):
        if actor[a] < 0:
            continue
        candidates = np.flatnonzero(links[a] & (actor == actor[a]) & (budget > budget[a]))
        if len(candidates):
            parent[a] = candidates[np.argmax(budget[candidates])]   # argmax returns the lowest index on ties
    depth = np.zeros(n, int)
    for a in np.argsort(-budget, kind='stable'):
        if parent[a] >= 0:
            depth[a] = depth[parent[a]] + 1
    return parent, depth


def forward(people, grain, parent, budget, *, share, retention, delay_bins):
    """Pass share of everything held up each chain; return what stays at every town."""
    held = np.asarray(people, float).copy(); food = np.asarray(grain, float).copy()
    parent = np.asarray(parent); n = len(held); retention = np.broadcast_to(np.asarray(retention, float), (n,))
    if food.shape != (12, n) or parent.shape != (n,) or not 0 <= share < 1 or np.any((retention <= 0) | (retention > 1)):
        raise ValueError('Twelve grain bins by town, a parent per town, share in [0,1) and retention in (0,1] required')
    passed = np.zeros(n); sent = np.zeros((12, n)); lost = np.zeros(n)
    for a in np.argsort(np.asarray(budget, float), kind='stable'):      # children always precede their parent
        if parent[a] < 0 or share == 0:
            continue
        passed[a] = held[a] * share; sent[:, a] = food[:, a] * share
        held[a] -= passed[a]; food[:, a] -= sent[:, a]
        held[parent[a]] += passed[a]
        food[:, parent[a]] += np.roll(sent[:, a], delay_bins) * retention[a]
        lost[a] = sent[:, a].sum() * (1 - retention[a])
    return dict(residents=held, grain=food, passed_people=passed, sent_grain=sent, leg_loss=lost)


def cohorts(residents, request, affiliated, *, institutional_request, minimum_community):
    """The existing cohort rule, applied to the people actually present after forwarding."""
    total = np.asarray(residents, float)
    active = np.asarray(affiliated, bool) & (total >= institutional_request + minimum_community) & (
        np.asarray(request, float) >= minimum_community)
    staff = np.where(active, institutional_request, 0.)
    return active, staff, total - staff


class MarketHierarchy(CerealFeedback):
    """The coupled solver with one extra test: the full-chain stream must still be fed."""

    def __init__(self, inputs, parent, depth, *, forward_share, leg_retention=None, **options):
        super().__init__(inputs, **options)
        self.parent = np.asarray(parent); self.depth = np.asarray(depth)
        if self.parent.shape != self.budget.shape or self.depth.shape != self.budget.shape:
            raise ValueError('One parent and depth per town required')
        if not np.isfinite(forward_share) or not 0 <= forward_share < 1:
            raise ValueError('Forward share must lie in [0,1)')
        self.share = float(forward_share)
        n = len(self.budget); self.leg_delay = self.collection_options['delay_bins']
        self.leg_retention = np.broadcast_to(np.asarray(
            self.collection_options['retention'] if leg_retention is None else leg_retention, float), (n,)).copy()
        if np.any((self.leg_retention <= 0) | (self.leg_retention > 1)):
            raise ValueError('Leg retention must lie in (0,1]')
        # Share of a catchment's grain that survives the whole chain to its root.
        self.chain = np.ones(n)
        if self.share > 0:
            for a in np.argsort(-self.budget, kind='stable'):
                if self.parent[a] >= 0:
                    self.chain[a] = self.leg_retention[a] * self.chain[self.parent[a]]

    def evaluate(self, total):
        trial = super().evaluate(total)
        if self.share > 0:
            target = trial['total']
            need = np.broadcast_to(target * self.kcal_day * self.year_days / 12, (12, len(target)))
            stream = periodic_food_year(trial['flow']['arrivals'] * self.chain, need,
                target * self.kcal_day * self.destination_store_days, loss_fraction_year=self.loss_fraction_year,
                step_days=self.year_days / 12)
            trial['feasible'] = trial['feasible'] & (stream.unmet <= 1e-8 * np.maximum(1, stream.needed))
        return trial

    def distribute(self, final):
        """Town-level residents and pooled grain for a solved catchment draw."""
        x = self.x; draw = final['total']
        flow = forward(draw, final['flow']['arrivals'], self.parent, self.budget, share=self.share,
            retention=self.leg_retention, delay_bins=self.leg_delay)
        residents = flow['residents']
        need = np.broadcast_to(residents * self.kcal_day * self.year_days / 12, (12, len(residents)))
        food = periodic_food_year(flow['grain'], need, residents * self.kcal_day * self.destination_store_days,
            loss_fraction_year=self.loss_fraction_year, step_days=self.year_days / 12, record=True)
        if np.any(food.unmet > 1e-8 * np.maximum(1, food.needed)):
            raise RuntimeError('Pooled town grain does not feed the forwarded residents')
        if abs(residents.sum() - draw.sum()) > 1e-9 * max(1, draw.sum()):
            raise RuntimeError('Forwarding changed the number of residents')
        active, staff, civil = cohorts(residents, x.civilian_request, x.affiliated,
            institutional_request=self.institutional_request, minimum_community=self.minimum_community)
        return dict(flow, draw=draw.copy(), town_food=food, active=active, staff=staff, civil=civil,
            community_viable=civil >= self.minimum_community)


def band_state(value, low, high):
    if low <= value <= high:
        return 'within_reference_band'
    return 'more_equal_than_every_reference' if value < low else 'more_unequal_than_every_reference'
