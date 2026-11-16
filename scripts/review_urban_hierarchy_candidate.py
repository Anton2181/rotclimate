"""Independent full-source fit,application and finite annual people/cereal review."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import lstsq
from scipy.spatial.distance import cdist

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from review_urban_hierarchy_refresh import forecast,stat

OUT=ROOT/'output/urban_hierarchy_candidate_20261116'
RELEASE=ROOT/'output/settlement_release4_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def close(a,b,atol=1e-6,rtol=1e-10):np.testing.assert_allclose(a,b,atol=atol,rtol=rtol)


def application(H,sites,symbols,capital,model,bounds,cell):
    coords=np.array([[s['row'],s['column']] for s in sites]);marked=np.array([s['marked'] for s in sites]);M=np.flatnonzero(marked);U=np.flatnonzero(~marked)
    distance=cdist(coords[U],coords[M]);owner=np.where(distance.min(1)*cell<=75,M[distance.argmin(1)],-1)
    rng=np.random.default_rng(2026);e=np.clip(np.random.default_rng(1).standard_normal(len(sites)),-2.5,2.5)
    for m in M:
        members=rng.permutation(U[owner==m]);pool=[int(m),*map(int,members[:round(model['hierarchy_phi']*len(members))])];winner=max(pool,key=lambda i:e[i]);e[m],e[winner]=e[winner],e[m]
    beta=model['full_coefficients'];area=np.array([min(bounds[1],max(bounds[0],math.exp(beta[0]+beta[1]*math.log(h)+beta[2]*cp+model['heldout_sigma']*v))) for h,cp,v in zip(H,capital,e)])
    before=sorted(area);rank={'imperial capital':0,'major imperial city':1,'fortified city':2,'fortified town':3};ranked=sorted([i for i,s in enumerate(symbols) if s in rank],key=lambda i:(rank[symbols[i]],-H[i],i))
    values=sorted(area[ranked],reverse=True)
    for i,v in zip(ranked,values):area[i]=v
    top=[i for i in ranked if symbols[i] in ('imperial capital','major imperial city')];largest=sorted(range(len(area)),key=lambda i:-area[i])[:len(top)]
    values=sorted(area,reverse=True)[:len(top)];freed=sorted([area[i] for i in top if i not in largest],reverse=True);holders=sorted(i for i in largest if i not in top)
    for i,v in zip(top,values):area[i]=v
    for i,v in zip(holders,freed):area[i]=v
    close(sorted(area),before,atol=1e-9);return area,e


def ownership(land,people,centres,cell):
    rows,cols=np.nonzero(land);locations=[];destinations=[];shares=[]
    for start in range(0,len(rows),2000):
        points=np.column_stack([rows[start:start+2000],cols[start:start+2000]])
        d2=cdist(points,centres,metric='sqeuclidean');near=d2.min(1);tie=(d2==near[:,None]) & (near[:,None]*cell**2<=3600)
        r,c=np.nonzero(tie);locations.append(points[r,0]*land.shape[1]+points[r,1]);destinations.append(c);shares.append(1/np.maximum(tie.sum(1)[r],1))
    loc,dest,weight=np.concatenate(locations),np.concatenate(destinations),np.concatenate(shares)
    H=np.bincount(dest,weights=people.ravel()[loc]*weight,minlength=len(centres))
    return H,loc,dest,weight


def annual(area,H,people,land,centres,cell,loc,dest,weight,reading,potential,collection_local,collection_owner):
    density=np.array([100 if reading=='low' else 100+400*max(0,min(1,math.log(max(float(a),1e-9)/50)/math.log(8))) for a in area]);wanted=area*density
    own=np.minimum(wanted,.5*H);fraction=np.divide(own,H,out=np.zeros_like(own),where=H>0)
    moved=np.bincount(loc,weights=people.ravel()[loc]*weight*fraction[dest],minlength=people.size);rural=(people.ravel()-moved).reshape(land.shape)
    extra=wanted-own;wide=np.zeros(len(area));radius=np.zeros(len(area));yy,xx=np.indices(land.shape)
    for i in sorted(range(len(area)),key=lambda i:-extra[i]):
        if extra[i]<=0:break
        d2=((yy-centres[i,0])**2+(xx-centres[i,1])**2)*cell**2
        for reach in [120.,240.,480.,960.,1920.]:
            use=land & (d2<=reach**2);pool=math.fsum(rural[use])
            if pool>=4*extra[i]:break
        amount=min(float(extra[i]),.25*pool);rural[use]*=1-amount/pool;wide[i]=amount;radius[i]=reach
    residents=own+wide;need=rural.ravel()[collection_local]*912500.;surplus=np.maximum(potential[collection_local]-need,0)
    collect=np.bincount(collection_owner,weights=surplus,minlength=len(area))*.095
    support=np.divide(collect,residents*912500,out=np.zeros_like(collect),where=residents>0)
    return dict(wanted=wanted,own=own,wide=wide,radius=radius,rural=rural,moved=people-rural,residents=residents,support=support,collect=collect,origin_deficit=int((potential[collection_local]<need-1e-6).sum()))


def main():
    r=json.loads((OUT/'results.json').read_text());control=json.loads((OUT/'control.json').read_text());release=json.loads((RELEASE/'release3/fantasy.json').read_text())
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert control['status']=='passed_exact_released_controls'
    archived=OUT/'failed_metadata_control/archived_atlas.json';current=ROOT/'atlases/earth_fit/data/atlas.json'
    a,b=json.loads(archived.read_text()),json.loads(current.read_text())
    for meta in [a,b]:
        meta['layers']=[v for v in meta['layers'] if v.get('id')!='land_forest'];meta['corrected_climate']['layers']=[v for v in meta['corrected_climate']['layers'] if v.get('id')!='land_forest']
    assert a==b and control['metadata_delta']['historical_atlas_sha256']==sha(archived) and control['metadata_delta']['current_atlas_sha256']==sha(current)
    failure=json.loads((OUT/'failed_metadata_control/control_failure.json').read_text());assert 'raw:inputs' in failure['error']
    assert failure['sources_sha256']['scripts/prepare_urban_candidate_control.py']==sha(OUT/'failed_metadata_control/producer_snapshot.txt')
    for mode in ['raw','corrected']:
        expected=release['climates'][mode];actual=control['controls'][mode]
        for key,v in actual.items():
            if key!='inputs':assert v==expected[key],(mode,key)
        for name,digest in expected['outputs'].items():assert sha(OUT/'control'/name)==digest
        ai=dict(actual['inputs']);ei=dict(expected['inputs']);assert ai.pop('atlases/earth_fit/data/atlas.json')==sha(current) and ei.pop('atlases/earth_fit/data/atlas.json')==sha(archived);assert ai==ei
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(ROOT/'output/urban_population_recipe_20261116/model.npz') as z:Hsource=z['floodplain_settlement_base__row_H']
    with np.load(ROOT/'output/urban_hierarchy_refresh_20261116/model.npz') as z:centre=z['centre'];cap=z['capital']
    X=np.array([[1.,math.log(v)] for v in Hsource]);y=np.array([math.log(v) for v in d['area']]);pred=np.zeros(664);receipts=[]
    for f in range(4):
        train=d['fold']!=f;beta,_,rank,_=lstsq(X[train],y[train],lapack_driver='gelsy');assert rank==2;pred[~train]=X[~train]@beta
        receipts.append(dict(heldout=f,training_n=int(train.sum()),test_n=int((~train).sum()),coefficients=beta.tolist()))
    sigma=math.sqrt(math.fsum((a-b)**2 for a,b in zip(y,pred))/664);bounds=r['fit']['bounds_ha'];pairs=list(np.flatnonzero(centre>=0));caps=list(np.flatnonzero(cap));observed=stat(d['area'],pred,caps,pairs,centre)
    rng=np.random.default_rng(2026);order={int(c):rng.permutation(np.flatnonzero(centre==c)) for c in caps};grid=[]
    for phi in [0.,.25,.5,.75,1.]:
        for shift in [round(i*.1,1) for i in range(14)]:
            values=[stat(forecast(pred,sigma,cap,order,phi,shift,s,bounds),pred,caps,pairs,centre) for s in [1,7,19,43,97]]
            mean=[math.fsum(v[k] for v in values)/5 for k in range(3)];loss=(mean[0]-observed[0])**2+math.log(mean[1]/observed[1])**2+math.log(mean[2]/observed[2])**2
            grid.append(dict(phi=phi,shift=shift,loss=loss,modeled_exceed=mean[0],modeled_median_ratio=mean[1],modeled_capital_factor=mean[2]))
    best=min(grid,key=lambda g:(g['loss'],g['phi'],g['shift']));beta,_,_,_=lstsq(X,y,lapack_driver='gelsy');fit=json.loads((OUT/'fit.json').read_text());assert fit==r['fit']
    close(fit['mean_coefficients'],beta,atol=1e-10);close(fit['sigma'],sigma,atol=1e-10);close(fit['observed_training'],observed,atol=1e-10)
    assert fit['source_records']==664 and fit['source_pairs']==95 and fit['source_capitals']==28 and fit['phi']==best['phi'] and fit['capital_shift']==best['shift'] and not fit['validation_claim'] and not fit['adopt']
    for a,b in zip(fit['folds'],receipts):
        for key in ['heldout','training_n','test_n']:assert a[key]==b[key]
        close(a['coefficients'],b['coefficients'],atol=1e-10)
    with (OUT/'fit_grid.csv').open() as file:rows=list(csv.DictReader(file))
    assert len(rows)==70
    for row,expected in zip(rows,grid):
        for key,v in expected.items():close(float(row[key]),v,atol=1e-10)
    earth=json.loads((OUT/'candidate_earth.json').read_text());assert not earth['adopt'] and earth['sizes']['primary']['gate']['passed'] is False
    model=earth['sizes']['primary']['models']['M1C'];close(model['full_coefficients'],list(beta)+[best['shift']],atol=1e-10);close(model['heldout_sigma'],sigma,atol=1e-10);assert model['hierarchy_phi']==best['phi']
    adapter=r['development_adapter'];source=(ROOT/adapter['canonical_path']).read_text();snapshot=(OUT/'development_adapter_snapshot.txt').read_text();assert source.count(adapter['literal_old'])==1 and source.replace(adapter['literal_old'],adapter['literal_new'])==snapshot
    assert sha(OUT/'development_adapter_snapshot.txt')==adapter['snapshot_sha256']
    oldearth=json.loads((RELEASE/'earth_results.json').read_text())['sizes']['primary'];oldmodel=oldearth['models'][oldearth['selected']]
    with np.load(OUT/'town_model.npz') as z:compact={k:z[k] for k in z.files}
    with (OUT/'town_changes.csv').open() as file:changes=list(csv.DictReader(file))
    maxarea=0.;maxpeople=0.;checked=0
    for mode in ['raw','corrected']:
        folder=ROOT/'atlases/earth_fit/data'/('corrected' if mode=='corrected' else '')
        sites=json.loads((OUT/f'control/placed_{mode}_sites.json').read_text())['sites'];assert (OUT/f'candidate/placed_{mode}_sites.json').read_bytes()==(RELEASE/f'release3/placed_{mode}_sites.json').read_bytes()
        with (OUT/f'control/placed_{mode}_towns.csv').open() as file:towns=list(csv.DictReader(file))
        symbols=[t['campaign_symbol'] for t in towns];centres=np.array([(s['row'],s['column']) for s in sites]);links=ROOT/'atlases/earth_fit/data'/('release3/hierarchy/corrected/hierarchy_links.csv' if mode=='corrected' else 'release3/hierarchy/hierarchy_links.csv')
        with links.open() as file:seats={a['province_seat'] for a in csv.DictReader(file)}
        capital=np.array([s['marked'] and s['name'] in seats for s in sites]);assert capital.sum()==19
        with np.load(folder/'administration_grid.npz') as z:land=z['land'];density=z['density']
        cell=r['cases'][mode]['cell_km'];people=np.where(land,density,0)*cell**2
        H,loc,dest,weight=ownership(land,people,centres,cell)
        with np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z:potential=z['potential_kcal']
        modechanges=[row for row in changes if row['mode']==mode];assert len(modechanges)==len(sites)
        for label,active in [('legacy',oldmodel),('candidate',model)]:
            prefix='control' if label=='legacy' else 'candidate'
            with np.load(OUT/f'{prefix}/placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
            area,e=application(H,sites,symbols,capital,active,bounds,cell);close(f['hinterland_people'],H);close(f['area_ha'],area,atol=1e-7);close(f['residual'],e,atol=0,rtol=0);close(f['people'],people,atol=0,rtol=0)
            maxarea=max(maxarea,float(np.max(np.abs(f['area_ha']-area))))
            for key in ['hinterland_people','area_ha','residual','residents_central','residents_low','from_own_hinterland_central','from_wider_region_central','from_own_hinterland_low','from_wider_region_low','local_support_share_central','local_support_share_low']:np.testing.assert_array_equal(compact[f'{mode}__{label}__{key}'],f[key])
            for reading in ['central','low']:
                expected=annual(area,H,people,land,centres,cell,loc,dest,weight,reading,potential,f['collection_local'],f['collection_owner'])
                for key,k in [('residents','residents'),('rural','rural'),('moved','moved'),('own','from_own_hinterland'),('wide','from_wider_region'),('radius','wider_radius_km'),('support','local_support_share')]:close(f[k+'_'+reading],expected[key],atol=2e-6)
                maxpeople=max(maxpeople,float(np.max(np.abs(f['rural_'+reading]-expected['rural']))))
                close(float(f['rural_'+reading].sum()+f['residents_'+reading].sum()),float(people.sum()),atol=1e-6)
                assert f['rural_'+reading].min()>=-1e-8 and (expected['wanted']+1e-6>=f['residents_'+reading]).all()
                if label=='candidate':
                    c=next(c for c in r['comparison'] if c['mode']==mode and c['reading']==reading)
                    close(c['candidate_requested_residents'],expected['wanted'].sum());close(c['candidate_allocated_residents'],expected['residents'].sum());close(c['candidate_rural_people'],expected['rural'].sum())
                    assert c['candidate_local_supported_sites']==int((expected['support']>=1).sum()) and c['candidate_local_import_dependent_sites']==int((expected['support']<1).sum()) and c['candidate_origin_cells_below_rural_need']==expected['origin_deficit']
                    close(c['candidate_unmet_residents'],np.maximum(expected['wanted']-expected['residents'],0).sum(),atol=1e-6)
            with (OUT/f'{prefix}/placed_{mode}_towns.csv').open() as file:rows=list(csv.DictReader(file))
            for i,row in enumerate(rows):
                assert row['id']==sites[i]['id'] and row['name']==sites[i]['name'] and row['campaign_symbol']==symbols[i]
                assert float(row['hinterland_people'])==round(float(f['hinterland_people'][i]),1) and float(row['calibrated_area_ha'])==round(float(f['area_ha'][i]),2)
                change=modechanges[i];assert change['id']==sites[i]['id'] and int(change['row'])==sites[i]['row'] and int(change['column'])==sites[i]['column']
                close(float(change[label+'_area_ha']),f['area_ha'][i])
                for reading in ['central','low']:
                    assert float(row['residents_'+reading])==round(float(f['residents_'+reading][i]),1)
                    assert float(row['from_wider_region_'+reading])==round(float(f['from_wider_region_'+reading][i]),1)
                    assert float(row['local_cereal_support_share_'+reading])==round(float(min(f['local_support_share_'+reading][i],99)),4)
                    assert row['import_dependent_'+reading]==str(bool(f['residents_'+reading][i]>0 and f['local_support_share_'+reading][i]<1))
                    close(float(change[label+'_residents_'+reading]),f['residents_'+reading][i])
                    if label=='candidate':close(float(change['candidate_local_support_'+reading]),f['local_support_share_'+reading][i])
                checked+=1
        with np.load(OUT/f'control/placed_{mode}_fields.npz') as a,np.load(OUT/f'candidate/placed_{mode}_fields.npz') as b:
            for key in ['land','people','hinterland_people','collection_local','collection_owner','tracks','prior','claimed','density','marked_cells']:np.testing.assert_array_equal(a[key],b[key])
        close(r['cases'][mode]['total_area_ha'],compact[f'{mode}__candidate__area_ha'].sum(),atol=1e-7)
    with (OUT/'comparison.csv').open() as file:comparisons=list(csv.DictReader(file))
    assert len(comparisons)==len(r['comparison'])==4
    for row,expected in zip(comparisons,r['comparison']):
        for k,v in expected.items():
            if isinstance(v,(str,bool)):assert row[k]==str(v)
            else:close(float(row[k]),v,atol=1e-8)
    for mode in ['raw','corrected']:
        group=[row for row in changes if row['mode']==mode]
        for row in group:close(float(row['area_ratio']),float(row['candidate_area_ha'])/float(row['legacy_area_ha']),atol=1e-12)
    assert not any(r[k] for k in ['adopt','new_validation_claim','climate_changed','placement_changed','population_changed','seasonal_origin_food_work_validated','main_atlas_published'])
    fresh={}
    for name in ['results.json',*r['files_sha256']]:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
        method='Six released artifact identities and all numeric controls;scoped forest-metadata A1 and preserved failure. Independent QR full/OOF fit,scalar70losses;previous independent forecast/stat helpers and source graph reused. Full-distance ownership;separate residual/lore replay,own/wider finite population movement and annual local-cereal equations;all site/control/compact/CSV values and fresh bytes.',
        full_source_records=664,fit_grid_candidates=70,released_controls_exact=6,site_case_rows_checked=checked,population_reading_cases=8,max_area_difference_ha=maxarea,max_rural_people_difference=maxpeople,fresh_byte_exact=fresh,
        annual_population_accounting_passed=True,seasonal_origin_food_work_validated=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed final fit,70losses,six exact controls,{checked}site-case rows and eight annual-ledger cases;seasonal qualification remains separate')


if __name__=='__main__':main()
