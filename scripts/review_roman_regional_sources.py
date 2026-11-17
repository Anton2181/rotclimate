"""Independent scalar chronology, identity, point-in-polygon and source-format review."""
import ast
from collections import Counter,defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct

import numpy as np
from pyproj import Transformer
from shapely import from_wkb,union_all

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/roman_regional_sources_20261117';SRC=OUT/'source'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())
def unpack(b):
    assert b[:3]==b'GP\x00';envelope=(b[3]>>1)&7
    offset=8+[0,32,48,48,64][envelope]
    assert struct.unpack('<i' if b[3]&1 else '>i',b[4:8])[0]==32636
    return from_wkb(b[offset:])


def ring_contains(coords,x,y):
    inside=False
    for (ax,ay),(bx,by) in zip(coords,coords[1:]):
        cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if cross==0 and min(ax,bx)<=x<=max(ax,bx) and min(ay,by)<=y<=max(ay,by):return True,True
        if (ay>y)!=(by>y) and x<ax+(y-ay)*(bx-ax)/(by-ay):inside=not inside
    return inside,False


def covers(p,x,y):
    yes,boundary=ring_contains(list(p.exterior.coords),x,y)
    if boundary:return True
    if not yes:return False
    for hole in p.interiors:
        yes,boundary=ring_contains(list(hole.coords),x,y)
        if boundary:return True
        if yes:return False
    return True


def area(p):
    def ring(coords):return abs(math.fsum(ax*by-bx*ay for (ax,ay),(bx,by) in zip(coords,coords[1:])))/2
    return ring(list(p.exterior.coords))-math.fsum(ring(list(h.coords)) for h in p.interiors)


