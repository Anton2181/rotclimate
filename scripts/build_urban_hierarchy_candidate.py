"""Full exposed-source fit and isolated fixed-site hierarchy/annual-ledger preview."""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.urban_hierarchy_trial import member_order,generate,hierarchy_stats
from polity import settlement_sizes as Z

OUT=ROOT/'output/urban_hierarchy_candidate_20261116'
RELEASE=ROOT/'output/settlement_release4_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/hierarchy_candidate_build.json'
SEEDS=[1,7,19,43,97]


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def final_fit():
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(ROOT/'output/urban_population_recipe_20261116/model.npz') as z:H=z['floodplain_settlement_base__row_H']
    with np.load(ROOT/'output/urban_hierarchy_refresh_20261116/model.npz') as z:centre=z['centre'];cap=z['capital']
    X=np.column_stack([np.ones(664),np.log(H)]);y=np.log(d['area']);fold=d['fold'];pred=np.zeros(664);receipts=[]
    for f in range(4):
        train=fold!=f;beta=np.linalg.lstsq(X[train],y[train],rcond=None)[0];pred[~train]=X[~train]@beta
        receipts.append(dict(heldout=f,training_n=int(train.sum()),test_n=int((~train).sum()),coefficients=beta.tolist()))
    sigma=float(np.sqrt(np.mean((y-pred)**2)));bounds=json.loads((RELEASE/'earth_results.json').read_text())['sizes']['primary']['area_range_ha']
    pairs=centre>=0;observed=hierarchy_stats(d['area'],pred,cap,pairs,centre);order=member_order(centre,cap);grid=[]
    for phi in [0.,.25,.5,.75,1.]:
        for shift in [round(i*.1,1) for i in range(14)]:
            modeled=np.mean([hierarchy_stats(generate(pred,sigma,cap,order,phi,shift,s,bounds),pred,cap,pairs,centre) for s in SEEDS],axis=0)
            loss=float((modeled[0]-observed[0])**2+np.log(modeled[1]/observed[1])**2+np.log(modeled[2]/observed[2])**2)
            grid.append(dict(phi=phi,shift=shift,loss=loss,modeled_exceed=float(modeled[0]),modeled_median_ratio=float(modeled[1]),modeled_capital_factor=float(modeled[2])))
    selected=min(grid,key=lambda x:(x['loss'],x['phi'],x['shift']));beta=np.linalg.lstsq(X,y,rcond=None)[0]
    fit=dict(status='full_training_source_fit_for_development_preview',source_records=664,source_pairs=int(pairs.sum()),source_capitals=int(cap.sum()),mean_coefficients=beta.tolist(),sigma=sigma,
             sigma_method='RMS four-province-fold OOF errors on complete training source',phi=selected['phi'],capital_shift=selected['shift'],selection_loss=selected['loss'],observed_training=observed.tolist(),folds=receipts,
             bounds_ha=bounds,validation_claim=False,adopt=False)
    old=json.loads((RELEASE/'earth_results.json').read_text())['sizes']['primary']
    model=dict(terms=['intercept','lnH','capital'],full_coefficients=beta.tolist()+[fit['capital_shift']],heldout_sigma=sigma,hierarchy_phi=fit['phi'],source='Complete exposed-source final fit;not new validation')
    earth=dict(status='unadopted_development_candidate',adopt=False,sizes=dict(primary=dict(selected='M1C',models={'M1C':model},gate=dict(passed=False,reason='Isolated preview;new adoption/transfer/full-chain gates outstanding'),area_range_ha=bounds,observed_quantiles_ha=old['observed_quantiles_ha'])))
    return fit,earth,grid


