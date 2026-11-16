"""Separate packet decode, full-distance H/area replay and dependency review."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.spatial.distance import cdist

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_hierarchy as SH

OUT=ROOT/'output/urban_integration_readiness_20261116'
RELEASE=ROOT/'output/settlement_release4_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text())
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    meta=json.loads((ROOT/'atlases/earth_fit/data/atlas.json').read_text());release=json.loads((RELEASE/'release3/fantasy.json').read_text());earth=json.loads((RELEASE/'earth_results.json').read_text())
    primary=earth['sizes']['primary'];model=primary['models'][primary['selected']];coef=model['full_coefficients'];maxH=0.;maxArea=0.
    for record in r['modes']:
        mode=record['mode'];folder=ROOT/'atlases/earth_fit/data'/('corrected' if mode=='corrected' else '')
        hm=json.loads((folder/'harvest.json').read_text());packet=(folder/'harvest.bin').read_bytes();desc=hm['arrays']['settlement_base'];shape=tuple(desc['shape']);dtype=np.dtype(desc['dtype'])
        assert desc['offset_bytes']+math.prod(shape)*dtype.itemsize<=len(packet)
        raw=np.frombuffer(packet,dtype=dtype,count=math.prod(shape),offset=desc['offset_bytes']).reshape(shape)
        base=raw.astype(float)*desc['scale']+desc['offset'];base=np.where(raw==desc['nodata'],0,base)
        with np.load(folder/'administration_grid.npz') as z:land=z['land'];density=z['density']
        central=hm['occupation']['scenarios']['central'];expected=np.where(land,base*central,0)
        np.testing.assert_array_equal(expected,density);assert list(shape)==record['shape']==hm['shape']
        cell=float(meta['width'])*float(meta['mi_per_px'])*1.609344/shape[1];population=np.where(land,density,0)*cell**2
        assert abs(float(population.sum())-record['world_people'])<1e-6 and abs(record['world_people']-release['climates'][mode]['world_people'])<1e-6
        assert int(land.sum())==record['land_cells'] and record['density_packet_exact'] and record['administration_cache_present']
        assert record['released_fields_cache_present']==(RELEASE/f'release3/placed_{mode}_fields.npz').exists()
        with (RELEASE/f'release3/placed_{mode}_towns.csv').open() as f:towns=list(csv.DictReader(f))
        sites=json.loads((RELEASE/f'release3/placed_{mode}_sites.json').read_text())['sites'];assert len(towns)==len(sites)==record['sites']
        centres=np.array([(int(t['row']),int(t['column'])) for t in towns]);lr,lc=np.nonzero(land);H=np.zeros(len(towns))
        for start in range(0,len(lr),2000):
            points=np.column_stack([lr[start:start+2000],lc[start:start+2000]])
            distances=cdist(points,centres,metric='sqeuclidean');near=distances.min(axis=1)
            owners=(distances==near[:,None]) & (near[:,None]*cell*cell<=3600)
            weights=owners/np.maximum(owners.sum(axis=1)[:,None],1)
            H+=population[points[:,0],points[:,1]]@weights
        listed=np.array([float(t['hinterland_people']) for t in towns]);maxH=max(maxH,float(np.max(np.abs(H-listed))))
        assert np.max(np.abs(H-listed))<=.0500001
        marked=np.array([t['marked']=='True' for t in towns]);M=np.flatnonzero(marked);U=np.flatnonzero(~marked)
        links=ROOT/'atlases/earth_fit/data'/('release3/hierarchy/corrected/hierarchy_links.csv' if mode=='corrected' else 'release3/hierarchy/hierarchy_links.csv')
        with links.open() as f:seats={a['province_seat'] for a in csv.DictReader(f)}
        capital=np.array([t['marked']=='True' and t['name'] in seats for t in towns]);assert int(capital.sum())==record['capital_shift_centres']==19
        assert len(M)==record['selection_centres']
        norms=np.clip(np.random.default_rng(1).normal(size=len(towns)),-2.5,2.5);dist=cdist(centres[U],centres[M]);closest=dist.argmin(axis=1);owner=np.where(dist.min(axis=1)*cell<=75,M[closest],-1)
        rng=np.random.default_rng(2026)
        for m in M:
            members=rng.permutation(U[owner==m]);take=int(round(model['hierarchy_phi']*len(members)));pool=[int(m),*map(int,members[:take])]
            j=max(pool,key=lambda k:norms[k]);norms[m],norms[j]=norms[j],norms[m]
        area=np.array([min(primary['area_range_ha'][1],max(primary['area_range_ha'][0],math.exp(coef[0]+coef[1]*math.log(h)+coef[2]*cp+model['heldout_sigma']*e))) for h,cp,e in zip(H,capital,norms)])
        ranks={'imperial capital':0,'major imperial city':1,'fortified city':2,'fortified town':3};symbols=[t['campaign_symbol'] for t in towns]
        ranked=sorted([i for i,s in enumerate(symbols) if s in ranks],key=lambda i:(ranks[symbols[i]],-H[i],i));values=sorted(area[ranked],reverse=True)
        for i,v in zip(ranked,values):area[i]=v
        top=[i for i in ranked if symbols[i] in ('imperial capital','major imperial city')];biggest=sorted(range(len(area)),key=lambda i:-area[i])[:len(top)]
        values=sorted(area,reverse=True)[:len(top)];freed=sorted([area[i] for i in top if i not in biggest],reverse=True);holders=sorted(i for i in biggest if i not in top)
        for i,v in zip(top,values):area[i]=v
        for i,v in zip(holders,freed):area[i]=v
        listedarea=np.array([float(t['calibrated_area_ha']) for t in towns]);maxArea=max(maxArea,float(np.max(np.abs(area-listedarea))));assert np.max(np.abs(area-listedarea))<=.0050001
        assert abs(float(area.sum())-release['climates'][mode]['total_area_ha'])<1e-6
        assert record['assigned_subordinates']==int((owner>=0).sum()) and record['lore_ranked']==len(ranked) and record['global_top_lore_places']==len(top)
    source,lat,lon,cap=SH.cohort();caps=np.flatnonzero(cap);centre={}
    def distance(i,j):
        a,b=map(math.radians,[lat[i],lat[j]]);dl=math.radians(lon[j]-lon[i]);dlat=b-a
        return 2*6371*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(a)*math.cos(b)*math.sin(dl/2)**2)))
    for i in np.flatnonzero(~cap):
        j=min(caps,key=lambda j:distance(i,j))
        if distance(i,j)<=75:centre[int(i)]=int(j)
    fold=[hashlib.sha256(a['province'].encode()).digest()[0]%4 for a in source]
    counts=dict(records=len(source),capitals=len(caps),subordinates=len(centre),same_fold_pairs=sum(fold[i]==fold[j] for i,j in centre.items()),cross_fold_pairs=sum(fold[i]!=fold[j] for i,j in centre.items()))
    h=r['readiness']['hierarchy'];assert h['pairs']==counts
    expected=[]
    for f in range(4):expected.append(dict(outer=f,test_records=fold.count(f),train_pair_records=sum(fold[i]!=f and fold[j]!=f for i,j in centre.items()),test_same_fold_pair_records=sum(fold[i]==f and fold[j]==f for i,j in centre.items()),old_training_pairs_with_test_centre=sum(fold[i]!=f and fold[j]==f for i,j in centre.items())))
    assert h['outer_support']==expected
    for name,records in [('outer_support',expected),('stages',r['stages'])]:
        with (OUT/f'{name}.csv').open() as f:actual=list(csv.DictReader(f))
        assert len(actual)==len(records)
        for a,b in zip(actual,records):assert a=={k:str(v) for k,v in b.items()}
    chain=json.loads((ROOT/'calibration/settlement_chain/release4_confluence.json').read_text())
    assert len(chain['stages'])==len(r['stages'])
    for i,(stage,record) in enumerate(zip(chain['stages'],r['stages'])):
        assert record==dict(order=i,name=stage['name'],script=stage['script'],script_sha256=sha(ROOT/stage['script']),outputs=len(stage.get('outputs',[]))+len(stage.get('outputs_reach',[])))
    soft=json.loads((ROOT/'output/settlement_hierarchy_20261115/results_soft.json').read_text());assert h['legacy_gate_passed']==soft['passed'] is False and h['full_fit']==soft['full_fit']
    assert h['global_scatter_uses_all_outer_responses'] and h['old_training_means_can_include_outer_test_responses']
    assert h['old_pair_loss_can_reference_outer_test_centres']==bool(counts['cross_fold_pairs'])
    flood=json.loads((ROOT/'output/fantasy_floodplain_20261114/results.json').read_text())
    for mode in ['raw','corrected']:
        for k,v in r['readiness']['floodplain'][mode].items():assert flood['modes'][mode][k]==v
        assert flood['modes'][mode]['qualifying_cells']==0 and not flood['modes'][mode]['basins_timing_ok']
    assert 'allocate_residents' not in (ROOT/'scripts/build_settlement_release2.py').read_text()
    assert not r['readiness']['map_adoption_ready'] and not r['readiness']['climate_rerun_required'] and not r['readiness']['fantasy_population_change_required_by_existing_port']
    for flag in ['fit_performed','new_predictive_score','climate_changed','adopt']:assert r[flag] is False
    fresh={}
    for name in ['results.json','stages.csv','outer_support.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),method='Separate harvest binary decode;full-distance cdist ownership with all ties/radius;scalar hierarchy/lore replay at declared CSV precision and unrounded total-area control. Independent haversine pair eligibility;complete dependency/CSV inventory. Previously reviewed source cohort reused.',
                modes=2,sites=sum(m['sites'] for m in r['modes']),max_H_difference_from_rounded_csv=maxH,max_area_difference_from_rounded_csv=maxArea,
                H_csv_precision_people=.1,area_csv_precision_ha=.01,source_pairs=counts,fresh_byte_exact=fresh,fit_performed=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('Reviewed both published packet/H/area controls,all chain stages and train/test hierarchy-pair accounting')


if __name__=='__main__':main()
