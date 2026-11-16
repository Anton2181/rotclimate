"""Independent source joins/aggregates and existing population dependency checks."""
import ast
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_release2_earth as R

OUT=ROOT/'output/urban_hinterland_provenance_20261116'
BASE=ROOT/'output/urban_geographic_residuals_20261116'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def quantile(vals,q):
    if not vals:return None
    values=sorted(vals);pos=(len(values)-1)*q;lo=math.floor(pos);hi=math.ceil(pos)
    return values[lo]+(values[hi]-values[lo])*(pos-lo)


def compare(a,b):
    assert set(a)==set(b)
    for key,value in b.items():
        if value is None or isinstance(value,(str,bool)):assert a[key]==value,(key,a[key],value)
        else:assert math.isclose(a[key],value,abs_tol=1e-9,rel_tol=1e-12),(key,a[key],value)


def main():
    result=json.loads((OUT/'results.json').read_text());prior=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_geographic_residuals.py')
    for name,digest in {**result['sources_sha256'],**result['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    # Reuse only pinned legacy geometry, as in the previous support review.
    old,_,_=R.cohort();old=[r for r in old if r['area'] not in (20.,30.)]
    with (R.CACHE/'areas.csv').open(encoding='utf-8-sig') as f:areas={row[0]:(float(row[1]),row[2]) for row in list(csv.reader(f))[1:]}
    with (R.CACHE/'cities.csv').open(encoding='cp1252') as f:cities={r['Primary Key']:r for r in csv.DictReader(f)}
    capitals={(r['town'],r['province']) for r in json.loads((ROOT/'output/capital_effect_20261115/results.json').read_text())['matched']}
    names=sorted({r['province'] for r in old});assert len(names)==51
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:d={k:z[k].tolist() for k in z.files}
    for i,r in enumerate(old):
        area,basis=areas[r['key']]
        if r['province'] in ('Achaea','Macedonia','Epirus') and basis.startswith('Walls'):area=area/3 if area>=100 else area/2
        assert math.isclose(area,d['area'][i],abs_tol=1e-12,rel_tol=1e-14)
        assert r['lnH']==d['lnH'][i] and names.index(r['province'])==d['province'][i]
        assert d['strict'][i]==(basis=='Inhabited area')
        assert d['fold'][i]==int(hashlib.sha256(r['province'].encode()).hexdigest()[:2],16)%4
        assert d['capital'][i]==((cities[r['key']]['Ancient Toponym'],r['province']) in capitals)
    expected=[];bases=[]
    for code,name in enumerate(names):
        use=[i for i,r in enumerate(old) if r['province']==name];st=[i for i in use if areas[old[i]['key']][1]=='Inhabited area']
        row=dict(province=code,province_name=name,outer=d['fold'][use[0]],mixed_n=len(use),strict_n=len(st),strict_small_sample=len(st)<5,
                 mixed_capitals=sum(d['capital'][i] for i in use),strict_capitals=sum(d['capital'][i] for i in st),
                 greek_wall_corrected_records=sum(not math.isclose(areas[old[i]['key']][0],d['area'][i]) for i in use))
        for label,indices in [('mixed',use),('strict',st)]:
            for key,q in [('min',0),('p25',.25),('p50',.5),('p75',.75),('max',1)]:row[f'{label}_H_{key}']=quantile([math.exp(d['lnH'][i]) for i in indices],q)
        expected.append(row)
        for basis,n in sorted(Counter(areas[old[i]['key']][1] for i in use).items()):bases.append(dict(province=code,province_name=name,estimate_basis=basis,n=n))
    named=[dict(r,province_name=names[r['province']]) for r in prior['provinces']]
    cells=0
    for key,records in [('crosswalk',expected),('bases',bases),('named_residuals',named)]:
        assert len(result[key])==len(records)
        for a,b in zip(result[key],records):compare(a,b)
        with (OUT/f'{key}.csv').open() as f:actual=list(csv.DictReader(f))
        assert len(actual)==len(records)
        for a,b in zip(actual,records):
            assert set(a)==set(b)
            for k,v in b.items():
                if v is None:assert a[k]==''
                elif isinstance(v,(str,bool)):assert a[k]==str(v)
                else:assert math.isclose(float(a[k]),v,abs_tol=1e-9,rel_tol=1e-12)
                cells+=1
    assert sum(r['mixed_n'] for r in expected)==664 and sum(r['strict_n'] for r in expected)==153
    assert sum(r['n'] for r in bases)==664 and len({r['province'] for r in named})==40
    p=result['provenance'];assert json.loads((OUT/'provenance.json').read_text())==p
    preparation=json.loads((ROOT/'output/settlement_locations_20261110/rome_preparation.json').read_text())
    release=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())
    supply=json.loads((ROOT/'output/settlement_release4_20261116/supply/results.json').read_text())
    qualpath=ROOT/'output/greek_walls_20261114/results.json';qual=json.loads(qualpath.read_text());qreview=json.loads((qualpath.parent/'review.json').read_text())
    level=json.loads((ROOT/'output/supply_people_level_20261114/results.json').read_text())
    cal=p['calibration'];assert cal['pool_sha256']==sha(ROOT/cal['pool'])==release['sources']['rome_inputs']==preparation['input_sha256']
    with np.load(ROOT/cal['pool']) as z:assert cal['shape']==list(z['land'].shape) and cal['cell_km']==float(z['cell_km'])
    assert cal['original_global_grid_sha256']==preparation['sources']['output/land_people/earth/earth.npz']
    assert cal['density_unit']=='people/km2' and cal['H_unit']=='people' and cal['size_fit_still_uses_original_pool']
    earthtext=(ROOT/'polity/earth.py').read_text();occupation=float(re.search(r'^OCCUPATION_CENTRAL = ([0-9.]+)',earthtext,re.M)[1]);assert cal['occupation_central']==occupation
    s=p['qualified_earth_supply'];assert s['calibration_sha256']==sha(qualpath)==supply['earth_calibration_sha256']==qreview['results_sha256']
    assert qreview['status']=='passed' and qreview['reviewer_sha256']==sha(ROOT/'scripts/review_greek_walls.py')
    assert s['marketed_share']==qual['greece_e95'] and qual['primary_pass']
    frier=float(re.search(r'FRIER = ([0-9.e+]+)',(ROOT/'scripts/supply_people_level.py').read_text())[1]);assert s['empire_people_target']==frier==61.4e6
    assert s['harvest_grid_sha256']==level['harvest_grid_sha256']
    assert not s['same_population_recipe_as_size_fit'] and not s['updated_H_fit_demonstrated']
    # AST-normalized statements establish the changed data dependencies separately.
    greek=ast.unparse(ast.parse((ROOT/'scripts/greek_walls.py').read_text()))
    for expression in ["SH.capacity(x['lat'], x['lon']) * x['history']", "x['density'] = p2 * PL.FRIER / float((p2[allowed] * cell).sum())", 'S.HARVEST = FS.GRID']:
        assert expression in greek
    fantasy=ast.unparse(ast.parse((ROOT/'scripts/settlement_fantasy_inputs.py').read_text()))
    assert "hf['settlement_base'] * hm['occupation']['scenarios']['central']" in fantasy and 'PL.FRIER' not in fantasy
    builder=ast.unparse(ast.parse((ROOT/'scripts/build_settlement_release2.py').read_text()))
    assert "land, density = (z['land'], z['density'])" in builder
    assert "Z.hinterlands(centres, land, people, cell)" in builder
    for key in ['earth_supply_Frier_pattern_used','harvest_core_alternative_used']:assert p['fantasy'][key] is False
    for artifact in p['artifacts']:
        path=ROOT/artifact['path'];assert path.exists()==artifact['present_at_audit']
        assert artifact['local_sha256']==(sha(path) if path.exists() else None)
    assert not p['qualified_grid_available_and_hash_matches'] and not p['numerically_aligned_current_supply_population_field_compared'] and p['old_new_H_ratio'] is None
    assert p['artifacts'][1]['recorded_sha256']==level['harvest_grid_sha256'] and not p['artifacts'][1]['present_at_audit'] and not p['artifacts'][2]['present_at_audit']
    assert p['artifacts'][3]['local_sha256']!=p['artifacts'][0]['recorded_sha256'] and p['artifacts'][3]['local_sha256']!=p['artifacts'][1]['recorded_sha256']
    for flag in ['fit_performed','new_predictive_score','new_blind_test','adopt','climate_changed']:assert result[flag] is False
    fresh={}
    for name in ['results.json','provenance.json','crosswalk.csv','bases.csv','named_residuals.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
                method='Pinned previously reviewed legacy geometry reused. Independent raw joins/labels/area correction/capital/fold encodings,scalar quantiles and all aggregate CSV cells. Separate code-AST dependency checks and receipt identities;no reconstruction claim for absent global arrays.',
                anonymous_design_rows=664,strict_targets=153,province_crosswalk=51,basis_aggregates=len(bases),named_residuals=240,csv_cells=cells,
                population_recipe_branches=3,current_supply_field_numeric_comparison=False,fresh_byte_exact=fresh,fit_performed=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed51province crosswalk,{cells}CSVcells and three population dependency branches;no unsupported current-field ratio')


if __name__=='__main__':main()
