"""Three fixed surface-drag candidates under full Earth and integrated-ocean gates."""
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
from benchmark_local import DEV31, DEV12_SPECS
from check_constrained_blend import benchmark, paired_score
from gate_local import evaluate
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json
from earth_benchmark import load_params
from rotclimate import earth, joint
from rotclimate.config import Params
from rotclimate.koppen import monthly_weights
from rotclimate.model import ClimateModel
from rotclimate.numerics import matrix_product

PROTECTED = ['north_india', 'iran_plateau', 'iberia', 'japan', 'mexico', 'east_australia', 'pacific_nw']


def ocean_one(job):
    name, region, params, identity, folder = job
    folder = Path(folder)
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case = earth.region_case(region, 56.0)
    derived = case_hash(case, observed_sea=True)
    path = folder/f'{name}_{region}.json'
    if path.exists():
        row = json.loads(path.read_text())
        if row['identity'] != identity or row['case_identity'] != derived or row['status'] != 'passed':
            raise ValueError('Changed inputs or preserved ocean failure')
        return row
    row = dict(name=name, region=region, identity=identity, case_identity=derived)
    started = time.monotonic()
    try:
        p = earth.earth_params(joint.earth_profile(Params(**params)), case)
        g = case.grid
        domain = np.ones_like(g.land)
        domain[[0, -1], :] = False
        domain[:, [0, -1]] = False
        sea = domain & ~g.land & np.isfinite(g.obs_sst).all(0) & (g.obs_sst.min(0) > -1)
        model = ClimateModel(p, grid=g)
        model.trace_cells = np.nonzero(domain)
        result = model.run()
        if result.numerics.get('all_checks_passed') is not True:
            raise ValueError('Ocean check numerical failure')
        speed = np.stack([np.hypot(t['moisture_u'], t['moisture_v']) for t in model.trace])
        sst = matrix_product(monthly_weights(result.days, p.year_days), np.stack([t['SST'] for t in model.trace]))
        error = sst[:, sea[domain]]-g.obs_sst[:, sea]
        row.update(status='passed', params=asdict(p), numerics=result.numerics,
                   sst=dict(cells=int(sea.sum()), monthly_mae_C=float(np.abs(error).mean())) if sea.any() else None,
                   column_speed=dict(maximum_ms=float(speed.max()), p95_ms=float(np.percentile(speed,95))))
    except Exception as error:
        row.update(status='failed', error=repr(error))
    row['seconds'] = time.monotonic()-started
    write_json(path, row)
    print('Ocean '+name+'/'+region+': '+row['status'], flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT/'calibration/surface_momentum_20261026/plan.json')
    parser.add_argument('--out', type=Path, default=ROOT/'output/surface_momentum_20261026')
    args = parser.parse_args()
    path = args.plan.resolve()
    plan = json.loads(path.read_text())
    out = args.out.resolve()
    out.mkdir(exist_ok=True)
    sources = list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__), path, ROOT/plan['physics'],
        ROOT/'scripts/benchmark_local.py', ROOT/'scripts/check_constrained_blend.py', ROOT/'scripts/gate_local.py',
        ROOT/'scripts/local_benchmark_protocol.py', ROOT/'scripts/earth_benchmark.py', ROOT/'scripts/rainfall_metrics.py',
        DEV12_SPECS, ROOT/'calibration/local_accuracy_20261023/policy_v2.json',
        ROOT/'calibration/local_accuracy_20261023/regions_sealed6.json', earth.WOA_SST]
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{key}.zip' for key in ['tavg','prec','elev','vapr']]
    for name in DEV31:
        sources += [ROOT/plan['archive']/'cases'/f'{name}.json']
    identity = freeze(out/'protocol.json', dict(plan=plan, protected_regions=PROTECTED,
        sources={str(p.relative_to(ROOT)): file_hash(p) for p in sources},
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','numba']}))
    params = out/'params'
    params.mkdir(exist_ok=True)
    base = load_params(ROOT/plan['physics'])
    all_params = {'reference': base}
    all_params.update({name: joint.update_block(base, 'physics', values) for name, values in plan['candidates'].items()})
    for name, profile in all_params.items():
        joint.earth_profile(profile).to_json(params/f'{name}.json')
    reference = benchmark(params/'reference.json', out/'reference', ['dev31'], 56.0)
    if reference is None:
        raise ValueError('Fresh reference failed')
    for name in DEV31:
        previous = json.loads((ROOT/plan['archive']/'cases'/f'{name}.json').read_text())
        row = reference['regions'][name]
        if (row['case_identity'] != previous['case_identity'] or
                abs(row['rain']['loss']-previous['rain']['loss']) > 1e-10 or
                abs(row['temperature']['monthly_mae_C']-previous['temperature']['monthly_mae_C']) > 1e-10):
            raise ValueError('Historical r39 error control changed: '+name)
    policy = json.loads((ROOT/'calibration/local_accuracy_20261023/policy_v2.json').read_text())
    rp = json.loads((out/'reference/protocol.json').read_text())
    reviews, finalists = {}, []
    for name in plan['candidates']:
        folder = out/'development'/name
        candidate = benchmark(params/f'{name}.json', folder, ['dev31'], 56.0)
        if candidate is None:
            reviews[name] = dict(passes_development_gate=False, failures=['Numerical failure'])
        else:
            cp = json.loads((folder/'protocol.json').read_text())
            review = evaluate(reference, candidate, rp, cp, policy)
            protections = []
            for region in PROTECTED:
                b, c = reference['regions'][region], candidate['regions'][region]
                rain = c['rain']['loss']/b['rain']['loss']
                s = .5*(rain+c['temperature']['monthly_mae_C']/b['temperature']['monthly_mae_C'])
                if region == 'north_india' and rain > .95:
                    protections.append('North India rain improvement below 5%')
                elif region == 'iran_plateau' and rain > 1.02:
                    protections.append('Iran rainfall worsens by more than 2%')
                elif region not in ['north_india','iran_plateau'] and s > 1.02:
                    protections.append(region+': protected combined error worsens')
            review['extra_protections'] = protections
            review['qualifies'] = review['passes_development_gate'] and not protections
            reviews[name] = review
            if review['qualifies']:
                finalists.append(name)
        write_json(out/'progress.json', dict(complete=False, development=reviews))
        print(name+': '+json.dumps(reviews[name]), flush=True)
    finalists.sort(key=lambda name: reviews[name]['score'])
    finalists = finalists[:2]
    ocean_reviews, fine, selected = {}, {}, None
    if finalists:
        ocean = out/'ocean'
        ocean.mkdir(exist_ok=True)
        with Pool(2) as pool:
            controls = {r['region']:r for r in pool.map(ocean_one,
                [('reference', r, asdict(base), identity, str(ocean)) for r in PROTECTED])}
            if any(r['status'] != 'passed' for r in controls.values()):
                raise ValueError('Ocean reference failed')
            for name in finalists:
                candidates = {r['region']:r for r in pool.map(ocean_one,
                    [(name, r, asdict(all_params[name]), identity, str(ocean)) for r in PROTECTED])}
                failures = []
                for region, c in candidates.items():
                    b = controls[region]
                    if c['status'] != 'passed':
                        failures.append(region+': failed solve')
                        continue
                    if c['case_identity'] != b['case_identity']:
                        raise ValueError('Unpaired ocean inputs')
                    if (b['sst'] is None) != (c['sst'] is None):
                        raise ValueError('Ocean coverage changed')
                    if c['sst'] and (c['sst']['cells'] != b['sst']['cells'] or
                            c['sst']['monthly_mae_C'] > b['sst']['monthly_mae_C']+.02):
                        failures.append(region+': SST protection failed')
                    if c['column_speed']['maximum_ms'] > 60 or c['column_speed']['p95_ms'] > 25:
                        failures.append(region+': speed protection failed')
                ocean_reviews[name] = dict(passed=not failures, failures=failures)
        names = ['california','western_europe','japan','new_zealand']
        qualified = [name for name in finalists if ocean_reviews[name]['passed']]
        if qualified:
            if benchmark(params/'reference.json', out/'fine_reference', names+['north_india'], 28.0) is None:
                raise ValueError('Fine reference failed')
            for name in qualified:
                folder = out/'fine'/name
                candidate = benchmark(params/f'{name}.json', folder, names+['north_india'], 28.0)
                if candidate is None:
                    fine[name] = dict(passed=False, reason='Numerical failure')
                else:
                    s = paired_score(out/'fine_reference', folder, names)
                    b = json.loads((out/'fine_reference/summary.json').read_text())
                    ratio = candidate['regions']['north_india']['rain']['loss']/b['regions']['north_india']['rain']['loss']
                    fine[name] = dict(S=s, north_india_rain_loss_ratio=ratio, passed=s<=1.01 and ratio<=.98)
                if fine[name]['passed']:
                    selected = name
                    break
    established = None
    if selected:
        specs = ROOT/'calibration/local_accuracy_20261023/regions_sealed6.json'
        names = list(json.loads(specs.read_text()))
        a = benchmark(params/'reference.json', out/'established_reference', names, 56.0, specs)
        b = benchmark(params/f'{selected}.json', out/'established_candidate', names, 56.0, specs)
        s = paired_score(out/'established_reference', out/'established_candidate', names) if a and b else None
        established = dict(S=s, passed=s is not None and s<=1.01, note='Reused established regions')
    adopted = bool(selected and established and established['passed'])
    profile = None
    if adopted:
        profile = ROOT/'calibration/local_accuracy_20261023/r40_params.json'
        values = asdict(all_params[selected])
        if profile.exists() and json.loads(profile.read_text()) != json.loads(json.dumps(values)):
            raise ValueError('Preserve existing r40 profile')
        write_json(profile, values)
    final = dict(complete=True, identity=identity, development=reviews, finalists=finalists,
        ocean=ocean_reviews, fine=fine, selected=selected, established=established,
        eligible_for_earth_adoption=adopted, profile=str(profile.relative_to(ROOT)) if profile else None,
        atlas_climate_adoption=False, reason='Qualified Earth profile; world refit required' if adopted else 'Retain r39')
    write_json(out/'review.json', final)
    write_json(out/'progress.json', final)
    print(json.dumps(final, indent=2), flush=True)


if __name__ == '__main__':
    main()
