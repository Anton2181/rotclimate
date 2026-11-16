"""Declared fixed-request concentration screen, including rank-only controls."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from polity.urban_concentration import area_from_people, redistribute
from polity.settlement_sizes import residents
from polity.urban_observations import interval_ks_lower_bound

BASE = ROOT/'output/urban_given_sites_20261116'
OUT = ROOT/'output/urban_concentration_20261116'
PLAN = ROOT/'calibration/urban_diagnosis_20261116/concentration_screen.json'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(area, lower, upper):
    valid = area > 0
    loss = np.zeros(len(area))
    below = valid & (area < lower)
    above = valid & (area > upper)
    loss[below] = np.log(lower[below]/area[below])
    loss[above] = np.log(area[above]/upper[above])
    return dict(interval_ks_lower_bound=interval_ks_lower_bound(area, lower, upper),
                paired_interval_hit=float(np.mean((area >= lower) & (area <= upper))),
                paired_mean_log_distance=float(loss.mean()) if valid.all() else None,
                zero_support_sites=int((~valid).sum()),
                total_area_ha=float(area.sum()), largest_area_ha=float(area.max()),
                above200=int((area > 200).sum()))


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT) == PLAN.read_bytes()
    plan = json.loads(PLAN.read_text())
    prior = json.loads((BASE/'results.json').read_text()); review = json.loads((BASE/'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(BASE/'results.json')
    assert review['reviewer_sha256'] == sha(ROOT/'scripts/review_urban_given_sites.py')
    for name,digest in {**prior['producers'],**prior['sources'],**prior['protected_sha256']}.items():
        assert sha(ROOT/name) == digest,name
    for name,digest in prior['files_sha256'].items(): assert sha(BASE/name) == digest,name
    with np.load(BASE/'model.npz') as z: baseline = {k:z[k] for k in z.files}
    fit = json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary']
    bounds = np.array(fit['area_range_ha'])
    arrays = {}; cases = []
    for old in prior['cases']:
        pool,cell,seed = old['pool'],old['cell_km'],old['seed']
        key = f'{pool}_{cell}km'; H = baseline[key+'__H']; a0 = baseline[key+f'__areas_{seed}']
        low = baseline[pool+'__lower_ha']; high = baseline[pool+'__upper_ha']; active = H > 0
        for reading in plan['readings']:
            original = residents(a0,reading); budget = float(original.sum()); available = old['available_model_people']
            lo,hi = [np.where(active,float(residents(b,reading)),0.) for b in bounds]
            for family in plan['families']:
                for exponent in plan['exponents']:
                    predictor = H if family == 'hinterland' else original
                    weights = original*(predictor/predictor.max())**(exponent-1)
                    request = redistribute(original,weights,lo,hi,available)
                    area = a0.copy() if exponent == 1 else area_from_people(request,reading)
                    np.testing.assert_allclose(residents(area,reading),request,atol=1e-7,rtol=1e-12)
                    if exponent == 1:
                        np.testing.assert_array_equal(area,a0);np.testing.assert_array_equal(request,original)
                    name = f'{key}_s{seed}_{reading}_{family}_q{exponent:g}'
                    arrays[name+'__area'] = area;arrays[name+'__requests'] = request
                    row = dict(case=name,pool=pool,cell_km=cell,seed=seed,reading=reading,family=family,exponent=exponent,
                               requested_urban_people=budget,available_people=available,remaining_people_budget=available-budget,
                               request_budget_error=float(request.sum()-budget),
                               lower_bound_hits=int(np.count_nonzero(active & np.isclose(request,lo,rtol=0,atol=1e-7))),
                               upper_bound_hits=int(np.count_nonzero(active & np.isclose(request,hi,rtol=0,atol=1e-7))),
                               source_comparison='censored_source_area_intervals' if pool=='floodplains' else 'reported_area_exact_no_precision_interval')
                    row.update(metrics(area,low,high));cases.append(row)
    assert len(cases) == 320
    out.mkdir(parents=True,exist_ok=True)
    with (out/'cases.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(cases[0]));writer.writeheader();writer.writerows(cases)
    np.savez_compressed(out/'model.npz',**arrays)
    protected = dict(prior['protected_sha256'])
    for name in ['results.json','cases.csv','model.npz','geometry.json','review.json']:
        protected[str((BASE/name).relative_to(ROOT))] = sha(BASE/name)
    for name,digest in {**prior['producers'],**prior['sources']}.items(): protected[name] = digest
    paths = [Path(__file__),ROOT/'polity/urban_concentration.py',ROOT/'tests/test_urban_concentration.py',PLAN]
    result = dict(status='development_fixed_requested_population_screen',cases=cases,
                  producers={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                  files_sha256={name:sha(out/name) for name in ['cases.csv','model.npz']},
                  fit_performed=False,new_blind_test=False,food_or_origin_feasibility=False,adopt=False,climate_changed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('Wrote all 320 declared fixed-request cases; no fit or adoption',flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
