"""Frozen production-circulation audit; --fetch acquires missing references only."""
from pathlib import Path
from dataclasses import asdict
from multiprocessing import Pool
import argparse
import importlib.metadata
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
from benchmark_local import DEV12_SPECS
from circulation_reference import (acquire, column_targets, geographic_wind,
    native_aggregation, projection_jacobian, vector_scores)
from earth_benchmark import load_params
from earth_calendar import observation_weights
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json
from rotclimate import earth, joint
from rotclimate.koppen import monthly_stats
from rotclimate.model import ClimateModel
from rotclimate.numerics import matrix_product

PLAN = ROOT/'calibration/circulation_audit_20261026/plan.json'
OUT = ROOT/'output/circulation_audit_20261026'


def one(job):
    name, plan, identity, reference = job
    path, arrays = OUT/f'{name}.json', OUT/f'{name}.npz'
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case = earth.region_case(name, plan['cell_km'])
    derived = case_hash(case, observed_sea=True)
    if path.exists():
        row = json.loads(path.read_text())
        if (row['identity'] != identity or row['case_identity'] != derived or row['status'] != 'passed'
                or not row['numerics']['all_checks_passed'] or file_hash(arrays) != row['arrays_sha256']):
            raise ValueError('Changed inputs or preserved failed circulation run')
        return row
    row = dict(region=name, identity=identity, case_identity=derived)
    started = time.monotonic()
    try:
        p = earth.earth_params(joint.earth_profile(load_params(ROOT/plan['physics'])), case)
        g = case.grid
        model = ClimateModel(p, grid=g)
        model.trace_cells = np.indices(g.land.shape).reshape(2, -1)
        result = model.run()
        row['numerics'] = result.numerics
        if not result.numerics['all_checks_passed']:
            raise ValueError('Climate numerical certificate failed')
        old = monthly_stats(result.T, result.P, result.days, p.year_days,
            summer_solstice=p.winter_solstice_day+p.year_days/2)
        mask = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
        archive = ROOT/plan['archive']
        prior = json.loads((archive/'cases'/f'{name}.json').read_text())
        prior_cells = archive/'cells'/f'{name}.npz'
        if case_hash(case) != prior['case_identity'] or file_hash(prior_cells) != prior['cells_sha256']:
            raise ValueError('Archived control geography or cells changed')
        with np.load(prior_cells) as saved:
            for key, value in [('Ts', old['Tm'][:, mask]), ('Ps', old['Pm'][:, mask]),
                               ('To', case.obs_T[:, mask]), ('Po', case.obs_P[:, mask])]:
                if not np.array_equal(value.astype(np.float32), saved[key]):
                    raise ValueError('Exact old climate control failed: '+key)
        spec = earth.REGIONS[name]
        mirrored = spec['lat0'] < 0
        latitude = -g.lat if mirrored else g.lat
        geometry = projection_jacobian(latitude, case.lon, spec['lat0'], spec['lon0'])
        weights, durations, order = observation_weights(result.days, mirrored=mirrored)
        fields = {var: reference[name, var] for var in ('uwnd', 'vwnd', 'shum', 'hgt')}
        targets, partial_water, height = column_targets(fields)
        # Reference stays in physical Jan-Dec coordinates until this explicit order.
        targets = {key: value[order].reshape(12, 2, -1) for key, value in targets.items()}
        area = g.cell_km**2/geometry[-1]
        aggregate, masks, native_area, coverage = native_aggregation(latitude, case.lon, area,
            g.inmap, g.land, g.elev, fields['shum'], height)
        recorded = dict(original_month=order, month_days=durations,
            reference_latitude=fields['shum'].latitude, reference_longitude=fields['shum'].longitude,
            partial_water_kgm2=partial_water[order], native_area_km2=native_area,
            **{f'mask_{key}': value for key, value in masks.items()},
            **{f'reference_{key}': value for key, value in targets.items()})
        scores = {}
        for kind, keys in [('surface', ('u', 'v')), ('moisture', ('moisture_u', 'moisture_v'))]:
            components = [np.stack([step[key] for step in model.trace]).reshape((len(result.days),)+g.land.shape) for key in keys]
            east, north = geographic_wind(*components, geometry, mirrored=mirrored)
            monthly = np.stack([matrix_product(weights, value.reshape(len(result.days), -1)).reshape((12,)+g.land.shape)
                                for value in (east, north)], axis=1)
            native = aggregate(monthly)
            recorded['model_'+kind] = native
            scores[kind] = {}
            for target, values in targets.items():
                scores[kind][target] = {}
                for land_type, selected in masks.items():
                    scores[kind][target][land_type] = None if not selected.any() else vector_scores(
                        native[:, :, selected], values[:, :, selected], native_area[selected], durations)
        with arrays.with_suffix('.tmp').open('wb') as stream:
            np.savez_compressed(stream, **recorded)
        arrays.with_suffix('.tmp').replace(arrays)
        row.update(status='passed', legacy_exact=True, params=asdict(p), mirrored=mirrored,
            coverage=coverage, scores=scores, original_month=order.tolist(), arrays_sha256=file_hash(arrays))
    except Exception as error:
        row.update(status='failed', error=repr(error))
    row['seconds'] = time.monotonic()-started
    write_json(path, row)
    print(name+': '+row['status'], flush=True)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    plan = json.loads(PLAN.read_text())
    fields, reference_sources = acquire(ROOT, plan, fetch=args.fetch)
    if not args.run:
        print('Reference provenance verified; no integrations requested.')
        return
    OUT.mkdir(parents=True, exist_ok=True)
    sources = list((ROOT/'rotclimate').glob('*.py')) + [PLAN, Path(__file__), DEV12_SPECS,
        ROOT/'scripts/circulation_reference.py', ROOT/'scripts/earth_calendar.py',
        ROOT/'scripts/local_benchmark_protocol.py', ROOT/'scripts/earth_benchmark.py',
        ROOT/'experiments/v10_forcing_audit.py', ROOT/plan['physics']]
    # The old reader imports these constants; bind that source epoch too.
    sources += list((ROOT/'rotclimate_v10').glob('*.py'))
    sources += [ROOT/'experiments'/f'{name}.py' for name in ['v10_thermodynamics']]
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{key}.zip' for key in ['tavg', 'prec', 'elev', 'vapr']]
    for name in plan['regions']:
        sources += [ROOT/plan['archive']/'cases'/f'{name}.json', ROOT/plan['archive']/'cells'/f'{name}.npz']
    identity = freeze(OUT/'protocol.json', dict(plan=plan, references=reference_sources,
        sources={str(p.relative_to(ROOT)): file_hash(p) for p in sources},
        packages={name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'numba']}))
    with Pool(2) as pool:
        rows = pool.map(one, [(name, plan, identity, fields) for name in plan['regions']])
    complete = all(row['status'] == 'passed' for row in rows)
    write_json(OUT/'review.json', dict(complete=complete, identity=identity, records=rows,
        physics_or_atlas_adoption=False, scope=plan['decision']))
    if not complete:
        raise SystemExit('Failed audit runs preserved; do not interpret reference differences')


if __name__ == '__main__':
    main()
