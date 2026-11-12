"""Run the declared longer-market-leg scenarios: seasonal town-to-town travel, distance-scaled loss."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_settlement_hierarchy import load, solve_case
from prepare_settlement_feedback import DATA
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_market_range_20261112/plan.json'
OUT = ROOT / 'output/settlement_market_range_20261112'
LIMIT = 12.


def key_of(mode, days, share):
    return f'{mode}_range{days}_share{round(share * 100)}'


def travel(mode, out=OUT):
    """Town-to-town days for every monthly bin, on the audited seasonal transport reconstruction."""
    from polity.administrative_world import audit_world
    from polity.administrative_hierarchy import month_graph
    x, _, _ = load(mode); nodes = x['nodes']; n = len(nodes)
    r, _ = audit_world(DATA.parent, mode)
    if set(nodes) != {t['row'] * x['land'].shape[1] + t['col'] for t in r['towns']} or not np.array_equal(x['land'], r['land']):
        raise ValueError('Transport reconstruction changed town nodes or land')
    days = np.full((12, n, n), np.inf, np.float32)
    for month in range(12):
        graph, _ = month_graph(r['world'], r['statics'], r['climate'], month, r['ports'], r['river_places'])
        for start in range(0, n, 100):
            block = dijkstra(graph, directed=True, indices=nodes[start:start + 100], limit=LIMIT)
            days[month, start:start + 100] = block[:, nodes]
        print(mode, 'town-to-town travel month', month + 1, flush=True)
    out.mkdir(parents=True, exist_ok=True); path = out / f'{mode}_travel.npz'
    np.savez_compressed(path, days=days, nodes=nodes, limit_days=LIMIT)
    reached = np.isfinite(days)
    write(out / f'{mode}_travel.json', dict(status='seasonal_town_to_town_travel', mode=mode, travel_sha256=sha(path),
        producer_sha256=sha(Path(__file__)), towns=int(n), limit_days=LIMIT, monthly_bins=12,
        graph='polity.administrative_hierarchy.month_graph on polity.administrative_world.audit_world',
        town_nodes_and_land_reproduced=True,
        mean_other_towns_within_limit_one_way=float((reached.sum(2) - 1).mean())))
    return days


def run(mode, days_each_way, share, out=OUT):
    plan = json.loads(PLAN.read_text())['scenarios']
    if mode not in plan['climate_modes'] or days_each_way not in plan['range_days_each_way'] or share not in plan['forward_share']:
        raise ValueError('Scenario outside the declared test')
    x, _, hashes = load(mode); receipt = json.loads((out / f'{mode}_travel.json').read_text())
    path = out / f'{mode}_travel.npz'
    if sha(path) != receipt['travel_sha256']:
        raise ValueError('Travel matrix changed')
    days = np.load(path)['days'].astype(float); n = days.shape[1]
    slowest = days.max(0)                                   # slowest monthly bin, a to b
    links = (slowest <= days_each_way) & (slowest.T <= days_each_way); np.fill_diagonal(links, False)
    return solve_case(mode, share, x, links, key_of(mode, days_each_way, share), PLAN, out,
        dict(hashes, travel_sha256=receipt['travel_sha256']),
        link_rule=f'at most {days_each_way} days each way in all 12 bins on the seasonal transport graph, same actor',
        leg_days=slowest, extra_producers=['scripts/build_settlement_market_range.py'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    p.add_argument('--travel', action='store_true'); p.add_argument('--days', type=int); p.add_argument('--share', type=float)
    a = p.parse_args()
    if a.travel:travel(a.mode)
    else:run(a.mode, a.days, a.share)
