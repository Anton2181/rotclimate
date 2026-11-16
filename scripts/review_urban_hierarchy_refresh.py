"""Independent QR, scalar hierarchy selection and empirical forecast review."""
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median
import subprocess
import sys

import numpy as np
from scipy.linalg import lstsq

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_hierarchy as SH

BASE=ROOT/'output/urban_integration_readiness_20261116'
OUT=ROOT/'output/urban_hierarchy_refresh_20261116'
SEEDS=[1,7,19,43,97]


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def compare(actual,expected,tol=1e-9):
    assert set(actual)==set(expected)
    for k,v in expected.items():
        if isinstance(v,(str,bool)) or v is None:assert actual[k]==v,(k,actual[k],v)
        else:assert math.isclose(actual[k],v,abs_tol=tol,rel_tol=1e-10),(k,actual[k],v)


def forecast(mean,sigma,cap,order,phi,shift,seed,bounds):
    e=np.clip(np.random.default_rng(seed).standard_normal(len(mean)),-2.5,2.5)
    for c,members in order.items():
        pool=[c,*map(int,members[:round(phi*len(members))])];winner=max(pool,key=lambda i:e[i]);e[c],e[winner]=e[winner],e[c]
    return np.array([min(bounds[1],max(bounds[0],math.exp(float(m)+shift*bool(cp)+sigma*float(v)))) for m,cp,v in zip(mean,cap,e)])


def stat(area,mean,caps,pairs,centre):
    ratio=[float(area[i])/float(area[centre[i]]) for i in pairs]
    return [sum(v>1 for v in ratio)/len(ratio),median(ratio),math.exp(math.fsum(math.log(area[i])-mean[i] for i in caps)/len(caps))]


def scores(areas,truth):
    samples=[[math.log(v) for v in row] for row in areas.T];observed=[math.log(v) for v in truth]
    crps=[];error=[]
    for values,y in zip(samples,observed):
        crps.append(math.fsum(abs(v-y) for v in values)/5-math.fsum(abs(a-b) for a in values for b in values)/50)
        error.append(y-median(values))
    return dict(n=len(truth),log_area_crps=math.fsum(crps)/len(truth),median_log_area_mae=math.fsum(abs(v) for v in error)/len(truth),median_log_area_rmse=math.sqrt(math.fsum(v*v for v in error)/len(truth)))


def seed_metrics(area,truth,mean,cap,centre,pairs,indices,claim):
    a=np.sort(area[indices]);b=np.sort(truth[indices]);points=np.concatenate([a,b]);ks=max(abs(np.searchsorted(a,points,side='right')/len(a)-np.searchsorted(b,points,side='right')/len(b)))
    caps=[i for i in indices if cap[i]]
    result=dict(n=len(indices),ks=float(ks),total_area_ratio=math.fsum(area[i] for i in indices)/math.fsum(truth[i] for i in indices),pair_scope='both_endpoints_in_matching_test_fold' if claim else 'not_claimed_for_strict_subset',pair_n=len(pairs) if claim else 0,
                exceed_share=None,observed_exceed_share=None,median_ratio=None,observed_median_ratio=None,capital_n=len(caps),capital_factor=None,observed_capital_factor=None)
    if claim:
        predicted=stat(area,mean,caps,pairs,centre);observed=stat(truth,mean,caps,pairs,centre)
        result.update(exceed_share=predicted[0],observed_exceed_share=observed[0],median_ratio=predicted[1],observed_median_ratio=observed[1],capital_factor=predicted[2],observed_capital_factor=observed[2])
    return result


