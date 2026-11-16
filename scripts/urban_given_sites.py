"""Unchanged size rule conditional on supplied source towns; not a forecast."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from urban_diagnosis import cohort
from polity.observed_hinterlands import hinterland_people,grid_points
from polity.urban_observations import interval_ks_lower_bound
from polity import settlement_sizes as Z

BASE=ROOT/'output/urban_diagnosis_20261116'
OUT=ROOT/'output/urban_given_sites_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/conditional_sites.json'
AMENDMENT=PLAN.parent/'conditional_projection_a1.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert subprocess.check_output(['git','show','HEAD:'+str(AMENDMENT.relative_to(ROOT))],cwd=ROOT)==AMENDMENT.read_bytes()
    prior=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text());inputs=json.loads((BASE/'input_receipt.json').read_text())
    assert review['status']=='passed' and review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_diagnosis.py')
    assert review['results_sha256']==sha(BASE/'results.json')
    for name,digest in {**prior['producers'],**prior['protected_sha256'],**inputs['inputs']}.items():assert sha(ROOT/name)==digest,name
    fit=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary'];model=fit['models'][fit['selected']];coef=model['full_coefficients'];sigma=model['heldout_sigma'];bounds=fit['area_range_ha']
    cases=[];arrays={};geometry={}
    for pool in ['floodplains','mexico']:
        folder=BASE/'archived_replay'/pool
        with np.load(folder/'inputs_3km.npz') as z:x3={k:z[k] for k in z.files}
        x3['cell_km']=3.
        with np.load(folder/'model.npz') as z:surveyed=z['3km__surveyed']
        raw,selected,cells,values,town,lower,upper,info=cohort(pool,x3,surveyed)
        selected=selected[town];lo=lower[town];hi=upper[town];sourcevalues=values[town]
        latitude=raw['lat'][selected];longitude=raw['lon'][selected]
        assert len(selected)==(119 if pool=='floodplains' else 27)
        arrays[pool+'__lower_ha']=lo;arrays[pool+'__upper_ha']=hi;arrays[pool+'__source_values']=sourcevalues
        geometry[pool]={}
        for cell in [3,9]:
            with np.load(folder/f'inputs_{cell}km.npz') as z:x={k:z[k] for k in z.files}
            x['cell_km']=float(cell);points=grid_points(latitude,longitude,x)
            expected=np.column_stack([a.ravel() for a in np.indices(x['land'].shape)])
            grid_error=float(np.max(np.abs(grid_points(x['lat'].ravel(),x['lon'].ravel(),x)-expected)))
            assert grid_error<1e-8,'Native grid projection does not round-trip'
            H=hinterland_people(x['density'],x['land'],points,cell)
            available=float(np.sum(x['density'][x['land']])*cell**2);served=float(H.sum())
            assert served<=available+1e-6
            key=f'{pool}_{cell}km';arrays[key+'__H']=H
            geometry[pool][str(cell)]=dict(records=len(points),distinct_fractional_points=len(np.unique(points,axis=0)),distinct_rounded_cells=len(np.unique(np.rint(points),axis=0)),supported_records=int((H>0).sum()),available_model_people=available,allocated_hinterland_people=served,unallocated_model_people=max(0.,available-served),native_grid_roundtrip_max_cells=grid_error,coordinate_basis='Native spherical AEQD; Mexico retains archived UTM14N/WGS84 assumption. Fractional indices avoid coarse rounding,not a source-accuracy claim')
            for seed in [1,7,19,43,97]:
                valid=H>0;area=np.zeros(len(H));e=Z.draws(len(H),seed)
                area[valid]=Z.generate_area(coef[0]+coef[1]*np.log(H[valid]),sigma,e[valid],*bounds)
                arrays[key+f'__areas_{seed}']=area
                total_lo=float(lo.sum());total_hi=None if np.isinf(hi).any() else float(hi.sum())
                flat=float(np.sum(area*100));central=float(np.sum(area*Z.density_per_ha(area)))
                row=dict(pool=pool,cell_km=cell,seed=seed,supplied_towns=len(area),supported_towns=int(valid.sum()),model_total_area_ha=float(area.sum()),source_total_lower_ha=total_lo,source_total_upper_ha=total_hi,model_largest_area_ha=float(area.max()),model_above200=int((area>200).sum()),interval_ks_lower_bound=interval_ks_lower_bound(area,lo,hi),paired_band_hit=None,sorted_band_hit=None,model_flat100_residents=flat,model_sliding_residents=central,available_model_people=available,urban_share_if_flat100=flat/available,urban_share_if_sliding=central/available,zero_H_sites_retained=True)
                if pool=='floodplains':
                    row['paired_band_hit']=float(np.mean((area>=lo)&(area<=hi)))
                    row['sorted_band_hit']=float(np.mean(np.searchsorted([4.05,10.05,20.05,40.05,200.5],np.sort(area)[::-1])+1==np.sort(sourcevalues)[::-1]))
                cases.append(row)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'cases.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(cases[0]));w.writeheader();w.writerows(cases)
    np.savez_compressed(out/'model.npz',**arrays)
    (out/'geometry.json').write_text(json.dumps(geometry,indent=2,allow_nan=False)+'\n')
    protected=dict(prior['protected_sha256'])
    for name in ['input_receipt.json','results.json','observations.json','positions.csv','sizes.csv','model.npz','review.json']:protected[str((BASE/name).relative_to(ROOT))]=sha(BASE/name)
    paths=[Path(__file__),ROOT/'polity/observed_hinterlands.py',ROOT/'tests/test_observed_hinterlands.py',ROOT/'scripts/urban_diagnosis.py',ROOT/'polity/urban_observations.py',ROOT/'polity/settlement_sizes.py',ROOT/'rotclimate/earth.py',PLAN,AMENDMENT]
    result=dict(status='observed_site_conditional_size_diagnosis',cases=cases,geometry=geometry,producers={str(p.relative_to(ROOT)):sha(p) for p in paths},sources={str((BASE/'input_receipt.json').relative_to(ROOT)):sha(BASE/'input_receipt.json')},protected_sha256=protected,files_sha256={name:sha(out/name) for name in ['cases.csv','model.npz','geometry.json']},fit_performed=False,site_forecast=False,new_blind_test=False,adopt=False,climate_changed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('Wrote20conditional size cases;119/27supplied sites retained at both resolutions',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
