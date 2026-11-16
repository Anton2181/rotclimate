"""Independent annual source/work, freight allocation and complete grain-ledger review."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_candidate_supply_20261116'
KCAL=912500.


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def close(a,b,atol=1e-5,rtol=3e-11):
    np.testing.assert_allclose(a,b,atol=atol,rtol=rtol)


def table(p):
    with p.open() as f:return list(csv.DictReader(f))


def independent_plan(grain,need,owner,share,between):
    n=len(need);delivered=np.zeros(n);sent=np.zeros(n)
    # Explicit sorted groups and compensated sums, separate from bincounts.
    for season in range(len(owner)):
        valid=(owner[season]>=0)&(share[season]>0)
        ids=owner[season,valid];order=np.argsort(ids,kind='stable');ids=ids[order]
        amounts=(grain[valid]/len(owner))[order];arrivals=amounts*share[season,valid][order]
        starts=np.r_[0,np.flatnonzero(np.diff(ids))+1];ends=np.r_[starts[1:],len(ids)]
        for start,end in zip(starts,ends):
            sent[ids[start]]+=math.fsum(amounts[start:end]);delivered[ids[start]]+=math.fsum(arrivals[start:end])
    excess=np.maximum(delivered-need,0);deficit=np.maximum(need-delivered,0)
    left=excess.copy();wanted=deficit.copy();received=np.zeros(n);exported=np.zeros(n);moves={}
    links=np.argwhere((between>0)&(excess[:,None]>0)&(deficit[None,:]>0)).tolist()
    for i,j in sorted(links,key=lambda pair:(-between[pair[0],pair[1]],pair[0],pair[1])):
        if left[i]<=0 or wanted[j]<=0:continue
        amount=min(left[i],wanted[j]/between[i,j]);left[i]-=amount;wanted[j]-=amount*between[i,j]
        received[j]+=amount*between[i,j];exported[i]+=amount;moves[(i,j)]=amount
        if wanted[j]<1e-9*max(1.,amount):wanted[j]=0.
    return dict(delivered=delivered,sent=sent,excess=excess,deficit=deficit,received=received,
                exported=exported,moves=moves,fed=np.minimum(delivered,need)+received)


def main():
    r=json.loads((OUT/'results.json').read_text());archived=json.loads((ROOT/'output/settlement_release4_20261116/supply/results.json').read_text())
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['variants']['control']==archived and r['released_control_exact']
    with np.load(OUT/'town_model.npz') as z:compact={k:z[k] for k in z.files}
    cases=0;towncases=0;maxdelivery=0.;maxreceived=0.;maxledger=0.
    for label in ['control','candidate']:
        variant=r['variants'][label]
        assert json.loads((OUT/label/'results.json').read_text())==variant
        for mode in ['raw','corrected']:
            sites=json.loads((OUT/f'packets/{label}/placed_{mode}_sites.json').read_text())['sites']
            with np.load(OUT/f'packets/{label}/placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
            with np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z:x={k:z[k] for k in z.files}
            with np.load(OUT/'network'/f'{mode}.npz') as z:net={k:z[k] for k in z.files}
            stamp=json.loads((OUT/'network'/f'{mode}.json').read_text())
            assert stamp==r['network'][mode] and stamp['cache_sha256']==sha(OUT/'network'/f'{mode}.npz')
            with np.load(OUT/label/f'supply_{mode}.npz') as z:arrays={k:z[k] for k in z.files}
            owner,share,between=net['owner'],net['share'],net['between'];n=len(sites);land=f['land'].ravel()
            assert np.array_equal(net['nodes'],[s['node'] for s in sites])
            assert np.array_equal(arrays['owner'],owner) and np.array_equal(arrays['share'],share.astype(np.float32))
            assert np.array_equal(arrays['between'],between) and np.array_equal(arrays['nodes'],net['nodes'])
            assert ((owner>=-1)&(owner<n)).all() and ((share>=0)&(share<=1)).all()
            assert ((between>=0)&(between<=1)).all() and not np.diag(between).any()
            assert np.array_equal(net['land'],f['land'])
            assert stamp['track_equals_placement_fields']==bool(np.array_equal(net['tracks'],f['tracks']))
            if label=='control':
                for name,digest in archived['climates'][mode]['outputs'].items():assert sha(OUT/label/name)==digest,name
            for name,digest in variant['climates'][mode]['outputs'].items():assert sha(OUT/label/name)==digest,name
            for key,s in variant['climates'][mode]['scenarios'].items():
                reading=s['density'];res=f['residents_'+reading];need=res*KCAL;rural=f['rural_'+reading].ravel();ruralneed=rural*KCAL
                potential=np.where(land,x['potential_kcal'],0.)
                workers=ruralneed/KCAL*.4;annual=workers*s['hours_worker_year'];peak=np.minimum(annual,workers*240.)
                annual_required=potential*x['listed_hours']/1e6;peak_required=potential*x['reaping_hours']/1e6
                kept=np.minimum(1.,np.minimum(np.divide(annual,annual_required,out=np.ones_like(annual),where=annual_required>0),
                    np.divide(peak,peak_required,out=np.ones_like(peak),where=peak_required>0)))
                kept=np.where(potential>0,kept,0.);produced=potential*kept
                surplus=np.where(land,np.maximum(produced-ruralneed,0),0);grain=surplus*s['extraction']
                assert (grain>=0).all() and (produced>=0).all() and (produced<=potential+1e-3).all()
                assert (annual_required*kept<=annual+1e-5).all() and (peak_required*kept<=peak+1e-5).all()
                p=independent_plan(grain,need,owner,share,between)
                fedshare=np.divide(p['fed'],need,out=np.ones_like(need),where=need>0)
                for field,expected in [('delivered',p['delivered']),('received',p['received']),('exported',p['exported']),('fed_share',fedshare)]:
                    actual=arrays[key+'_'+field];close(actual,expected,atol=.05 if field!='fed_share' else 1e-9)
                    np.testing.assert_array_equal(compact[f'{label}__{mode}__{key}_{field}'],actual)
                maxdelivery=max(maxdelivery,float(np.max(np.abs(p['delivered']-arrays[key+'_delivered']))/KCAL))
                maxreceived=max(maxreceived,float(np.max(np.abs(p['received']-arrays[key+'_received']))/KCAL))
                actualmoves=arrays[key+'_shipments'];expectedmoves=np.array([[i,j,v,v*between[i,j]] for (i,j),v in sorted(p['moves'].items())]).reshape(-1,4)
                close(actualmoves,expectedmoves,atol=.05)
                np.testing.assert_array_equal(compact[f'{label}__{mode}__{key}_shipments'],actualmoves)
                assert len(p['moves'])==s['shipments'] and (p['exported']<=p['excess']+.05).all()
                assert (p['fed']<=need+.05).all() and not ((p['exported']>0)&(p['received']>0)).any()
                sent=math.fsum(p['sent']);delivered=math.fsum(p['delivered']);shipped=math.fsum(p['moves'].values());received=math.fsum(p['received'])
                L=dict(available=math.fsum(grain),sent_to_towns=sent,left_in_cells=math.fsum(grain)-sent,
                    delivered_to_towns=delivered,hinterland_transport=sent-delivered,
                    eaten_from_hinterland=math.fsum(np.minimum(p['delivered'],need)),
                    shipped_between_towns=shipped,received_between_towns=received,
                    between_town_transport=shipped-received,unused_excess=math.fsum(p['excess'])-shipped)
                L['residual']=L['available']-L['left_in_cells']-L['hinterland_transport']-L['eaten_from_hinterland']-L['between_town_transport']-L['received_between_towns']-L['unused_excess']
                for field,v in L.items():close(s['ledger_person_years'][field],v/KCAL)
                maxledger=max(maxledger,abs(L['residual']/KCAL))
                assert min(v for k,v in L.items() if k!='residual')>=-.05
                full=fedshare>=1-1e-6;local=p['delivered']>=need*(1-1e-9)
                expected=dict(residents=math.fsum(res),produced_person_years=math.fsum(produced[land])/KCAL,
                    rural_people=math.fsum(rural),marketed_per_rural_person=math.fsum(grain)/KCAL/math.fsum(rural),
                    residents_fed=math.fsum(p['fed'])/KCAL,fed_share_of_residents=math.fsum(p['fed'])/math.fsum(need),
                    residents_in_short_towns=math.fsum(res[~full]))
                for field,v in expected.items():close(s[field],v)
                for field,v in [('towns',n),('self_sufficient_towns',local.sum()),('fed_with_imports_towns',(full&~local).sum()),
                                ('short_towns',(~full).sum()),('exporters',(p['exported']>0).sum()),('importers',(p['received']>0).sum())]:assert s[field]==v,(label,mode,key,field)
                deficit=np.maximum(ruralneed-produced,0);d=r['diagnostics'][label][mode][key]
                independent=dict(rural_people=math.fsum(rural),rural_workers=math.fsum(workers),
                    rural_food_shortfall_person_years=math.fsum(deficit[land])/KCAL,
                    cells_below_rural_need=int((land&(deficit>1e-6)).sum()),
                    production_forgone_person_years=math.fsum((potential-produced)[land])/KCAL,
                    annual_hours_available=math.fsum(annual[land]),annual_hours_used=math.fsum((annual_required*kept)[land]),
                    reaping_hours_available=math.fsum(peak[land]),reaping_hours_used=math.fsum((peak_required*kept)[land]),
                    rural_need_person_years=math.fsum(ruralneed[land])/KCAL,source_surplus_person_years=math.fsum(surplus)/KCAL,
                    marketed_person_years=math.fsum(grain)/KCAL,town_unfed_person_years=s['residents']-s['residents_fed'])
                assert d.keys()==independent.keys()
                for field,v in independent.items():close(d[field],v)
                if key==variant['headline']:
                    rows=table(OUT/label/f'supply_{mode}_towns.csv');assert len(rows)==n
                    for i,(row,site) in enumerate(zip(rows,sites)):
                        assert row['id']==site['id'] and row['name']==site['name']
                        for field,v in [('residents',res[i]),('hinterland_grain_people',p['delivered'][i]/KCAL),
                            ('exported_people',p['exported'][i]/KCAL),('imported_people',p['received'][i]/KCAL)]:
                            assert float(row[field])==round(float(v),1)
                        assert float(row['fed_share'])==round(float(fedshare[i]),4)
                        assert row['status']==('self-sufficient' if local[i] else 'fed with imports' if full[i] else 'short')
                cases+=1;towncases+=n
            print('Independent annual supply review',label,mode,flush=True)
    comp=table(OUT/'comparison.csv');assert len(comp)==len(r['comparison'])==16
    for a,b in zip(comp,r['comparison']):
        for key,v in b.items():
            if isinstance(v,str):assert a[key]==v
            else:close(float(a[key]),v)
        old=r['variants']['control']['climates'][b['mode']]['scenarios'][b['scenario']]
        new=r['variants']['candidate']['climates'][b['mode']]['scenarios'][b['scenario']]
        for prefix,s in [('old',old),('new',new)]:
            for k,field in [('residents','residents'),('fed_share','fed_share_of_residents'),('short_towns','short_towns'),('fed','residents_fed')]:assert b[prefix+'_'+k]==s[field]
    candidate=json.loads((OUT/'packets/candidate/fantasy.json').read_text());assert candidate['adopt'] is False and candidate['gate']['passed'] is False
    assert not any(r[k] for k in ['adopt','main_atlas_published','seasonal_origin_food_work_validated'])
    for name in ['results.json',*r['files_sha256']]:assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
        scope='Independent field-work equations,explicit sorted source groups with compensated sums,separate sorted-link shipment allocator,complete grain/source/work diagnostics and summaries. Freight network reused,not independently rederived. Exact published controls and fresh compact exports.',
        annual_scenarios=cases,town_scenario_rows=towncases,exact_released_control_files=4,
        max_delivery_difference_person_years=maxdelivery,max_received_difference_person_years=maxreceived,
        max_grain_residual_person_years=maxledger,seasonal_origin_food_work_validated=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
