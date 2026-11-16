"""Paired legacy/refreshed-H hierarchy trial under repaired training isolation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.stats import ks_2samp

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_hierarchy as SH
from polity.urban_hierarchy_trial import fit_fold,closed_pairs,ensemble_scores
from polity.survey_transfer import sphere_distance

BASE=ROOT/'output/urban_integration_readiness_20261116'
OUT=ROOT/'output/urban_hierarchy_refresh_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/hierarchy_refresh_trial.json'
SEEDS=[1,7,19,43,97]


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def seed_scores(area,truth,mean,cap,centre,pairs,mask,claim_pairs):
    record=dict(n=int(mask.sum()),ks=float(ks_2samp(area[mask],truth[mask]).statistic),total_area_ratio=float(area[mask].sum()/truth[mask].sum()),
                pair_scope='both_endpoints_in_matching_test_fold' if claim_pairs else 'not_claimed_for_strict_subset',
                pair_n=int(pairs.sum()) if claim_pairs else 0,exceed_share=None,observed_exceed_share=None,median_ratio=None,observed_median_ratio=None,
                capital_n=int((cap & mask).sum()),capital_factor=None,observed_capital_factor=None)
    if claim_pairs:
        ratio=area[pairs]/area[centre[pairs]];observed=truth[pairs]/truth[centre[pairs]];caps=cap & mask
        record.update(exceed_share=float(np.mean(ratio>1)),observed_exceed_share=float(np.mean(observed>1)),median_ratio=float(np.median(ratio)),observed_median_ratio=float(np.median(observed)),
                      capital_factor=float(np.exp(np.mean(np.log(area[caps])-mean[caps]))),observed_capital_factor=float(np.exp(np.mean(np.log(truth[caps])-mean[caps]))))
    return record


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    audit=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_integration_readiness.py')
    for name,digest in {**audit['sources_sha256'],**audit['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in audit['files_sha256'].items():assert sha(BASE/name)==digest,name
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(ROOT/'output/urban_population_recipe_20261116/model.npz') as z:H=z['floodplain_settlement_base__row_H']
    rows,lat,lon,cap=SH.cohort();np.testing.assert_array_equal(cap,d['capital']);np.testing.assert_array_equal([r['area'] for r in rows],d['area'])
    centre=np.full(len(rows),-1);C=np.flatnonzero(cap)
    for i in np.flatnonzero(~cap):
        distance=sphere_distance(lat[C],lon[C],lat[i],lon[i]);j=int(np.argmin(distance))
        if distance[j]<=75:centre[i]=C[j]
    fold=d['fold'];truth=d['area'];y=np.log(truth);allpairs=np.zeros(len(rows),bool)
    for outer in range(4):
        test=closed_pairs(centre,fold,outer);train=closed_pairs(centre,fold,outer,True);allpairs |= test
        expected=audit['readiness']['hierarchy']['outer_support'][outer]
        assert int(test.sum())==expected['test_same_fold_pair_records'] and int(train.sum())==expected['train_pair_records']
    assert len(rows)==664 and len(C)==28 and (centre>=0).sum()==95 and allpairs.sum()==76 and (H>0).all()
    features={'legacy':d['lnH'],'refreshed':np.log(H)};support=[]
    for variant,lnH in features.items():
        X=np.column_stack([np.ones(len(rows)),lnH])
        for outer in range(4):
            for inner in [None]+[v for v in range(4) if v!=outer]:
                tr=(fold!=outer)&((fold!=inner) if inner is not None else True);rank=int(np.linalg.matrix_rank(X[tr]))
                assert tr.sum()>=10 and rank==2;support.append(dict(variant=variant,outer=outer,inner=inner,n=int(tr.sum()),rank=rank))
    arrays=dict(centre=centre,capital=cap,fold=fold);fits=[];grid=[];scores=[];fold_scores=[];seeds=[];fold_seeds=[]
    bounds=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary']['area_range_ha']
    for variant,lnH in features.items():
        areas=np.zeros((5,len(rows)));mean=np.zeros(len(rows))
        for outer in range(4):
            ensemble,pred,receipt,candidates=fit_fold(lnH,y,fold,cap,centre,outer,bounds=bounds)
            test=fold==outer;areas[:,test]=ensemble[:,test];mean[test]=pred[test]
            fits.append(dict(variant=variant,**receipt))
            for c in candidates:grid.append(dict(variant=variant,outer=outer,phi=c['phi'],shift=c['shift'],loss=c['loss'],modeled_exceed=c['modeled'][0],modeled_median_ratio=c['modeled'][1],modeled_capital_factor=c['modeled'][2]))
        arrays[variant+'__areas']=areas;arrays[variant+'__mean']=mean
        for cohort,mask in [('all',np.ones(len(rows),bool)),('strict',d['strict'])]:
            scores.append(dict(variant=variant,cohort=cohort,**ensemble_scores(areas[:,mask],truth[mask])))
            for outer in range(4):
                use=mask & (fold==outer);fold_scores.append(dict(variant=variant,cohort=cohort,outer=outer,**ensemble_scores(areas[:,use],truth[use])))
            for j,seed in enumerate(SEEDS):
                seeds.append(dict(variant=variant,cohort=cohort,seed=seed,**seed_scores(areas[j],truth,mean,cap,centre,allpairs,mask,cohort=='all')))
                for outer in range(4):
                    use=mask & (fold==outer);pairs=closed_pairs(centre,fold,outer)
                    fold_seeds.append(dict(variant=variant,cohort=cohort,seed=seed,outer=outer,**seed_scores(areas[j],truth,mean,cap,centre,pairs,use,cohort=='all')))
    assert len(fits)==8 and len(grid)==560 and len(scores)==4 and len(fold_scores)==16 and len(seeds)==20 and len(fold_seeds)==80
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'model.npz',**arrays)
    for name,records in [('grid',grid),('scores',scores),('fold_scores',fold_scores),('seeds',seeds),('fold_seeds',fold_seeds),('support',support)]:table(out/f'{name}.csv',records)
    protected=dict(audit['protected_sha256']);protected.update(audit['sources_sha256'])
    for name in ['results.json','review.json',*audit['files_sha256']]:protected[str((BASE/name).relative_to(ROOT))]=sha(BASE/name)
    paths=[Path(__file__),PLAN,ROOT/'polity/urban_hierarchy_trial.py',ROOT/'tests/test_urban_hierarchy_trial.py',ROOT/'polity/urban_predictive_pilot.py']
    result=dict(status='paired_joint_hierarchy_development_trial_training_isolated',fits=fits,scores=scores,fold_scores=fold_scores,seeds=seeds,fold_seeds=fold_seeds,support=support,
                source_graph=dict(records=664,capitals=28,edges=95,closed_test_edges=76,cross_fold_edges_reported_not_pair_scored=19),bounds_ha=bounds,
                producers={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                files_sha256={name:sha(out/name) for name in ['model.npz','grid.csv','scores.csv','fold_scores.csv','seeds.csv','fold_seeds.csv','support.csv']},
                conditional_geometry='All source positions and supplied capital labels known;outer-test areas excluded from all mean/sigma/phi/shift fitting.',
                archived_validation_relabelled=False,new_blind_test=False,map_adopted=False,climate_changed=False,full_data_map_fit=False)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote8isolated hierarchy fits,560grid losses,complete664/153target ensembles and76closed held-out pairs')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
