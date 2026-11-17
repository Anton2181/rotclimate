"""Fixed-field, same-source spatial diagnostic; no population/count calibration."""
import argparse
import csv
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from pyproj import CRS,Transformer
from shapely import box,segmentize,transform as shape_transform,union_all
from shapely.ops import transform as coordinate_transform

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from qualify_roman_regional_sources import sha,read,write,table,load,geometry,OUT as SOURCE
from polity import earth as E
from polity.settlement_sizes import hinterlands

OUT=ROOT/'output/levant_spatial_diagnostic_20261117'
PLAN=ROOT/'calibration/roman_benchmark_20261117/levant_spatial_diagnostic.json'
ROMAN=ROOT/'output/settlement_locations_20261110/rome_inputs.npz'
RECIPE=ROOT/'output/urban_population_recipe_20261116'
GRID=RECIPE/'restored/grid/earth.npz'


def finite(value):
    if math.isfinite(value):return float(value)
    return '-inf' if value<0 else 'inf'


def score(area,count,weight):
    n=float(count.sum());norm=float(np.dot(area,weight));baseline=area/area.sum()
    if norm<=0:return dict(normalization_valid=False,site_n=int(n),log_likelihood='-inf',mean_log_gain='-inf',presence_background_auc=.5,zero_weight_occupied_cells=int((count>0).sum())),np.zeros_like(weight)
    p=area*weight/norm;occupied=count>0
    zero=occupied&(p==0)
    likelihood=-math.inf if zero.any() else float(np.dot(count[occupied],np.log(p[occupied])))
    gain=-math.inf if zero.any() else float(np.dot(count[occupied],np.log(p[occupied]/baseline[occupied]))/n)
    comparison=(weight[:,None]>weight[None,:]).astype(float)+.5*(weight[:,None]==weight[None,:])
    auc=float(np.sum(count[:,None]*area[None,:]*comparison)/(n*area.sum()))
    return dict(normalization_valid=True,site_n=int(n),log_likelihood=finite(likelihood),mean_log_gain=finite(gain),presence_background_auc=auc,zero_weight_occupied_cells=int(zero.sum())),p


