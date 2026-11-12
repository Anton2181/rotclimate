"""Independent review of the market-hierarchy scenarios: links, chains, grain, people, cohorts, metrics."""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from review_settlement_feedback import cycle, inventory, production, repeating_initial
from review_settlement_size_shape import TAILS, metrics, same
from settlement_locations_earth import sha, write

BASE = ROOT / 'output/settlement_feedback_20261112'
FAMILIES = {
    'hierarchy': dict(plan=ROOT / 'calibration/settlement_hierarchy_20261112/plan.json',
                      out=ROOT / 'output/settlement_hierarchy_20261112'),
    'market': dict(plan=ROOT / 'calibration/settlement_market_range_20261112/plan.json',
                   out=ROOT / 'output/settlement_market_range_20261112')}


def close(a, b, rtol=1e-9, atol=1e-3):
    np.testing.assert_allclose(a, b, rtol=rtol, atol=atol)


def footprint_links(mode, nodes):
    """Membership of every town node in every site-month footprint, by plain set lookups."""
    f = dict(np.load(BASE / f'{mode}_footprints.npz')); land = f['landnodes'].tolist(); where = {node: i for i, node in enumerate(land)}
    town = [where[int(node)] for node in nodes]; months = {}; cells = f['covered'].tolist(); offsets = f['offsets'].tolist()
    for k, (month, site) in enumerate(f['keys'].tolist()):
        covered = set(cells[offsets[k]:offsets[k + 1]])
        months.setdefault(site, []).append({b for b, cell in enumerate(town) if cell in covered})
    links = np.zeros((len(nodes), len(nodes)), bool)
    for site, sets in months.items():
        if len(sets) == 12:
            for b in set.intersection(*sets):
                if b != site:links[site, b] = True
    return links, None


def travel_links(mode, limit, out):
    days = np.load(out / f'{mode}_travel.npz')['days']; n = days.shape[1]
    links = np.ones((n, n), bool); slowest = np.zeros((n, n))
    for month in range(12):
        there = days[month].astype(float); links &= (there <= limit) & (there.T <= limit); slowest = np.maximum(slowest, there)
    links[np.arange(n), np.arange(n)] = False
    return links, slowest


def spot_check_travel(mode, out):
    """Reverse searches on the transposed graph must reproduce stored outward times."""
    from scipy.sparse.csgraph import dijkstra
    from polity.administrative_world import audit_world
    from polity.administrative_hierarchy import month_graph
    z = dict(np.load(out / f'{mode}_travel.npz')); days, nodes = z['days'], z['nodes']
    r, _ = audit_world(ROOT / 'atlases/earth_fit', mode); chosen = np.random.default_rng(20261112).choice(len(nodes), 40, replace=False)
    checked = 0
    for month in (0, 4, 8):
        graph, _ = month_graph(r['world'], r['statics'], r['climate'], month, r['ports'], r['river_places'])
        inward = dijkstra(graph.T.tocsr(), directed=True, indices=nodes[chosen], limit=12.)[:, nodes]
        stored = days[month][:, chosen].T
        assert np.array_equal(np.isfinite(inward), np.isfinite(stored))
        finite = np.isfinite(stored); np.testing.assert_allclose(inward[finite], stored[finite], rtol=2e-6); checked += int(finite.sum())
    return checked


