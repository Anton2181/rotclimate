"""Three fixed population recipes on identical Roman geometry; no area fit."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.ndimage import map_coordinates

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_hierarchy as SH
from polity import earth as E
from polity.settlement_sizes import hinterlands

OUT=ROOT/'output/urban_population_recipe_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/population_recipe_replay.json'
GRID=OUT/'restored/grid/earth.npz'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def summaries(H,old,people,oldpeople):
    valid=(H>0)&(old>0)
    result=dict(n=len(H),positive_H_rows=int((H>0).sum()),zero_H_rows=int((H==0).sum()),positive_pair_rows=int(valid.sum()))
    delta=np.log(H[valid]/old[valid]);share=delta-np.log(people/oldpeople)
    for label,v in [('H_people',H),('positive_pair_log_H_change',delta),('positive_pair_log_H_share_change',share)]:
        for k,value in zip(['min','p25','p50','p75','max'],np.quantile(v,[0,.25,.5,.75,1]) if len(v) else [None]*5):result[f'{label}_{k}']=float(value) if value is not None else None
    return result


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    receipt=json.loads((OUT/'restoration.json').read_text());assert receipt['status']=='passed_exact_qualified_grid_replay'
    for name,digest in {**receipt['sources_sha256'],**receipt['protected_sha256'],**receipt['files_sha256']}.items():assert sha(ROOT/name)==digest,name
    assert sha(GRID)==receipt['expected_grid_sha256']
    with np.load(SH.R.POOLS/'rome_inputs.npz') as z:x={k:z[k] for k in z.files}
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:d={k:z[k] for k in z.files}
    rows,_,_,_=SH.cohort();cells=np.array([r['cell'] for r in rows]);assert len(rows)==664
    _,counts,_=SH.R.cohort();assert counts['legacy_cells_reproduced']
    names=sorted({r['province'] for r in rows});province=np.array([names.index(r['province']) for r in rows]);np.testing.assert_array_equal(province,d['province'])
    land=x['land'];cell=float(x['cell_km']);centres=np.column_stack(np.unravel_index(x['real'],land.shape))
    original_path=E.EARTH_NPZ
    try:
        E.EARTH_NPZ=GRID;base,_,coverage=E.earth_people(x['lat'],x['lon'])
    finally:E.EARTH_NPZ=original_path
    with np.load(GRID) as z:
        zl,zo=z['lat'],z['lon'];step=float(zl[0]-zl[1]);r=(zl[0]+step/2-x['lat'])/step-.5;c=(x['lon']-(zo[0]-step/2))/step-.5
        inside=(r>=-.5)&(r<=len(zl)-.5)&(c>=-.5)&(c<=len(zo)-.5)
        capacity=np.where(inside,map_coordinates(np.nan_to_num(z['capacity']).astype(float),[np.clip(r,0,len(zl)-1),np.clip(c,0,len(zo)-1)],order=0),0.)
    p2=np.where(land,capacity*x['history'],0.);allowed=land & x['allowed'];target=61.4e6
    factor=target/float((p2[allowed]*cell**2).sum())
    densities={'legacy':x['density'],'floodplain_settlement_base':np.where(land,base,0.),'floodplain_P2_Frier':p2*target/float((p2[allowed]*cell**2).sum())}
    arrays={};windows=[];cohorts=[];provinces=[];oldH=None;oldpeople=None
    for variant,density in densities.items():
        assert np.isfinite(density).all() and (density>=0).all()
        _,H=hinterlands(centres,land,density*land*cell**2,cell)
        people=float((density[land]*cell**2).sum());served=float(H.sum());assert served<=people+1e-6
        actual=H[cells];arrays[variant+'__centre_H']=H;arrays[variant+'__row_H']=actual
        if variant=='legacy':
            np.testing.assert_allclose(np.log(actual),d['lnH'],rtol=1e-13,atol=1e-12);oldH=actual;oldpeople=people
        windows.append(dict(variant=variant,window_people=people,allowed_people=float((density[allowed]*cell**2).sum()),assigned_centre_H_people=served,
                            unassigned_people=people-served,centres=len(H),zero_H_centres=int((H==0).sum()),zero_density_land_cells=int((density[land]==0).sum()),
                            nonfinite_density_cells=int((~np.isfinite(density)).sum()),harvest_coverage_of_land=float(inside[land].mean()),
                            P2_level_factor=factor if variant=='floodplain_P2_Frier' else None))
        for cohort,mask in [('mixed',np.ones(len(rows),bool)),('strict',d['strict'])]:
            cohorts.append(dict(variant=variant,cohort=cohort,**summaries(actual[mask],oldH[mask],people,oldpeople)))
            for code,name in enumerate(names):
                use=mask & (province==code)
                provinces.append(dict(variant=variant,cohort=cohort,province=code,province_name=name,small_sample=bool(use.sum()<5),**summaries(actual[use],oldH[use],people,oldpeople)))
    assert abs(windows[2]['allowed_people']-target)<1e-6 and len(provinces)==306
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'model.npz',**arrays)
    for name,data in [('windows',windows),('cohorts',cohorts),('provinces',provinces)]:table(out/f'{name}.csv',data)
    protected=dict(receipt['protected_sha256']);protected.update(receipt['sources_sha256'])
    for name in ['restoration.json',*receipt['files_sha256']]:
        path=OUT/name if name=='restoration.json' else ROOT/name;protected[str(path.relative_to(ROOT))]=sha(path)
    paths=[Path(__file__),PLAN,ROOT/'scripts/restore_urban_population_inputs.py',ROOT/'polity/earth.py',ROOT/'harvest/models.py',ROOT/'polity/settlement_sizes.py']
    result=dict(status='fixed_geometry_population_recipe_input_replay',windows=windows,cohorts=cohorts,provinces=provinces,
                producers={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                files_sha256={n:sha(out/n) for n in ['model.npz','windows.csv','cohorts.csv','provinces.csv']},
                fixed_eligible_records=664,strict_records=153,centre_geometry_unchanged=True,zero_H_rows_retained=True,
                log_change_scope='Positive pairs only;all zero-H counts retained. Hshare denominator is full-window population. Repeated shared-cell row H is a covariate,not an independently conserved people ledger.',
                fit_performed=False,predictive_score=False,new_blind_test=False,climate_fit=False,adopt=False)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote3fixed population recipes,6cohort/306province summaries;no size fit or map change')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
