"""Fixed quadrant holdouts with separated catchment disks; no new features."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from conditional_grain_extent import OUT as GRAIN, ROMAN, WINDOW, SEEDS, verify_inputs
from cereal_activity_packet import read, write, sha, table
from polity.settlement_sizes import draws, generate_area
from run_roman_benchmark import node_scores, score, masks

OUT=ROOT/'output/geographic_extent_transfer_20261117'
PLAN=ROOT/'calibration/roman_benchmark_20261117/geographic_transfer.json'
NAMES=['SW','SE','NW','NE']


def guard():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    verify_inputs();q=read(GRAIN/'qualification.json')
    for n,h in q['sources_sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in q['files_sha256'].items():assert sha(GRAIN/n)==h,n


def geometry():
    with np.load(WINDOW) as z:w=dict(z)
    with np.load(GRAIN/'features.npz') as z:f=dict(z)
    rc=np.column_stack(np.unravel_index(w['real'][f['row_centre']],w['land'].shape))
    lat=w['lat'][rc[:,0],rc[:,1]];lon=w['lon'][rc[:,0],rc[:,1]]
    group=2*(lat>=38).astype(int)+(lon>=17)
    distance=np.sqrt(np.sum((rc[:,None,:]-rc[None,:,:])**2,axis=2))*float(w['cell_km'])
    arrays=dict(group=group,centre_rc=rc,centre_lat=lat,centre_lon=lon,lnH=f['x__H_reference'])
    support=[];ready=True
    for outer in range(4):
        test=group==outer;assert test.any()
        train=(group!=outer)&(distance[:,test].min(1)>120)
        arrays[f'test_{outer}']=test;arrays[f'train_{outer}']=train
        for held in [None]+[j for j in range(4) if j!=outer]:
            te=test if held is None else train&(group==held)
            tr=train if held is None else train&(group!=held)&(distance[:,te].min(1)>120 if te.any() else False)
            if held is not None:arrays[f'inner_train_{outer}_{held}']=tr;arrays[f'inner_test_{outer}_{held}']=te
            rank=int(np.linalg.matrix_rank(np.column_stack([np.ones(len(group)),f['x__H_reference']])[tr])) if tr.any() else 0
            ok=bool(tr.sum()>=10 and te.any() and rank==2);ready &= ok
            support.append(dict(outer=NAMES[outer],inner_heldout=None if held is None else NAMES[held],
                training_n=int(tr.sum()),test_n=int(te.sum()),design_rank=rank,ready=ok,
                min_train_test_projected_km=float(distance[tr][:,te].min()) if tr.any() and te.any() else None))
    return arrays,support,ready


def fit(X,y,a,outer):
    tr=a[f'train_{outer}'];beta=np.linalg.lstsq(X[tr],y[tr],rcond=None)[0];residual=[];inner=[]
    for held in range(4):
        if held==outer:continue
        ti=a[f'inner_train_{outer}_{held}'];te=a[f'inner_test_{outer}_{held}']
        b=np.linalg.lstsq(X[ti],y[ti],rcond=None)[0];r=y[te]-X[te]@b;residual.extend(r)
        inner.append(dict(heldout=held,coefficients=b.tolist(),training_n=int(ti.sum()),test_n=int(te.sum()),squared_error=float(r@r)))
    sigma=float(np.sqrt(np.mean(np.square(residual))));assert np.isfinite(sigma) and sigma>0
    return beta,sigma,inner


def run(out):
    assert not (out/'results.json').exists(),'Preserve completed result; use --out'
    guard();a,support,ready=geometry();out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'design.npz',**a);write(out/'support.json',dict(ready=ready,rows=support))
    paths=[PLAN,Path(__file__),GRAIN/'qualification.json',GRAIN/'features.npz',ROMAN/'design.npz',
           ROMAN/'results.json',WINDOW,ROOT/'scripts/conditional_grain_extent.py',
           ROOT/'scripts/run_roman_benchmark.py',ROOT/'polity/settlement_sizes.py']
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    if not ready:
        write(out/'results.json',dict(status='geographical_support_gate_failed_no_fit',sources_sha256=sources,
            files_sha256={n:sha(out/n) for n in ['design.npz','support.json']},new_fits=0,adopt=False))
        print('Frozen support fails gate; no fits and no boundary/buffer change.');return
    with np.load(ROMAN/'design.npz') as z:d=dict(z)
    y=np.log(d['area']);n=len(y);bounds=read(ROMAN/'results.json')['bounds_ha']
    ensembles={};fits=[];means={}
    for model in ['M0','H_reference']:
        X=np.ones((n,1)) if model=='M0' else np.column_stack([np.ones(n),a['lnH']])
        ensemble=np.zeros((len(SEEDS),n));mean=np.zeros(n)
        for outer in range(4):
            beta,sigma,inner=fit(X,y,a,outer);te=a[f'test_{outer}'];mean[te]=X[te]@beta
            fits.append(dict(model=model,outer=outer,coefficients=beta.tolist(),sigma=sigma,inner=inner))
            for j,seed in enumerate(SEEDS):ensemble[j,te]=generate_area(X@beta,sigma,draws(n,int(seed)),*bounds)[te]
        ensembles[model]=ensemble;means[model]=mean
    scores=[];groups=[]
    for model,area in ensembles.items():
        ns=node_scores(area,d['area'])
        for cohort,mask in masks(d).items():
            scores.append(dict(model=model,cohort=cohort,**score(area,d['area'],ns,mask)))
            for group in range(4):groups.append(dict(model=model,cohort=cohort,group=NAMES[group],**score(area,d['area'],ns,mask&(a['group']==group))))
    np.savez_compressed(out/'ensembles.npz',**ensembles,**{'mean__'+k:v for k,v in means.items()},seeds=SEEDS)
    table(out/'scores.csv',scores);table(out/'groups.csv',groups)
    files=['design.npz','support.json','ensembles.npz','scores.csv','groups.csv']
    write(out/'results.json',dict(status='conditional_extent_contiguous_geographical_transfer',sources_sha256=sources,
        files_sha256={n:sha(out/n) for n in files},scores=scores,fits=fits,bounds_ha=bounds,
        original_training_pool=664,outer_mean_fits=8,projected_buffer_km=120,group_names=NAMES,
        shared_centre_grouping=True,new_feature_or_hour_search=False,blind_validation=False,
        dated_extents_qualified=False,historical_capacity_fit=False,atlas_changed=False,adopt=False))
    for r in scores:
        if r['cohort'] in ['AD200_compatible','AD200_strict']:print(r)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT)
    run(p.parse_args().out)