def check_case(folder, plan_path, mode, share, x, links, slowest):
    r = json.loads((folder / 'results.json').read_text()); f = dict(np.load(folder / 'fields.npz'))
    assert r['fields_sha256'] == sha(folder / 'fields.npz') and r['plan_sha256'] == sha(plan_path)
    for p, digest in r['producers'].items():assert sha(ROOT / p) == digest, p
    assert r['inputs_sha256'] == sha(BASE / f'{mode}_inputs.npz') and r['forward_share'] == share and r['adopt'] is False
    base_folder = BASE / f'{mode}_h600_f0.075'; base = dict(np.load(base_folder / 'fields.npz'))
    assert r['base_fields_sha256'] == sha(base_folder / 'fields.npz') == json.loads((base_folder / 'results.json').read_text())['fields_sha256']
    np.testing.assert_array_equal(f['base_total'], base['total']); np.testing.assert_array_equal(f['base_active'], base['active'])
    n = len(x['nodes']); local = x['local_index']; owner = x['owner']; people = x['people'][local]
    np.testing.assert_array_equal(np.unpackbits(f['links'])[:n * n].reshape(n, n).astype(bool), links)
    budget = np.bincount(owner, weights=people * .075, minlength=n); close(f['budget'], budget)
    # Forest by an explicit search over each town's linked candidates.
    parent = np.full(n, -1)
    for a in range(n):
        best = -1
        if x['actor'][a] >= 0:
            for b in np.flatnonzero(links[a]).tolist():
                if x['actor'][b] == x['actor'][a] and budget[b] > budget[a] and (best < 0 or budget[b] > budget[best]):best = b
        parent[a] = best
    np.testing.assert_array_equal(parent, f['parent'])
    depth = np.zeros(n, int)
    for a in range(n):
        b = a
        while parent[b] >= 0:b = parent[b]; depth[a] += 1; assert depth[a] <= n
    np.testing.assert_array_equal(depth, f['depth'])
    retention = np.full(n, .95)
    if slowest is not None:
        retention = np.array([.95 ** max(1., slowest[a, parent[a]]) if parent[a] >= 0 else 1. for a in range(n)])
        close(f['leg_days'], [max(1., slowest[a, parent[a]]) if parent[a] >= 0 else 0. for a in range(n)], atol=1e-12)
    # People: every catchment's draw is walked up its own chain.
    draw = f['draw']; assert np.all(draw >= 0) and np.all(draw <= f['upper'] + 1e-7) and np.all(draw <= budget + 1e-7)
    moved = people * .075 * np.divide(draw, budget, out=np.zeros(n), where=budget > 0)[owner]
    close(f['moved'], moved); close(f['rural'], people - moved); close(np.bincount(owner, weights=moved, minlength=n), draw)
    residents = np.zeros(n); grain = np.zeros((12, n)); lost = np.zeros(n); worst = np.ones(n)
    for c in range(n):
        amount = draw[c]; food = f['local_arrivals'][:, c].copy(); a = c
        while parent[a] >= 0 and share > 0:
            residents[a] += amount * (1 - share); grain[:, a] += food * (1 - share)
            lost[a] += (food * share).sum() * (1 - retention[a])
            amount *= share; food = np.roll(food * share, 1) * retention[a]; worst[c] *= retention[a]; a = parent[a]
        residents[a] += amount; grain[:, a] += food
    close(f['total'], residents); close(f['arrivals'], grain, rtol=1e-9, atol=1e-2); close(f['leg_loss'], lost, atol=1e-2)
    close(f['chain_retention'], worst, atol=1e-12)
    assert abs(residents.sum() - draw.sum()) <= 1e-7 * max(1, draw.sum())
    assert abs(f['local_arrivals'].sum() - grain.sum() - lost.sum()) <= 1e-9 * max(1, grain.sum())
    # Pooled town grain by the separate monthly recurrence; no resident may go unfed.
    need = np.broadcast_to(residents * 2500 * 365 / 12, (12, n)); capacity = residents * 2500 * 90
    year = inventory(grain, need, capacity, repeating_initial(grain, need, capacity)); cycle(year)
    assert np.all(year['unmet'] <= 1e-7 * np.maximum(1, year['needed'])); close(f['town_consumed'], year['consumed'], atol=1e-1)
    # The full-chain stream of every positive catchment is fed on its own.
    positive = draw > 0; stream_need = np.broadcast_to(draw * 2500 * 365 / 12, (12, n)); stream = f['local_arrivals'] * worst
    alone = inventory(stream, stream_need, draw * 2500 * 90, repeating_initial(stream, stream_need, draw * 2500 * 90))
    assert np.all(alone['unmet'][positive] <= 1e-7 * np.maximum(1, alone['needed'][positive]))
    # Cohorts on residents actually present.
    active = x['affiliated'] & (residents >= 150) & (x['civilian_request'] >= 50)
    np.testing.assert_array_equal(active, f['active']); close(f['staff'], np.where(active, 100., 0.)); close(f['civilian'] + f['staff'], residents)
    # Origins: work-limited production and the rural source-food gate.
    produced = production(x['potential_kcal'][local], x['listed_hours'][local], x['reaping_hours'][local], f['rural'], 600)[0]
    close(f['rural_harvested'], produced, atol=1.); close(f['rural_needed'], f['rural'] * 2500 * 365, atol=1.)
    deficit = np.bincount(owner, weights=f['rural_unmet'] > 1e-8 * np.maximum(1, f['rural_needed']), minlength=n)
    np.testing.assert_array_equal(deficit == 0, f['source_supported']); assert f['source_supported'][positive].all()
    outside = x['people'].sum() - people.sum()
    assert abs(x['people'].sum() - outside - f['rural'].sum() - residents.sum()) <= 1e-8 * x['people'].sum()
    # Reported counts, metrics and verdicts.
    assert abs(r['town_people'] - residents.sum()) <= 1e-6 and r['active_sources'] == int(active.sum())
    assert r['cohorts_lost'] == int((base['active'] & ~active).sum()) and r['cohorts_gained'] == int((~base['active'] & active).sum())
    assert r['viable_communities'] == int((residents - np.where(active, 100., 0.) >= 50).sum())
    assert abs(r['grain_lost_on_forwarding_legs_kcal'] - lost.sum()) <= 1e-9 * max(1, lost.sum())
    children = np.bincount(parent[parent >= 0], minlength=n); forest = r['forest']
    assert (forest['towns_with_parent'], forest['maximum_depth'], forest['maximum_children'], forest['linked_pairs_year_round']) == (
        int((parent >= 0).sum()), int(depth.max()), int(children.max()), int(links.sum()))
    assert forest['isolated_towns'] == int(((parent < 0) & (children == 0)).sum())
    band = json.loads((ROOT / 'output/settlement_size_shape_20261112/results.json').read_text())['reference_band']
    assert r['shape_results_sha256'] == sha(ROOT / 'output/settlement_size_shape_20261112/results.json'); states = set()
    for label, tail in TAILS.items():
        own = metrics(residents, tail, exact=True); same(r['shape_metrics'][label], own, 1e-8)
        same(r['base_shape_metrics'][label], metrics(base['total'], tail, exact=True), 1e-8)
        for name in ('gini', 'log10_sd'):
            low, high = band[label][name]; v = r['shape_verdict'][label][name]
            state = 'within_reference_band' if low <= own[name] <= high else 'more_equal_than_every_reference' if own[name] < low else 'more_unequal_than_every_reference'
            assert v['state'] == state and v['reference_band'] == [low, high]; states.add(state)
    assert r['shape_supported'] == (states == {'within_reference_band'})
    top = int(np.argmax(residents)); assert r['largest_towns'][0]['site'] == top
    return dict(key=r['key'], towns_with_parent=int((parent >= 0).sum()), residents=float(residents.sum()),
        largest=float(residents.max()), gini=r['shape_metrics']['all_places']['gini'], cohorts=int(active.sum()),
        shape_supported=r['shape_supported'], states=sorted(states))


