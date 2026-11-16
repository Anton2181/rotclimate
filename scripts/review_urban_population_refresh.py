"""Independent QR/scalar review of the controlled H-input refresh pilot."""
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.linalg import lstsq

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_urban_measurement_pilot import stats

BASE=ROOT/'output/urban_measurement_pilot_20261116'
INPUT=ROOT/'output/urban_population_recipe_20261116'
OUT=ROOT/'output/urban_population_refresh_20261116'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def metrics(r,s):
    if not len(r):return dict(n=0,mae=None,rmse=None,nll=None,coverage80=None,coverage95=None,width80=None,width95=None)
    v=stats(r,s)
    return {new:v[old] for new,old in [('n','n'),('mae','log_area_mae'),('rmse','log_area_rmse'),('nll','gaussian_log_area_nll'),('coverage80','coverage80'),('coverage95','coverage95'),('width80','mean_log_width80'),('width95','mean_log_width95')]}


def compare(actual,expected):
    assert set(actual)==set(expected)
    for k,v in expected.items():
        if isinstance(v,(str,bool)) or v is None:assert actual[k]==v,(k,actual[k],v)
        else:assert math.isclose(actual[k],v,abs_tol=1e-9,rel_tol=1e-11),(k,actual[k],v)


def main():
    result=json.loads((OUT/'results.json').read_text());inputreview=json.loads((INPUT/'review.json').read_text());oldreview=json.loads((BASE/'review.json').read_text())
    assert inputreview['status']=='passed' and inputreview['results_sha256']==sha(INPUT/'results.json') and inputreview['reviewer_sha256']==sha(ROOT/'scripts/review_urban_population_recipe.py')
    assert oldreview['status']=='passed' and oldreview['results_sha256']==sha(BASE/'results.json') and oldreview['reviewer_sha256']==sha(ROOT/'scripts/review_urban_measurement_pilot.py')
    for name,digest in {**result['producers'],**result['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    with np.load(BASE/'design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(INPUT/'model.npz') as z:H=z['floodplain_settlement_base__row_H']
    with np.load(OUT/'model.npz') as z:actual={k:z[k] for k in z.files}
    with np.load(BASE/'predictions.npz') as z:old={k:z[k] for k in z.files}
    assert len(H)==664 and (H>0).all() and np.isfinite(H).all()
    y=np.array([math.log(a) for a in d['area']]);f=d['fold'];idx=np.flatnonzero(d['strict']);assert len(idx)==153
    X0=np.array([[1.,float(h),float(c)] for h,c in zip(d['lnH'],d['capital'])]);X1=np.array([[1.,math.log(h),float(c)] for h,c in zip(H,d['capital'])])
    alternatives=[('M0_control',X0,1,'M0'),('legacy_M1',X0,2,'M1'),('legacy_M1C',X0,3,'M1C'),('floodplain_base_M1',X1,2,None),('floodplain_base_M1C',X1,3,None)]
    folds=[];summary=[];provinces=[];groups=[];predictions=[];expectedfits=[];support=[];keys=set();maxdiff=0.
    for name,X,p,control in alternatives:
        mean=np.zeros(153);sigma=np.zeros(153)
        for outer in range(4):
            train=f!=outer
            for inner in [None]+[v for v in range(4) if v!=outer]:
                use=train & ((f!=inner) if inner is not None else True)
                _,_,rank,_=lstsq(X[use,:p],y[use],lapack_driver='gelsy');assert rank==p and sum(use)>=10
                support.append(dict(alternative=name,outer=outer,inner=inner,n=int(sum(use)),rank=rank,columns=p))
            squared=[];receipts=[]
            for held in range(4):
                if held==outer:continue
                tr=train & (f!=held);te=train & (f==held)
                beta,_,rank,_=lstsq(X[tr,:p],y[tr],lapack_driver='gelsy');assert rank==p
                residual=[float(a)-math.fsum(float(b)*float(v) for b,v in zip(beta,x)) for a,x in zip(y[te],X[te,:p])]
                sse=math.fsum(v*v for v in residual);squared.extend(v*v for v in residual)
                receipts.append(dict(heldout=held,training_rows=int(sum(tr)),test_rows=int(sum(te)),coefficients=beta.tolist(),squared_error=sse))
            sig=math.sqrt(math.fsum(squared)/len(squared));beta,_,rank,_=lstsq(X[train,:p],y[train],lapack_driver='gelsy');assert rank==p
            use=f[idx]==outer;mean[use]=[math.fsum(float(b)*float(v) for b,v in zip(beta,x)) for x in X[idx[use],:p]];sigma[use]=sig
            folds.append(dict(alternative=name,outer=outer,training_n=int(sum(train)),sigma=sig,intercept=float(beta[0]),lnH_coefficient=float(beta[1]) if p>1 else None,capital_coefficient=float(beta[2]) if p>2 else None,**metrics(y[idx[use]]-mean[use],sigma[use])))
            expectedfits.append(dict(alternative=name,outer=outer,coefficients=beta.tolist(),sigma=sig,inner=receipts))
        for suffix,v in [('mean',mean),('sigma',sigma)]:
            key=name+'__'+suffix;keys.add(key);maxdiff=max(maxdiff,float(np.max(np.abs(actual[key]-v))))
            np.testing.assert_allclose(actual[key],v,atol=1e-10,rtol=1e-11)
            if control:np.testing.assert_array_equal(actual[key],old[f'mixed_{control}__{suffix}'])
        r=y[idx]-mean;summary.append(dict(alternative=name,**metrics(r,sigma)))
        for province in sorted(set(d['province'][idx])):
            use=d['province'][idx]==province;provinces.append(dict(alternative=name,province=int(province),outer=int(f[idx[use]][0]),small_sample=bool(sum(use)<5),**metrics(r[use],sigma[use])))
        for outer in range(4):
            for cap in [False,True]:
                use=(f[idx]==outer)&(d['capital'][idx]==cap);groups.append(dict(alternative=name,outer=outer,capital=cap,**metrics(r[use],sigma[use])))
        for i,row in enumerate(idx):predictions.append(dict(alternative=name,row=int(row),province=int(d['province'][row]),outer=int(f[row]),capital=bool(d['capital'][row]),observed_log_area=float(y[row]),predicted_log_area=float(mean[i]),sigma=float(sigma[i]),residual=float(r[i])))
    assert set(actual)==keys and len(result['support'])==len(support)==80
    for a,b in zip(result['support'],support):compare(a,b)
    assert len(result['fits'])==len(expectedfits)==20
    for a,b in zip(result['fits'],expectedfits):
        assert a['alternative']==b['alternative'] and a['outer']==b['outer']
        np.testing.assert_allclose(a['coefficients'],b['coefficients'],atol=1e-10,rtol=1e-10);assert abs(a['sigma']-b['sigma'])<1e-10
        assert len(a['inner'])==len(b['inner'])==3
        for ai,bi in zip(a['inner'],b['inner']):
            for k in ['heldout','training_rows','test_rows']:assert ai[k]==bi[k]
            np.testing.assert_allclose(ai['coefficients'],bi['coefficients'],atol=1e-10,rtol=1e-10);assert abs(ai['squared_error']-bi['squared_error'])<1e-8
    csvcells=0
    for key,rows in [('folds',folds),('summary',summary),('provinces',provinces),('capital_groups',groups),('predictions',predictions)]:
        if key!='predictions':
            assert len(result[key])==len(rows)
            for a,b in zip(result[key],rows):compare(a,b)
        with (OUT/f'{key}.csv').open() as file:actualrows=list(csv.DictReader(file))
        assert len(actualrows)==len(rows)
        for a,b in zip(actualrows,rows):
            assert set(a)==set(b)
            for k,v in b.items():
                if v is None:assert a[k]==''
                elif isinstance(v,(str,bool)):assert a[k]==str(v)
                else:assert math.isclose(float(a[k]),v,abs_tol=1e-9,rel_tol=1e-11)
                csvcells+=1
    assert result['prior_controls_exact']==3 and result['common_targets']==153 and result['fixed_records']==664
    for flag in ['new_blind_test','dated_extent_certification','fantasy_harvest_equivalence','adopt','climate_fit']:assert result[flag] is False
    fresh={}
    for name in ['results.json','model.npz','folds.csv','summary.csv','provinces.csv','capital_groups.csv','predictions.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_urban_predictive_pilot.py'],cwd=ROOT,text=True,capture_output=True,check=True);assert '4 passed' in tests.stdout
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),scalar_metric_reviewer_sha256=sha(ROOT/'scripts/review_urban_measurement_pilot.py'),results_sha256=sha(OUT/'results.json'),
                method='No new producer/nested-fit component import. GELSY QR mean fits and scalar inner-OOF RMS sigma;previous independent scalar normal-score reviewer reused. All80support splits,60inner fits/20outer fits,metrics and CSV cells;3prior prediction/sigma controls bit exact.',
                alternatives=5,outer_cases=20,predictions=765,province_cases=200,capital_group_cases=40,csv_cells=csvcells,max_mean_or_sigma_difference=maxdiff,
                controls_stdout=tests.stdout,fresh_byte_exact=fresh,adopt=False,new_blind_test=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed20outercases/765predictions/{csvcells}CSVcells;three exact legacy controls;four leakage/accounting tests')


if __name__=='__main__':main()
