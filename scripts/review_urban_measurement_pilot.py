"""Independent QR least squares and scalar nested predictive-score review."""
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist
import subprocess
import sys

import numpy as np
from scipy.linalg import lstsq

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_measurement_pilot_20261116'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def stats(residual,sigma):
    n=len(residual);z80=NormalDist().inv_cdf(.9);z95=NormalDist().inv_cdf(.975)
    return dict(n=n,log_area_mae=math.fsum(abs(r) for r in residual)/n,log_area_rmse=math.sqrt(math.fsum(r*r for r in residual)/n),
                gaussian_log_area_nll=math.fsum(.5*math.log(2*math.pi)+math.log(s)+r*r/(2*s*s) for r,s in zip(residual,sigma))/n,
                coverage80=sum(abs(r)<=z80*s for r,s in zip(residual,sigma))/n,coverage95=sum(abs(r)<=z95*s for r,s in zip(residual,sigma))/n,
                mean_log_width80=math.fsum(2*z80*s for s in sigma)/n,mean_log_width95=math.fsum(2*z95*s for s in sigma)/n)


def check(actual,expected,tol=1e-9):
    assert set(actual)==set(expected),(set(actual),set(expected))
    for k,v in expected.items():
        if isinstance(v,(int,float)):assert abs(actual[k]-v)<tol,(k,actual[k],v)
        else:assert actual[k]==v,(k,actual[k],v)


