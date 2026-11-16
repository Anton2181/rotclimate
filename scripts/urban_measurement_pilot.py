"""Six declared source-basis alternatives with nested train-only dispersion."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.special import ndtri

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from polity.urban_predictive_pilot import nested_fit

OUT=ROOT/'output/urban_measurement_pilot_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/measurement_basis_pilot.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def scores(residual,sigma):
    nll=.5*np.log(2*np.pi)+np.log(sigma)+.5*(residual/sigma)**2
    return dict(n=len(residual),log_area_mae=float(np.mean(np.abs(residual))),log_area_rmse=float(np.sqrt(np.mean(residual**2))),
                gaussian_log_area_nll=float(np.mean(nll)),coverage80=float(np.mean(np.abs(residual)<=ndtri(.9)*sigma)),
                coverage95=float(np.mean(np.abs(residual)<=ndtri(.975)*sigma)),mean_log_width80=float(np.mean(2*ndtri(.9)*sigma)),mean_log_width95=float(np.mean(2*ndtri(.975)*sigma)))


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main(out):
    for path in [PLAN,OUT/'eligibility.json',OUT/'support_review.json']:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    eligibility=json.loads((OUT/'eligibility.json').read_text());review=json.loads((OUT/'support_review.json').read_text())
    assert eligibility['support_gate_passed'] and review['status']=='passed' and review['eligibility_sha256']==sha(OUT/'eligibility.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_measurement_support.py')
    for name,digest in {**eligibility['sources_sha256'],**eligibility['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    assert sha(OUT/'design.npz')==eligibility['files_sha256']['design.npz']
    with np.load(OUT/'design.npz') as z:d={k:z[k] for k in z.files}
    X=np.column_stack([np.ones(len(d['area'])),d['lnH'],d['capital']]);y=np.log(d['area']);fold=d['fold'];strict=d['strict'];idx=np.flatnonzero(strict)
    folds=[];summary=[];provinces=[];predictions=[];fits=[];arrays={}
    for cohort,eligible in [('mixed',np.ones(len(y),bool)),('strict',strict)]:
        for model,p in [('M0',1),('M1',2),('M1C',3)]:
            mean=np.zeros(len(idx));sig=np.zeros(len(idx));key=f'{cohort}_{model}'
            for outer in range(4):
                beta,sigma,inner=nested_fit(X[:,:p],y,fold,eligible,outer)
                test=fold[idx]==outer;mean[test]=X[idx[test],:p]@beta;sig[test]=sigma
                row=dict(training_cohort=cohort,model=model,outer=outer,training_rows=int((eligible & (fold!=outer)).sum()),test_provinces=len(np.unique(d['province'][idx[test]])),sigma=sigma,
                         intercept=float(beta[0]),lnH_coefficient=float(beta[1]) if p>1 else None,capital_coefficient=float(beta[2]) if p>2 else None)
                row.update(scores(y[idx[test]]-mean[test],sig[test]));folds.append(row)
                fits.append(dict(training_cohort=cohort,model=model,outer=outer,coefficients=beta.tolist(),sigma=sigma,inner=inner))
            residual=y[idx]-mean;arrays[key+'__mean']=mean;arrays[key+'__sigma']=sig
            summary.append(dict(training_cohort=cohort,model=model,**scores(residual,sig)))
            for province in sorted(set(d['province'][idx])):
                use=d['province'][idx]==province
                provinces.append(dict(training_cohort=cohort,model=model,province=int(province),outer=int(fold[idx[use]][0]),**scores(residual[use],sig[use])))
            for i,source_index in enumerate(idx):
                predictions.append(dict(training_cohort=cohort,model=model,row=int(source_index),province=int(d['province'][source_index]),outer=int(fold[source_index]),observed_log_area=float(y[source_index]),mean_log_area=float(mean[i]),sigma=float(sig[i]),residual=float(residual[i])))
    assert len(folds)==24 and len(summary)==6 and len(provinces)==240 and len(predictions)==918
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('folds',folds),('summary',summary),('provinces',provinces),('predictions',predictions)]:table(out/f'{name}.csv',rows)
    np.savez_compressed(out/'predictions.npz',**arrays)
    protected=dict(eligibility['protected_sha256']);protected.update(eligibility['sources_sha256'])
    for name in ['design.npz','eligibility.json','support_review.json']:protected[str((OUT/name).relative_to(ROOT))]=sha(OUT/name)
    paths=[Path(__file__),ROOT/'polity/urban_predictive_pilot.py',ROOT/'tests/test_urban_predictive_pilot.py',PLAN]
    result=dict(status='source_basis_conditional_extent_development_pilot',folds=folds,summary=summary,provinces=provinces,fits=fits,
                producers={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                files_sha256={n:sha(out/n) for n in ['folds.csv','summary.csv','provinces.csv','predictions.csv','predictions.npz']},
                new_blind_test=False,dated_area_certification=False,demographic_calibration=False,adopt=False,climate_changed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote 24 outer-fold cases / 6 fixed alternatives on153 common targets, nested training-only dispersion',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
