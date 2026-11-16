"""Declared five-alternative matched-population-input predictive pilot."""
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

BASE=ROOT/'output/urban_measurement_pilot_20261116'
INPUT=ROOT/'output/urban_population_recipe_20261116'
OUT=ROOT/'output/urban_population_refresh_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/population_refresh_pilot.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def score(r,s):
    return dict(n=len(r),mae=float(np.mean(np.abs(r))) if len(r) else None,rmse=float(np.sqrt(np.mean(r*r))) if len(r) else None,
                nll=float(np.mean(.5*np.log(2*np.pi)+np.log(s)+.5*(r/s)**2)) if len(r) else None,
                coverage80=float(np.mean(np.abs(r)<=ndtri(.9)*s)) if len(r) else None,coverage95=float(np.mean(np.abs(r)<=ndtri(.975)*s)) if len(r) else None,
                width80=float(np.mean(2*ndtri(.9)*s)) if len(r) else None,width95=float(np.mean(2*ndtri(.975)*s)) if len(r) else None)


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    input_result=json.loads((INPUT/'results.json').read_text());review=json.loads((INPUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(INPUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_population_recipe.py')
    for name,digest in {**input_result['producers'],**input_result['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in input_result['files_sha256'].items():assert sha(INPUT/name)==digest,name
    old_review=json.loads((BASE/'review.json').read_text());assert old_review['status']=='passed' and old_review['results_sha256']==sha(BASE/'results.json')
    with np.load(BASE/'design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(BASE/'predictions.npz') as z:old={k:z[k] for k in z.files}
    with np.load(INPUT/'model.npz') as z:H=z['floodplain_settlement_base__row_H']
    assert len(H)==664 and (H>0).all() and np.isfinite(H).all()
    y=np.log(d['area']);fold=d['fold'];idx=np.flatnonzero(d['strict']);assert len(idx)==153
    oldX=np.column_stack([np.ones(664),d['lnH'],d['capital']]);newX=np.column_stack([np.ones(664),np.log(H),d['capital']])
    alternatives=[('M0_control',oldX,1,'M0'),('legacy_M1',oldX,2,'M1'),('legacy_M1C',oldX,3,'M1C'),('floodplain_base_M1',newX,2,None),('floodplain_base_M1C',newX,3,None)]
    support=[]
    for name,X,p,_ in alternatives:
        for outer in range(4):
            for inner in [None]+[f for f in range(4) if f!=outer]:
                train=(fold!=outer) & ((fold!=inner) if inner is not None else True)
                rank=int(np.linalg.matrix_rank(X[train,:p]));assert train.sum()>=10 and rank==p
                support.append(dict(alternative=name,outer=outer,inner=inner,n=int(train.sum()),rank=rank,columns=p))
    folds=[];summaries=[];provinces=[];capital_groups=[];predictions=[];fits=[];arrays={}
    for name,X,p,control in alternatives:
        mean=np.zeros(153);sigma=np.zeros(153)
        for outer in range(4):
            beta,sig,inner=nested_fit(X[:,:p],y,fold,np.ones(664,bool),outer)
            use=fold[idx]==outer;mean[use]=X[idx[use],:p]@beta;sigma[use]=sig
            folds.append(dict(alternative=name,outer=outer,training_n=int((fold!=outer).sum()),sigma=sig,intercept=float(beta[0]),lnH_coefficient=float(beta[1]) if p>1 else None,capital_coefficient=float(beta[2]) if p>2 else None,**score(y[idx[use]]-mean[use],sigma[use])))
            fits.append(dict(alternative=name,outer=outer,coefficients=beta.tolist(),sigma=sig,inner=inner))
        if control is not None:
            np.testing.assert_array_equal(mean,old[f'mixed_{control}__mean']);np.testing.assert_array_equal(sigma,old[f'mixed_{control}__sigma'])
        arrays[name+'__mean']=mean;arrays[name+'__sigma']=sigma;r=y[idx]-mean
        summaries.append(dict(alternative=name,**score(r,sigma)))
        for province in sorted(set(d['province'][idx])):
            use=d['province'][idx]==province
            provinces.append(dict(alternative=name,province=int(province),outer=int(fold[idx[use]][0]),small_sample=bool(use.sum()<5),**score(r[use],sigma[use])))
        for outer in range(4):
            for cap in [False,True]:
                use=(fold[idx]==outer)&(d['capital'][idx]==cap)
                capital_groups.append(dict(alternative=name,outer=outer,capital=cap,**score(r[use],sigma[use])))
        for i,row in enumerate(idx):predictions.append(dict(alternative=name,row=int(row),province=int(d['province'][row]),outer=int(fold[row]),capital=bool(d['capital'][row]),observed_log_area=float(y[row]),predicted_log_area=float(mean[i]),sigma=float(sigma[i]),residual=float(r[i])))
    assert len(folds)==20 and len(provinces)==200 and len(predictions)==765 and len(support)==80
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'model.npz',**arrays)
    for name,rows in [('folds',folds),('summary',summaries),('provinces',provinces),('capital_groups',capital_groups),('predictions',predictions)]:table(out/f'{name}.csv',rows)
    protected=dict(input_result['protected_sha256']);protected.update(input_result['producers'])
    for name in ['results.json','review.json',*input_result['files_sha256']]:protected[str((INPUT/name).relative_to(ROOT))]=sha(INPUT/name)
    for name in ['results.json','review.json','predictions.npz']:protected[str((BASE/name).relative_to(ROOT))]=sha(BASE/name)
    paths=[Path(__file__),PLAN,ROOT/'polity/urban_predictive_pilot.py',ROOT/'tests/test_urban_predictive_pilot.py']
    result=dict(status='controlled_same_population_recipe_input_refresh_pilot',folds=folds,summary=summaries,provinces=provinces,capital_groups=capital_groups,fits=fits,support=support,
                producers={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                files_sha256={name:sha(out/name) for name in ['model.npz','folds.csv','summary.csv','provinces.csv','capital_groups.csv','predictions.csv']},
                prior_controls_exact=3,fixed_records=664,common_targets=153,new_blind_test=False,dated_extent_certification=False,fantasy_harvest_equivalence=False,adopt=False,climate_fit=False)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote20outer cases/5fixed alternatives/765predictions;3prior controls exact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