def semantic(value):
    if value in [None,'','NULL']:return None
    text=str(value).strip()
    if text.startswith('{') and text.endswith('}'):
        return tuple(v.strip() for v in next(csv.reader([text[1:-1]],skipinitialspace=True)))
    return text


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed input review'
    r=read(OUT/'results.json');summary=read(OUT/'input_summary.json');cohort=read(OUT/'cohort.json')
    for n,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/n)==digest,n
    for n,digest in r['files_sha256'].items():assert sha(OUT/n)==digest,n
    for n,digest in r['local_source_sha256'].items():assert sha(SRC/n)==digest,n
    for n in ['results.json',*r['files_sha256']]:assert (OUT/n).read_bytes()==(OUT/'fresh'/n).read_bytes(),n
    connection=sqlite3.connect('file:'+str((SRC/'dataset/dataset.gpkg').resolve())+'?mode=ro',uri=True);connection.row_factory=sqlite3.Row
    sites=[dict(x) for x in connection.execute('select * from archaeo_sites order by fid')]
    polygons=[dict(x) for x in connection.execute('select * from archaeo_survey_areas order by fid')];connection.close()
    refs=defaultdict(list)
    for row in polygons:
        p=unpack(row['geom']);assert p.is_valid and p.geom_type=='Polygon'
        assert math.isclose(area(p),p.area,rel_tol=2e-11,abs_tol=.01)
        if row['reference']:refs[row['reference']].append(p)
    assert len(polygons)==69 and len(refs)==8
    ids=defaultdict(list);phase=[];residential=[]
    for row in sites:
        if row['Period']=='Late Roman' and row['StartDate']==70 and row['EndDate']==324:
            phase.append(row)
            if row['Type'] in ['Settlement','Fortified Settlement']:
                residential.append(row)
                if row['LocQual']=='A':ids[row['SiteID']].append(row)
    chosen=[];unmatched=[];outside=[];collapse=0;conflicts=0;checks=0
    for site,rows in sorted(ids.items()):
        first=rows[0];point=unpack(first['geom'])
        if not all(row['Source']==first['Source'] and unpack(row['geom']).wkb==point.wkb for row in rows):conflicts+=1;continue
        collapse+=len(rows)-1
        if first['Source'] not in refs:unmatched.append(first);continue
        found=any(covers(p,point.x,point.y) for p in refs[first['Source']]);checks+=1
        (chosen if found else outside).append(first)
    assert [row['fid'] for row in chosen]==cohort['selected_fids']
    assert [row['SiteID'] for row in chosen]==cohort['selected_site_ids']
    assert [row['fid'] for row in outside]==cohort['excluded']['outside_own_polygon_fids']
    expected=dict(all_phase_rows=len(sites),unique_site_ids=len({r['SiteID'] for r in sites}),exact_Late_Roman70_324_rows=len(phase),
        Late_Roman_label_inconsistent_span=sum(x['Period']=='Late Roman' and (x['StartDate'],x['EndDate'])!=(70,324) for x in sites),
        residential_type_rows=len(residential),exact_centroid_quality_rows=sum(len(x) for x in ids.values()),
        deduplicated_site_ids=len(ids)-conflicts,identity_conflict_site_ids=conflicts,duplicate_phase_rows_collapsed=collapse,
        own_reference_available_site_ids=len(chosen)+len(outside),inside_own_reference_site_ids=len(chosen),outside_own_reference_site_ids=len(outside),unmatched_reference_site_ids=len(unmatched))
    assert expected==r['counts']==cohort['counts']==summary['counts']
    transform=Transformer.from_crs(32636,4326,always_xy=True)
    with np.load(OUT/'observations.npz') as z:
        assert len(z['fid'])==565 and len(set(z['site_id'].tolist()))==565
        for i,row in enumerate(chosen):
            p=unpack(row['geom']);lon,lat=transform.transform(p.x,p.y)
            for key,value in [('fid',row['fid']),('site_id',row['SiteID']),('east',p.x),('north',p.y),('lon',lon),('lat',lat)]:assert z[key][i]==value
            assert cohort['source_names'][z['source_code'][i]]==row['Source']
    with (OUT/'survey_support.csv').open() as f:support=list(csv.DictReader(f))
    for row in support:
        name=row['reference'];polys=refs[name]
        expected_area=area(polys[0]) if len(polys)==1 else union_all(polys).area
        assert math.isclose(float(row['union_area_sqkm']),expected_area/1e6,rel_tol=2e-11,abs_tol=1e-8)
        assert int(row['inside_own_polygon'])==sum(r['Source']==name for r in chosen)
        assert int(row['outside_own_polygon'])==sum(r['Source']==name for r in outside)
        assert row['walked_area_certified']==row['detection_probability_known']=='False'
    # Classify serialization separately from actual/unresolved data differences.
    with (OUT/'cross_format_differences.csv').open() as f:diff=list(csv.DictReader(f))
    classified=Counter();substantive=Counter()
    for row in diff:
        a,b=row['csv_value'],row['gpkg_value']
        if semantic(a)==semantic(b):kind='representation_only'
        else:kind='data_or_unresolved_representation';substantive[row['field']]+=1
        classified[kind]+=1
    assert len(diff)==summary['csv_gpkg_discrepancies']
    for flag in ['uniform_detection_qualified','walked_footprint_qualified','absolute_count_or_population_benchmark_ready','phase_specific_area_benchmark_ready','model_scores_performed']:assert summary[flag] is False
    tree=ast.parse((ROOT/'scripts/qualify_roman_regional_sources.py').read_text());modules=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):modules.extend(x.name.split('.')[0] for x in node.names)
        if isinstance(node,ast.ImportFrom):modules.append(node.module.split('.')[0])
    assert not ({'rotclimate','polity','harvest','land','population'}&set(modules))
    for name,digest in r['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    result=dict(status='passed_independent_period_identity_scalar_polygon_and_format_review',reviewer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),source_phase_rows_checked=len(sites),polygon_rows_checked=len(polygons),own_reference_membership_checks=checks,
        selected_unique_sites=len(chosen),observation_values_checked=7*len(chosen),duplicate_phase_rows_collapsed=collapse,
        geometry_area_review='Independent compensated shoelace; union library reused only if reference has multiple polygons.',
        point_membership_review='Separate scalar ray crossing with hole/boundary handling; no producer coverage call.',
        cross_format_difference_classes=dict(classified),substantive_or_unresolved_fields=dict(substantive),
        fresh_outputs_byte_exact=True,model_imports_absent=True,model_scores_performed=False,main_atlas_changed=False,new_fit=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
