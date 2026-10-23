"""Reproducible paired physics experiments on Earth or the three atlas worlds.

Every case retains strict numerical checks, input hashes and explicit failures.
Earth regions are reused development benchmarks, not fresh validation data.
Profiles and scientific sources are frozen on the first invocation per output.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import pickle
import sys
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from rotclimate.config import Params

GROUPS = dict(
    training=['california', 'iberia', 'southeast_us', 'levant', 'central_asia', 'east_china', 'east_australia', 'mexico'],
    former_holdout=['chile', 'cape', 'sw_australia', 'south_brazil', 'japan'],
    midlatitude=['pacific_nw', 'western_europe', 'eastern_europe', 'us_midwest', 'manchuria', 'new_zealand'])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def finite(value):
    if isinstance(value, dict): return {k: finite(v) for k, v in value.items()}
    if isinstance(value, list): return [finite(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value): return None
    return value


def one(job):
    name, profile, region, protocol, out, identity = job
    started = time.time()
    out = Path(out)
    tag = f'{name}_{region}'
    path = out / 'cases' / f'{tag}.json'
    if path.exists():
        row = json.loads(path.read_text())
        if row['identity'] != identity: raise ValueError('Case inputs changed: ' + tag)
        return row
    p = Params(**protocol['bases'][region]).replace(**profile)
    row = dict(profile=name, region=region, params=asdict(p), identity=identity)
    try:
        if protocol['mode'] == 'earth':
            from rotclimate import earth
            from rotclimate.model import ClimateModel
            case = earth.region_case(region, protocol['cell_km'])
            result = ClimateModel(earth.earth_params(p, case), grid=case.grid).run(diagnose_moisture=True)
            row['metrics'] = finite(earth.compare(result, case))
        else:
            from rotclimate.model import run_ensemble
            from rotclimate import biome_targets as B
            from scripts.whittaker_target_experiment import metrics
            result = run_ensemble(p, protocol['seeds'])
            row['metrics'] = finite(metrics(result))
            row['coverage'] = B.rendered_coverage(result)
            checkpoint = out / 'checkpoints' / f'{tag}.pkl'
            with checkpoint.with_suffix('.tmp').open('wb') as file:
                pickle.dump(dict(identity=identity, result=result), file)
            checkpoint.with_suffix('.tmp').replace(checkpoint)
        row['numerics'] = result.numerics
        if not result.numerics['all_checks_passed']: raise RuntimeError('Observed numerical checks failed')
        row['status'] = 'passed'
    except Exception as exc:
        row.update(status='failed', error=repr(exc))
    row['seconds'] = round(time.time() - started, 2)
    write(path, row)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profiles', type=Path, required=True, help='JSON mapping names to Params overrides, including baseline')
    ap.add_argument('--mode', choices=['earth', 'map'], default='earth')
    ap.add_argument('--regions', nargs='+', help='Earth region names, or atlas names in map mode')
    ap.add_argument('--start', type=Path, default=ROOT/'atlases/earth_fit/params.json')
    ap.add_argument('--cell-km', type=float, default=56.)
    ap.add_argument('--downsample', type=int, default=32)
    ap.add_argument('--seeds', nargs='+', type=int, default=[1, 2, 3])
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if not 1 <= a.workers <= 4: ap.error('Use 1–4 workers')
    profiles = json.loads(a.profiles.read_text())
    if profiles.get('baseline') != {}: ap.error('Profiles must include an unchanged baseline')
    regions = a.regions or (sum(GROUPS.values(), []) if a.mode == 'earth' else ['free_fit', 'earth_fit', 'whittaker_fit'])
    bases = {}
    for region in regions:
        path = a.start if a.mode == 'earth' else ROOT/'atlases'/region/'params.json'
        p = Params.from_json(path)
        if a.mode == 'map': p = p.replace(downsample=a.downsample)
        # Preserve saved strict criteria and reject permissive input profiles.
        if not (p.t_require_convergence and p.moisture_require_convergence and p.solver_require_convergence):
            ap.error('Base profiles must require all three convergence checks')
        bases[region] = asdict(p)
    sources = list((ROOT/'rotclimate').glob('*.py')) + [Path(__file__)]
    sources += [p for p in (ROOT/'data/source').iterdir() if p.is_file()]
    sources += [ROOT/'data/whittaker_biomes.csv', ROOT/'data/biome_target_crosswalk.json', ROOT/'data/whittaker_coverage.json']
    if a.mode == 'earth':
        sources += [ROOT/'data/cache/earth'/f'{r}_{a.cell_km:g}km_1100pad.npz' for r in regions]
        sources += [ROOT/'data/cache/earth'/f'west_fetch_{km}km.npz' for km in (1700, 5100)]
    protocol = dict(mode=a.mode, profiles=profiles, bases=bases, regions=regions,
        cell_km=a.cell_km, downsample=a.downsample, seeds=a.seeds, groups=GROUPS,
        sources={str(p.relative_to(ROOT)):sha(p) for p in sources},
        note='Paired development comparisons. No atlas promotion implied. Failed cases are retained, never averaged as successes.')
    protocol = json.loads(json.dumps(protocol))
    a.out.mkdir(parents=True, exist_ok=True)
    for folder in ['cases', 'checkpoints']: (a.out/folder).mkdir(exist_ok=True)
    frozen = a.out/'protocol.json'
    if frozen.exists() and json.loads(frozen.read_text()) != protocol:
        raise ValueError('Frozen scientific inputs changed; use a new output directory')
    write(frozen, protocol)
    identity = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    jobs = [(name, profile, region, protocol, str(a.out), identity) for name, profile in profiles.items() for region in regions]
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context('spawn')) as pool:
        pending = [pool.submit(one, job) for job in jobs]
        for future in as_completed(pending):
            row = future.result(); rows.append(row)
            metric = row.get('metrics', {})
            print(json.dumps(dict(profile=row['profile'], region=row['region'], status=row['status'],
                seconds=row['seconds'], score=metric.get('climate_distance', metric.get('zonefit')),
                error=row.get('error'))), flush=True)
    summary = dict(identity=identity, profiles={})
    for name in profiles:
        own = [r for r in rows if r['profile'] == name]
        complete = len(own) == len(regions) and all(r['status'] == 'passed' for r in own)
        record = dict(complete=complete)
        if a.mode == 'earth' and complete:
            distances = {r['region']: r['metrics']['climate_distance'] for r in own}
            record['distances'] = distances
            record['all'] = float(np.mean(list(distances.values())))
            for group, members in GROUPS.items():
                if set(members) <= set(distances): record[group] = float(np.mean([distances[r] for r in members]))
        summary['profiles'][name] = record
    write(a.out/'summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)
    if any(r['status'] != 'passed' for r in rows): raise SystemExit('Some cases failed; inspect records')


if __name__ == '__main__': main()
