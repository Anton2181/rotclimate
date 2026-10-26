"""Frozen shear pilot: exact legacy controls, protected land/ocean comparisons."""
from dataclasses import asdict
from pathlib import Path
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
from benchmark_local import DEV12_SPECS, temperature_metrics
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json
from rainfall_metrics import local_metrics
from rotclimate import earth, joint
from rotclimate.config import Params
from rotclimate.koppen import monthly_stats, monthly_weights
from rotclimate.numerics import matrix_product
from rotclimate.model import ClimateModel


def run_one(job):
    name, region, ratio, plan, identity, out = job
    out = Path(out)
    folder = out/name
    folder.mkdir(exist_ok=True)
    path, arrays = folder/f'{region}.json', folder/f'{region}.npz'
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case = earth.region_case(region, float(plan['cell_km']))
    derived = case_hash(case, observed_sea=True)
    if path.exists():
        previous = json.loads(path.read_text())
        if (previous['identity'] != identity or previous['case_identity'] != derived or previous['status'] != 'passed'
                or file_hash(arrays) != previous['arrays_sha256']):
            raise ValueError('Changed or preserved failed shear run: '+str(path))
        return previous
    started = time.monotonic()
    row = dict(name=name, region=region, ratio=ratio, identity=identity, case_identity=derived)
    try:
        physics = load_params(ROOT/plan['physics']).replace(moisture_pressure_drag_ratio=ratio)
        p = earth.earth_params(joint.earth_profile(physics), case)
        g = case.grid
        mask = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
        domain = np.ones_like(mask)
        domain[[0, -1], :] = False
        domain[:, [0, -1]] = False
        sea = domain & ~g.land & np.isfinite(g.obs_sst).all(0) & (g.obs_sst.min(0) > -1)
        model = ClimateModel(p, grid=g)
        model.trace_cells = np.nonzero(domain)
        result = model.run(diagnose_moisture=True)
        if result.numerics.get('all_checks_passed') is not True:
            raise ValueError('Required per-step numerical checks failed')
        st = monthly_stats(result.T, result.P, result.days, p.year_days,
                           summer_solstice=p.winter_solstice_day+p.year_days/2)
        if ratio == 1:
            archive = ROOT/plan['archive']
            prior = json.loads((archive/'cases'/f'{region}.json').read_text())
            old_cells = archive/'cells'/f'{region}.npz'
            if case_hash(case) != prior['case_identity'] or file_hash(old_cells) != prior['cells_sha256']:
                raise ValueError('Archived geography or cell evidence changed')
            with np.load(old_cells) as old:
                for key, value in [('Ts', st['Tm'][:, mask]), ('Ps', st['Pm'][:, mask]),
                                   ('To', case.obs_T[:, mask]), ('Po', case.obs_P[:, mask])]:
                    if not np.array_equal(value.astype(np.float32), old[key]):
                        raise ValueError('Legacy control changed: '+key)
        weights = monthly_weights(result.days, p.year_days)
        traces = {key: np.stack([step[key] for step in model.trace])
                  for key in ['SST', 'u', 'v', 'moisture_u', 'moisture_v', 'W', 'Ws']}
        speed = np.hypot(traces['moisture_u'], traces['moisture_v'])
        row['column_speed'] = dict(maximum_ms=float(speed.max()), p95_ms=float(np.percentile(speed, 95)))
        monthly_sst = matrix_product(weights, traces['SST'])
        sea_columns = sea[domain]
        if sea_columns.any():
            error = monthly_sst[:, sea_columns]-g.obs_sst[:, sea]
            row['sst'] = dict(cells=int(sea.sum()), monthly_mae_C=float(np.abs(error).mean()))
        else:
            row['sst'] = None
        sl = g.map_slice()
        fields = dict(valid=mask[sl], elev=g.elev[sl], observed=case.obs_P[(slice(None),)+sl],
                      simulated=st['Pm'][(slice(None),)+sl])
        for key, value in result.moisture_budget.items():
            fields[key] = matrix_product(weights, value.reshape(len(result.days), -1)).reshape(
                (12,)+value.shape[1:])*p.year_days/12
        columns = mask[domain]
        fields.update({key: matrix_product(weights, value[:, columns]) for key, value in traces.items() if key != 'SST'})
        row['monthly_rain'] = dict(simulated=st['Pm'][:, mask].mean(1).tolist(),
                                   observed=case.obs_P[:, mask].mean(1).tolist())
        row['rain'] = local_metrics(st['Pm'], np.nan_to_num(case.obs_P), mask)
        row['temperature'] = temperature_metrics(st['Tm'][:, mask], case.obs_T[:, mask])
        row.update(status='passed', legacy_exact=ratio == 1, params=asdict(p), numerics=result.numerics)
        with arrays.with_suffix('.tmp').open('wb') as stream:
            np.savez_compressed(stream, **fields)
        arrays.with_suffix('.tmp').replace(arrays)
        row['arrays_sha256'] = file_hash(arrays)
    except Exception as error:
        row.update(status='failed', error=repr(error))
    row['seconds'] = time.monotonic()-started
    write_json(path, row)
    print(name+'/'+region+': '+row['status'], flush=True)
    return row