def main(family):
    spec = FAMILIES[family]; plan = json.loads(spec['plan'].read_text())['scenarios']; out = spec['out']; rows = []; spot = {}
    for mode in plan['climate_modes']:
        x = dict(np.load(BASE / f'{mode}_inputs.npz'))
        if family == 'hierarchy':
            links, slowest = footprint_links(mode, x['nodes'])
            for share in plan['forward_share']:
                rows.append(check_case(out / f'{mode}_share{round(share * 100)}', spec['plan'], mode, share, x, links, slowest))
        else:
            receipt = json.loads((out / f'{mode}_travel.json').read_text()); assert receipt['travel_sha256'] == sha(out / f'{mode}_travel.npz')
            spot[mode] = spot_check_travel(mode, out)
            for limit in plan['range_days_each_way']:
                links, slowest = travel_links(mode, limit, out)
                for share in plan['forward_share']:
                    rows.append(check_case(out / f'{mode}_range{limit}_share{round(share * 100)}', spec['plan'], mode, share, x, links, slowest))
        print(family, mode, 'reviewed', flush=True)
    results = {str((out / r['key'] / 'results.json').relative_to(ROOT)): sha(out / r['key'] / 'results.json') for r in rows}
    write(out / 'review.json', dict(status='passed', family=family, plan_sha256=sha(spec['plan']), reviewer_sha256=sha(Path(__file__)),
        results_sha256=results, cases=rows, travel_times_spot_checked=spot,
        checks='links and forest rebuilt; every catchment walked up its chain for people and grain; pooled and full-chain food by a separate monthly recurrence; population and grain closure; cohort rule; work-limited production and rural source gate; metrics and verdicts',
        reviewer_scope='Independent accounting and metric review of declared scenarios. Not a validation of the share, range, link rule, absolute sizes or locations.'))
    print('Reviewed', len(rows), family, 'cases.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--family', choices=tuple(FAMILIES), required=True)
    main(p.parse_args().family)