def main():
    result=json.loads((OUT/'results.json').read_text());audit=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_integration_readiness.py')
    for name,digest in {**result['producers'],**result['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(ROOT/'output/urban_population_recipe_20261116/model.npz') as z:H=z['floodplain_settlement_base__row_H']
    with np.load(OUT/'model.npz') as z:actualarrays={k:z[k] for k in z.files}
    rows,lat,lon,cap=SH.cohort();np.testing.assert_array_equal(cap,d['capital']);C=np.flatnonzero(cap);centre=np.full(664,-1)
    def distance(i,j):
        a,b=map(math.radians,[lat[i],lat[j]]);dl=math.radians(lon[j]-lon[i])
        return 12742*math.asin(min(1,math.sqrt(math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(dl/2)**2)))
    for i in np.flatnonzero(~cap):
        j=min(C,key=lambda j:distance(i,j))
        if distance(i,j)<=75:centre[i]=j
    np.testing.assert_array_equal(centre,actualarrays['centre']);np.testing.assert_array_equal(cap,actualarrays['capital']);np.testing.assert_array_equal(d['fold'],actualarrays['fold'])
    fold=d['fold'];truth=d['area'];y=np.array([math.log(v) for v in truth]);bounds=result['bounds_ha'];rng=np.random.default_rng(2026);order={int(c):rng.permutation(np.flatnonzero(centre==c)) for c in C}
    allpairs=[i for i in range(664) if centre[i]>=0 and fold[i]==fold[centre[i]]];assert len(allpairs)==76
    expectedgrid=[];expectedfits=[];support=[];pooled=[];foldscores=[];seedrows=[];foldseedrows=[];maxarea=0.
    for variant,lnH in [('legacy',d['lnH']),('refreshed',np.array([math.log(v) for v in H]))]:
        X=np.array([[1.,h] for h in lnH]);areas=np.zeros((5,664));means=np.zeros(664)
        for outer in range(4):
            tr=fold!=outer;trainpairs=[i for i in range(664) if centre[i]>=0 and tr[i] and tr[centre[i]]];caps=[int(i) for i in C if tr[i]]
            assert len(trainpairs)==audit['readiness']['hierarchy']['outer_support'][outer]['train_pair_records']
            for held in [None]+[f for f in range(4) if f!=outer]:
                mask=tr & ((fold!=held) if held is not None else True);_,_,rank,_=lstsq(X[mask],y[mask],lapack_driver='gelsy');assert rank==2 and mask.sum()>=10
                support.append(dict(variant=variant,outer=outer,inner=held,n=int(mask.sum()),rank=rank))
            beta,_,_,_=lstsq(X[tr],y[tr],lapack_driver='gelsy');final=X@beta;training_mean=final.copy();errors=[];inner=[]
            for held in range(4):
                if held==outer:continue
                train=tr & (fold!=held);test=tr & (fold==held);b,_,_,_=lstsq(X[train],y[train],lapack_driver='gelsy');training_mean[test]=X[test]@b
                e=[float(a-p) for a,p in zip(y[test],training_mean[test])];errors.extend(e)
                inner.append(dict(heldout=held,training_rows=int(train.sum()),test_rows=int(test.sum()),coefficients=b.tolist(),squared_error=math.fsum(v*v for v in e)))
            sigma=math.sqrt(math.fsum(v*v for v in errors)/len(errors));observed=stat(np.exp(y),training_mean,caps,trainpairs,centre);candidates=[]
            for phi in [0,.25,.5,.75,1]:
                for shift in [round(i*.1,1) for i in range(14)]:
                    values=[stat(forecast(training_mean,sigma,cap,order,phi,shift,s,bounds),training_mean,caps,trainpairs,centre) for s in SEEDS]
                    modeled=[math.fsum(v[j] for v in values)/5 for j in range(3)]
                    loss=(modeled[0]-observed[0])**2+math.log(modeled[1]/observed[1])**2+math.log(modeled[2]/observed[2])**2
                    candidate=dict(variant=variant,outer=outer,phi=phi,shift=shift,loss=loss,modeled_exceed=modeled[0],modeled_median_ratio=modeled[1],modeled_capital_factor=modeled[2]);expectedgrid.append(candidate);candidates.append(candidate)
            best=min(candidates,key=lambda c:(c['loss'],c['phi'],c['shift']));test=fold==outer
            expectedfits.append(dict(variant=variant,outer=outer,training_records=int(tr.sum()),training_pairs=len(trainpairs),training_capitals=len(caps),coefficients=beta.tolist(),sigma=sigma,selected_phi=best['phi'],selected_shift=best['shift'],selected_loss=best['loss'],observed_training=observed,inner=inner))
            for j,s in enumerate(SEEDS):areas[j,test]=forecast(final,sigma,cap,order,best['phi'],best['shift'],s,bounds)[test]
            means[test]=final[test]
        maxarea=max(maxarea,float(np.max(np.abs(areas-actualarrays[variant+'__areas']))));np.testing.assert_allclose(actualarrays[variant+'__areas'],areas,atol=1e-7,rtol=1e-10);np.testing.assert_allclose(actualarrays[variant+'__mean'],means,atol=1e-10,rtol=1e-10)
        assert (areas>=bounds[0]).all() and (areas<=bounds[1]).all()
        for cohort,indices in [('all',np.arange(664)),('strict',np.flatnonzero(d['strict']))]:
            pooled.append(dict(variant=variant,cohort=cohort,**scores(areas[:,indices],truth[indices])))
            for outer in range(4):
                use=indices[fold[indices]==outer];foldscores.append(dict(variant=variant,cohort=cohort,outer=outer,**scores(areas[:,use],truth[use])))
            for j,s in enumerate(SEEDS):
                seedrows.append(dict(variant=variant,cohort=cohort,seed=s,**seed_metrics(areas[j],truth,means,cap,centre,allpairs,indices,cohort=='all')))
                for outer in range(4):
                    use=indices[fold[indices]==outer];pairs=[i for i in allpairs if fold[i]==outer]
                    foldseedrows.append(dict(variant=variant,cohort=cohort,seed=s,outer=outer,**seed_metrics(areas[j],truth,means,cap,centre,pairs,use,cohort=='all')))
    for a,b in zip(result['fits'],expectedfits):
        for key in ['variant','outer','training_records','training_pairs','training_capitals','selected_phi','selected_shift']:assert a[key]==b[key],(key,a[key],b[key])
        np.testing.assert_allclose(a['coefficients'],b['coefficients'],atol=1e-10,rtol=1e-10);np.testing.assert_allclose(a['observed_training'],b['observed_training'],atol=1e-10,rtol=1e-10)
        assert abs(a['sigma']-b['sigma'])<1e-10 and abs(a['selected_loss']-b['selected_loss'])<1e-10
        for ai,bi in zip(a['inner'],b['inner']):
            for key in ['heldout','training_rows','test_rows']:assert ai[key]==bi[key]
            np.testing.assert_allclose(ai['coefficients'],bi['coefficients'],atol=1e-10,rtol=1e-10);assert abs(ai['squared_error']-bi['squared_error'])<1e-8
    assert len(result['fits'])==len(expectedfits)==8 and len(expectedgrid)==560
    csvcells=0
    for key,records in [('grid',expectedgrid),('scores',pooled),('fold_scores',foldscores),('seeds',seedrows),('fold_seeds',foldseedrows),('support',support)]:
        if key!='grid':
            assert len(result[key])==len(records)
            for a,b in zip(result[key],records):compare(a,b)
        with (OUT/f'{key}.csv').open() as f:csvrows=list(csv.DictReader(f))
        assert len(csvrows)==len(records)
        for row,expected in zip(csvrows,records):
            assert set(row)==set(expected)
            for k,v in expected.items():
                if v is None:assert row[k]==''
                elif isinstance(v,(str,bool)):assert row[k]==str(v)
                else:assert math.isclose(float(row[k]),v,abs_tol=1e-9,rel_tol=1e-10),(k,row[k],v)
                csvcells+=1
    assert result['source_graph']==dict(records=664,capitals=28,edges=95,closed_test_edges=76,cross_fold_edges_reported_not_pair_scored=19)
    for k in ['archived_validation_relabelled','new_blind_test','map_adopted','climate_changed','full_data_map_fit']:assert result[k] is False
    fresh={}
    for name in ['results.json','model.npz','grid.csv','scores.csv','fold_scores.csv','seeds.csv','fold_seeds.csv','support.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_urban_hierarchy_trial.py'],cwd=ROOT,text=True,capture_output=True,check=True);assert '4 passed' in tests.stdout
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),method='No trial producer/hierarchy/nested component imports. Independent haversine graph,QR means,scalar innerOOF RMS,all560training losses/8choices,residual swap/area equations,empirical CRPS/point/CDF/closed-pair metrics and every CSV cell. Fixed RNG and previously reviewed cohort reader reused.',
                outer_fits=8,grid_losses=560,primary_targets=664,strict_sensitivity_targets=153,closed_pairs=76,csv_cells=csvcells,max_area_difference_ha=maxarea,controls_stdout=tests.stdout,fresh_byte_exact=fresh,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed8isolated hierarchy fits,560losses,76closed pairs,{csvcells}CSVcells and four isolation/permutation controls')


if __name__=='__main__':main()