def main(out):
    for p in [PLAN,SOURCE/'qualification.json']:
        assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
    assert not (out/'results.json').exists(),'Preserve completed diagnostic; use isolated --out'
    q=read(SOURCE/'qualification.json');assert q['status'].startswith('passed_conditional_Levant')
    protected=dict(q['protected_sha256']);protected.update(q['sources_sha256'])
    for n,d in q['files_sha256'].items():protected[str((SOURCE/n).relative_to(ROOT))]=d
    protected[str((SOURCE/'qualification.json').relative_to(ROOT))]=sha(SOURCE/'qualification.json')
    for n,d in protected.items():assert sha(ROOT/n)==d,n
    with np.load(SOURCE/'observations.npz') as z:observations=dict(z)
    cohort=read(SOURCE/'cohort.json');names=cohort['source_names']
    with np.load(ROMAN) as z:x={k:z[k] for k in ['land','density','lat','lon','cell_km','real']}
    ny,nx=x['land'].shape;cell=float(x['cell_km'])*1000;assert (ny,nx,cell)==(400,600,9000.)
    projection=CRS.from_proj4('+proj=aeqd +lat_0=40 +lon_0=17 +R=6371000 +units=m +no_defs')
    to_model=Transformer.from_crs(32636,projection,always_xy=True);ll_to_model=Transformer.from_crs(4326,projection,always_xy=True)
    mx,my=ll_to_model.transform(x['lon'],x['lat']);expectedx=(np.arange(nx)-(nx-1)/2)*cell;expectedy=((ny-1)/2-np.arange(ny))*cell
    projection_error=max(float(abs(mx-expectedx[None,:]).max()),float(abs(my-expectedy[:,None]).max()))
    assert projection_error<1e-6
    # Exact fixed input recipe replay, not a new climate/agriculture simulation.
    old=E.EARTH_NPZ
    try:E.EARTH_NPZ=GRID;density,_,covered=E.earth_people(x['lat'],x['lon'])
    finally:E.EARTH_NPZ=old
    refreshed=np.where(x['land'],density,0.)
    centres=np.column_stack(np.unravel_index(x['real'],x['land'].shape))
    _,H=hinterlands(centres,x['land'],refreshed*float(x['cell_km'])**2,float(x['cell_km']))
    with np.load(RECIPE/'model.npz') as z:np.testing.assert_array_equal(H,z['floodplain_settlement_base__centre_H'])
    with (RECIPE/'windows.csv').open() as f:expected=next(r for r in csv.DictReader(f) if r['variant']=='floodplain_settlement_base')
    assert float((refreshed[x['land']]*float(x['cell_km'])**2).sum())==float(expected['window_people'])
    fields=dict(uniform=np.ones((ny,nx)),legacy=x['density'],refreshed=refreshed)
    for a in fields.values():assert np.isfinite(a).all() and (a>=0).all()
    _,_,polygons,_=load();groups={name:[] for name in names}
    for r in polygons:
        if r['reference'] in groups:groups[r['reference']].append(geometry(r['geom']))
    polygons={name:union_all(values) for name,values in groups.items()}
    px,py=to_model.transform(observations['east'],observations['north'])
    col=np.rint(px/cell+(nx-1)/2).astype(int);row=np.rint((ny-1)/2-py/cell).astype(int)
    ingrid=(row>=0)&(row<ny)&(col>=0)&(col<nx);onland=np.zeros(len(row),bool);onland[ingrid]=x['land'][row[ingrid],col[ingrid]]
    retained=ingrid&onland
    cells=[];supports=[];scores=[];arrays={};probabilities={label:[] for label in fields}
    for code,name in enumerate(names):
        g=polygons[name];dense=segmentize(g,1000.);gm=coordinate_transform(to_model.transform,dense);assert gm.is_valid
        minx,miny,maxx,maxy=gm.bounds
        c0=max(0,int(math.floor(minx/cell+nx/2)));c1=min(nx-1,int(math.floor(maxx/cell+nx/2)))
        r0=max(0,int(math.floor(ny/2-maxy/cell)));r1=min(ny-1,int(math.floor(ny/2-miny/cell)))
        counts={}
        for rr,cc in zip(row[(observations['source_code']==code)&retained],col[(observations['source_code']==code)&retained]):counts[int(rr),int(cc)]=counts.get((int(rr),int(cc)),0)+1
        local=[];allarea=0.;seaarea=0.
        for rr in range(r0,r1+1):
            for cc in range(c0,c1+1):
                left=(cc-nx/2)*cell;top=(ny/2-rr)*cell
                intersection=gm.intersection(box(left,top-cell,left+cell,top));a=intersection.area/1e6
                if a<=0:continue
                allarea+=a
                if not x['land'][rr,cc]:seaarea+=a;continue
                local.append(dict(source_code=code,reference=name,row=rr,column=cc,model_area_sqkm=a,site_count=counts.get((rr,cc),0),
                                  legacy_weight=float(fields['legacy'][rr,cc]),refreshed_weight=float(fields['refreshed'][rr,cc])))
        assert len(local)>0 and abs(allarea-gm.area/1e6)<1e-7
        assert sum(c['site_count'] for c in local)==int(((observations['source_code']==code)&retained).sum()),'Point must fall in positive-area own-source model support'
        a=np.array([c['model_area_sqkm'] for c in local]);n=np.array([c['site_count'] for c in local])
        source_mask=observations['source_code']==code
        supports.append(dict(reference=name,source_UTM_area_sqkm=g.area/1e6,model_projection_area_sqkm=gm.area/1e6,model_land_area_sqkm=float(a.sum()),
            model_nonland_area_sqkm=seaarea,model_land_cells=len(local),occupied_model_cells=int((n>0).sum()),original_sites=int(source_mask.sum()),
            retained_sites=int(n.sum()),off_grid_sites=int((source_mask&~ingrid).sum()),off_land_sites=int((source_mask&ingrid&~onland).sum()),
            coincident_native_cell_excess=int(n.sum()-(n>0).sum()),field_covered_land=bool(covered[[c['row'] for c in local],[c['column'] for c in local]].all())))
        for label in fields:
            weight=np.ones(len(local)) if label=='uniform' else np.array([c[label+'_weight'] for c in local])
            s,p=score(a,n,weight);scores.append(dict(reference=name,model=label,**s));probabilities[label].extend(p.tolist())
        cells.extend(local)
    arrays=dict(source_code=np.array([c['source_code'] for c in cells]),row=np.array([c['row'] for c in cells]),column=np.array([c['column'] for c in cells]),
                area_sqkm=np.array([c['model_area_sqkm'] for c in cells]),count=np.array([c['site_count'] for c in cells]),
                legacy_weight=np.array([c['legacy_weight'] for c in cells]),refreshed_weight=np.array([c['refreshed_weight'] for c in cells]),
                observation_row=row,observation_column=col,observation_retained=retained)
    arrays.update({label+'_probability':np.array(p) for label,p in probabilities.items()})
    summaries=[]
    for label in fields:
        chosen=[s for s in scores if s['model']==label];gains=np.array([float(s['mean_log_gain']) for s in chosen]);ns=np.array([s['site_n'] for s in chosen])
        summaries.append(dict(model=label,sources=len(chosen),retained_site_n=int(ns.sum()),normalization_valid=all(s['normalization_valid'] for s in chosen),
            equal_source_mean_log_gain=finite(float(np.mean(gains))),pooled_site_mean_log_gain=finite(float(np.dot(gains,ns)/ns.sum())),
            equal_source_presence_background_auc=float(np.mean([s['presence_background_auc'] for s in chosen])),
            zero_weight_occupied_cells=sum(s['zero_weight_occupied_cells'] for s in chosen)))
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'model_support.npz',**arrays)
    table(out/'cells.csv',cells);table(out/'support.csv',supports);table(out/'scores.csv',scores);table(out/'summary.csv',summaries)
    paths=[Path(__file__),PLAN,SOURCE/'qualification.json',SOURCE/'observations.npz',ROMAN,GRID,RECIPE/'model.npz',RECIPE/'windows.csv',ROOT/'polity/earth.py',ROOT/'harvest/models.py']
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    for n,d in protected.items():assert sha(ROOT/n)==d,n
    files=['model_support.npz','cells.csv','support.csv','scores.csv','summary.csv']
    write(out/'results.json',dict(status='conditional_Levant_spatial_presence_diagnostic_not_population_validation',sources_sha256=sources,protected_sha256=protected,
        files_sha256={n:sha(out/n) for n in files},source_names=names,projection_maximum_centre_error_metres=projection_error,
        source_sites=565,retained_sites=int(retained.sum()),off_grid_sites=int((~ingrid).sum()),off_land_sites=int((ingrid&~onland).sum()),
        source_model_cell_pairs=len(cells),distinct_model_cells=len(set(zip(arrays['row'].tolist(),arrays['column'].tolist()))),
        recipe_all_centre_H_control_exact=True,recipe_total_people_control_exact=True,summaries=summaries,
        native_cell_km=9,uniform_within_source_detection_assumed_not_qualified=True,site_intensity_population_link_assumed_not_qualified=True,
        source_period='70–324AD',new_fit=False,new_blind_test=False,new_validation_claim=False,
        food_work_climate_route_solver_calls=0,actual_population_allocated=False,main_atlas_changed=False,adopt=False))
    print('Completed fixed-field diagnostic:',int(retained.sum()),'sites;',len(cells),'source/cell pairs',flush=True)
    for row in summaries:print(row,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