def main():
    result=json.loads((OUT/'results.json').read_text());support=json.loads((OUT/'support_review.json').read_text())
    assert support['status']=='passed' and support['eligibility_sha256']==sha(OUT/'eligibility.json')
    assert support['reviewer_sha256']==sha(ROOT/'scripts/review_urban_measurement_support.py')
    for name,digest in {**result['producers'],**result['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    with np.load(OUT/'design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(OUT/'predictions.npz') as z:actualarrays={k:z[k] for k in z.files}
    y=np.array([math.log(a) for a in d['area']]);X=np.column_stack([np.ones(len(y)),d['lnH'],d['capital']]);fold=d['fold'];strict=d['strict'];idx=np.flatnonzero(strict)
    expectedfolds=[];expectedsummary=[];expectedprovince=[];expectedpredictions=[];expectedfits=[];expectedkeys=set();maxpred=0.
    for cohort in ['mixed','strict']:
        eligible=np.ones(len(y),bool) if cohort=='mixed' else strict
        for model,p in [('M0',1),('M1',2),('M1C',3)]:
            mean=np.zeros(len(idx));sigma=np.zeros(len(idx));key=f'{cohort}_{model}'
            for outer in range(4):
                train=eligible & (fold!=outer);squared=[];inner=[]
                for held in range(4):
                    if held==outer:continue
                    tr=train & (fold!=held);te=train & (fold==held)
                    beta,_,rank,_=lstsq(X[tr,:p],y[tr],lapack_driver='gelsy');assert rank==p
                    residual=[float(a-sum(float(b)*float(v) for b,v in zip(beta,x))) for a,x in zip(y[te],X[te,:p])]
                    sse=math.fsum(r*r for r in residual);squared.extend(r*r for r in residual)
                    inner.append(dict(heldout=held,training_rows=int(sum(tr)),test_rows=int(sum(te)),coefficients=beta.tolist(),squared_error=sse))
                sig=math.sqrt(math.fsum(squared)/len(squared));assert sig>0
                beta,_,rank,_=lstsq(X[train,:p],y[train],lapack_driver='gelsy');assert rank==p
                test=fold[idx]==outer
                mean[test]=[sum(float(b)*float(v) for b,v in zip(beta,x)) for x in X[idx[test],:p]];sigma[test]=sig
                expectedfits.append(dict(training_cohort=cohort,model=model,outer=outer,coefficients=beta.tolist(),sigma=sig,inner=inner))
                row=dict(training_cohort=cohort,model=model,outer=outer,training_rows=int(sum(train)),test_provinces=len(set(d['province'][idx[test]])),sigma=sig,
                         intercept=float(beta[0]),lnH_coefficient=float(beta[1]) if p>1 else None,capital_coefficient=float(beta[2]) if p>2 else None,
                         **stats(y[idx[test]]-mean[test],sigma[test]))
                expectedfolds.append(row)
            for suffix,v in [('mean',mean),('sigma',sigma)]:
                k=key+'__'+suffix;expectedkeys.add(k);maxpred=max(maxpred,float(np.max(np.abs(actualarrays[k]-v))))
                np.testing.assert_allclose(actualarrays[k],v,rtol=1e-11,atol=1e-10)
            residual=y[idx]-mean
            expectedsummary.append(dict(training_cohort=cohort,model=model,**stats(residual,sigma)))
            for province in sorted(set(d['province'][idx])):
                mask=d['province'][idx]==province
                expectedprovince.append(dict(training_cohort=cohort,model=model,province=int(province),outer=int(fold[idx[mask]][0]),**stats(residual[mask],sigma[mask])))
            for i,row in enumerate(idx):
                expectedpredictions.append(dict(training_cohort=cohort,model=model,row=int(row),province=int(d['province'][row]),outer=int(fold[row]),observed_log_area=float(y[row]),mean_log_area=float(mean[i]),sigma=float(sigma[i]),residual=float(residual[i])))
    assert set(actualarrays)==expectedkeys
    for name,rows in [('folds',expectedfolds),('summary',expectedsummary),('provinces',expectedprovince)]:
        assert len(result[name])==len(rows)
        for actual,expected in zip(result[name],rows):check(actual,expected)
    assert len(result['fits'])==len(expectedfits)==24
    for actual,expected in zip(result['fits'],expectedfits):
        assert actual['training_cohort']==expected['training_cohort'] and actual['model']==expected['model'] and actual['outer']==expected['outer']
        np.testing.assert_allclose(actual['coefficients'],expected['coefficients'],atol=1e-10,rtol=1e-10)
        assert abs(actual['sigma']-expected['sigma'])<1e-10
        for a,e in zip(actual['inner'],expected['inner']):
            np.testing.assert_allclose(a['coefficients'],e['coefficients'],atol=1e-10,rtol=1e-10)
            for k in ['heldout','training_rows','test_rows']:assert a[k]==e[k]
            assert abs(a['squared_error']-e['squared_error'])<1e-8
    csv_cells=0
    for name,rows in [('folds',expectedfolds),('summary',expectedsummary),('provinces',expectedprovince),('predictions',expectedpredictions)]:
        with (OUT/f'{name}.csv').open() as f:actual=list(csv.DictReader(f))
        assert len(actual)==len(rows)
        for a,e in zip(actual,rows):
            assert set(a)==set(e)
            for k,v in e.items():
                if v is None:assert a[k]==''
                elif isinstance(v,(int,float)):assert abs(float(a[k])-v)<1e-9
                else:assert a[k]==v
                csv_cells+=1
    for flag in ['new_blind_test','dated_area_certification','demographic_calibration','adopt','climate_changed']:assert result[flag] is False
    fresh={}
    for name in ['results.json','folds.csv','summary.csv','provinces.csv','predictions.csv','predictions.npz']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_urban_predictive_pilot.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    assert '4 passed' in tests.stdout
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
                method='No pilot producer or nested-fit component import. Independent scipy GELSY QR solves,scalar inner-OOF squared-error sigma,normal log density/coverage/width via statistics.NormalDist,all fitted receipts/metrics/CSV cells.',
                outer_cases=24,fixed_alternatives=6,common_targets=153,province_cases=240,prediction_rows=918,csv_cells=csv_cells,
                max_mean_or_sigma_difference=maxpred,controls_stdout=tests.stdout,fresh_byte_exact=fresh,adopt=False,new_blind_test=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed24outer cases,6alternatives,918prediction rows,{csv_cells}CSVcells and four leakage/accounting controls')


if __name__=='__main__':main()
