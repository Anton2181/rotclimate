"""Decompose reviewed fixed predictions; no fit, exclusion or new predictor."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/urban_measurement_pilot_20261116'
OUT=ROOT/'output/urban_geographic_residuals_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/geographic_residual_audit.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def decomposition(residual,sigma):
    n=len(residual)
    names=['mean_signed_log_residual','bias_squared','centered_residual_mean_square','mse','mae','rmse',
           'mean_log_normalization','mean_half_standardized_square','gaussian_log_area_nll']
    result={'n':n}
    if not n:
        result.update({k:None for k in names})
    else:
        bias=float(np.mean(residual));variance=float(np.mean((residual-bias)**2));mse=float(np.mean(residual**2))
        normalization=float(np.mean(.5*np.log(2*np.pi)+np.log(sigma)))
        standardized=float(np.mean(.5*(residual/sigma)**2))
        assert abs(mse-bias*bias-variance)<1e-12
        result.update(dict(zip(names,[bias,bias*bias,variance,mse,float(np.mean(np.abs(residual))),float(np.sqrt(mse)),
                                      normalization,standardized,normalization+standardized])))
    for k in [1,5,10]:
        result[f'top{k}_count']=min(k,n)
        for name,values in [('absolute',np.abs(residual)),('squared',residual**2)]:
            mass=float(values.sum())
            result[f'top{k}_{name}_error_share']=float(np.sort(values)[-k:].sum()/mass) if mass>0 else None
    return result


def support(trainH,targetH,train_capital,target_capital):
    result=dict(training_rows=len(trainH),training_capitals=int(train_capital.sum()),target_capitals=int(target_capital.sum()))
    for label,values in [('training',trainH),('target',targetH)]:
        for key,value in zip(['min','p25','p50','p75','max'],np.quantile(values,[0,.25,.5,.75,1])):
            result[f'{label}_H_{key}']=float(value)
    result['target_H_outside_training_count']=int(np.count_nonzero((targetH<trainH.min()) | (targetH>trainH.max())))
    result['target_H_outside_training_fraction']=result['target_H_outside_training_count']/len(targetH)
    return result


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    previous=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_measurement_pilot.py')
    for name,digest in {**previous['producers'],**previous['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in previous['files_sha256'].items():assert sha(BASE/name)==digest,name
    with np.load(BASE/'design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(BASE/'predictions.npz') as z:pred={k:z[k] for k in z.files}
    index=np.flatnonzero(d['strict']);y=np.log(d['area'][index]);H=np.exp(d['lnH']);fold=d['fold'][index];province=d['province'][index];capital=d['capital'][index]
    cases=[];pooled=[];provinces=[];capital_groups=[]
    for cohort in ['mixed','strict']:
        eligible=np.ones(len(H),bool) if cohort=='mixed' else d['strict']
        for model in ['M0','M1','M1C']:
            key=cohort+'_'+model;residual=y-pred[key+'__mean'];sigma=pred[key+'__sigma']
            pooled.append(dict(training_cohort=cohort,model=model,**decomposition(residual,sigma)))
            for outer in range(4):
                target=fold==outer;train=eligible & (d['fold']!=outer)
                row=dict(training_cohort=cohort,model=model,outer=outer,**decomposition(residual[target],sigma[target]))
                row.update(support(H[train],H[index[target]],d['capital'][train],capital[target]));cases.append(row)
                for is_capital in [False,True]:
                    use=target & (capital==is_capital)
                    capital_groups.append(dict(training_cohort=cohort,model=model,outer=outer,capital=is_capital,**decomposition(residual[use],sigma[use])))
            for p in sorted(set(province)):
                use=province==p
                provinces.append(dict(training_cohort=cohort,model=model,province=int(p),outer=int(fold[use][0]),small_sample=bool(use.sum()<5),**decomposition(residual[use],sigma[use])))
    assert len(cases)==24 and len(pooled)==6 and len(provinces)==240 and len(capital_groups)==48
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('cases',cases),('pooled',pooled),('provinces',provinces),('capital_groups',capital_groups)]:table(out/f'{name}.csv',rows)
    protected=dict(previous['protected_sha256']);protected.update(previous['producers'])
    for name in ['results.json','review.json',*previous['files_sha256']]:protected[str((BASE/name).relative_to(ROOT))]=sha(BASE/name)
    result=dict(status='fixed_prediction_geographic_residual_audit',cases=cases,pooled=pooled,provinces=provinces,capital_groups=capital_groups,
                producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN]},protected_sha256=protected,
                files_sha256={name:sha(out/name) for name in ['cases.csv','pooled.csv','provinces.csv','capital_groups.csv']},
                residual_sign='observed log area minus predicted log area; positive means underprediction',
                H_quantiles='Unlogged hinterland people; linear interpolation of sorted values at (n-1)*q',
                top_error_shares='All-target/fold metrics remain unchanged. Top-k shares use all errors as denominator; tied magnitudes have equal mass.',
                fit_performed=False,new_scores_on_source=False,new_blind_test=False,adopt=False,climate_changed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote24fixed fold cases,6pooled,240province and48capital-group decompositions;no refit')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