def screening(rows, plan):
    names = plan['regions']
    controls = {r['region']: r for r in rows if r['name'] == 'reference'}
    if set(controls) != set(names) or any(r['status'] != 'passed' or not r['legacy_exact'] for r in controls.values()):
        raise ValueError('Need all exact reference controls before screening')
    limits = plan['screen']
    reviews = {}
    for name in plan['candidates']:
        candidates = {r['region']: r for r in rows if r['name'] == name}
        failures, ratios = [], {}
        if set(candidates) != set(names) or any(r['status'] != 'passed' for r in candidates.values()):
            reviews[name] = dict(qualifies=False, failures=['Incomplete or failed numerical screen'])
            continue
        for region in names:
            b, c = controls[region], candidates[region]
            if b['case_identity'] != c['case_identity']:
                raise ValueError('Unpaired region or SST observations')
            t = c['temperature']['monthly_mae_C']/b['temperature']['monthly_mae_C']
            rain = c['rain']['loss']/b['rain']['loss']
            ratios[region] = dict(temperature=t, rain=rain, S=.5*(t+rain))
            if region == 'north_india':
                if rain > limits['north_india_rain_loss_ratio_max']:
                    failures.append('North India rain improvement below 5%')
            elif .5*(t+rain) > limits['each_other_region_S_max']:
                failures.append(region+': combined error worsens by more than 2%')
            if (b['sst'] is None) != (c['sst'] is None):
                raise ValueError('SST mask changed')
            if b['sst'] is not None and (b['sst']['cells'] != c['sst']['cells'] or
                    c['sst']['monthly_mae_C'] > b['sst']['monthly_mae_C']+limits['each_region_integrated_SST_mae_increase_max_C']):
                failures.append(region+': integrated SST protection failed')
            if (c['column_speed']['maximum_ms'] > limits['column_speed_domain_max_ms'] or
                    c['column_speed']['p95_ms'] > limits['column_speed_domain_p95_ms']):
                failures.append(region+': column-wind speed bound failed')
        def ratio_of_means(key, metric):
            return sum(candidates[r][key][metric] for r in names)/sum(controls[r][key][metric] for r in names)
        t, rain = ratio_of_means('temperature', 'monthly_mae_C'), ratio_of_means('rain', 'loss')
        combined = .5*(t+rain)
        if combined > limits['mean_combined_S_max']:
            failures.append('Mean combined improvement below 0.5%')
        if rain > limits['mean_rain_loss_ratio_max']:
            failures.append('Mean rain improvement below 1%')
        if t > limits['mean_temperature_ratio_max']:
            failures.append('Mean temperature worsens by more than 1%')
        reviews[name] = dict(qualifies=not failures, failures=failures, S=combined,
                              temperature_ratio=t, rain_ratio=rain, regions=ratios)
    return reviews


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'output/column_shear_20261026')
    args = parser.parse_args()
    path = ROOT/'calibration/column_shear_20261026/plan.json'
    plan = json.loads(path.read_text())
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sources = list((ROOT/'rotclimate').glob('*.py'))+[path, Path(__file__), DEV12_SPECS,
        ROOT/plan['physics'], earth.WOA_SST, ROOT/'scripts/benchmark_local.py', ROOT/'scripts/earth_benchmark.py',
        ROOT/'scripts/local_benchmark_protocol.py', ROOT/'scripts/rainfall_metrics.py',
        ROOT/'scripts/advance_column_shear.py', ROOT/'scripts/check_constrained_blend.py',
        ROOT/'scripts/gate_local.py', ROOT/'scripts/build_woa_sst.py',
        ROOT/'calibration/local_accuracy_20261023/policy_v2.json']
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{key}.zip' for key in ['tavg', 'prec', 'elev', 'vapr']]
    for region in plan['regions']:
        sources += [ROOT/plan['archive']/'cases'/f'{region}.json', ROOT/plan['archive']/'cells'/f'{region}.npz']
    identity = freeze(out/'protocol.json', dict(plan=plan,
        sources={str(p.relative_to(ROOT)): file_hash(p) for p in sources},
        packages={name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'numba']}))
    rows = []
    with Pool(2) as pool:
        rows = pool.map(run_one, [('reference', region, 1., plan, identity, str(out)) for region in plan['regions']])
        write_json(out/'progress.json', dict(complete=False, records=rows))
        if any(r['status'] != 'passed' or not r['legacy_exact'] for r in rows):
            raise SystemExit('Preserve failed control; do not run candidates')
        for name, ratio in plan['candidates'].items():
            rows += pool.map(run_one, [(name, region, ratio, plan, identity, str(out)) for region in plan['regions']])
            write_json(out/'progress.json', dict(complete=False, records=rows))
    reviews = screening(rows, plan)
    selected = sorted((name for name in reviews if reviews[name]['qualifies']), key=lambda name: reviews[name]['S'])
    selected = selected[:plan['screen']['maximum_development_finalists']]
    write_json(out/'review.json', dict(complete=True, identity=identity, screen=reviews,
        development_finalists=selected, all_per_step_checks_passed=all(r['status'] == 'passed' for r in rows),
        physics_or_atlas_adoption=False, next_step='Full development/fine gates required' if selected else 'No candidate advances; retain r39'))
    write_json(out/'progress.json', dict(complete=True, records=rows))
    print(json.dumps(reviews, indent=2), flush=True)


if __name__ == '__main__':
    main()
