"""Frozen current hierarchy family versus a simple same-training log-area baseline."""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from prepare_roman_benchmark import OUT,PLAN,DESIGN,HIERARCHY,sha,read,write,table
from polity.urban_hierarchy_trial import generate,member_order
from polity.settlement_sizes import draws

POPULATION=ROOT/'output/urban_population_recipe_20261116/model.npz'
SEEDS=np.arange(1000,1256)


def masks(d):
    return dict(all664=np.ones(len(d['area']),bool),AD200_compatible=d['year200'],
                AD200_strict=d['year200']&d['strict'],AD200_known_end=d['year200']&d['end_known'])


def node_scores(areas,truth):
    z=np.log(areas);y=np.log(truth);median=np.median(z,axis=0);error=median-y;k=len(z)
    ordered=np.sort(z,axis=0);weight=(2*np.arange(1,k+1)-k-1)[:,None]
    crps=np.mean(abs(z-y),axis=0)-np.sum(weight*ordered,axis=0)/k**2
    return dict(crps=crps,absolute_error=abs(error),squared_error=error**2,bias=error,median=np.exp(median))


def score(area,truth,ns,mask):
    n=int(mask.sum());keys=['log_area_crps','median_log_area_mae','median_log_area_rmse','median_log_bias','mean_generated_total_area_ratio']
    if not n:return dict(n=0,**{key:None for key in keys})
    return dict(n=n,log_area_crps=float(ns['crps'][mask].mean()),median_log_area_mae=float(ns['absolute_error'][mask].mean()),
                median_log_area_rmse=float(np.sqrt(ns['squared_error'][mask].mean())),median_log_bias=float(ns['bias'][mask].mean()),
                mean_generated_total_area_ratio=float(area[:,mask].sum(axis=1).mean()/truth[mask].sum()))


