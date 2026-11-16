"""Full province crosswalk and existing H/population recipe provenance; no fit."""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_hierarchy as SH

BASE=ROOT/'output/urban_geographic_residuals_20261116'
DESIGN=ROOT/'output/urban_measurement_pilot_20261116/design.npz'
OUT=ROOT/'output/urban_hinterland_provenance_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/hinterland_provenance_audit.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def source_constant(path,key):
    for statement in ast.parse(path.read_text()).body:
        if isinstance(statement,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in statement.targets):return ast.literal_eval(statement.value)
    raise ValueError(key)


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    prior=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_geographic_residuals.py')
    for name,digest in {**prior['producers'],**prior['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in prior['files_sha256'].items():assert sha(BASE/name)==digest,name
    rows,_,_,capital=SH.cohort()
    with (SH.R.CACHE/'areas.csv').open(encoding='utf-8-sig') as f:source={r['Primary Key']:r for r in csv.DictReader(f)}
    with np.load(DESIGN) as z:d={k:z[k] for k in z.files}
    names=sorted({r['province'] for r in rows});H=np.exp([r['lnH'] for r in rows]);strict=np.array([source[r['key']]['Estimate Basis']=='Inhabited area' for r in rows]);fold=np.array([SH.Z.province_fold(r['province']) for r in rows]);province=np.array([names.index(r['province']) for r in rows])
    expected=dict(area=np.array([r['area'] for r in rows]),lnH=np.array([r['lnH'] for r in rows]),strict=strict,fold=fold,province=province,capital=capital)
    assert set(expected)==set(d)
    for key,value in expected.items():np.testing.assert_array_equal(value,d[key])
    crosswalk=[];bases=[]
    for code,name in enumerate(names):
        take=province==code;st=take & strict
        corrected=[i for i in np.flatnonzero(take) if float(source[rows[i]['key']]['Area'])!=rows[i]['area']]
        row=dict(province=code,province_name=name,outer=int(fold[take][0]),mixed_n=int(take.sum()),strict_n=int(st.sum()),strict_small_sample=bool(st.sum()<5),
                 mixed_capitals=int(capital[take].sum()),strict_capitals=int(capital[st].sum()),greek_wall_corrected_records=len(corrected))
        for label,mask in [('mixed',take),('strict',st)]:
            for key,value in zip(['min','p25','p50','p75','max'],np.quantile(H[mask],[0,.25,.5,.75,1]) if mask.any() else [None]*5):row[f'{label}_H_{key}']=float(value) if value is not None else None
        crosswalk.append(row)
        for basis in sorted({source[rows[i]['key']]['Estimate Basis'] for i in np.flatnonzero(take)}):
            count=sum(source[rows[i]['key']]['Estimate Basis']==basis for i in np.flatnonzero(take))
            bases.append(dict(province=code,province_name=name,estimate_basis=basis,n=count))
    named=[dict(r,province_name=names[r['province']]) for r in prior['provinces']]
    preparation=ROOT/'output/settlement_locations_20261110/rome_preparation.json'
    release=ROOT/'output/settlement_release4_20261116/earth_results.json';supply=ROOT/'output/settlement_release4_20261116/supply/results.json'
    qualified=ROOT/'output/greek_walls_20261114/results.json';qualified_review=qualified.parent/'review.json';level=ROOT/'output/supply_people_level_20261114/results.json'
    pre=json.loads(preparation.read_text());r4=json.loads(release.read_text());sup=json.loads(supply.read_text());qual=json.loads(qualified.read_text());qreview=json.loads(qualified_review.read_text());lev=json.loads(level.read_text())
    assert sha(SH.R.POOLS/'rome_inputs.npz')==pre['input_sha256']==r4['sources']['rome_inputs']
    assert qreview['status']=='passed' and qreview['results_sha256']==sha(qualified)==sup['earth_calibration_sha256']
    assert qreview['reviewer_sha256']==sha(ROOT/'scripts/review_greek_walls.py') and qual['producer_sha256']==sha(ROOT/'scripts/greek_walls.py')
    assert qual['primary_pass'] and qual['variants']['greece']['decision']['transferable']
    target=source_constant(ROOT/'scripts/supply_people_level.py','FRIER')
    occupation=source_constant(ROOT/'polity/earth.py','OCCUPATION_CENTRAL')
    # Check the exact code links claimed below, without executing a supply run.
    anchors={
        'scripts/settlement_locations_earth.py':"g['density'],_,_=E.earth_people(lat,lon)",
        'scripts/settlement_release2_earth.py':"people = np.where(land, x['density'], 0.0) * cell ** 2",
        'scripts/greek_walls.py':"x['density'] = p2 * PL.FRIER / float((p2[allowed] * cell).sum())",
        'scripts/supply_heartland_people.py':"z = np.load(S.HARVEST)",
        'scripts/settlement_fantasy_inputs.py':"density = np.where(land, hf['settlement_base'] * hm['occupation']['scenarios']['central'], 0.)",
        'scripts/build_settlement_release2.py':"land, density = z['land'], z['density']",
        'scripts/build_settlement_release3.py':"density=w['density']",
    }
    for path,anchor in anchors.items():assert anchor in (ROOT/path).read_text(),path
    with np.load(SH.R.POOLS/'rome_inputs.npz') as z:shape=list(z['land'].shape);cell=float(z['cell_km'])
    artifacts=[]
    for role,path,expectedsha in [
        ('original_global_grid_recorded_by_preparation','output/land_people/earth/earth.npz',pre['sources']['output/land_people/earth/earth.npz']),
        ('qualified_supply_floodplain_global_grid','output/land_people/earth_floodplain/earth.npz',lev['harvest_grid_sha256']),
        ('qualified_supply_basin_fields','output/floodplain_rule_20261114/fields.npz',None),
        ('separate_restored_baseline','output/land_people/earth_restored_20261113/earth.npz',None)]:
        p=ROOT/path;artifacts.append(dict(role=role,path=path,recorded_sha256=expectedsha,present_at_audit=p.exists(),local_sha256=sha(p) if p.exists() else None))
    grid=artifacts[1]
    comparable=grid['present_at_audit'] and grid['local_sha256']==grid['recorded_sha256']
    # This stage does not construct a replacement density even if a grid exists.
    provenance=dict(
        calibration=dict(pool='output/settlement_locations_20261110/rome_inputs.npz',pool_sha256=pre['input_sha256'],shape=shape,cell_km=cell,
                         density_unit='people/km2',H_unit='people',density_recipe='sampled settlement_base * OCCUPATION_CENTRAL',occupation_central=occupation,
                         H_recipe='nearest distinct occupied grid cell within60km; exact ties share. Each catalogue row in a shared cell receives the same H covariate,not a separate conserved population allocation.',
                         original_global_grid_sha256=artifacts[0]['recorded_sha256'],size_fit_still_uses_original_pool=True),
        qualified_earth_supply=dict(calibration_path=str(qualified.relative_to(ROOT)),calibration_sha256=sha(qualified),review_path=str(qualified_review.relative_to(ROOT)),
                                    harvest_grid_sha256=lev['harvest_grid_sha256'],density_recipe='sampled floodplain crop capacity * legacy history; normalized to Frier target on allowed Roman land',
                                    density_unit='people/km2',empire_people_target=target,marketed_share=qual['greece_e95'],
                                    same_population_recipe_as_size_fit=False,updated_H_fit_demonstrated=False),
        fantasy=dict(density_recipe='published settlement_base * published central occupation on administrative grid',
                     H_recipe='same nearest-centre60km primitive on released marked/proposed sites',
                     earth_supply_Frier_pattern_used=False,harvest_core_alternative_used=False,
                     code_paths=['scripts/settlement_fantasy_inputs.py','scripts/build_settlement_release3.py','scripts/build_settlement_release2.py'],
                     evidence='Code dependency trace; no fantasy climate,people or settlement rebuild in this audit.'),
        artifacts=artifacts,numerically_aligned_current_supply_population_field_compared=False,
        qualified_grid_available_and_hash_matches=bool(comparable),old_new_H_ratio=None,
        reason_no_ratio='Qualified floodplain grid and basin field absent in this checkout; restored baseline has a different identity. The available population recipes also differ,so a field substitution alone would confound recipe and harvest changes.')
    assert not comparable and not artifacts[2]['present_at_audit'],'Declare a new availability state before comparing restored current fields'
    out.mkdir(parents=True,exist_ok=True)
    for name,data in [('crosswalk',crosswalk),('bases',bases),('named_residuals',named)]:table(out/f'{name}.csv',data)
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    protected=dict(prior['protected_sha256']);protected.update(prior['producers'])
    for name in ['results.json','review.json',*prior['files_sha256']]:protected[str((BASE/name).relative_to(ROOT))]=sha(BASE/name)
    paths=[Path(__file__),PLAN,preparation,release,supply,qualified,qualified_review,level,ROOT/'scripts/review_greek_walls.py',
           ROOT/'scripts/supply_people_level.py',ROOT/'scripts/floodplain_supply.py',ROOT/'scripts/settlement_supply_calibration.py',
           ROOT/'scripts/settlement_hierarchy_map.py',ROOT/'scripts/wide_supply_greek_walls.py',ROOT/'harvest/models.py',ROOT/'harvest/export.py']
    paths += [ROOT/p for p in anchors]
    paths += [ROOT/'polity/earth.py',ROOT/'scripts/settlement_hierarchy.py',ROOT/'scripts/prepare_settlement_feedback.py']
    result=dict(status='province_and_population_recipe_provenance_audit',crosswalk=crosswalk,bases=bases,named_residuals=named,provenance=provenance,
                sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                files_sha256={name:sha(out/name) for name in ['crosswalk.csv','bases.csv','named_residuals.csv','provenance.json']},
                fit_performed=False,new_predictive_score=False,new_blind_test=False,adopt=False,climate_changed=False,
                limits='Raw identity joins use exposed sources; only province-level aggregates exported. Code/receipt trace certifies recorded dependencies,not reconstruction of absent historical global grids or causal explanation of residuals.')
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote full51province crosswalk,240named fixed residual summaries and three population-recipe provenance branches;no new fit')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
