"""Audit actual r39 moisture sources with exact archived climate controls."""
from dataclasses import asdict
from pathlib import Path
from multiprocessing import Pool
import argparse
import json
import sys
import time
import importlib.metadata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np

from benchmark_local import DEV12_SPECS, temperature_metrics
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json
from rainfall_metrics import local_metrics
from rotclimate import earth, joint
from rotclimate.koppen import monthly_stats, monthly_weights
from rotclimate.model import ClimateModel


def audit_one(job):
    name, plan, identity, out = job
    out = Path(out)
    started = time.monotonic()
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case = earth.region_case(name, float(plan['cell_km']))
    derived = case_hash(case)
    record, arrays = out/f'{name}.json', out/f'{name}.npz'
    if record.exists():
        previous = json.loads(record.read_text())
        if (previous['identity'] != identity or previous['case_identity'] != derived or
                previous['status'] != 'passed' or file_hash(arrays) != previous['arrays_sha256']):
            raise ValueError('Changed inputs or preserved failed audit: '+name)
        return previous
    row = dict(region=name, identity=identity, case_identity=derived)
    try:
        physics = load_params(ROOT/plan['physics'])
        p = earth.earth_params(joint.earth_profile(physics), case)
        historical = earth.earth_params(physics, case)
        active = joint.SHARED_FIELDS | joint.NUMERICAL_FIELDS | joint.EARTH_FORCING.keys() | {'lat_center'}
        if any(getattr(p, key) != getattr(historical, key) for key in active):
            raise ValueError('Active historical Earth inputs changed')
        evidence = ROOT/plan['archive']
        old_record = json.loads((evidence/'cases'/f'{name}.json').read_text())
        old_cells = evidence/'cells'/f'{name}.npz'
        if derived != old_record['case_identity'] or file_hash(old_cells) != old_record['cells_sha256']:
            raise ValueError('Archived case inputs changed')
        g = case.grid
        mask = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
        model = ClimateModel(p, grid=g)
        model.trace_cells = np.nonzero(mask)
        result = model.run(diagnose_moisture=True)
        if result.numerics.get('all_checks_passed') is not True:
            raise ValueError('Observed per-step numerical checks failed')
        stats = monthly_stats(result.T, result.P, result.days, p.year_days,
                              summer_solstice=p.winter_solstice_day+p.year_days/2)
        with np.load(old_cells) as archived:
            for key, actual in [('Ts', stats['Tm'][:, mask]), ('Ps', stats['Pm'][:, mask]),
                                ('To', case.obs_T[:, mask]), ('Po', case.obs_P[:, mask])]:
                if not np.array_equal(actual.astype(np.float32), archived[key]):
                    raise ValueError('Exact archived climate control failed: '+key)
        weights = monthly_weights(result.days, p.year_days)
        def monthly(values):
            shape = values.shape[1:]
            return (weights @ values.reshape(len(result.days), -1)).reshape((12,)+shape)
        sl = g.map_slice()
        cropped = mask[sl]
        fields = dict(valid=cropped, elev=g.elev[sl], lat=g.lat[sl], lon=case.lon[sl],
                      observed=case.obs_P[(slice(None),)+sl], simulated=stats['Pm'][(slice(None),)+sl])
        for key, value in result.moisture_budget.items():
            fields[key] = monthly(value) * p.year_days/12
        for key in ['W', 'Ws', 'A', 'u', 'v', 'gain', 'sinkd', 'orog', 'conv', 'damp']:
            fields['trace_'+key] = monthly(np.stack([step[key] for step in model.trace]))
        fields['trace_relative_humidity'] = monthly(np.stack([step['W']/step['Ws'] for step in model.trace]))
        terms = ['evaporation', 'column_drying', 'convergence_import', 'advection', 'diffusion', 'storm_exchange']
        reconstructed = sum(fields[key] for key in terms) - fields['simulated']
        gap = float(np.max(np.abs((reconstructed-fields['residual'])[:, cropped])))
        if gap > 1e-4:
            raise ValueError('Exported equation components do not reconstruct the residual')
        groups = dict(all_land=cropped, lowland=cropped & (fields['elev'] < 1000),
                      upland=cropped & (fields['elev'] >= 1000))
        summaries = {}
        for label, own in groups.items():
            if not own.any():
                continue
            summaries[label] = dict(cells=int(own.sum()),
                monthly={key: fields[key][:, own].mean(1).tolist() for key in
                         ['observed', 'simulated', *terms, 'monsoon_drying', 'residual', 'absolute_residual']})
            # Traces use the full scored-land order, without the cropped sea.
            trace_own = (g.elev[mask] < 1000 if label == 'lowland' else
                         g.elev[mask] >= 1000 if label == 'upland' else np.ones(mask.sum(), bool))
            summaries[label]['trace_monthly'] = {key: fields['trace_'+key][:, trace_own].mean(1).tolist()
                                                for key in ['relative_humidity', 'W', 'Ws', 'A', 'u', 'v',
                                                            'gain', 'sinkd', 'orog', 'conv', 'damp']}
        temporary = arrays.with_suffix('.tmp')
        with temporary.open('wb') as stream:
            np.savez_compressed(stream, **fields)
        temporary.replace(arrays)
        row.update(status='passed', exact_climate_control=True, params=asdict(p), numerics=result.numerics,
                   arrays_sha256=file_hash(arrays), source_reconstruction_max_mm_month=gap,
                   temperature=temperature_metrics(stats['Tm'][:, mask], case.obs_T[:, mask]),
                   rain=local_metrics(stats['Pm'], np.nan_to_num(case.obs_P), mask), summaries=summaries)
    except Exception as error:
        row.update(status='failed', error=repr(error))
    row['seconds'] = time.monotonic()-started
    write_json(record, row)
    print(name+': '+row['status'], flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'output/moisture_sources_20261026')
    args = parser.parse_args()
    plan_path = ROOT/'calibration/moisture_sources_20261026/plan.json'
    plan = json.loads(plan_path.read_text())
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sources = list((ROOT/'rotclimate').glob('*.py')) + [Path(__file__), plan_path, DEV12_SPECS,
        ROOT/plan['physics'], ROOT/plan['world'], ROOT/'scripts/benchmark_local.py',
        ROOT/'scripts/earth_benchmark.py', ROOT/'scripts/local_benchmark_protocol.py',
        ROOT/'scripts/rainfall_metrics.py']
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{key}.zip' for key in ['tavg', 'prec', 'elev', 'vapr']]
    for name in plan['regions']:
        sources += [ROOT/plan['archive']/'cases'/f'{name}.json', ROOT/plan['archive']/'cells'/f'{name}.npz']
    identity = freeze(out/'protocol.json', dict(plan=plan,
        source_hashes={str(path.relative_to(ROOT)): file_hash(path) for path in sources},
        packages={name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'numba']}))
    with Pool(2) as pool:
        rows = pool.map(audit_one, [(name, plan, identity, str(out)) for name in plan['regions']])
    complete = all(row['status'] == 'passed' for row in rows)
    write_json(out/'review.json', dict(complete=complete, identity=identity, records=rows,
        physics_or_atlas_adoption=False, interpretation=plan['scope']))
    if not complete:
        raise SystemExit('Failed audit preserved; do not interpret or publish failed controls')


if __name__ == '__main__':
    main()
