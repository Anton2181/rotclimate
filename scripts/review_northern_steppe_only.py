"""Review the sole-target world search and independently reconstruct final climate scores."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import ast
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import label

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.config import Params
from rotclimate.geography import build_grid
from rotclimate.model import ClimateModel
from rotclimate.koppen import CODES

OUT=ROOT/'output/northern_steppe_only_20261116'
FOLDER=ROOT/'calibration/northern_steppe_only_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def close(a,b,atol=1e-9,rtol=1e-10):np.testing.assert_allclose(a,b,atol=atol,rtol=rtol)


def monthly(T,P,year):
    nt=len(T);edges=np.arange(13)*year/12;w=np.zeros((12,nt));dt=year/nt
    for m in range(12):
        for t in range(nt):w[m,t]=max(0,min(edges[m+1],(t+1)*dt)-max(edges[m],t*dt))
    w/=w.sum(1)[:,None]
    return np.einsum('mt,tyx->myx',w,T),np.einsum('mt,tyx->myx',w,P)*year/12


def statistics(Tm,Pm,mask,year,solstice):
    MAT=Tm.mean(0);MAP=Pm.sum(0);Tcold=Tm.min(0);Thot=Tm.max(0)
    centres=(np.arange(12)+.5)*year/12
    summer=np.abs((centres-(solstice+year/2)+year/2)%year-year/2)<year/4
    Ps=Pm[summer].sum(0);Pw=Pm[~summer].sum(0)
    threshold=np.maximum(np.where(Pw>=.7*MAP,2*MAT,np.where(Ps>=.7*MAP,2*MAT+28,2*MAT+14)),.5)
    aridity=MAP/(10*threshold)
    # Independent formula, rather than score.memberships/climate_indices.
    sig=lambda x:1/(1+np.exp(-np.clip(x,-30,30)))
    membership=sig((18-MAT)/1.2)*sig(-np.log(np.maximum(aridity,.001))/.18)
    score=math.fsum(membership[mask])/int(mask.sum())
    cold=MAT<18;desert=(MAP<5*threshold)&cold;steppe=(MAP>=5*threshold)&(MAP<10*threshold)&cold
    metrics=dict(score=score,target_cells=int(mask.sum()),MAT=float(np.median(MAT[mask])),
        MAP=float(np.median(MAP[mask])),aridity=float(np.median(aridity[mask])),
        Tcold=float(np.median(Tcold[mask])),Thot=float(np.median(Thot[mask])),
        BSk_share=float(steppe[mask].mean()),BWk_share=float(desert[mask].mean()),
        cold_dry_koppen_share=float((steppe|desert)[mask].mean()),
        monthly_T_median=[float(np.median(v[mask])) for v in Tm],
        monthly_P_median=[float(np.median(v[mask])) for v in Pm])
    return metrics,dict(MAT=MAT,MAP=MAP,aridity=aridity,Tcold=Tcold,Thot=Thot),membership


def main():
    protocol=json.loads((FOLDER/'protocol.json').read_text());plan=json.loads((FOLDER/'plan.json').read_text())
    result=json.loads((OUT/'results.json').read_text());comparison=json.loads((OUT/'comparison.json').read_text())
    assert result['protocol_sha256']==sha(FOLDER/'protocol.json')
    assert protocol['plan_sha256']==sha(FOLDER/'plan.json')
    for name,digest in {**protocol['sources_sha256'],**protocol['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert protocol['objective_weights']['cold_dry']==1
    assert all(v==0 for k,v in protocol['objective_weights'].items() if k!='cold_dry')
    # The actual optimization function must use only its target metrics score.
    tree=ast.parse((ROOT/'scripts/northern_steppe_only.py').read_text())
    job=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='score_job')
    calls=[n for n in ast.walk(job) if isinstance(n,ast.Call)]
    assert not any(isinstance(n.func,ast.Name) and n.func.id in ['evaluate','objective'] for n in calls)
    rows=[json.loads(s) for s in (OUT/'evals.jsonl').read_text().splitlines()]
    assert len(rows)==97 and sorted(r['eval'] for r in rows)==list(range(1,98))
    assert plan['search']['evaluations']==97 and plan['search']['population']==12
    base=protocol['base'];space=protocol['space'];free={v[0] for v in space}|{'downsample','beyond_seed'}
    for row in rows:
        assert len(row['x'])==len(space)
        for x,(name,lo,hi) in zip(row['x'],space):
            assert 0<=x<=1
            expected=(lo+x*(hi-lo)>.5) if name=='retrograde' else lo+x*(hi-lo)
            close(row['params'][name],expected,atol=1e-11)
        for name,value in base.items():
            if name not in free:assert row['params'][name]==value,(row['eval'],name)
        assert row['params']['downsample']==64 and row['params']['beyond_seed']==1
        assert row['numerics_passed'] and 0<=row['score']<=1
    best=max(rows,key=lambda r:(r['score'],-r['eval']));saved=json.loads((OUT/'best.json').read_text())
    assert best==saved and json.loads((OUT/'best_params.json').read_text())==best['params']
    search=json.loads((OUT/'search.json').read_text());assert search['attempted']==97 and search['best_eval']==best['eval']
    assert search['best_score']==best['score'] and search['termination']=={'budget_complete':True}
    numerics=json.loads((OUT/'numerics.json').read_text());assert set(numerics)=={'baseline','candidate'}
    for records in numerics.values():assert len(records)==3 and all(r['all_checks_passed'] for r in records)
    assert comparison['layouts']==[1,2,3] and comparison['final_downsample']==16 and not comparison['selection_after_comparison']
    with np.load(OUT/'preview.npz') as z:preview={k:z[k] for k in z.files}
    checked=0;membershipchecks={}
    for name,params in [('baseline',base),('candidate',best['params'])]:
        p=Params(**params).replace(downsample=16,beyond_seed=1);g=build_grid(p)
        mask=g.inmap&g.land&(g.target==2)
        for key,value in [('land',g.land),('inmap',g.inmap),('target',g.target),('steppe_mask',mask),('lat',g.lat),('elev',g.elev)]:
            np.testing.assert_array_equal(preview[name+'__'+key],value)
        members=[]
        for j in [1,2,3]:
            with np.load(OUT/'members'/f'{name}_{j}.npz') as z:T,P=z['T'],z['P']
            Tm,Pm=monthly(T,P,p.year_days);m,_,_=statistics(Tm,Pm,mask,p.year_days,p.winter_solstice_day)
            for key,value in m.items():close(comparison['members'][name][j-1][key],value)
            members.append((T,P));checked+=1
        T=np.mean([a[0] for a in members],axis=0).astype(np.float32);P=np.mean([a[1] for a in members],axis=0).astype(np.float32)
        Tm,Pm=monthly(T,P,p.year_days);m,fields,mem=statistics(Tm,Pm,mask,p.year_days,p.winter_solstice_day)
        close(preview[name+'__Tm'],Tm);close(preview[name+'__Pm'],Pm)
        for key,value in fields.items():close(preview[name+'__'+key],value)
        for key,value in m.items():close(comparison['ensemble'][name][key],value)
        assert comparison['ensemble'][name]['target_components']==label(mask)[1]
        close(comparison['ensemble'][name]['target_latitude_range'],[g.lat[mask].min(),g.lat[mask].max()])
        # Adversarially replace all other-zone monthly fields. The objective
        # stays exact even when their climates change drastically.
        other=~mask;changedT=Tm.copy();changedP=Pm.copy();changedT[:,other]+=90;changedP[:,other]*=100
        changed,_,_=statistics(changedT,changedP,mask,p.year_days,p.winter_solstice_day)
        assert changed['score']==m['score']
        membershipchecks[name]=m['score']
        cold=preview[name+'__koppen'];bs=next(i for i,c in enumerate(CODES) if c=='BSk');bw=next(i for i,c in enumerate(CODES) if c=='BWk')
        close((cold[mask]==bs).mean(),m['BSk_share']);close((cold[mask]==bw).mean(),m['BWk_share'])
    # Re-run only baseline and selected coarse point; no post-check reselection.
    replay={}
    for tag,row in [('baseline',next(r for r in rows if r['eval']==1)),('candidate',best)]:
        p=Params(**row['params']);r=ClimateModel(p).run();assert r.numerics['all_checks_passed']
        Tm,Pm=monthly(r.T,r.P,p.year_days);mask=r.grid.inmap&r.grid.land&(r.grid.target==2)
        m,_,_=statistics(Tm,Pm,mask,p.year_days,p.winter_solstice_day)
        close(m['score'],row['score']);replay[tag]=m['score'];print('Fresh coarse score replay',tag,m['score'],flush=True)
    assert not result['adopt'] and not result['main_atlas_changed'] and not result['new_validation_claim']
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
        evaluations_checked=97,final_members_checked=checked,final_ensembles_checked=2,
        coarse_scores_replayed=replay,final_scores=membershipchecks,non_target_objective_perturbation_exact=True,
        source_and_locked_parameter_hashes_passed=True,
        scope='Independent monthly overlap weights,annual/aridity/membership/BSk/BWk equations;all97 parameter bounds and winner;all6 saved members and2 field means; fresh coarse baseline/winner simulations reuse canonical physics. No other-zone optimization or post-comparison reselection.',
        adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
