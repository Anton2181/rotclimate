"""Independent scalar root/density and source-interval review of all 320 cases."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from review_urban_diagnosis import cdf_bound

BASE = ROOT/'output/urban_given_sites_20261116'
OUT = ROOT/'output/urban_concentration_20261116'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def density(a,reading):
    return 100. if reading == 'low' else 100+400*max(0,min(1,math.log(max(a,1e-9)/50)/math.log(8)))


def inverse(p,reading):
    return 0. if p == 0 else brentq(lambda a:a*density(a,reading)-p,0,p/100+1,xtol=1e-11)


def main():
    result = json.loads((OUT/'results.json').read_text())
    prior = json.loads((BASE/'results.json').read_text()); reviewed = json.loads((BASE/'review.json').read_text())
    assert reviewed['status'] == 'passed' and reviewed['results_sha256'] == sha(BASE/'results.json')
    assert reviewed['reviewer_sha256'] == sha(ROOT/'scripts/review_urban_given_sites.py')
    for name,digest in {**result['producers'],**result['protected_sha256']}.items(): assert sha(ROOT/name) == digest,name
    for name,digest in result['files_sha256'].items(): assert sha(OUT/name) == digest,name
    fit = json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary']
    minimum,maximum = fit['area_range_ha']
    with np.load(BASE/'model.npz') as z: base = {k:z[k] for k in z.files}
    with np.load(OUT/'model.npz') as z: arrays = {k:z[k] for k in z.files}
    expected = set(itertools.product(['floodplains','mexico'],[3,9],[1,7,19,43,97],['low','central'],['hinterland','rank_control'],[1.,1.25,1.5,2.]))
    seen = set(); max_people = max_area = max_budget = 0.; names = set(); exact = 0
    for row in result['cases']:
        pool,cell,seed,reading,family,q = [row[k] for k in ['pool','cell_km','seed','reading','family','exponent']]
        case = pool,cell,seed,reading,family,q
        assert case in expected and case not in seen;seen.add(case)
        key = f'{pool}_{cell}km'; H = base[key+'__H'].tolist(); a0 = base[key+f'__areas_{seed}'].tolist()
        lo = base[pool+'__lower_ha'];hi = base[pool+'__upper_ha']
        original = [a*density(a,reading) for a in a0]; budget = math.fsum(original)
        available = prior['geometry'][pool][str(cell)]['available_model_people']
        assert budget <= available
        lower = [minimum*density(minimum,reading) if h>0 else 0. for h in H]
        upper = [maximum*density(maximum,reading) if h>0 else 0. for h in H]
        predictor = H if family == 'hinterland' else original
        weights = [b*(h/max(predictor))**(q-1) for b,h in zip(original,predictor)]
        if q == 1:
            requested = original;area = a0
        else:
            limit = max(u/w for u,w in zip(upper,weights) if w>0)
            def total(v): return math.fsum(min(u,max(l,v*w)) for l,u,w in zip(lower,upper,weights))
            root = brentq(lambda v:total(v)-budget,0,limit,xtol=1e-12,rtol=1e-14)
            requested = [min(u,max(l,root*w)) for l,u,w in zip(lower,upper,weights)]
            area = [inverse(p,reading) for p in requested]
        name = f'{key}_s{seed}_{reading}_{family}_q{q:g}'
        assert name == row['case']; names.update([name+'__area',name+'__requests'])
        actualp = arrays[name+'__requests'];actuala = arrays[name+'__area']
        max_people = max(max_people,float(np.max(np.abs(actualp-requested))))
        max_area = max(max_area,float(np.max(np.abs(actuala-area))))
        np.testing.assert_allclose(actualp,requested,atol=1e-6,rtol=1e-10)
        np.testing.assert_allclose(actuala,area,atol=1e-8,rtol=1e-10)
        for p,a,l,u,h in zip(actualp,actuala,lower,upper,H):
            assert l <= p <= u
            assert abs(a*density(a,reading)-p) < 1e-6
            if h == 0: assert p == 0 and a == 0
        if q == 1:
            np.testing.assert_array_equal(actuala,base[key+f'__areas_{seed}'])
            # Direct scalar and vector density can differ by a final binary digit.
            np.testing.assert_allclose(actualp,original,atol=1e-8,rtol=1e-15)
            exact += 1
        def close(key,value,tol=1e-8):
            assert abs(row[key]-value) <= tol,(name,key,row[key],value)
        close('requested_urban_people',budget,1e-6)
        close('available_people',available)
        close('remaining_people_budget',available-budget,1e-6)
        error = math.fsum(actualp)-budget;max_budget = max(max_budget,abs(error))
        close('request_budget_error',error,1e-6);assert abs(error)<1e-6
        assert row['remaining_people_budget'] >= 0
        assert row['lower_bound_hits'] == sum(h>0 and abs(p-l)<=1e-7 for h,p,l in zip(H,actualp,lower))
        assert row['upper_bound_hits'] == sum(h>0 and abs(p-u)<=1e-7 for h,p,u in zip(H,actualp,upper))
        close('interval_ks_lower_bound',cdf_bound(actuala,lo,hi),1e-12)
        close('paired_interval_hit',sum(l<=a<=u for a,l,u in zip(actuala,lo,hi))/len(area),1e-12)
        if all(a>0 for a in actuala):
            loss = math.fsum(math.log(l/a) if a<l else math.log(a/u) if a>u else 0 for a,l,u in zip(actuala,lo,hi))/len(area)
            close('paired_mean_log_distance',loss,1e-12)
        else: assert row['paired_mean_log_distance'] is None
        assert row['zero_support_sites'] == sum(a==0 for a in actuala)
        close('total_area_ha',math.fsum(actuala),1e-8);close('largest_area_ha',max(actuala),1e-8)
        assert row['above200'] == sum(a>200 for a in actuala)
        assert row['source_comparison'] == ('censored_source_area_intervals' if pool=='floodplains' else 'reported_area_exact_no_precision_interval')
    assert seen == expected and set(arrays) == names and len(result['cases']) == 320
    for flag in ['fit_performed','new_blind_test','food_or_origin_feasibility','adopt','climate_changed']:assert result[flag] is False
    with (OUT/'cases.csv').open() as f: rows = list(csv.DictReader(f))
    assert len(rows) == 320
    for row,actual in zip(rows,result['cases']):
        assert set(row) == set(actual)
        for key,value in actual.items():
            if value is None: assert row[key] == ''
            elif isinstance(value,(int,float)): assert float(row[key]) == value
            else: assert row[key] == value
    fresh = {}
    for name in ['results.json','model.npz','cases.csv']:
        assert (OUT/name).read_bytes() == (OUT/'fresh'/name).read_bytes(),name
        fresh[name] = sha(OUT/name)
    tests = subprocess.run([sys.executable,'-m','pytest','-q','tests/test_urban_concentration.py','tests/test_urban_observations.py','tests/test_observed_hinterlands.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    assert '44 passed' in tests.stdout
    report = dict(status='passed',reviewer_sha256=sha(Path(__file__)),cdf_reviewer_sha256=sha(ROOT/'scripts/review_urban_diagnosis.py'),results_sha256=sha(OUT/'results.json'),cases=320,
                  method='No screen producer or concentration/density components imported. Scalar direct density, Brent bounded allocation and area inverse; independent CDF envelope, all metrics and CSV cells; prior reviewed anonymous source vectors retained.',
                  max_request_difference_people=max_people,max_area_difference_ha=max_area,max_budget_error_people=max_budget,identity_cases=exact,
                  controls_stdout=tests.stdout,fresh_byte_exact=fresh,adopt=False,new_blind_test=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Reviewed all 320 cases, 80 identity controls, 44 tests and three fresh files',flush=True)


if __name__ == '__main__': main()