def main(out):
    for p in [PLAN,OUT/'preparation.json',OUT/'preparation_review.json']:
        assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
    assert not (out/'results.json').exists(),'Preserve completed benchmark; use isolated --out'
    prep=read(OUT/'preparation.json');review=read(OUT/'preparation_review.json')
    assert review['status']=='passed_independent_source_dates_basis_masks_and_coverage'
    assert review['preparation_sha256']==sha(OUT/'preparation.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_roman_benchmark_preparation.py')
    for n,digest in {**prep['sources_sha256'],**prep['protected_sha256']}.items():assert sha(ROOT/n)==digest,n
    for n,digest in prep['files_sha256'].items():assert sha(OUT/n)==digest,n
    with np.load(OUT/'design.npz') as z:d=dict(z)
    with np.load(HIERARCHY/'model.npz') as z:old=dict(z)
    with np.load(POPULATION) as z:H=z['floodplain_settlement_base__row_H']
    prior=read(HIERARCHY/'results.json');bounds=prior['bounds_ha'];n=len(H);y=np.log(d['area']);fold=d['fold']
    assert n==664 and (H>0).all()
    X=np.column_stack([np.ones(n),np.log(H)]);order=member_order(d['centre'],d['capital'])
    fits=[];ensemble={label:np.zeros((len(SEEDS),n)) for label in ['baseline','hierarchy']};old_control=np.zeros((5,n))
    for outer in range(4):
        receipt=next(r for r in prior['fits'] if r['variant']=='refreshed' and r['outer']==outer)
        test=fold==outer;training=~test;mean=X@np.array(receipt['coefficients'])
        np.testing.assert_allclose(mean[test],old['refreshed__mean'][test],rtol=0,atol=2e-15)
        for j,seed in enumerate([1,7,19,43,97]):
            old_control[j,test]=generate(mean,receipt['sigma'],d['capital'],order,receipt['selected_phi'],receipt['selected_shift'],seed,bounds)[test]
        mu=float(y[training].mean());residual=[];inner=[]
        for held in range(4):
            if held==outer:continue
            tr=training&(fold!=held);te=training&(fold==held);inner_mean=float(y[tr].mean())
            residual.extend(y[te]-inner_mean);inner.append(dict(heldout=held,training_n=int(tr.sum()),test_n=int(te.sum()),mean_log_area=inner_mean))
        sigma=float(np.sqrt(np.mean(np.square(residual))))
        fits.append(dict(outer=outer,training_n=int(training.sum()),test_n=int(test.sum()),baseline_mean_log_area=mu,baseline_sigma=sigma,inner=inner,
                         hierarchy_coefficients=receipt['coefficients'],hierarchy_sigma=receipt['sigma'],phi=receipt['selected_phi'],shift=receipt['selected_shift']))
        for j,seed in enumerate(SEEDS):
            e=draws(n,int(seed));baseline=np.clip(np.exp(mu+sigma*e),*bounds)
            ensemble['baseline'][j,test]=baseline[test]
            ensemble['hierarchy'][j,test]=generate(mean,receipt['sigma'],d['capital'],order,receipt['selected_phi'],receipt['selected_shift'],int(seed),bounds)[test]
    np.testing.assert_array_equal(old_control,old['refreshed__areas'])
    sets=masks(d);scores=[];provinces=[];folds=[];predictions=[];nodal={label:node_scores(a,d['area']) for label,a in ensemble.items()}
    for label,a in ensemble.items():
        ns=nodal[label]
        for cohort,mask in sets.items():
            scores.append(dict(model=label,cohort=cohort,**score(a,d['area'],ns,mask)))
            for outer in range(4):folds.append(dict(model=label,cohort=cohort,outer=outer,**score(a,d['area'],ns,mask&(fold==outer))))
            for code,name in enumerate(prep['province_names']):
                use=mask&(d['province']==code);provinces.append(dict(model=label,cohort=cohort,province=name,outer=int(fold[d['province']==code][0]),small_sample=bool(use.sum()<5),**score(a,d['area'],ns,use)))
    for i in range(n):
        row=dict(source_row=i,province=prep['province_names'][d['province'][i]],outer=int(fold[i]),AD200_compatible=bool(d['year200'][i]),strict_basis=bool(d['strict'][i]),end_known=bool(d['end_known'][i]))
        for label in ensemble:
            for key in ['crps','absolute_error','squared_error','bias','median']:row[label+'_'+key]=float(nodal[label][key][i])
        predictions.append(row)
    comparisons=[]
    for cohort in sets:
        a,b=[next(r for r in scores if r['cohort']==cohort and r['model']==label) for label in ['baseline','hierarchy']]
        group={label:[r for r in provinces if r['model']==label and r['cohort']==cohort and r['n']>0] for label in ensemble}
        comparisons.append(dict(cohort=cohort,n=a['n'],province_n=len(group['baseline']),
            pooled_crps_relative_improvement=1-b['log_area_crps']/a['log_area_crps'],
            pooled_mae_relative_improvement=1-b['median_log_area_mae']/a['median_log_area_mae'],
            baseline_equal_province_crps=float(np.mean([r['log_area_crps'] for r in group['baseline']])),
            hierarchy_equal_province_crps=float(np.mean([r['log_area_crps'] for r in group['hierarchy']])),
            province_crps_wins=sum(v['log_area_crps']<u['log_area_crps'] for u,v in zip(group['baseline'],group['hierarchy']))))
    out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'ensemble.npz',**ensemble,seeds=SEEDS,old_control=old_control)
    for name,rows in [('scores',scores),('provinces',provinces),('folds',folds),('predictions',predictions),('comparisons',comparisons)]:table(out/(name+'.csv'),rows)
    paths=[Path(__file__),PLAN,OUT/'preparation.json',OUT/'preparation_review.json',OUT/'design.npz',HIERARCHY/'results.json',HIERARCHY/'model.npz',POPULATION,
           ROOT/'polity/urban_hierarchy_trial.py',ROOT/'polity/settlement_sizes.py']
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    for name,digest in prep['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(out/'results.json',dict(status='conditional_Roman_size_benchmark_development_only',sources_sha256=sources,protected_sha256=prep['protected_sha256'],
        files_sha256={name:sha(out/name) for name in ['ensemble.npz','scores.csv','provinces.csv','folds.csv','predictions.csv','comparisons.csv']},
        fits=fits,old_five_seed_control_exact=True,evaluation_seeds=SEEDS.tolist(),bounds_ha=bounds,scores=scores,comparisons=comparisons,
        original_training_records=664,AD200_target_filter_not_training_filter=True,new_baseline_fits=4,hierarchy_refit=False,
        known_site_geometry_and_capitals_supplied=True,province_hash_folds_not_contiguous_blocks=True,
        new_fit=True,new_blind_test=False,new_validation_claim=False,dated_extent_qualification=False,population_forecast=False,
        food_work_climate_route_solver_calls=0,main_atlas_changed=False,adopt=False))
    print('Exact five-seed control; completed256seed comparison with four baseline fits, no hierarchy refit',flush=True)
    for row in comparisons:print(row,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=OUT);main(parser.parse_args().out)
