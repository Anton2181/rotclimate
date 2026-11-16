"""Independent recruitment, physical work, canonical stocks, routes and finite staff review."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.sparse import coo_matrix,load_npz

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from review_urban_hierarchy_candidate import ownership
from harvest.food_stocks import periodic_food_year
from polity.settlement_support import permanent_food_ceiling

OUT=ROOT/'output/urban_candidate_seasonal_20261116';BASE=ROOT/'output/urban_hierarchy_candidate_20261116';KCAL=912500.


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def close(a,b,atol=1e-5,rtol=3e-11):np.testing.assert_allclose(a,b,atol=atol,rtol=rtol)


def people_review():
    cases=0;links=0;maximum=0.
    for mode in ['raw','corrected']:
        sites=json.loads((BASE/f'control/placed_{mode}_sites.json').read_text())['sites']
        with np.load(BASE/f'control/placed_{mode}_fields.npz') as z:land=z['land'];people=z['people'];cell=float(z['cell_km'])
        centres=np.array([(s['row'],s['column']) for s in sites]);source=np.flatnonzero(land);lookup=np.full(land.size,-1,int);lookup[source]=np.arange(len(source))
        H,loc,dest,weight=ownership(land,people,centres,cell);yy,xx=np.indices(land.shape)
        for model in ['control','candidate']:
            with np.load(BASE/f'{model}/placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
            for reading in ['central','low']:
                area=f['area_ha'];density=np.array([100 if reading=='low' else 100+400*max(0,min(1,math.log(max(float(a),1e-9)/50)/math.log(8))) for a in area])
                wanted=area*density;own=np.minimum(wanted,.5*H);extra=wanted-own
                amounts=people.ravel()[loc]*weight*np.divide(own,H,out=np.zeros_like(own),where=H>0)[dest]
                rural=people.ravel()-np.bincount(loc,weights=amounts,minlength=people.size)
                rows=[lookup[loc]];cols=[dest];values=[amounts]
                for i in sorted(range(len(sites)),key=lambda i:-extra[i]):
                    if extra[i]<=0:break
                    d2=((yy-centres[i,0])**2+(xx-centres[i,1])**2)*cell**2
                    for radius in [120.,240.,480.,960.,1920.]:
                        mask=land&(d2<=radius**2);pool=math.fsum(rural[mask.ravel()])
                        if pool>=4*extra[i]:break
                    amount=min(extra[i],.25*pool);ids=np.flatnonzero(mask);v=rural[ids]*amount/pool
                    rows.append(lookup[ids]);cols.append(np.full(len(ids),i));values.append(v);rural[ids]*=1-amount/pool
                expected=coo_matrix((np.concatenate(values),(np.concatenate(rows),np.concatenate(cols))),shape=(len(source),len(sites))).tocsr();expected.eliminate_zeros()
                actual=load_npz(OUT/f'prepared/people_{mode}_{model}_{reading}.npz')
                np.testing.assert_array_equal(actual.indptr,expected.indptr);np.testing.assert_array_equal(actual.indices,expected.indices)
                close(actual.data,expected.data,atol=1e-8);maximum=max(maximum,float(np.max(np.abs(actual.data-expected.data))))
                close(np.asarray(actual.sum(0)).ravel(),f['residents_'+reading],atol=1e-6)
                close(people.ravel()[source]-np.asarray(actual.sum(1)).ravel(),f['rural_'+reading].ravel()[source],atol=1e-6)
                cases+=1;links+=actual.nnz;print('Independent people links',mode,model,reading,flush=True)
    return dict(cases=cases,sparse_links=links,max_link_difference_people=maximum)


def check_inventory(a,prefix,harvest,need,capacity):
    y=periodic_food_year(harvest,need,capacity,loss_fraction_year=.05,step_days=365/12,record=True)
    scale=np.maximum(1,np.maximum(y.harvested,y.needed));tol=1e-10*scale+100*np.finfo(float).eps*scale
    for field in ['initial_stock','final_stock','peak_stock','harvested','needed','consumed','unmet','spoiled','overflow','stock_path','unmet_path']:
        assert np.all(np.abs(a[prefix+'__'+field]-getattr(y,field))<=tol),(prefix,field,float((np.abs(a[prefix+'__'+field]-getattr(y,field))/tol).max()))
    assert y.periodic_converged.all();return y


def inspect_case(c):
    key=c['key'];mode=c['mode'];model=c['model'];reading=c['reading'];path=OUT/'cases'/key
    assert sha(path/'fields.npz')==c['fields_sha256']
    assert json.loads((path/'results.json').read_text())==c
    with np.load(path/'fields.npz') as z:a={k:z[k] for k in z.files}
    with np.load(BASE/f'{model}/placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
    with np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z:x={k:z[k] for k in z.files}
    with np.load(OUT/f'prepared/network_{mode}.npz') as z:net={k:z[k] for k in z.files}
    M=load_npz(OUT/f'prepared/people_{mode}_{model}_{reading}.npz');source=np.flatnonzero(f['land'])
    sites=json.loads((BASE/f'{model}/placed_{mode}_sites.json').read_text())['sites'];n=len(sites)
    np.testing.assert_array_equal(a['source'],source);np.testing.assert_array_equal(a['request'],f['residents_'+reading])
    people=f['people'].ravel()[source];np.testing.assert_array_equal(a['people'],people)
    frac=np.clip(np.divide(a['target'],a['request'],out=np.zeros(n),where=a['request']>0),0,1);moved=M@frac;rural=people-moved
    close(a['rural'],rural,atol=1e-8);close(a['moved'],moved,atol=1e-8)
    assert rural.min()>=-1e-8 and (a['target']<=a['request']+1e-6).all()
    close(people.sum(),rural.sum()+a['target'].sum(),atol=1e-6)
    potential=x['potential_kcal'][source];listed=x['listed_hours'][source];reaping=x['reaping_hours'][source]
    workers=rural*.4;annual=workers*c['hours_worker_year'];peak=np.minimum(annual,workers*240)
    req=potential*listed/1e6;reap=potential*reaping/1e6
    retained=np.where(potential>0,np.minimum(1,np.minimum(np.divide(annual,req,out=np.ones_like(annual),where=req>0),np.divide(peak,reap,out=np.ones_like(peak),where=reap>0))),0)
    produced=potential*retained
    for field,v in [('produced',produced),('annual_hours_available',annual),('annual_hours_used',req*retained),('reaping_hours_available',peak),('reaping_hours_used',reap*retained)]:close(a[field],v,atol=.001)
    assert (a['annual_hours_used']<=annual+1e-5).all() and (a['reaping_hours_used']<=peak+1e-5).all()
    bits=x['boundaries'][source].astype(int);first=np.log2(np.maximum(bits&-bits,1)).astype(int)
    harvest=np.zeros((12,len(source)));harvest[first,np.arange(len(source))]=a['produced']
    np.testing.assert_array_equal(a['harvest'],harvest)
    rn=np.broadcast_to(a['rural']*KCAL/12,harvest.shape)
    ry=check_inventory(a,'rural',harvest,rn,a['rural']*KCAL)
    protected=ry.unmet<=1e-8*np.maximum(1,ry.needed)
    # Check marketed overflow against saved stocks too, avoiding amplification
    # of the permitted root difference into a different export input.
    available=a['rural__stock_path'][:-1]+harvest-rn-a['rural']*KCAL
    marketed=np.maximum(available,0)*protected*c['marketed_share'];close(a['marketed'],marketed,atol=.001)
    owner=net['owner'][:,source];share=net['share'][:,source];dispatch=np.broadcast_to(marketed.sum(0)/12,marketed.shape).copy()
    for month in range(12):dispatch[month]*=(owner[month//3]>=0)&(share[month//3]>0)
    ey=check_inventory(a,'export',a['marketed'],dispatch,a['marketed'].sum(0))
    close(a['departures'],dispatch-a['export__unmet_path'],atol=.001)
    assert not (a['departures'][:,~protected]>1e-6).any()
    direct=np.zeros((12,n))
    for month in range(12):
        q=month//3;valid=(owner[q]>=0)&(share[q]>0)
        np.add.at(direct[(month+1)%12],owner[q,valid],a['departures'][month,valid]*share[q,valid])
    close(direct,a['direct'],atol=.01)
    tn=np.broadcast_to(a['target']*KCAL/12,(12,n));capacity=a['target']*2500*90
    ly=check_inventory(a,'direct',a['direct'],tn,capacity)
    local_supported=(a['target']>0)&(a['direct__unmet']<=1e-8*np.maximum(1,a['direct__needed']))
    overflow=np.maximum(a['direct__stock_path'][:-1]+a['direct']-tn-capacity,0)*local_supported
    received=np.zeros((12,n));exported=received.copy();flows=[]
    for month in range(12):
        b=net['between'][month//3];left=overflow[month].copy();need=a['direct__unmet_path'][(month+1)%12].copy()
        links=np.argwhere((b>0)&(left[:,None]>0)&(need[None,:]>0)).tolist()
        for i,j in sorted(links,key=lambda ij:(-b[ij[0],ij[1]],ij[0],ij[1])):
            if left[i]<=0 or need[j]<=0:continue
            v=min(left[i],need[j]/b[i,j]);left[i]-=v;need[j]-=v*b[i,j]
            exported[month,i]+=v;received[(month+1)%12,j]+=v*b[i,j];flows.append([month,i,j,v,v*b[i,j]])
            if need[j]<1e-9*max(1,v):need[j]=0.
    close(a['shipments'],np.array(flows).reshape(-1,5),atol=.01)
    close(a['inter_exported'],exported,atol=.01);close(a['inter_received'],received,atol=.01)
    assert (exported<=overflow+.01).all() and not ((exported.sum(0)>0)&(received.sum(0)>0)).any()
    close(a['arrivals'],a['direct']+received,atol=.01)
    ty=check_inventory(a,'town',a['arrivals'],tn,capacity)
    parent_frac=np.clip(np.divide(a['certificate_from_target'],a['request'],out=np.zeros(n),where=a['request']>0),0,1)
    ceiling=permanent_food_ceiling(a['certificate_from_arrivals']);close(a['food_ceiling'],ceiling,atol=1e-8)
    budget=np.bincount(M.indices,weights=M.data*parent_frac[M.indices],minlength=n)
    affiliation=np.array([bool(s.get('actor')) for s in sites]);active=affiliation&(a['request']>=50)&(np.minimum(budget,ceiling)>=150)
    staff=active*100.;civil=np.minimum(np.minimum(a['request'],np.maximum(budget-staff,0)),np.maximum(ceiling-staff,0))
    close(a['staff'],staff);close(a['civilian'],civil);close(a['allocator_total'],staff+civil);np.testing.assert_array_equal(a['active'],active)
    assert (staff+civil<=budget+1e-7).all()
    qualified=bool(c['physical_certificate'] and np.all(a['town__unmet']<=1e-8*np.maximum(1,a['town__needed'])) and np.all(np.abs(a['allocator_total']-a['target'])<=np.maximum(1e-6,1e-10*a['request'])))
    assert c['qualified']==qualified and 64<=c['iterations']<=512
    history=c['history'];assert len(history)==c['iterations']
    close(history[0]['requested_total'],a['request'].sum())
    assert all(history[i+1]['requested_total']<=history[i]['requested_total']+1e-6 for i in range(len(history)-1))
    close((history[-1]['supported_total'] if c['physical_certificate'] or not c['converged'] else history[-1]['requested_total']),a['target'].sum())
    if c['physical_certificate']:close(history[-1]['requested_total'],a['certificate_from_target'].sum())
    # Use recorded (canonical-replay checked) stock paths to close the same
    # physical source/export/town ledger with compensated scalar summation.
    S=lambda v:math.fsum(np.asarray(v).ravel())
    ledger=dict(produced_kcal=S(a['produced']),rural_meals_kcal=S(a['rural__consumed']),rural_spoiled_kcal=S(a['rural__spoiled']),
        export_spoiled_kcal=S(a['export__spoiled']),town_spoiled_kcal=S(a['town__spoiled']),
        source_unused_kcal=S(a['rural__overflow'])-S(a['marketed'])+S(a['export__overflow']),
        town_unused_kcal=S(a['town__overflow'])-S(exported),source_transport_loss_kcal=S(a['departures'])-S(a['direct']),
        intertown_transport_loss_kcal=S(exported)-S(received),town_meals_kcal=S(a['town__consumed']),
        stock_change_kcal=sum(S(a[p+'__final_stock']-a[p+'__initial_stock']) for p in ['rural','export','town']))
    for field,value in ledger.items():close(c['audit']['ledger'][field],value,atol=.1)
    residual=ledger['produced_kcal']-math.fsum(v for k,v in ledger.items() if k!='produced_kcal')
    assert abs(residual)<1e-9*ledger['produced_kcal']
    for field,value in [('supported',S(a['target'])),('requested',S(a['request'])),('rural_people',S(a['rural'])),('world_people',S(a['people'])),('staff',S(staff)),('civilians',S(civil))]:close(c[field],value)
    assert c['active_institutions']==int(active.sum())
    assert c['audit']['rural_deficit_origins']==int((a['rural__unmet']>1e-8*np.maximum(1,a['rural__needed'])).sum())
    print('Independent seasonal case',key,'qualified',qualified,flush=True)
    return dict(town_rows=n,source_cells=len(source),shipments=len(flows),grain_residual_person_years=residual/KCAL)


def main(provenance_only):
    prep=json.loads((OUT/'preparation.json').read_text())
    for name,digest in {**prep['sources_sha256'],**prep['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    provenance=people_review()
    if provenance_only:
        (OUT/'people_review.json').write_text(json.dumps(dict(status='passed',reviewer_sha256=sha(Path(__file__)),**provenance),indent=2)+'\n');return
    r=json.loads((OUT/'results.json').read_text())
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert len(r['cases'])==16 and r['all_cases_completed']
    checks=[inspect_case(c) for c in r['cases']]
    with (OUT/'towns.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==33392
    with np.load(OUT/'town_model.npz') as z:
        for c in r['cases']:
            key=c['key'];group=[t for t in rows if t['case']==key];assert len(group)==len(z[key+'__target'])
            for i,row in enumerate(group):
                for field,v in [('requested','request'),('supported','target'),('civilian','civilian'),('staff','staff'),('conditional_initial_supported','initial_supported')]:close(float(row[field]),z[key+'__'+v][i])
                assert row['active']==str(bool(z[key+'__active'][i])) and row['qualified']==str(c['qualified'])
    assert not r['adopt'] and not r['main_atlas_published'] and not r['new_validation_claim']
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),provenance=provenance,
        seasonal_cases=16,town_scenario_rows=sum(c['town_rows'] for c in checks),physical_source_cases=sum(c['source_cells'] for c in checks),
        shipment_rows=sum(c['shipments'] for c in checks),max_grain_residual_person_years=max(abs(c['grain_residual_person_years']) for c in checks),
        qualified_cases=sum(c['qualified'] for c in r['cases']),
        scope='Independent full-distance/compensated recruitment links;separate field-work and sorted-link trade;canonical bisection stock replay versus isolated closed root;finite cohort/budget formulas and complete physical grain ledger. Freight physics and permanent-food-ceiling primitive reused,not independently rederived.',adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--provenance-only',action='store_true');a=p.parse_args();main(a.provenance_only)
