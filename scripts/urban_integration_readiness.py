"""Read-only published-packet, hierarchy and rebuild dependency audit."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from population.export import decode_harvest
from polity import settlement_sizes as Z
from polity.survey_transfer import sphere_distance
import settlement_hierarchy as SH

BASE=ROOT/'output/urban_population_refresh_20261116'
RELEASE=ROOT/'output/settlement_release4_20261116'
OUT=ROOT/'output/urban_integration_readiness_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/integration_readiness.json'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def replay_areas(H,marked,capital,symbols,centres,cell,model,bounds):
    beta=model['full_coefficients'];sigma=model['heldout_sigma'];phi=model['hierarchy_phi'];valid=H>0
    mean=beta[0]+beta[1]*np.log(H)+beta[2]*capital
    e=Z.draws(len(H),1);M=np.flatnonzero(marked & valid);U=np.flatnonzero(~marked & valid)
    distances=np.sqrt(((centres[U,None,:]-centres[None,M,:])**2).sum(2))*cell
    owner=np.where(distances.min(1)<=75,M[distances.argmin(1)],-1);rng=np.random.default_rng(2026)
    for m in M:
        members=rng.permutation(U[owner==m]);pool=np.r_[m,members[:int(round(phi*len(members)))]]
        largest=pool[np.argmax(e[pool])];e[m],e[largest]=e[largest],e[m]
    area=Z.generate_area(mean,sigma,e,*bounds)
    rank={'imperial capital':0,'major imperial city':1,'fortified city':2,'fortified town':3}
    ranked=sorted((i for i,s in enumerate(symbols) if s in rank),key=lambda i:(rank[symbols[i]],-H[i],i))
    area[ranked]=np.sort(area[ranked])[::-1]
    top=[i for i in ranked if symbols[i] in ('imperial capital','major imperial city')];k=len(top)
    if k:
        biggest=list(np.argsort(-area,kind='stable')[:k]);values=np.sort(area)[::-1][:k].copy()
        freed=sorted([area[i] for i in top if i not in biggest],reverse=True);holders=sorted(i for i in biggest if i not in top)
        area[top]=values
        for i,v in zip(holders,freed):area[i]=v
    return area,dict(selection_centres=len(M),capital_shift_centres=int(capital.sum()),assigned_subordinates=int((owner>=0).sum()),lore_ranked=len(ranked),global_top_lore_places=k)


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    prior=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_population_refresh.py')
    for name,digest in {**prior['producers'],**prior['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in prior['files_sha256'].items():assert sha(BASE/name)==digest,name
    meta_path=ROOT/'atlases/earth_fit/data/atlas.json';meta=json.loads(meta_path.read_text());release=json.loads((RELEASE/'release3/fantasy.json').read_text());earth=json.loads((RELEASE/'earth_results.json').read_text())
    fit=earth['sizes']['primary'];model=fit['models'][fit['selected']];modes=[];inputs=[meta_path,RELEASE/'release3/fantasy.json',RELEASE/'earth_results.json']
    for mode in ['raw','corrected']:
        folder=meta_path.parent/('corrected' if mode=='corrected' else '');hm,hf=decode_harvest(folder)
        with np.load(folder/'administration_grid.npz') as z:land=z['land'];density=z['density']
        expected=np.where(land,hf['settlement_base']*hm['occupation']['scenarios']['central'],0.)
        np.testing.assert_array_equal(density,expected);assert list(density.shape)==hm['shape']
        cell=meta['width']/density.shape[1]*meta['mi_per_px']*1.609344;people=np.where(land,density,0)*cell**2
        town_path=RELEASE/f'release3/placed_{mode}_towns.csv';sites_path=RELEASE/f'release3/placed_{mode}_sites.json'
        with town_path.open() as f:towns=list(csv.DictReader(f))
        sites=json.loads(sites_path.read_text())['sites'];assert len(towns)==len(sites)==release['climates'][mode]['sites']
        for t,s in zip(towns,sites):assert (int(t['row']),int(t['column']),t['name'])==(s['row'],s['column'],s['name'])
        centres=np.array([[s['row'],s['column']] for s in sites]);_,H=Z.hinterlands(centres,land,people,cell)
        listed=np.array([float(t['hinterland_people']) for t in towns]);np.testing.assert_array_equal([round(float(v),1) for v in H],listed)
        links=meta_path.parent/('release3/hierarchy/corrected/hierarchy_links.csv' if mode=='corrected' else 'release3/hierarchy/hierarchy_links.csv')
        with links.open() as f:seats={r['province_seat'] for r in csv.DictReader(f)}
        marked=np.array([s['marked'] for s in sites]);capital=np.array([s['marked'] and s['name'] in seats for s in sites]);symbols=[t['campaign_symbol'] for t in towns]
        area,structure=replay_areas(H,marked,capital,symbols,centres,cell,model,fit['area_range_ha'])
        observed=np.array([float(t['calibrated_area_ha']) for t in towns]);np.testing.assert_array_equal([round(float(v),2) for v in area],observed)
        assert abs(float(area.sum())-release['climates'][mode]['total_area_ha'])<1e-7
        assert abs(float(people.sum())-release['climates'][mode]['world_people'])<1e-6
        for name in [town_path.name,sites_path.name]:assert sha(RELEASE/'release3'/name)==release['climates'][mode]['outputs'][name]
        modes.append(dict(mode=mode,shape=list(land.shape),cell_km=cell,land_cells=int(land.sum()),world_people=float(people.sum()),sites=len(sites),
                          density_packet_exact=True,max_H_difference_people=float(np.max(np.abs(H-listed))),max_area_difference_ha=float(np.max(np.abs(area-observed))),
                          administration_cache_present=True,released_fields_cache_present=(RELEASE/f'release3/placed_{mode}_fields.npz').exists(),
                          occupation_central=hm['occupation']['scenarios']['central'],**structure))
        inputs += [folder/'harvest.json',folder/'harvest.bin',folder/'administration_grid.npz',town_path,sites_path,links]
    flood_path=ROOT/'output/fantasy_floodplain_20261114/results.json';flood_review=flood_path.parent/'review.json';flood=json.loads(flood_path.read_text());fr=json.loads(flood_review.read_text())
    assert fr['status']=='passed' and fr['results_sha256']==sha(flood_path) and fr['reviewer_sha256']==sha(ROOT/'scripts/review_fantasy_floodplain.py')
    flood_summary={m:{k:v[k] for k in ['basins','basins_timing_ok','qualifying_cells','basin_km2','crop_capacity_total_before','crop_capacity_total_after']} for m,v in flood['modes'].items()}
    soft_path=ROOT/'output/settlement_hierarchy_20261115/results_soft.json';soft=json.loads(soft_path.read_text());rows,lat,lon,cap=SH.cohort();C=np.flatnonzero(cap);centre=np.full(len(rows),-1)
    for i in np.flatnonzero(~cap):
        distances=sphere_distance(lat[C],lon[C],lat[i],lon[i]);nearest=int(np.argmin(distances))
        if distances[nearest]<=75:centre[i]=C[nearest]
    fold=np.array([Z.province_fold(r['province']) for r in rows]);sub=np.flatnonzero(centre>=0)
    pairs=dict(records=len(rows),capitals=len(C),subordinates=len(sub),same_fold_pairs=int((fold[sub]==fold[centre[sub]]).sum()),cross_fold_pairs=int((fold[sub]!=fold[centre[sub]]).sum()))
    byfold=[]
    for f in range(4):
        byfold.append(dict(outer=f,test_records=int((fold==f).sum()),train_pair_records=int(((fold[sub]!=f)&(fold[centre[sub]]!=f)).sum()),test_same_fold_pair_records=int(((fold[sub]==f)&(fold[centre[sub]]==f)).sum()),
                           old_training_pairs_with_test_centre=int(((fold[sub]!=f)&(fold[centre[sub]]==f)).sum())))
    chain_path=ROOT/'calibration/settlement_chain/release4_confluence.json';chain=json.loads(chain_path.read_text());stages=[]
    for n,stage in enumerate(chain['stages']):
        script=ROOT/stage['script'];assert script.exists()
        stages.append(dict(order=n,name=stage['name'],script=stage['script'],script_sha256=sha(script),outputs=len(stage.get('outputs',[]))+len(stage.get('outputs_reach',[]))))
    soft_code=(ROOT/'scripts/settlement_hierarchy_soft.py').read_text()
    assert 'sig = float(np.std(y - pred))' in soft_code and 'area[s] / area[centre[s]]' in soft_code
    readiness=dict(floodplain=flood_summary,hierarchy=dict(legacy_gate_passed=soft['passed'],owner_decision=earth['owner_decision'],full_fit=soft['full_fit'],pairs=pairs,outer_support=byfold,
                global_scatter_uses_all_outer_responses=True,old_training_means_can_include_outer_test_responses=True,old_pair_loss_can_reference_outer_test_centres=bool(pairs['cross_fold_pairs']),
                source_selection_centres='Roman capital-labelled records',application_selection_centres='all marked fantasy sites;capital shift only at existing seats'),
                ledger=dict(released_size_builder='legacy own/wider population movement and annual local cereal check',finite_origin_allocator='polity/settlement_residents.py:allocate_residents',joint_origin_food_audit='polity/settlement_residents.py:audit_origin_food',
                            chain_automatic_joint_origin_food_certification=False,requires_full_origin_food_labour_validation=True),
                status='development_preflight_only',fantasy_population_change_required_by_existing_port=False,climate_rerun_required=False,map_adoption_ready=False)
    inputs += [flood_path,flood_review,soft_path,chain_path,ROOT/'scripts/settlement_hierarchy.py',ROOT/'scripts/settlement_hierarchy_soft.py',ROOT/'scripts/settlement_hierarchy_map.py',
               ROOT/'scripts/build_settlement_release2.py',ROOT/'scripts/build_settlement_release3.py',ROOT/'scripts/settlement_fantasy_inputs.py',ROOT/'scripts/prepare_settlement_feedback.py',ROOT/'polity/settlement_residents.py',ROOT/'population/export.py']
    inputs += [ROOT/s['script'] for s in stages]
    protected=dict(prior['protected_sha256']);protected.update(prior['producers'])
    for name in ['results.json','review.json',*prior['files_sha256']]:protected[str((BASE/name).relative_to(ROOT))]=sha(BASE/name)
    out.mkdir(parents=True,exist_ok=True)
    for name,records in [('stages',stages),('outer_support',byfold)]:
        with (out/f'{name}.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    result=dict(status='read_only_integration_readiness_audit',modes=modes,readiness=readiness,stages=stages,
                sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,*inputs]},protected_sha256=protected,
                files_sha256={name:sha(out/name) for name in ['stages.csv','outer_support.csv']},shared_primitives='Published harvest decoder,unchanged hinterland and spherical-distance primitives reused;independent reviewer checks packet math and ownership separately.',
                fit_performed=False,new_predictive_score=False,climate_changed=False,adopt=False)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print('Audited both published population/H/area controls,zero-cell floodplain port,hierarchy leakage risks and full rebuild dependencies')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
