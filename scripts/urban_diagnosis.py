"""Spent-pool diagnosis of observation definitions and the release-4 transfer.

No fits, invented known capitals, density corrections or new blind scores.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import ks_2samp

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import floodplains_blind as F
import valley_of_mexico_blind as V
from polity import settlement_sizes as Z
from polity.settlement_locations import confluence_field,match_count,prior_tiling_sites,site_fields
from polity.urban_observations import interval_ks_lower_bound

OUT=ROOT/'output/urban_diagnosis_20261116'
CAL=ROOT/'calibration/urban_diagnosis_20261116'
SEEDS=[1,7,19,43,97]
VARIANTS=['release3_subset_draw','release3_full_draw','release4_full_draw']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def cohort(pool,x,surveyed):
    m=F if pool=='floodplains' else V;r=m.rows()
    finite=np.isfinite(r['lat'])&np.isfinite(r['lon'])
    active=finite&((r['start']<=200)&(r['end']>=200)&(r['size']>0) if pool=='floodplains' else np.isin(r['period'],['Classic','Early Classic']))
    ids=r['ids'] if pool=='floodplains' else r['site'];sizes=r['size'] if pool=='floodplains' else r['area'];best={}
    for i in np.flatnonzero(active):
        if ids[i] not in best or np.nan_to_num(sizes[i])>np.nan_to_num(sizes[best[ids[i]]]):best[ids[i]]=i
    indices=np.array(sorted(best.values()))
    inside=(abs(r['lat'][indices]-m.LAT0)<m.HKM/2/111.32)&(abs(r['lon'][indices]-m.LON0)<m.WKM/2/(111.32*np.cos(np.radians(m.LAT0))))
    selected=indices[inside];tree=cKDTree(F.xyz(x['lat'].ravel(),x['lon'].ravel()))
    cells=tree.query(F.xyz(r['lat'][selected],r['lon'][selected]))[1];keep=surveyed.ravel()[cells]
    selected=selected[keep];cells=cells[keep];values=sizes[selected]
    town=(values>=3) if pool=='floodplains' else (np.nan_to_num(values)>=10)
    lower=np.array([F.BANDS[int(c)][0] for c in values]) if pool=='floodplains' else values.copy()
    upper=np.array([np.inf if int(c)==6 else F.BANDS[int(c)][1] for c in values]) if pool=='floodplains' else values.copy()
    info=dict(source_rows=len(ids),cohort_unique_ids=len(indices),selected_source_records=len(selected),distinct_grid_cells=len(np.unique(cells)),town_records=int(town.sum()),distinct_town_grid_cells=len(np.unique(cells[town])),source_defined_town_threshold_ha=10.1 if pool=='floodplains' else 10.0,survey_proxy_area_km2=float(surveyed.sum()*float(x['cell_km'])**2),survey_proxy_is_independent_coverage=False)
    if pool=='floodplains':
        spans=r['end'][selected]-r['start'][selected]
        info.update(area_observation='ordinal area intervals; final class right-censored',area_class_counts={str(i):int((values==i).sum()) for i in F.BANDS},occupation_span_years_quantiles=[float(v) for v in np.quantile(spans,[0,.25,.5,.75,1])],date_boundary_at_200=int(((r['start'][selected]==200)|(r['end'][selected]==200)).sum()),finite_upper_bound_for_class6=False)
    else:
        pop=r['pop'][selected];pmin=r['popmin'][selected];pmax=r['popmax'][selected];good=np.isfinite(values)&(values>0)
        total=float(np.nansum(pop));area=float(np.sum(values[good]));low=float(np.nansum(pmin));high=float(np.nansum(pmax))
        old=json.loads((ROOT/'output/valley_of_mexico_blind_20261116/results.json').read_text())['grids']['3']['people']['model']
        info.update(area_observation='site hectares, metadata says nearest0.1ha; not asserted equivalent to inhabited Old World urban area',observed_area_ha=area,selected_largest_area_ha=float(np.max(values[good])),all_period_largest_area_ha=float(np.nanmax(r['area'])),largest_population_estimate=float(np.nanmax(pop)),population_estimate=total,population_min=low,population_max=high,missing_population_rows=int((~np.isfinite(pop)).sum()),estimate_equals_max_rows=int((np.isfinite(pop)&np.isfinite(pmax)&(pop==pmax)).sum()),estimated_people_per_area_ha=total/area if area else None,old_world_flat100_residents_on_observed_areas=float(np.sum(values[good]*100)),old_world_sliding_residents_on_observed_areas=float(np.sum(values[good]*Z.density_per_ha(values[good]))),archived_model_to_estimate=old/total,archived_model_to_minmax=[old/high,old/low],population_is_estimate_not_census=True,area_to_population_estimation_method_confirmed=False,teotihuacan_exclusion_confirmed_by_this_audit=False)
    return r,selected,cells,values,town,lower,upper,info


def position_metrics(field,towns,observed,surveyed,cell):
    distinct=np.unique(observed);background=np.sort(field[surveyed]);values=field.ravel()[distinct]
    pct=float(np.mean((np.searchsorted(background,values,'left')+np.searchsorted(background,values,'right'))/(2*len(background))))
    points=np.column_stack(np.divmod(distinct,field.shape[1]))
    capture=float(np.mean(cKDTree(towns).query(points)[0]*cell<=10)) if len(towns) else 0.
    return pct,capture


def main(out):
    for p in [CAL/'plan.json',CAL/'analysis_spec.json']:
        assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
    plan=json.loads((CAL/'plan.json').read_text());receipt=json.loads((OUT/'input_receipt.json').read_text())
    assert receipt['preparer_sha256']==sha(ROOT/'scripts/prepare_urban_diagnosis.py')
    for name,digest in {**plan['protected_sha256'],**receipt['inputs']}.items():assert sha(ROOT/name)==digest,name
    released=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary']
    model=released['models'][released['selected']];coef=model['full_coefficients'];sigma=model['heldout_sigma'];bounds=released['area_range_ha']
    original=json.loads(F.SIZES.read_text())['sizes']['primary'];old=original['models']['M1']
    assert coef[:2]==old['full_coefficients'] and sigma==old['heldout_sigma'] and bounds==original['area_range_ha']
    observations={};positions=[];sizes=[];arrays={}
    saved=os.environ.get('ROTCLIMATE_CONFLUENCE_K')
    try:
        for pool in ['floodplains','mexico']:
            base=OUT/'archived_replay'/pool
            with np.load(base/'model.npz') as z:legacy={k:z[k] for k in z.files}
            observations[pool]={}
            for cell in [3,9]:
                with np.load(base/f'inputs_{cell}km.npz') as z:x={k:z[k] for k in z.files}
                x['cell_km']=float(cell);surveyed=legacy[f'{cell}km__surveyed'];r,selected,obs,values,town,lower,upper,info=cohort(pool,x,surveyed)
                observations[pool][str(cell)]=info;prefix=f'{pool}_{cell}km'
                for key,value in dict(surveyed=surveyed,observed_cells=obs,observed_values=values,town_mask=town,lower_ha=lower,upper_ha=upper).items():arrays[prefix+'__'+key]=value
                args={k:x[k] for k in ['density','land','water_km','road','elev']};args.update(cell_km=float(cell),allowed=x['allowed'],aridity=x['aridity'])
                os.environ['ROTCLIMATE_CONFLUENCE_K']='1'
                count=len(legacy[f'{cell}km__production'])
                _,newtowns=match_count(lambda sp:prior_tiling_sites(**args,prior=x['history800'],seat_people=sp),count)
                newtowns=np.array(newtowns,int).reshape(-1,2)
                score,eligible=site_fields(**args)
                for variant in VARIANTS:
                    key=prefix+'__'+variant;isnew=variant.startswith('release4');towns=newtowns if isnew else legacy[f'{cell}km__release3']
                    field=np.where(eligible,score*x['history800']*(1+confluence_field(x['water_km'],cell) if isnew else 1),0.)
                    percentile,capture=position_metrics(field,towns,obs[town],surveyed,cell)
                    positions.append(dict(pool=pool,cell_km=cell,variant=variant,count_target=count,window_towns=len(towns),count_difference=len(towns)-count,survey_proxy_towns=int(surveyed[towns[:,0],towns[:,1]].sum()),observed_town_records=info['town_records'],observed_town_cells=info['distinct_town_grid_cells'],town_field_percentile=percentile,capture_10km=capture,known_centres=0,known_capitals=0))
                    arrays[key+'__towns']=towns;arrays[key+'__field']=field
                    if cell!=9:continue
                    _,H=Z.hinterlands(towns,x['land'],x['density']*x['land']*cell**2,cell)
                    keep=surveyed[towns[:,0],towns[:,1]]&(H>0);n=int(keep.sum());arrays[key+'__H']=H;arrays[key+'__keep']=keep
                    for seed in SEEDS:
                        if variant=='release3_subset_draw':
                            a=Z.generate_area(coef[0]+coef[1]*np.log(H[keep]),sigma,Z.draws(n,seed),*bounds)
                        else:
                            valid=H>0;a=np.zeros(len(H));e=Z.draws(len(H),seed)
                            a[valid]=Z.generate_area(coef[0]+coef[1]*np.log(H[valid])+coef[2]*np.zeros(int(valid.sum())),sigma,e[valid],*bounds)
                            a=a[keep]
                        arrays[key+f'__areas_{seed}']=a
                        observed=values[np.isfinite(values)&(values>0)];ranked=np.sort(observed)[::-1][:n];gen=np.sort(a)[::-1]
                        row=dict(pool=pool,cell_km=cell,variant=variant,seed=seed,survey_model_towns=n,observed_records=len(observed),shape_status='defined_but_count_and_coverage_conditional' if n else 'not_evaluable_no_model_towns',model_total_ha=float(a.sum()),model_largest_ha=float(a.max()) if n else None,model_above200=int((a>200).sum()),original_same_band=None,original_ks=None,original_total_ratio=None,original_formula_pass=None,topn_lower_ha=None,topn_upper_ha=None,threshold_model_count=0,threshold_observed_count=int(town.sum()),interval_ks_lower_bound=None)
                        if n:
                            if pool=='floodplains':
                                codes=ranked.astype(int);lo=np.array([F.BANDS[c][0] for c in codes]);legacyhi=np.array([F.BANDS[c][1] for c in codes])
                                same=float(np.mean(np.searchsorted([4.05,10.05,20.05,40.05,200.5],gen)+1==codes))
                                row.update(original_same_band=same,topn_lower_ha=float(lo.sum()),topn_upper_ha=None if (codes==6).any() else float(legacyhi.sum()),original_formula_pass=bool(same>=.5 and .67*lo.sum()<=a.sum()<=1.5*legacyhi.sum()))
                            else:
                                ks=float(ks_2samp(gen,ranked).statistic);ratio=float(gen.sum()/ranked.sum())
                                row.update(original_ks=ks,original_total_ratio=ratio,original_formula_pass=bool(ks<=.2 and .67<=ratio<=1.5),topn_lower_ha=float(ranked.sum()),topn_upper_ha=float(ranked.sum()))
                            cut=info['source_defined_town_threshold_ha'];comparable=a[a>=cut];row['threshold_model_count']=len(comparable)
                            if len(comparable) and town.any():row['interval_ks_lower_bound']=interval_ks_lower_bound(comparable,lower[town],upper[town])
                        sizes.append(row)
    finally:
        if saved is None:os.environ.pop('ROTCLIMATE_CONFLUENCE_K',None)
        else:os.environ['ROTCLIMATE_CONFLUENCE_K']=saved
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('positions.csv',positions),('sizes.csv',sizes)]:
        with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    np.savez_compressed(out/'model.npz',**arrays);write(out/'observations.json',observations)
    paths=[Path(__file__),ROOT/'polity/urban_observations.py',ROOT/'polity/settlement_locations.py',ROOT/'polity/settlement_sizes.py',ROOT/'polity/settle.py',ROOT/'tests/test_urban_observations.py',ROOT/'data/source/urban_diagnosis_20261116/tdar_dataset193.html',CAL/'plan.json',CAL/'analysis_spec.json']
    write(out/'results.json',dict(status='spent_pool_release4_diagnosis_only',positions=positions,sizes=sizes,empty_anchor_size_parameters_equal=True,population_multiplier_for_10x_H=10**coef[1],input_receipt_sha256=sha(OUT/'input_receipt.json'),producers={str(p.relative_to(ROOT)):sha(p) for p in paths},files_sha256={name:sha(out/name) for name in ['positions.csv','sizes.csv','model.npz','observations.json']},protected_sha256=plan['protected_sha256'],adopt=False,new_blind_test=False,climate_changed=False))
    print('Wrote12position cases and30seeded size cases;no fit or adoption',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
