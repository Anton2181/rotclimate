"""Match declared archive contexts to the frozen Earth grid, without model scores.

Projected source records/matches stay in the private cache. Public preparation
contains aggregate coverage, cell/class support and explicit transform limits.
"""
import collections
import hashlib
import json
from pathlib import Path
import sys
import warnings

import numpy as np
import pyproj
from pyproj.aoi import AreaOfInterest
from pyproj.transformer import TransformerGroup

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,sha,write
from polity.observed_role_contrast import match_full_grid,cell_class_summary

PLAN=ROOT/'calibration/settlement_role_contrast_20261111/plan.json'
OUT=ROOT/'output/settlement_role_contrast_20261111'
CACHE=ROOT/'data/cache/settlement_role_contrast_20261111'
SOURCE=ROOT/'data/cache/roman_rural_britain_2018'
INPUT=ROOT/'output/settlement_locations_20261110/rome_inputs.npz'


def main():
    OUT.mkdir(parents=True,exist_ok=True);CACHE.mkdir(parents=True,exist_ok=True)
    plan=json.loads(PLAN.read_text());snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    for source in json.loads(snapshot.read_text())['files']:
        if sha(SOURCE/source['name'])!=source['sha256']:raise ValueError('Changed observation source')
    old=json.loads((ROOT/'output/settlement_locations_20261110/results.json').read_text())
    if sha(INPUT)!=old['pools']['rome']['input_sha256']:raise ValueError('Changed frozen Roman grid')
    core,_=table((SOURCE/'rrs_core_data.csv').read_bytes(),['ID'])
    sites,_=table((SOURCE/'rrs_site_data.csv').read_bytes(),['ID'])
    roles,_=table((SOURCE/'rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID')
    byid={identifier(r['id']):r for r in core};labels=collections.defaultdict(set)
    for row in roles:labels[identifier(row['id'])].add(row['sitetypeminor'].casefold().strip())
    positive=set(plan['target']['positive_labels']);negative=set(plan['target']['comparison_labels'])
    chosen=[];classes=[]
    for row in sites:
        key=identifier(row['id']);n=bool(labels[key]&positive);f=bool(labels[key]&negative)
        if row['domesticoccupation'].strip().casefold()=='yes' and n!=f:
            chosen.append(byid[key]);classes.append(int(n))
    classes=np.asarray(classes,int)
    assert len(chosen)==2475 and np.sum(classes)==426 and np.sum(classes==0)==2049
    east=np.array([float(r['xrefmap']) for r in chosen]);north=np.array([float(r['yrefmap']) for r in chosen])
    pyproj.network.set_network_enabled(False)
    with warnings.catch_warnings(record=True) as caught:
        group=TransformerGroup(27700,4326,always_xy=True,allow_ballpark=False,
                               area_of_interest=AreaOfInterest(-6.5,49.5,2.,56.))
    if not group.transformers:raise ValueError('No non-ballpark British-grid transform available')
    transform=group.transformers[0]
    # Reconstruct the declared AEQD footprint, checking every archived grid centre.
    spec=json.loads((ROOT/'calibration/polity_20261025/plan.json').read_text())['earth_windows']['rome']
    projection=pyproj.Proj(proj='aeqd',lat_0=spec['lat0'],lon_0=spec['lon0'],R=6371000,units='km')
    x=dict(np.load(INPUT));gx,gy=projection(x['lon'],x['lat']);cell=float(x['cell_km'])
    h,w=x['land'].shape
    expected_x=np.broadcast_to((np.arange(w)-(w-1)/2)*cell,(h,w))
    expected_y=np.broadcast_to(((h-1)/2-np.arange(h))[:,None]*cell,(h,w))
    geometry_error=max(float(np.max(abs(gx-expected_x))),float(np.max(abs(gy-expected_y))))
    if geometry_error>1e-6:raise ValueError('Window metadata does not reproduce frozen grid geometry')
    offsets=[('central',0,0)]+[(f'{axis}_{sign*km:+d}km',sign*km*1000 if axis=='east' else 0,
        sign*km*1000 if axis=='north' else 0) for km in [2,5] for axis in ['east','north'] for sign in [-1,1]]
    scenarios=[];cells=[];statuses=[]
    for name,de,dn in offsets:
        lon,lat=transform.transform(east+de,north+dn,errcheck=True)
        px,py=projection(lon,lat)
        inside=(abs(px)<=w*cell/2)&(abs(py)<=h*cell/2)
        index,status=match_full_grid(lat,lon,x['lat'],x['lon'],x['land'],x['allowed'],inside)
        summary=cell_class_summary(index,classes,status)
        summary.update(name=name,easting_offset_metres=de,northing_offset_metres=dn,
            coverage_by_class={str(k):{label:int(np.sum((classes==k)&(status==code)))
                for code,label in enumerate(['included','outside_window','nonland','disallowed'])} for k in [0,1]})
        scenarios.append(summary);cells.append(index);statuses.append(status)
    np.savez_compressed(CACHE/'matched.npz',source_ids=np.array([identifier(r['id']) for r in chosen]),
        classes=classes,cells=np.asarray(cells),status=np.asarray(statuses),scenario_names=np.array([s['name'] for s in scenarios]))
    result=dict(status='conditional_source_grid_preparation_no_predictor_scores',adopt=False,
        plan_sha256=sha(PLAN),producer_sha256=sha(Path(__file__)),
        matching_module_sha256=sha(ROOT/'polity/observed_role_contrast.py'),
        parser_sha256=sha(ROOT/'scripts/audit_vidarbha_preparation.py'),
        table_reader_sha256=sha(ROOT/'scripts/audit_roman_rural_preparation.py'),
        original_source_snapshot_sha256=sha(snapshot),roman_input_sha256=sha(INPUT),
        original_results_sha256=sha(ROOT/'output/settlement_locations_20261110/results.json'),
        private_matches_sha256=sha(CACHE/'matched.npz'),private_matches_redistributed=False,
        records=len(chosen),source_class_counts={'0':2049,'1':426},class_meaning={'0':'recorded farm/villa context','1':'recorded nucleated context'},
        transform=dict(pyproj_version=pyproj.__version__,PROJ_version=pyproj.proj_version_str,
            description=transform.description,pipeline=transform.definition,reported_accuracy_metres=transform.accuracy,
            most_accurate_operation_available=group.best_available,network_grid_downloads=False,
            warnings=[str(v.message) for v in caught],accuracy_is_not_source_survey_precision=True),
        grid=dict(shape=[h,w],cell_km=cell,window_spec=spec,geometry_reconstruction_max_error_km=geometry_error,
            nearest_full_grid_before_land_check=True),scenarios=scenarios,
        preparation_gate_passed=scenarios[0]['preparation_gate_passed'],
        selected_source_projection_performed=True,whole_archive_projection_performed=False,
        model_predictor_scores_computed=False,AUC_computed=False,source_map_generated=False,
        limits='Selected archive-context contrast, not AD200 roles/census/true absence. Source coordinates operationally interpreted; missing best transform grid and source positional uncertainty remain explicit. Mixed cells retain both classes; no source observation or population is merged.')
    write(OUT/'preparation.json',result)
    print('Preparation gate',result['preparation_gate_passed'],'central support',json.dumps(scenarios[0]),flush=True)


if __name__=='__main__':main()
