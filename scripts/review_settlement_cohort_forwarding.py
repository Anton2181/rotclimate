"""Independent review of cohort-protected forwarding: recursion from the roots, both rules, grain, cohorts, metrics."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from review_settlement_feedback import cycle, inventory, production, repeating_initial
from review_settlement_hierarchy import BASE, close, travel_links
from review_settlement_size_shape import TAILS, metrics, same
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_cohort_forwarding_20261112/plan.json'
OUT = ROOT / 'output/settlement_cohort_forwarding_20261112'
MARKET = ROOT / 'output/settlement_market_range_20261112'
SHARE = .5; FLOOR = 150.


def check_case(mode, days, rule, x, links, slowest):
    folder = OUT / f'{mode}_range{days}_share50_{rule}'
    r = json.loads((folder / 'results.json').read_text()); f = dict(np.load(folder / 'fields.npz'))
    assert r['fields_sha256'] == sha(folder / 'fields.npz') and r['plan_sha256'] == sha(PLAN) and r['adopt'] is False
    for p, digest in r['producers'].items():assert sha(ROOT / p) == digest, p
    assert (r['rule'], r['floor_people'], r['forward_share'], r['range_days_each_way']) == (rule, FLOOR, SHARE, days)
    flat_folder = MARKET / f'{mode}_range{days}_share50'; flat = dict(np.load(flat_folder / 'fields.npz'))
    assert r['flat_share_fields_sha256'] == sha(flat_folder / 'fields.npz')
    base = dict(np.load(BASE / f'{mode}_h600_f0.075/fields.npz')); assert r['base_fields_sha256'] == sha(BASE / f'{mode}_h600_f0.075/fields.npz')
    n = len(x['nodes']); local = x['local_index']; owner = x['owner']; people = x['people'][local]
    np.testing.assert_array_equal(np.unpackbits(f['links'])[:n * n].reshape(n, n).astype(bool), links)
    budget = np.bincount(owner, weights=people * .075, minlength=n); close(f['budget'], budget)
    parent = np.full(n, -1)
    for a in range(n):
        if x['actor'][a] < 0:continue
        for b in np.flatnonzero(links[a]).tolist():
            if x['actor'][b] == x['actor'][a] and budget[b] > budget[a] and (parent[a] < 0 or budget[b] > budget[parent[a]]):parent[a] = b
    np.testing.assert_array_equal(parent, f['parent']); np.testing.assert_array_equal(parent, flat['parent'])
    retention = np.array([.95 ** max(1., slowest[a, parent[a]]) if parent[a] >= 0 else 1. for a in range(n)])
    # Declared regression: the draws are those of the published flat-share case.
    draw = f['draw']; np.testing.assert_array_equal(draw, flat['draw'])
    capable = x['affiliated'] & (x['civilian_request'] >= 50); np.testing.assert_array_equal(capable, f['capable'])
    children = [[] for _ in range(n)]
    for a in range(n):
        if parent[a] >= 0:children[parent[a]].append(a)
    cache = {}

    def fraction(holding, can):
        if not can:return SHARE
        if rule == 'excess':return SHARE * (1 - FLOOR / holding) if holding > FLOOR else 0.
        if holding < FLOOR:return SHARE
        return (holding - FLOOR) / holding if holding - FLOOR < SHARE * holding else SHARE

    def state(j):
        """What town j holds (people, monthly grain) once everything below it has arrived."""
        if j not in cache:
            holding = float(draw[j]); grain = f['local_arrivals'][:, j].astype(float).copy()
            for c in sorted(children[j], key=lambda k: (budget[k], k)):
                h, g = state(c); share = fraction(h, capable[c])
                holding += h * share; grain += np.roll(g * share, 1) * retention[c]
            cache[j] = (holding, grain)
        return cache[j]
    residents = np.zeros(n); arrivals = np.zeros((12, n)); passed = np.zeros(n); lost = np.zeros(n)
    for j in range(n):
        h, g = state(j); share = fraction(h, capable[j]) if parent[j] >= 0 else 0.
        passed[j] = h * share; residents[j] = h - passed[j]; arrivals[:, j] = g * (1 - share); lost[j] = (g * share).sum() * (1 - retention[j])
    close(f['total'], residents, atol=1e-6); close(f['passed_people'], passed, atol=1e-6)
    close(f['arrivals'], arrivals, rtol=1e-9, atol=1e-1); close(f['leg_loss'], lost, rtol=1e-9, atol=1e-1)
    close(f['held_before_passing'], residents + passed, atol=1e-6)
    assert abs(residents.sum() - draw.sum()) <= 1e-7 * draw.sum()
    assert abs(f['local_arrivals'].sum() - arrivals.sum() - lost.sum()) <= 1e-9 * arrivals.sum()
    # The floor holds: a capable town that held the floor before passing keeps at least the floor.
    protected = capable & (parent >= 0) & (residents + passed >= FLOOR)
    assert np.all(residents[protected] >= FLOOR - 1e-7)
    if rule == 'excess':assert np.all(passed[capable & (residents + passed <= FLOOR)] == 0)
    need = np.broadcast_to(residents * 2500 * 365 / 12, (12, n)); capacity = residents * 2500 * 90
    year = inventory(arrivals, need, capacity, repeating_initial(arrivals, need, capacity)); cycle(year)
    assert np.all(year['unmet'] <= 1e-7 * np.maximum(1, year['needed'])); close(f['town_consumed'], year['consumed'], atol=1.)
    active = x['affiliated'] & (residents >= 150 - 1e-9) & (x['civilian_request'] >= 50)
    exact = x['affiliated'] & (residents >= 150) & (x['civilian_request'] >= 50)
    np.testing.assert_array_equal(exact, f['active'])
    borderline = int((active != exact).sum())            # towns held at the floor by rounding only
    close(f['staff'], np.where(f['active'], 100., 0.)); close(f['civilian'] + f['staff'], residents, atol=1e-6)
    moved = people * .075 * np.divide(draw, budget, out=np.zeros(n), where=budget > 0)[owner]
    close(f['moved'], moved); close(f['rural'], people - moved)
    produced = production(x['potential_kcal'][local], x['listed_hours'][local], x['reaping_hours'][local], f['rural'], 600)[0]
    close(f['rural_harvested'], produced, atol=1.)
    deficit = np.bincount(owner, weights=f['rural_unmet'] > 1e-8 * np.maximum(1, f['rural_needed']), minlength=n)
    assert f['source_supported'][draw > 0].all() and np.array_equal(deficit == 0, f['source_supported'])
    assert abs(x['people'].sum() - (x['people'].sum() - people.sum()) - f['rural'].sum() - residents.sum()) <= 1e-8 * x['people'].sum()
    assert r['active_sources'] == int(f['active'].sum()) and r['base_active_sources'] == int(base['active'].sum())
    assert r['flat_share_active_sources'] == int(flat['active'].sum())
    assert r['cohorts_lost_against_base'] == int((base['active'] & ~f['active']).sum())
    assert r['cohorts_gained_against_base'] == int((~base['active'] & f['active']).sum())
    assert r['cohorts_kept_that_flat_share_lost'] == int((f['active'] & ~flat['active']).sum())
    assert abs(r['town_people'] - residents.sum()) <= 1e-6 and abs(r['people_passed_up'] - passed.sum()) <= 1e-6
    assert abs(r['town_people'] - r['flat_share_town_people']) <= 1e-6
    band = json.loads((ROOT / 'output/settlement_size_shape_20261112/results.json').read_text())['reference_band']; inside = 0
    for label, tail in TAILS.items():
        own = metrics(f['total'], tail, exact=True); same(r['shape_metrics'][label], own, 1e-8)
        same(r['flat_share_shape_metrics'][label], metrics(flat['total'], tail, exact=True), 1e-8)
        for name in ('gini', 'log10_sd'):
            low, high = band[label][name]
            state_name = 'within_reference_band' if low <= own[name] <= high else 'more_equal_than_every_reference' if own[name] < low else 'more_unequal_than_every_reference'
            assert r['shape_verdict'][label][name]['state'] == state_name; inside += state_name == 'within_reference_band'
    assert r['shape_checks_within_band'] == inside and r['shape_supported'] == (inside == 6)
    return dict(key=r['key'], residents=float(residents.sum()), largest=float(residents.max()), gini=r['shape_metrics']['all_places']['gini'],
        checks_within_band=inside, cohorts=int(f['active'].sum()), base_cohorts=int(base['active'].sum()), flat_share_cohorts=int(flat['active'].sum()),
        towns_at_floor_within_rounding=borderline)


def main():
    plan = json.loads(PLAN.read_text())['scenarios']; rows = []
    for mode in plan['climate_modes']:
        x = dict(np.load(BASE / f'{mode}_inputs.npz'))
        for days in plan['range_days_each_way']:
            links, slowest = travel_links(mode, days, MARKET)
            for rule in plan['rules']:rows.append(check_case(mode, days, rule, x, links, slowest))
        print(mode, 'reviewed', flush=True)
    write(OUT / 'review.json', dict(status='passed', plan_sha256=sha(PLAN), reviewer_sha256=sha(Path(__file__)),
        results_sha256={str((OUT / r['key'] / 'results.json').relative_to(ROOT)): sha(OUT / r['key'] / 'results.json') for r in rows}, cases=rows,
        checks='links and forest rebuilt; holdings by recursion from the roots; both passing rules re-implemented; grain redistributed; pooled food by a separate monthly recurrence; floor honoured; draws equal the published flat-share case; population and grain closure; cohort rule; production and rural source gate; metrics and verdicts',
        reviewer_scope='Independent accounting and metric review of declared scenarios. Not a validation of the floor, share, range or rules, absolute sizes or locations.'))
    print('Reviewed', len(rows), 'cohort-protected cases.')
    for r in rows:print(r)


if __name__ == '__main__':main()
