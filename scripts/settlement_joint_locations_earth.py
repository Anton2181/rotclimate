"""Run the preregistered 224 common-input settlement-location comparisons.

All observation pools are spent development data. This driver changes no atlas
population, food, staffing, control or settlement defaults.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity.settlement_locations import site_fields, fixed_count_sites
from polity.settlement_intensity import adaptive_count_sites
from polity.settlement_joint import density_score, history_prior, variants
from settlement_locations_earth import baseline, metrics, sha, write
from settlement_intensity_earth import quality, means

PLAN = ROOT / 'calibration/settlement_joint_locations_20261111/plan.json'
OUT = ROOT / 'output/settlement_joint_locations_20261112'
CORE = ROOT / 'output/core_population_inputs_20261111'
ORIGINAL = ROOT / 'output/settlement_locations_20261110'
SEEDS = (1, 7, 19, 43, 97)
METRICS = ('unique_F1', 'F1', 'M1', 'M3')


def checked_inputs():
    committed = subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT)
    if committed != PLAN.read_bytes():
        raise ValueError('Commit the exact comparison protocol before running')
    core = json.loads((CORE / 'results.json').read_text())
    review = json.loads((CORE / 'review.json').read_text())
    if review['status'] != 'passed':
        raise ValueError('Supported core inputs require a successful review')
    # Review is bound to this result, not merely an old successful status.
    if review['results_sha256'] != sha(CORE / 'results.json'):
        raise ValueError('Stale supported-core review')
    missing = {}
    for name, digest in core['sources'].items():
        if not (ROOT / name).is_file():
            missing[name] = digest
        elif sha(ROOT / name) != digest:
            raise ValueError('Changed core source: ' + name)
    # A resumed checkout may omit private upstream caches. Consume the exact
    # checked, committed derived inputs; do not pretend to rebuild their sources.
    for name in ('results.json', 'review.json', 'replay.json'):
        path = CORE / name
        archived = subprocess.check_output(['git', 'show', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT)
        if archived != path.read_bytes():
            raise ValueError('Archived core evidence changed: ' + name)
    if review['reviewer_sha256'] != sha(ROOT / 'scripts/review_core_population_inputs.py'):
        raise ValueError('Core reviewer source changed')
    if core['producer_sha256'] != sha(ROOT / 'scripts/build_core_population_inputs.py'):
        raise ValueError('Core producer source changed')
    replay = json.loads((CORE / 'replay.json').read_text())
    if replay['status'] != 'passed':
        raise ValueError('Archived core replay failed')
    for name, digest in replay['byte_exact_outputs'].items():
        if sha(CORE / name) != digest:
            raise ValueError('Archived replay output changed: ' + name)
    if sha(CORE / 'distances.npz') != core['distance_archive_sha256']:
        raise ValueError('Changed supported travel distances')
    inputs = {}
    for pool, receipt in core['pools'].items():
        path = ROOT / receipt['input_path']; history = CORE / f'{pool}_history.npz'
        if sha(path) != receipt['input_sha256'] or sha(history) != receipt['history_sha256']:
            raise ValueError('Changed population/history input: ' + pool)
        x = dict(np.load(path)); h = dict(np.load(history))
        required = x['land'] & x['allowed']
        if not (h['covered'][required].all() and h['connected'][required].all()
                and np.isfinite(h['distance_km'][required]).all()):
            raise ValueError('Required settlement land lacks supported history')
        if not np.array_equal(h['old_clipped_history800'], x['history']):
            raise ValueError('Old-history ablation does not share these inputs')
        inputs[pool] = dict(path=receipt['input_path'], sha256=receipt['input_sha256'],
                            history_path=str(history.relative_to(ROOT)), history_sha256=receipt['history_sha256'])
    return inputs, missing


def summarize(rows):
    ranking = []
    for name in sorted({r['variant'] for r in rows if r['family'] != 'ablation'}):
        selected = [r for r in rows if r['variant'] == name]
        pools = {p: means([r for r in selected if r['pool'] == p]) for p in ('han', 'rome')}
        average = {k: float(np.mean([p[k] for p in pools.values()])) for k in METRICS}
        ranking.append(dict(variant=name, family=selected[0]['family'], pools=pools, mean=average,
                            Q=quality(average), feasible=all(p['max_shortfall'] == 0 for p in pools.values())))
    ranking.sort(key=lambda r: (not r['feasible'], -r['Q'], r['variant']))
    feasible = [r for r in ranking if r['feasible']]
    def vector(r):
        return np.array([r['mean']['unique_F1'], r['mean']['M1'], -r['mean']['M3']])
    frontier = [r['variant'] for r in feasible if not any(
        np.all(vector(o) >= vector(r)) and np.any(vector(o) > vector(r)) for o in feasible)]
    sensitivity = {}
    for weight in (.4, .6, .8):
        leader = min(feasible, key=lambda r: (-quality(r['mean'], weight), r['variant']))
        sensitivity[str(weight)] = dict(variant=leader['variant'], family=leader['family'],
                                        Q=quality(leader['mean'], weight))
    return ranking, frontier, sensitivity


def run(out=OUT):
    inputs, missing = checked_inputs(); out.mkdir(parents=True, exist_ok=True)
    rows, positions = [], {}
    protected = [ORIGINAL / n for n in ('results.json', 'positions.npz', 'han_inputs.npz', 'rome_inputs.npz')]
    protected += [ROOT / 'atlases' / name / 'data/atlas.json' for name in ('free_fit', 'earth_fit', 'whittaker_fit')]
    protected = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    for pool, receipt in inputs.items():
        x = dict(np.load(ROOT / receipt['path'])); h = dict(np.load(ROOT / receipt['history_path']))
        cell = float(x['cell_km'])
        legacy, eligible = site_fields(x['density'], x['land'], x['water_km'], x['road'], x['elev'], cell,
                                       allowed=x['allowed'], aridity=x['aridity'])
        production = baseline(x); count = len(production)
        def save(spec, seed, towns, shortfall=0):
            key = f'{pool}__{spec["variant"]}__{seed}'
            positions[key] = np.asarray(towns, dtype=np.int64).reshape(-1, 2)
            row = dict(pool=pool, **spec, seed=seed, requested=count, shortfall=shortfall, **metrics(x, towns))
            row['Q'] = quality(row); rows.append(row)
        save(dict(variant='production', family='production'), 1, production)
        fixed = fixed_count_sites(legacy, eligible, count, cell, min_spacing_km=18.,
                                  history=h['history800'], stochastic=False)
        save(dict(variant='fixed18_L800', family='fixed'), 1, fixed.towns, fixed.shortfall)
        for spec in variants():
            score = density_score(legacy, x['density'], x['land'], eligible, spec['power'])
            prior = history_prior(h['distance_km'], spec['scale_km'], spec['floor'])
            for seed in SEEDS:
                placed = adaptive_count_sites(score, eligible, count, cell, history=prior,
                    coefficient=.35, maximum_spacing_km=45., seed=seed, stochastic=True)
                save(dict(**spec, family='adaptive'), seed, placed.towns, placed.shortfall)
            print(pool, spec['variant'], 'five seeds complete', flush=True)
        for seed in SEEDS:
            placed = adaptive_count_sites(legacy, eligible, count, cell,
                history=h['old_clipped_history800'] ** (800. / 450.), coefficient=.35,
                maximum_spacing_km=45., seed=seed, stochastic=True)
            save(dict(variant='old_clipped_b1_L450_f0', family='ablation', power=1., scale_km=450, floor=0.),
                 seed, placed.towns, placed.shortfall)
        if sha(ROOT / receipt['path']) != receipt['sha256']:
            raise ValueError('Population inputs mutated')
    if len(rows) != 224 or len(positions) != 224:
        raise ValueError('Incomplete declared placement grid')
    ranking, frontier, sensitivity = summarize(rows)
    lead = next(r for r in ranking if r['feasible'])
    np.savez_compressed(out / 'positions.npz', **positions)
    sources = [Path(__file__), ROOT / 'polity/settlement_joint.py', ROOT / 'polity/settlement_intensity.py',
               ROOT / 'polity/settlement_locations.py', ROOT / 'polity/settle.py',
               ROOT / 'scripts/settlement_locations_earth.py', ROOT / 'scripts/settlement_intensity_earth.py']
    for name, digest in protected.items():
        if sha(ROOT / name) != digest:
            raise ValueError('Protected prior evidence/atlas changed: ' + name)
    result = dict(status='exposed_development_only', adopt=False, plan_sha256=sha(PLAN),
        inputs=inputs, upstream={str((CORE / n).relative_to(ROOT)): sha(CORE / n) for n in ('results.json', 'review.json', 'replay.json')},
        sources={str(p.relative_to(ROOT)): sha(p) for p in sources}, protected=protected,
        positions_sha256=sha(out / 'positions.npz'), rows=rows, ranking=ranking,
        pareto_frontier=frontier, location_weight_sensitivity=sensitivity, development_lead=lead['variant'],
        count_policy='Natural production count on each complete current input, identical across alternatives; no observed count fitting.',
        scope='Han corrected ecological coverage; Rome original population paired control; both supported history fields. All source pools spent.',
        population_food_staff_control_changed=False, prospective_validation=False,
        caveat='Location intensity is not resident population or occupation age. No automatic fantasy adoption; shared-ledger allocation remains required.')
    result['input_replay_scope'] = dict(exact_committed_derived_inputs=True,
        upstream_raw_rebuilt_in_this_run=False, unavailable_transitive_source_files=missing)
    write(out / 'results.json', result)
    print('Completed224placements. Development lead:', lead['variant'], 'Q', lead['Q'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    run(parser.parse_args().out)
