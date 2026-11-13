"""Placement iteration: heartland prior strength at fixed 18 km spacing, cross-pool selection.

Declared in calibration/settlement_placement_iteration_20261113/plan.json.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity.settlement_locations import site_fields, fixed_count_sites
from polity.settlement_joint import history_prior
from settlement_locations_earth import baseline, metrics, sha, write
from settlement_intensity_earth import quality

PLAN = ROOT / 'calibration/settlement_placement_iteration_20261113/plan.json'
OUT = ROOT / 'output/settlement_placement_iteration_20261113'
POOLS = ROOT / 'output/settlement_locations_20261110'; CORE = ROOT / 'output/core_population_inputs_20261111'
OLD = ROOT / 'output/settlement_joint_locations_20261112/positions.npz'
QUADS = ('north_west', 'north_east', 'south_west', 'south_east')


def masks(allowed):
    ar, ac = np.nonzero(allowed); mr, mc = np.median(ar), np.median(ac); yy, xx = np.indices(allowed.shape)
    return dict(north_west=(yy <= mr) & (xx <= mc), north_east=(yy <= mr) & (xx > mc),
                south_west=(yy > mr) & (xx <= mc), south_east=(yy > mr) & (xx > mc))


def run(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    plan = json.loads(PLAN.read_text()); out.mkdir(parents=True, exist_ok=True)
    old = np.load(OLD); table = {}; positions = {}; counts = {}
    paths = {p: ROOT / r['input_path'] for p, r in json.loads((CORE / 'results.json').read_text())['pools'].items()}
    for pool in ('han', 'rome'):
        x = dict(np.load(paths[pool])); h = np.load(CORE / f'{pool}_history.npz'); cell = float(x['cell_km'])
        score, eligible = site_fields(x['density'], x['land'], x['water_km'], x['road'], x['elev'], cell, allowed=x['allowed'], aridity=x['aridity'])
        production = np.asarray(baseline(x)); n = len(production)
        if not np.array_equal(production, old[f'{pool}__production__1']):
            raise ValueError('Production control not reproduced')
        placed = {'production': production}
        for L in plan['family']['values']:
            prior = None if L == 'none' else history_prior(h['distance_km'], float(L), 0.)
            p = fixed_count_sites(score, eligible, n, cell, min_spacing_km=18., history=prior, stochastic=False)
            if p.shortfall:
                raise ValueError('Shortfall')
            placed[f'L{L}'] = np.asarray(p.towns)
        if not np.array_equal(placed['L800'], old[f'{pool}__fixed18_L800__1']):
            raise ValueError('L800 control does not reproduce fixed18_L800')
        mk = masks(x['allowed']); obs = np.column_stack(np.unravel_index(x['real'], x['allowed'].shape))
        counts[pool] = dict(observed={q: int((x['allowed'] & m)[obs[:, 0], obs[:, 1]].sum()) for q, m in mk.items()})
        for name, towns in placed.items():
            positions[f'{pool}__{name}'] = towns
            row = dict(whole=quality(metrics(x, towns))); cnt = {}
            for q, m in mk.items():
                sub = dict(x); sub['allowed'] = x['allowed'] & m
                inside = towns[sub['allowed'][towns[:, 0], towns[:, 1]]]
                row[q] = quality(metrics(sub, inside)); cnt[q] = len(inside)
            row['quadrant_mean'] = float(np.mean([row[q] for q in QUADS]))
            table[f'{pool}__{name}'] = row; counts[pool][name] = cnt
    variants = [f'L{L}' for L in plan['family']['values']]
    best = lambda pool: max(reversed(variants), key=lambda v: table[f'{pool}__{v}']['quadrant_mean'])   # ties to weaker prior
    chosen = {'han': best('rome'), 'rome': best('han')}; in_pool = {p: best(p) for p in ('han', 'rome')}
    wins = sum(table[f'{p}__{chosen[p]}'][q] > table[f'{p}__production'][q] for p in chosen for q in QUADS)
    whole = all(table[f'{p}__{chosen[p]}']['whole'] > table[f'{p}__production']['whole'] for p in chosen)
    overall = max(reversed(variants), key=lambda v: np.mean([table[f'{p}__{v}'][q] for p in ('han', 'rome') for q in QUADS]))
    np.savez_compressed(out / 'positions.npz', **positions)
    result = dict(status='placement_iteration_cross_pool_development', plan_sha256=sha(PLAN), producer_sha256=sha(__file__),
        controls=dict(production_reproduced=True, L800_equals_fixed18_L800=True),
        inputs={p: dict(path=str(v.relative_to(ROOT)), sha256=sha(v)) for p, v in paths.items()}, scores=table, centre_counts=counts,
        cross_selected=chosen, in_pool_selected=in_pool, quadrant_wins=int(wins), both_pools_better=bool(whole),
        passed=bool(wins >= 6 and whole), best_over_all_eight_quadrants=overall,
        wins_by_variant={v: int(sum(table[f'{p}__{v}'][q] > table[f'{p}__production'][q] for p in ('han', 'rome') for q in QUADS)) for v in variants},
        positions_sha256=sha(out / 'positions.npz'))
    write(out / 'results.json', result); return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('--out', type=Path, default=OUT); r = run(a.parse_args().out)
    for k, v in r['scores'].items(): print(k.ljust(20), ' '.join(f'{v[q]:.3f}' for q in ('whole',) + QUADS + ('quadrant_mean',)))
    print({k: r[k] for k in ('cross_selected', 'in_pool_selected', 'quadrant_wins', 'both_pools_better', 'passed', 'best_over_all_eight_quadrants', 'wins_by_variant')})
    for p, c in r['centre_counts'].items(): print(p, {k: list(v.values()) for k, v in c.items()})
