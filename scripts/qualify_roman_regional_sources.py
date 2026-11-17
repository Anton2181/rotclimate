"""Qualify three source candidates and the South Levant presence/support contract."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import subprocess

import numpy as np
from pyproj import Transformer
import shapely
from shapely import from_wkb,union_all,Point

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/roman_regional_sources_20261117';SRC=OUT/'source'
PLAN=ROOT/'calibration/roman_benchmark_20261117/regional_source_screen.json'
CONTRACT=ROOT/'calibration/roman_benchmark_20261117/south_levant_observation_contract.json'
PARENT=ROOT/'output/roman_benchmark_20261117'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def table(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def geometry(blob):
    assert blob[:2]==b'GP' and blob[2]==0
    flag=blob[3];envelope=(flag>>1)&7;endian='<' if flag&1 else '>'
    srid=struct.unpack(endian+'i',blob[4:8])[0];assert srid==32636
    skip=8+{0:0,1:32,2:48,3:48,4:64}[envelope]
    return from_wkb(blob[skip:])


def load():
    c=sqlite3.connect('file:'+str((SRC/'dataset/dataset.gpkg').resolve())+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
    layers=[dict(r) for r in c.execute('select table_name,data_type,srs_id from gpkg_contents')]
    records=[dict(r) for r in c.execute('select * from archaeo_sites order by fid')]
    polygons=[dict(r) for r in c.execute('select * from archaeo_survey_areas order by fid')]
    types={r[1]:r[2] for r in c.execute('pragma table_info(archaeo_sites)')};c.close()
    return layers,records,polygons,types


def protected():
    q=read(PARENT/'qualification.json');assert q['status'].startswith('passed_conditional_')
    frozen=dict(q['protected_sha256']);frozen.update(q['sources_sha256'])
    for n,d in q['files_sha256'].items():frozen[str((PARENT/n).relative_to(ROOT))]=d
    frozen[str((PARENT/'qualification.json').relative_to(ROOT))]=sha(PARENT/'qualification.json')
    for n,d in frozen.items():assert sha(ROOT/n)==d,n
    return frozen


def main(out):
    for p in [PLAN,CONTRACT]:assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
    assert not (out/'results.json').exists(),'Preserve completed qualification; use --out for fresh replay'
    frozen=protected();receipt=read(OUT/'source_receipt.json')
    for name,meta in receipt['files'].items():
        p=SRC/name;assert sha(p)==meta['sha256'] and p.stat().st_size==meta['bytes'],name
        if 'git_blob_sha1' in meta:
            b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==meta['git_blob_sha1']
    assert receipt['commit']==read(PLAN)['source_commit']
    layers,records,polygons,types=load();to_ll=Transformer.from_crs(32636,4326,always_xy=True)
    for row in records:row['point']=geometry(row['geom']);assert row['point'].geom_type=='Point' and row['point'].is_valid and not row['point'].is_empty
    groups=defaultdict(list);polyrows=[]
    for p in polygons:
        g=geometry(p['geom']);assert g.geom_type=='Polygon' and g.is_valid and not g.is_empty
        ref=p['reference'];polyrows.append(dict(fid=p['fid'],reference=ref or '',geometric_area_sqkm=g.area/1e6,published_area_sqkm=p['area_sqkm'],survey_type=p['survey_type'] or '',attribution_known=bool(ref)))
        if ref:groups[ref].append(g)
    unions={ref:union_all(geoms) for ref,geoms in sorted(groups.items())};names=list(unions)
    with (SRC/'dataset/archaeo_sites.csv').open(encoding='utf-8-sig',newline='') as f:csvrows=list(csv.DictReader(f))
    assert len(csvrows)==len(records)
    fields=[k for k in types if k not in ['fid','geom']];diff=[]
    identity=['SiteID','Period','Type','Source','StartDate','EndDate']
    for row,old in zip(records,csvrows):
        for key in fields:
            actual=row[key];text=old[key];numeric=types[key] in ['MEDIUMINT','INTEGER','REAL']
            value=None if text in ['','NULL'] else float(text) if numeric else text
            equal=(actual is None and value is None) or actual==value
            if numeric and actual is not None and value is not None:equal=math.isclose(float(actual),float(value),rel_tol=2e-14,abs_tol=1e-9)
            if not equal:
                assert key not in identity,'CSV/GPKG row identity differs; do not align by row order'
                diff.append(dict(fid=row['fid'],site_id=row['SiteID'],period=row['Period'],field=key,csv_value='' if value is None else value,gpkg_value='' if actual is None else actual))
    # CSV/GPKG discrepancies are retained, never applied as source corrections.
    phase=[r for r in records if r['Period']=='Late Roman' and r['StartDate']==70 and r['EndDate']==324]
    residential=[r for r in phase if r['Type'] in ['Settlement','Fortified Settlement']]
    loc=[r for r in residential if r['LocQual']=='A']
    identities=defaultdict(list)
    for r in loc:identities[r['SiteID']].append(r)
    unique=[];conflicts=[]
    for site,rows in sorted(identities.items()):
        first=rows[0];same=all(r['Source']==first['Source'] and r['point'].equals_exact(first['point'],0) for r in rows)
        if same:unique.append(first)
        else:conflicts.append(dict(site_id=site,fids=[r['fid'] for r in rows]))
    matched=[r for r in unique if r['Source'] in unions]
    selected=[r for r in matched if unions[r['Source']].covers(r['point'])]
    outside=[r for r in matched if not unions[r['Source']].covers(r['point'])]
    counts=dict(all_phase_rows=len(records),unique_site_ids=len(set(r['SiteID'] for r in records)),
                exact_Late_Roman70_324_rows=len(phase),Late_Roman_label_inconsistent_span=sum(r['Period']=='Late Roman' and (r['StartDate'],r['EndDate'])!=(70,324) for r in records),
                residential_type_rows=len(residential),exact_centroid_quality_rows=len(loc),deduplicated_site_ids=len(unique),identity_conflict_site_ids=len(conflicts),
                duplicate_phase_rows_collapsed=len(loc)-sum(len(identities[s['site_id']]) for s in conflicts)-len(unique),
                own_reference_available_site_ids=len(matched),inside_own_reference_site_ids=len(selected),outside_own_reference_site_ids=len(outside),
                unmatched_reference_site_ids=len(unique)-len(matched))
    support=[]
    for ref,g in unions.items():
        primary=[r for r in matched if r['Source']==ref];inside=[r for r in selected if r['Source']==ref]
        support.append(dict(reference=ref,polygon_count=len(groups[ref]),union_area_sqkm=g.area/1e6,phase_sites_with_source=len(primary),inside_own_polygon=len(inside),outside_own_polygon=len(primary)-len(inside),walked_area_certified=False,detection_probability_known=False))
    all_union=union_all(list(unions.values()));geometry_summary=dict(crs='EPSG:32636',units='metres',polygon_rows=len(polygons),valid_polygon_rows=len(polygons),
        named_reference_rows=sum(bool(p['reference']) for p in polygons),anonymous_polygon_rows=sum(not p['reference'] for p in polygons),named_references=len(unions),
        sum_named_area_sqkm=sum(g.area for g in unions.values())/1e6,union_named_area_sqkm=all_union.area/1e6,
        between_reference_overlap_sqkm=(sum(g.area for g in unions.values())-all_union.area)/1e6,
        polygons_are_published_envelopes_not_certified_walked_land=True)
    errors=[]
    for r in records:
        x,y=to_ll.transform(r['point'].x,r['point'].y)
        if r['Latitude'] is not None and r['Longitude'] is not None:errors.append(max(abs(x-r['Longitude']),abs(y-r['Latitude'])))
    geometry_summary.update(maximum_geometry_vs_WGS84_attribute_difference_degrees=max(errors),geometry_vs_attributes_over_1e_5_degree_rows=sum(v>1e-5 for v in errors))
    excluded=dict(inconsistent_phase_fids=[r['fid'] for r in records if r['Period']=='Late Roman' and (r['StartDate'],r['EndDate'])!=(70,324)],
                  identity_conflicts=conflicts,outside_own_polygon_fids=[r['fid'] for r in outside])
    qcounts={key:dict(Counter(str(r[key]) for r in records)) for key in ['Period','Type','LocQual','SizeQual']}
    # Preserve every chosen site's original identity and geometry; no model read.
    arrays=dict(fid=np.array([r['fid'] for r in selected],dtype=np.int64),site_id=np.array([r['SiteID'] for r in selected],dtype=np.int64),
                east=np.array([r['point'].x for r in selected]),north=np.array([r['point'].y for r in selected]),source_code=np.array([names.index(r['Source']) for r in selected],dtype=np.int64))
    ll=np.array([to_ll.transform(x,y) for x,y in zip(arrays['east'],arrays['north'])]);arrays['lon']=ll[:,0];arrays['lat']=ll[:,1]
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'observations.npz',**arrays)
    table(out/'survey_support.csv',support);table(out/'polygon_audit.csv',polyrows)
    # Keep a stable header even if no discrepancy exists.
    with (out/'cross_format_differences.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['fid','site_id','period','field','csv_value','gpkg_value']);w.writeheader();w.writerows(diff)
    table(out/'source_candidates.csv',[
        dict(candidate='Rural Britain',phase_definition='site occupation spans; functions undated',spatial_support='excavation/report-selected records',population_definition='not supplied',decision='not_qualified_for_complete_regional_counts'),
        dict(candidate='Potenza Valley Survey',phase_definition='Roman pottery; second-third-century diagnostic hiatus',spatial_support='intensive/extensive sample areas; no machine-readable support qualified here',population_definition='not supplied',decision='not_selected_for_immediate_numerical_test'),
        dict(candidate='South Levant',phase_definition='exact Late Roman70–324 site-phase subset',spatial_support='own-primary-source attributed published polygons',population_definition='not supplied; phase size not population',decision='conditional_spatial_presence_contract_only')])
    write(out/'cohort.json',dict(counts=counts,source_names=names,selected_fids=arrays['fid'].tolist(),selected_site_ids=arrays['site_id'].tolist(),excluded=excluded,
        primary_phase='70–324AD; not simultaneous AD200 census',phase_source_types=['Settlement','Fortified Settlement']))
    write(out/'input_summary.json',dict(layers=layers,counts=counts,geometry=geometry_summary,quality_counts=qcounts,
        csv_gpkg_discrepancies=len(diff),csv_gpkg_discrepancy_fields=dict(Counter(r['field'] for r in diff)),
        version_count_note='Pinned current files supersede published5542sites/14142phases; retain actual counts rather than relabelling old release.',
        dependency_versions=dict(numpy=np.__version__,shapely=shapely.__version__),
        spatial_presence_contract_prepared=True,uniform_detection_qualified=False,walked_footprint_qualified=False,
        absolute_count_or_population_benchmark_ready=False,phase_specific_area_benchmark_ready=False,model_scores_performed=False))
    sources={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,CONTRACT,OUT/'source_receipt.json',PARENT/'qualification.json']}
    for n,d in frozen.items():assert sha(ROOT/n)==d,n
    files=['observations.npz','survey_support.csv','polygon_audit.csv','cross_format_differences.csv','source_candidates.csv','cohort.json','input_summary.json']
    write(out/'results.json',dict(status='prepared_three_source_screen_and_conditional_Levant_presence_inputs',sources_sha256=sources,protected_sha256=frozen,
        local_source_sha256={n:meta['sha256'] for n,meta in receipt['files'].items()},files_sha256={n:sha(out/n) for n in files},
        candidates=3,source_commit=receipt['commit'],counts=counts,model_scores_performed=False,new_fit=False,new_validation_claim=False,
        food_work_climate_route_solver_calls=0,main_atlas_changed=False,adopt=False))
    print(json.dumps(counts),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
