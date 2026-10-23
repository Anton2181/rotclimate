"""Verify local rainfall with strict physics on real Earth geography.

Example: python -I scripts/benchmark_rainfall.py --fits baseline=atlases/earth_fit/params.json
    --regions california japan --out output/rainfall_check

This compares 56 km land cells with WorldClim 2.1 monthly 1970-2000 normals.
Named city samples are the containing grid cells, not station observations.
Previously used regions remain development comparisons, not new validation.
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
import sys
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from rotclimate import earth
from rotclimate.config import Params
from scripts.rainfall_metrics import LOSS_SPEC, compare, loss


def write(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)


def safe(data):
    if isinstance(data, dict): return {k:safe(v) for k,v in data.items()}
    if isinstance(data, list): return [safe(v) for v in data]
    if isinstance(data, float) and not np.isfinite(data): return None
    return data


def one(job):
    fit, region, protocol, identity, out = job
    out = Path(out)
    dest = out/'cases'/f'{fit}_{region}.json'
    if dest.exists():
        record = json.loads(dest.read_text())
        if record['identity'] != identity: raise ValueError('Case inputs changed')
        return record
    started = time.monotonic()
    record = dict(fit=fit, region=region, identity=identity)
    try:
        p = Params(**protocol['fits'][fit])
        case = earth.region_case(region, protocol['cell_km'], pad_km=protocol['pad_km'])
        result = earth.run_case(p, case, steps=p.steps_per_year)
        record['numerics'] = result.numerics
        if not result.numerics.get('all_checks_passed'):
            raise RuntimeError('Observed numerical checks failed')
        record.update(rainfall=compare(result, case), climate=safe(earth.compare(result, case)),
                      stations=safe(earth.station_table(result, case)), status='passed')
    except Exception as error:
        record.update(status='failed', error=repr(error))
    record['seconds'] = round(time.monotonic()-started, 2)
    write(dest, record)
    return record


def summarize(rows, fits, regions):
    out = {}
    keys = ['loss', 'monthly_mae_mm', 'monthly_rmse_mm', 'annual_mae_mm', 'annual_log_rmse',
            'annual_within_25pct', 'annual_within_50pct', 'seasonality_total_variation']
    for fit in fits:
        own = [r for r in rows if r['fit'] == fit]
        complete = len(own) == len(regions) and all(r['status'] == 'passed' for r in own)
        record = dict(complete=complete, expected_regions=len(regions), completed_cases=len(own))
        if complete:
            record['equal_region_mean'] = {
                key:float(np.mean([r['rainfall'][key] for r in own]))
                if all(r['rainfall'][key] is not None for r in own) else None for key in keys}
            # These percentages are explicitly pooled cells, unlike the
            # equal-region objective. Report the denominator alongside them.
            wet = sum(r['rainfall']['wet_scored_cells'] for r in own)
            record['pooled_wet_cells'] = wet
            record['pooled_annual_within_25pct'] = sum(
                (r['rainfall']['annual_within_25pct'] or 0) * r['rainfall']['wet_scored_cells']
                for r in own)/wet if wet else None
            record['pooled_annual_within_50pct'] = sum(
                (r['rainfall']['annual_within_50pct'] or 0) * r['rainfall']['wet_scored_cells']
                for r in own)/wet if wet else None
        out[fit] = record
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fits', nargs='+', required=True, help='NAME=PARAMS.json, e.g. baseline=atlases/earth_fit/params.json')
    ap.add_argument('--regions', nargs='+', default=list(earth.REGIONS), choices=list(earth.REGIONS))
    ap.add_argument('--cell-km', type=float, default=56.)
    ap.add_argument('--pad-km', type=float, default=1100.)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if not 1 <= a.workers <= 2: ap.error('Use one or two workers')
    if len(a.regions) != len(set(a.regions)): ap.error('Repeated regions change weighting')
    fits = {}
    for spec in a.fits:
        name, path = spec.split('=', 1)
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
            ap.error('Fit names must contain only letters, numbers, underscores or hyphens')
        if name in fits: ap.error('Repeated fit name')
        p = Params.from_json(path)
        if not (p.t_require_convergence and p.moisture_require_convergence and
                p.solver_require_convergence and p.moisture_residual_tol > 0):
            ap.error('Rainfall benchmarks require verified numerical criteria')
        fits[name] = asdict(p)
    sources = list((ROOT/'rotclimate').glob('*.py')) + [Path(__file__), ROOT/'scripts/rainfall_metrics.py']
    sources += [ROOT/'data/cache/earth'/f'{r}_{a.cell_km:g}km_{a.pad_km:g}pad.npz' for r in a.regions]
    sources += [ROOT/'data/cache/earth'/f'west_fetch_{km}km.npz' for km in (1700, 5100)]
    protocol = dict(fits=fits, regions=a.regions, cell_km=a.cell_km, pad_km=a.pad_km,
                    rainfall_loss=LOSS_SPEC,
                    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                    reference='WorldClim 2.1, monthly 1970-2000 normals; area-averaged to local projected cells',
                    note='Reused development regions; city values are grid-cell samples, not station observations.')
    protocol = json.loads(json.dumps(protocol))
    identity = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    a.out.mkdir(parents=True, exist_ok=True); (a.out/'cases').mkdir(exist_ok=True)
    path = a.out/'protocol.json'
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError('Frozen experiment changed; use a new output folder')
    write(path, protocol)
    jobs = [(fit, region, protocol, identity, str(a.out)) for fit in fits for region in a.regions]
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=mp.get_context('spawn')) as pool:
        pending = [pool.submit(one, job) for job in jobs]
        for future in as_completed(pending):
            row = future.result(); rows.append(row)
            print(json.dumps(dict(fit=row['fit'], region=row['region'], status=row['status'],
                                  loss=row.get('rainfall', {}).get('loss'), seconds=row['seconds'])), flush=True)
    summary = dict(identity=identity, fits=summarize(rows, fits, a.regions))
    write(a.out/'summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)
    if any(r['status'] != 'passed' for r in rows): raise SystemExit('Failed cases retained; no aggregate score')


if __name__ == '__main__': main()