def development_builder():
    source=ROOT/'scripts/settlement_hierarchy_map.py';text=source.read_text()
    old='"if not size[\'gate\'][\'passed\'] or names not in ((\'lnH\',), (\'lnH\', \'capital\')):"'
    new='"if names not in ((\'lnH\',), (\'lnH\', \'capital\')):"'
    assert text.count(old)==1
    adapted=text.replace(old,new);module=types.ModuleType('isolated_urban_candidate_hierarchy');module.__file__=str(source)
    exec(compile(adapted,str(source), 'exec'),module.__dict__)
    builder=module.patched_build()
    return builder,adapted,dict(canonical_path=str(source.relative_to(ROOT)),canonical_sha256=sha(source),literal_old=old,literal_new=new,scope='Only runtime development builder adoption guard;metadata gate staysFalse. No canonical source file edited.')


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    control=json.loads((OUT/'control.json').read_text());assert control['status']=='passed_exact_released_controls'
    for name,digest in {**control['sources_sha256'],**control['protected_sha256'],**control['files_sha256']}.items():assert sha(ROOT/name)==digest,name
    fit,earth,grid=final_fit();assert not earth['adopt'] and earth['sizes']['primary']['gate']['passed'] is False
    out.mkdir(parents=True,exist_ok=True);(out/'candidate').mkdir(exist_ok=True)
    (out/'fit.json').write_text(json.dumps(fit,indent=2)+'\n');(out/'candidate_earth.json').write_text(json.dumps(earth,indent=2)+'\n');table(out/'fit_grid.csv',grid)
    builder,adapted,adapter=development_builder();builder.HIER_PHI=fit['phi'];Z.MODELS['M1C']=('lnH','capital')
    (out/'development_adapter_snapshot.txt').write_text(adapted);adapter['snapshot_sha256']=sha(out/'development_adapter_snapshot.txt')
    cases={};comparisons=[];changes=[];compact={}
    for mode in ['raw','corrected']:
        print(mode,':building candidate on fixed released sites',flush=True)
        source=OUT/f'control/placed_{mode}_sites.json';sites=json.loads(source.read_text())['sites']
        with np.load(OUT/f'prepared/{mode}.npz') as z:p={k:z[k] for k in z.files}
        custom=dict(sites=sites,local=p['local'],catchment=p['catchment'],prefix='placed',extra={k:p[k] for k in ['tracks','prior','claimed','density','marked_cells']})
        target=out/'candidate';(target/source.name).write_bytes(source.read_bytes())
        summary=builder.build(mode,earth,target,custom=custom);summary['outputs'][source.name]=sha(target/source.name)
        summary['candidate_only']=True;summary['seasonal_origin_food_work_validated']=False;summary['hierarchy_selection']=copy.deepcopy(builder.HIER_STATS[mode]);cases[mode]=summary
        with np.load(OUT/f'control/placed_{mode}_fields.npz') as z:old={k:z[k] for k in z.files}
        with np.load(target/f'placed_{mode}_fields.npz') as z:new={k:z[k] for k in z.files}
        for key in ['land','people','hinterland_people','collection_local','collection_owner','tracks','prior','claimed','density','marked_cells']:np.testing.assert_array_equal(old[key],new[key])
        with (OUT/f'control/placed_{mode}_towns.csv').open() as f:oldtowns=list(csv.DictReader(f))
        for reading in ['central','low']:
            desired=Z.residents(new['area_ha'],reading);allocated=new['residents_'+reading];before=control['controls'][mode]['residents'][reading];after=summary['residents'][reading]
            comparisons.append(dict(mode=mode,reading=reading,sites=len(sites),world_people=summary['world_people'],legacy_area_ha=control['controls'][mode]['total_area_ha'],candidate_area_ha=summary['total_area_ha'],
                legacy_residents=before['total'],candidate_requested_residents=float(desired.sum()),candidate_allocated_residents=float(allocated.sum()),candidate_unmet_residents=float(np.maximum(desired-allocated,0).sum()),
                candidate_rural_people=float(new['rural_'+reading].sum()),people_budget_residual=summary['world_people']-float(new['rural_'+reading].sum())-float(allocated.sum()),
                legacy_local_supported_sites=before['local_cereal']['fully_supported_sites'],candidate_local_supported_sites=after['local_cereal']['fully_supported_sites'],
                candidate_local_import_dependent_sites=after['local_cereal']['import_dependent_sites'],candidate_origin_cells_below_rural_need=after['local_cereal']['origin_cells_below_rural_need'],
                seasonal_origin_food_work_validated=False))
        for i,(site,town) in enumerate(zip(sites,oldtowns)):
            row=dict(mode=mode,id=site['id'],name=site['name'],row=site['row'],column=site['column'],marked=bool(site['marked']),campaign_symbol=town['campaign_symbol'],actor=site.get('actor') or '',
                     hinterland_people=float(new['hinterland_people'][i]),legacy_area_ha=float(old['area_ha'][i]),candidate_area_ha=float(new['area_ha'][i]),area_ratio=float(new['area_ha'][i]/old['area_ha'][i]))
            for reading in ['central','low']:
                row['legacy_residents_'+reading]=float(old['residents_'+reading][i]);row['candidate_residents_'+reading]=float(new['residents_'+reading][i]);row['candidate_local_support_'+reading]=float(new['local_support_share_'+reading][i])
            changes.append(row)
        for label,data in [('legacy',old),('candidate',new)]:
            for key in ['hinterland_people','area_ha','residual','residents_central','residents_low','from_own_hinterland_central','from_wider_region_central','from_own_hinterland_low','from_wider_region_low','local_support_share_central','local_support_share_low']:
                compact[f'{mode}__{label}__{key}']=data[key]
        print(mode,':candidate complete;positions/population/collection/tracks exact',flush=True)
    table(out/'comparison.csv',comparisons);table(out/'town_changes.csv',changes);np.savez_compressed(out/'town_model.npz',**compact)
    protected=dict(control['protected_sha256']);protected.update(control['sources_sha256']);protected.update(control['files_sha256']);protected[str((OUT/'control.json').relative_to(ROOT))]=sha(OUT/'control.json')
    sources=[Path(__file__),PLAN,ROOT/'polity/urban_hierarchy_trial.py',ROOT/'scripts/settlement_hierarchy_map.py',ROOT/'scripts/build_settlement_release2.py']
    files=['fit.json','candidate_earth.json','fit_grid.csv','development_adapter_snapshot.txt','comparison.csv','town_changes.csv','town_model.npz']
    for mode in cases:
        files += [f'candidate/placed_{mode}_{suffix}' for suffix in ['sites.json','towns.csv','fields.npz']]
    result=dict(status='isolated_fixed_site_development_candidate',cases=cases,comparison=comparisons,fit=fit,development_adapter=adapter,
                sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},protected_sha256=protected,files_sha256={n:sha(out/n) for n in files},
                adopt=False,new_validation_claim=False,climate_changed=False,placement_changed=False,population_changed=False,seasonal_origin_food_work_validated=False,main_atlas_published=False)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote complete candidate and annual-ledger comparison;adoptFalse/gateFalse;main atlas unchanged',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
