"""Independent scalar decomposition and support review of frozen predictions."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/urban_measurement_pilot_20261116'
OUT=ROOT/'output/urban_geographic_residuals_20261116'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def scalar(residual,sigma):
    n=len(residual);mean=math.fsum(residual)/n if n else None
    result=dict(n=n,mean_signed_log_residual=mean,bias_squared=mean*mean if n else None,
                centered_residual_mean_square=math.fsum((r-mean)**2 for r in residual)/n if n else None,
                mse=math.fsum(r*r for r in residual)/n if n else None,mae=math.fsum(abs(r) for r in residual)/n if n else None,
                rmse=math.sqrt(math.fsum(r*r for r in residual)/n) if n else None,
                mean_log_normalization=math.fsum(math.log(s)+math.log(2*math.pi)/2 for s in sigma)/n if n else None,
                mean_half_standardized_square=math.fsum(r*r/(2*s*s) for r,s in zip(residual,sigma))/n if n else None,
                gaussian_log_area_nll=math.fsum(math.log(s)+math.log(2*math.pi)/2+r*r/(2*s*s) for r,s in zip(residual,sigma))/n if n else None)
    if n:
        assert math.isclose(result['mse'],result['bias_squared']+result['centered_residual_mean_square'],abs_tol=1e-12)
        assert math.isclose(result['gaussian_log_area_nll'],result['mean_log_normalization']+result['mean_half_standardized_square'],abs_tol=1e-12)
    for k in [1,5,10]:
        result[f'top{k}_count']=min(k,n)
        for name,vals in [('absolute',[abs(r) for r in residual]),('squared',[r*r for r in residual])]:
            total=math.fsum(vals)
            result[f'top{k}_{name}_error_share']=math.fsum(sorted(vals,reverse=True)[:k])/total if total>0 else None
    return result


def quantile(values,q):
    values=sorted(values);position=(len(values)-1)*q;i=math.floor(position);j=math.ceil(position)
    return values[i]+(values[j]-values[i])*(position-i)


def compare(actual,expected):
    assert set(actual)==set(expected),(set(actual),set(expected))
    for k,v in expected.items():
        if isinstance(v,bool) or v is None or isinstance(v,str):assert actual[k]==v,(k,actual[k],v)
        else:assert math.isclose(actual[k],v,rel_tol=1e-12,abs_tol=1e-9),(k,actual[k],v)


def main():
    # Arithmetic controls independent of any scientific source values.
    control=scalar([1.,3.],[2.,2.]);assert control['bias_squared']==4 and control['centered_residual_mean_square']==1 and control['mse']==5
    assert control['top1_absolute_error_share']==.75 and control['top1_squared_error_share']==.9
    assert scalar([0.,0.],[1.,1.])['top1_squared_error_share'] is None
    assert scalar([],[])['mse'] is None and scalar([],[])['top10_count']==0
    assert quantile([0,1,4,9],.25)==.75
    result=json.loads((OUT/'results.json').read_text());previous=json.loads((BASE/'review.json').read_text())
    assert previous['status']=='passed' and previous['results_sha256']==sha(BASE/'results.json')
    assert previous['reviewer_sha256']==sha(ROOT/'scripts/review_urban_measurement_pilot.py')
    for name,digest in {**result['producers'],**result['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    with np.load(BASE/'design.npz') as z:d={k:z[k].tolist() for k in z.files}
    with np.load(BASE/'predictions.npz') as z:pred={k:z[k].tolist() for k in z.files}
    target=[i for i,v in enumerate(d['strict']) if v];assert len(target)==153
    H=[math.exp(h) for h in d['lnH']];y=[math.log(d['area'][i]) for i in target]
    expected={k:[] for k in ['cases','pooled','provinces','capital_groups']}
    for cohort in ['mixed','strict']:
        for model in ['M0','M1','M1C']:
            key=cohort+'_'+model;residual=[a-b for a,b in zip(y,pred[key+'__mean'])];sig=pred[key+'__sigma']
            expected['pooled'].append(dict(training_cohort=cohort,model=model,**scalar(residual,sig)))
            for outer in range(4):
                selected=[k for k,i in enumerate(target) if d['fold'][i]==outer]
                training=[i for i in range(len(H)) if d['fold'][i]!=outer and (cohort=='mixed' or d['strict'][i])]
                record=dict(training_cohort=cohort,model=model,outer=outer,**scalar([residual[k] for k in selected],[sig[k] for k in selected]),
                            training_rows=len(training),training_capitals=sum(d['capital'][i] for i in training),target_capitals=sum(d['capital'][target[k]] for k in selected))
                for label,values in [('training',[H[i] for i in training]),('target',[H[target[k]] for k in selected])]:
                    for name,q in [('min',0),('p25',.25),('p50',.5),('p75',.75),('max',1)]:record[f'{label}_H_{name}']=quantile(values,q)
                count=sum(H[target[k]]<record['training_H_min'] or H[target[k]]>record['training_H_max'] for k in selected)
                record.update(target_H_outside_training_count=count,target_H_outside_training_fraction=count/len(selected));expected['cases'].append(record)
                for is_capital in [False,True]:
                    use=[k for k in selected if d['capital'][target[k]]==is_capital]
                    expected['capital_groups'].append(dict(training_cohort=cohort,model=model,outer=outer,capital=is_capital,**scalar([residual[k] for k in use],[sig[k] for k in use])))
            for province in sorted({d['province'][i] for i in target}):
                selected=[k for k,i in enumerate(target) if d['province'][i]==province]
                expected['provinces'].append(dict(training_cohort=cohort,model=model,province=province,outer=d['fold'][target[selected[0]]],small_sample=len(selected)<5,
                                                  **scalar([residual[k] for k in selected],[sig[k] for k in selected])))
    csv_cells=0
    for name,records in expected.items():
        assert len(result[name])==len(records)
        for actual,record in zip(result[name],records):compare(actual,record)
        with (OUT/f'{name}.csv').open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==len(records)
        for row,record in zip(rows,records):
            assert set(row)==set(record)
            for k,v in record.items():
                if v is None:assert row[k]==''
                elif isinstance(v,bool) or isinstance(v,str):assert row[k]==str(v)
                else:assert math.isclose(float(row[k]),v,rel_tol=1e-12,abs_tol=1e-9)
                csv_cells+=1
    # Complete province/fold/capital accounting; no record can disappear.
    for row in result['pooled']:
        same=lambda r:r['training_cohort']==row['training_cohort'] and r['model']==row['model']
        for group in ['cases','provinces','capital_groups']:
            selected=[r for r in result[group] if same(r)]
            assert sum(r['n'] for r in selected)==row['n']==153
            assert math.isclose(math.fsum(r['mse']*r['n'] for r in selected if r['n'])/153,row['mse'],abs_tol=1e-12)
        assert sum(r['n'] for r in result['capital_groups'] if same(r) and r['capital'])==4
    for flag in ['fit_performed','new_scores_on_source','new_blind_test','adopt','climate_changed']:assert result[flag] is False
    fresh={}
    for name in ['results.json','cases.csv','pooled.csv','provinces.csv','capital_groups.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
                method='No producer import or fit. Scalar math.fsum bias/variance/NLL decomposition,sorted-list interpolated H quantiles/support,top-k masses and complete fold/province/capital accounting;all CSV cells.',
                fold_cases=24,pooled_cases=6,province_cases=240,capital_group_cases=48,csv_cells=csv_cells,common_targets=153,capital_targets=4,
                arithmetic_controls=5,fresh_byte_exact=fresh,fit_performed=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed24fold/240province decompositions,{csv_cells}CSVcells and five exact fresh files;all153targets retained')


if __name__=='__main__':main()
