"""Separate closed-form baseline, scalar hierarchy replay and pairwise CRPS review."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/roman_benchmark_20261117'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())
def table(p):
    with p.open() as f:return list(csv.DictReader(f))


def close(a,b):
    if b is None:assert a in [None,''];return
    assert math.isclose(float(a),float(b),rel_tol=3e-12,abs_tol=3e-12),(a,b)


def main():
    assert not (OUT/'review.json').exists(),'Preserve reviewed benchmark'
    r=read(OUT/'results.json');prep=read(OUT/'preparation.json')
    for n,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/n)==digest,n
    for n,digest in r['files_sha256'].items():assert sha(OUT/n)==digest,n
    for n in ['results.json',*r['files_sha256']]:assert (OUT/n).read_bytes()==(OUT/'fresh'/n).read_bytes(),n
    with np.load(OUT/'design.npz') as z:d=dict(z)
    with np.load(OUT/'ensemble.npz') as z:ensembles=dict(z)
    with np.load(ROOT/'output/urban_hierarchy_refresh_20261116/model.npz') as z:np.testing.assert_array_equal(ensembles['old_control'],z['refreshed__areas'])
    with np.load(ROOT/'output/urban_population_recipe_20261116/model.npz') as z:H=z['floodplain_settlement_base__row_H']
    n=len(H);y=[math.log(float(v)) for v in d['area']];fold=d['fold'];lo,hi=r['bounds_ha'];maxdifference=0.
    assert ensembles['seeds'].tolist()==list(range(1000,1256))==r['evaluation_seeds']
    draws_checked=0
    for outer in range(4):
        fit=r['fits'][outer];assert fit['outer']==outer
        train=[i for i in range(n) if fold[i]!=outer];test=[i for i in range(n) if fold[i]==outer]
        mu=math.fsum(y[i] for i in train)/len(train);squares=[]
        for record in fit['inner']:
            held=record['heldout'];inner=[i for i in train if fold[i]!=held];targets=[i for i in train if fold[i]==held]
            inner_mu=math.fsum(y[i] for i in inner)/len(inner)
            close(record['mean_log_area'],inner_mu)
            assert record['training_n']==len(inner) and record['test_n']==len(targets)
            squares.extend((y[i]-inner_mu)**2 for i in targets)
        sigma=math.sqrt(math.fsum(squares)/len(squares))
        close(fit['baseline_mean_log_area'],mu);close(fit['baseline_sigma'],sigma)
        assert fit['training_n']==len(train) and fit['test_n']==len(test)
        order={};rng=np.random.default_rng(2026)
        for c in np.flatnonzero(d['capital']):order[int(c)]=rng.permutation(np.flatnonzero(d['centre']==c))
        for s,seed in enumerate(ensembles['seeds']):
            e=np.clip(np.random.default_rng(int(seed)).standard_normal(n),-2.5,2.5)
            baseline=e.copy()
            for c,members in order.items():
                pool=[c]+members[:int(round(fit['phi']*len(members)))].tolist()
                winner=max(pool,key=lambda i:float(e[i]));e[c],e[winner]=e[winner],e[c]
            a,b=fit['hierarchy_coefficients']
            for i in test:
                expected_base=min(hi,max(lo,math.exp(mu+sigma*float(baseline[i]))))
                mean=float(a)+float(b)*math.log(float(H[i]))+fit['shift']*bool(d['capital'][i])
                expected_current=min(hi,max(lo,math.exp(mean+fit['hierarchy_sigma']*float(e[i]))))
                for label,v in [('baseline',expected_base),('hierarchy',expected_current)]:
                    actual=float(ensembles[label][s,i]);assert math.isclose(actual,v,rel_tol=3e-14,abs_tol=3e-11)
                    maxdifference=max(maxdifference,abs(actual-v));draws_checked+=1
    sets=dict(all664=np.ones(n,bool),AD200_compatible=d['year200'],AD200_strict=d['year200']&d['strict'],AD200_known_end=d['year200']&d['end_known'])
    nodes={};maxcrps=0.
    for label in ['baseline','hierarchy']:
        a=ensembles[label];ns=[]
        for i in range(n):
            z=np.log(a[:,i]);observed=y[i];delta=float(np.median(z))-observed
            # Direct pair distances, unlike the producer's sorted-weight formula.
            crps=math.fsum(abs(float(v)-observed) for v in z)/len(z)-.5*float(np.mean(np.abs(z[:,None]-z[None,:])))
            ns.append(dict(crps=crps,absolute_error=abs(delta),squared_error=delta*delta,bias=delta,median=math.exp(float(np.median(z)))))
        nodes[label]=ns
    csvpred=table(OUT/'predictions.csv');assert len(csvpred)==n
    for i,row in enumerate(csvpred):
        assert int(row['source_row'])==i and row['province']==prep['province_names'][d['province'][i]]
        assert int(row['outer'])==fold[i]
        for flag,key in [('AD200_compatible','year200'),('strict_basis','strict'),('end_known','end_known')]:assert row[flag]==str(bool(d[key][i]))
        for label in nodes:
            for key,value in nodes[label][i].items():
                close(row[label+'_'+key],value)
                if key=='crps':maxcrps=max(maxcrps,abs(float(row[label+'_'+key])-value))
    def metrics(label,use):
        indices=np.flatnonzero(use).tolist();count=len(indices)
        if not count:return dict(n=0,log_area_crps=None,median_log_area_mae=None,median_log_area_rmse=None,median_log_bias=None,mean_generated_total_area_ratio=None)
        ns=nodes[label];average=lambda k:math.fsum(ns[i][k] for i in indices)/count
        ratio=math.fsum(float(v) for v in ensembles[label][:,indices].ravel())/256/math.fsum(float(d['area'][i]) for i in indices)
        return dict(n=count,log_area_crps=average('crps'),median_log_area_mae=average('absolute_error'),median_log_area_rmse=math.sqrt(average('squared_error')),
                    median_log_bias=average('bias'),mean_generated_total_area_ratio=ratio)
    cells=0
    for name in ['scores','folds','provinces']:
        actual=table(OUT/(name+'.csv'))
        expected_n={'scores':8,'folds':32,'provinces':8*len(prep['province_names'])}[name];assert len(actual)==expected_n
        for row in actual:
            use=sets[row['cohort']].copy()
            if name=='folds':use &= fold==int(row['outer'])
            if name=='provinces':
                use &= d['province']==prep['province_names'].index(row['province'])
                assert row['small_sample']==str(use.sum()<5)
            expected=metrics(row['model'],use)
            for key,value in expected.items():close(row[key],value);cells+=1
    comparisons=table(OUT/'comparisons.csv')
    for row in comparisons:
        cohort=row['cohort'];base=metrics('baseline',sets[cohort]);current=metrics('hierarchy',sets[cohort])
        close(row['pooled_crps_relative_improvement'],1-current['log_area_crps']/base['log_area_crps'])
        close(row['pooled_mae_relative_improvement'],1-current['median_log_area_mae']/base['median_log_area_mae'])
        provinces=[];wins=0
        for code in range(len(prep['province_names'])):
            use=sets[cohort]&(d['province']==code)
            if not use.any():continue
            a,b=metrics('baseline',use)['log_area_crps'],metrics('hierarchy',use)['log_area_crps'];provinces.append((a,b));wins+=b<a
        assert int(row['province_n'])==len(provinces) and int(row['province_crps_wins'])==wins
        for label,index in [('baseline',0),('hierarchy',1)]:close(row[label+'_equal_province_crps'],math.fsum(p[index] for p in provinces)/len(provinces))
    assert r['new_baseline_fits']==4 and not r['hierarchy_refit'] and r['old_five_seed_control_exact']
    assert not any(r[k] for k in ['new_blind_test','new_validation_claim','dated_extent_qualification','population_forecast','main_atlas_changed','adopt'])
    receipt=dict(status='passed_independent_baseline_hierarchy_draws_pairwise_scores_and_all_regions',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
                 draw_values_checked=draws_checked,max_area_difference_ha=maxdifference,max_pairwise_crps_difference=maxcrps,
                 aggregate_cells_checked=cells,all_664_prediction_rows_checked=True,old_five_seed_control_exact=True,fresh_outputs_byte_exact=True,
                 dated_demographic_validation=False,hierarchy_refit=False,new_blind_test=False,main_atlas_changed=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
