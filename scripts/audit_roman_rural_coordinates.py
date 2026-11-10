"""Explore CSV axis/grid interpretation against declared official site anchors.

This is schema verification on exposed source data, never a climate/settlement
accuracy score. No whole-source projection, individual coordinates or site map
is published. Every official point in a multipoint entry remains in the test.
"""
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha, table, write

CONFIG = ROOT/'calibration/roman_rural_coordinates_20261110'
CACHE = ROOT/'data/cache/roman_rural_britain_metadata/anchors'
OUT = ROOT/'output/roman_rural_coordinates_20261110'


def national_grid(reference):
    """British National Grid notation -> nominal SW-corner E/N, resolution.

    This decodes notation; it does not transform datums, estimate survey accuracy
    or choose a point within a protected monument's geometry.
    """
    compact = re.sub(r'\s+', '', reference).upper()
    if not re.fullmatch(r'[A-HJ-Z]{2}(?:\d{2}){1,5}', compact):
        raise ValueError('Expected two-letter, equal-axis British grid reference')
    alphabet = 'ABCDEFGHJKLMNOPQRSTUVWXYZ'
    a, b = (alphabet.index(v) for v in compact[:2])
    east = ((a-2) % 5)*5 + b % 5
    north = 19 - (a//5)*5 - b//5
    if not (0 <= east <= 6 and 0 <= north <= 12):
        raise ValueError('Grid square outside British National Grid')
    digits = compact[2:];half = len(digits)//2;resolution = 10**(5-half)
    return (east*100000 + int(digits[:half])*resolution,
            north*100000 + int(digits[half:])*resolution, resolution)


def official_references(body):
    class Fields(HTMLParser):
        def __init__(self):
            super().__init__();self.tag=None;self.chunks=[];self.want=False;self.values=[]
        def handle_starttag(self, tag, attrs):
            if tag in ['dt','dd']:
                self.tag=tag;self.chunks=[]
        def handle_data(self, data):
            if self.tag:self.chunks.append(data)
        def handle_endtag(self, tag):
            if tag==self.tag:
                text=' '.join(''.join(self.chunks).split())
                if tag=='dt':self.want=text.rstrip(':').strip()=='National Grid Reference'
                elif self.want:self.values.append(text);self.want=False
                self.tag=None
    parser=Fields();parser.feed(body)
    values=list(dict.fromkeys(parser.values))
    if len(values)!=1:raise ValueError('Expected one unambiguous official NGR field')
    refs=[r.strip() for r in values[0].split(',')]
    for reference in refs:national_grid(reference)
    return refs


def compare_axes(x, y, references, threshold=1000):
    if not references or not all(math.isfinite(v) for v in [x,y,threshold]) or threshold<=0:
        raise ValueError('Finite source point, positive threshold and references required')
    result={}
    for name,a,b in [('X_easting_Y_northing_metres',x,y),('X_northing_Y_easting_metres',y,x)]:
        distances=[math.hypot(a-e,b-n) for e,n,_ in map(national_grid,references)]
        result[name]=dict(distances_metres=distances,all_references_within_threshold=all(d<=threshold for d in distances))
    return result


def main():
    plan=json.loads((CONFIG/'plan.json').read_text());OUT.mkdir(parents=True,exist_ok=True)
    if sha(CONFIG/'plan_v1.json')!=plan['amendment_before_distance_computation']['previous_plan_sha256']:
        raise ValueError('Changed original coordinate protocol')
    previous=json.loads((OUT/'source_snapshot.json').read_text()) if (OUT/'source_snapshot.json').exists() else None
    expected={s['url']:s['sha256'] for s in previous['files']} if previous else {}
    snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    source=next(v for v in json.loads(snapshot.read_text())['files'] if v['name']=='rrs_core_data.csv')
    path=ROOT/'data/cache/roman_rural_britain_2018/rrs_core_data.csv'
    if sha(path)!=source['sha256']:raise ValueError('Changed source core observations')
    rows,_=table(path.read_bytes(),['ID','SITE_NAME','X_REF_MAP','Y_REF_MAP'])
    distances={};site_passes={};sources=[];resolutions=[]
    for anchor in plan['anchors']:
        selected=[r for r in rows if r['sitename'].strip().casefold()==anchor['source_name'].casefold()]
        if len(selected)!=1:raise ValueError('Ambiguous or missing exact named anchor')
        page=CACHE/(anchor['heritage_list_entry']+'.html')
        url='https://historicengland.org.uk/listing/the-list/list-entry/'+anchor['heritage_list_entry']
        if not page.exists():
            page.parent.mkdir(parents=True,exist_ok=True)
            request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=30) as response:body=response.read()
            page.write_bytes(body)
        if url in expected and sha(page)!=expected[url]:raise ValueError('Changed official anchor page: '+url)
        refs=official_references(page.read_text())
        for reference in refs:resolutions.append(national_grid(reference)[2])
        r=selected[0];result=compare_axes(float(r['xrefmap']),float(r['yrefmap']),refs)
        for candidate,value in result.items():
            distances.setdefault(candidate,[]).extend(value['distances_metres'])
            site_passes.setdefault(candidate,[]).append(value['all_references_within_threshold'])
        sources.append(dict(url=url,
            sha256=sha(page),bytes=page.stat().st_size,official_references=len(refs)))
    write(OUT/'source_snapshot.json',dict(files=sources,raw_pages_redistributed=False,
        checksum_scope='Locally recorded content hashes, not independently published checksums.'))
    # A Mercator Y ordinate has a mathematical latitude independent of UK grid.
    mercator_lat=[math.degrees(math.atan(math.sinh(float(r['yrefmap'])/6378137))) for r in rows]
    summary={}
    for candidate,values in distances.items():
        ordered=sorted(values);length=len(values)
        median=(ordered[(length-1)//2]+ordered[length//2])/2
        summary[candidate]=dict(reference_points=length,min_distance_metres=min(values),
            median_distance_metres=median,max_distance_metres=max(values),
            reference_points_within_1km=sum(v<=1000 for v in values),
            named_sites_all_references_within_1km=sum(site_passes[candidate]))
    operational=all(site_passes['X_easting_Y_northing_metres'])
    result=dict(status='exploratory_coordinate_interpretation_no_model_evaluation',
        plan_sha256=sha(CONFIG/'plan.json'),producer_sha256=sha(Path(__file__)),
        parser_sha256=sha(ROOT/'scripts/audit_vidarbha_preparation.py'),
        table_reader_sha256=sha(ROOT/'scripts/audit_roman_rural_preparation.py'),
        original_source_snapshot_sha256=sha(snapshot),anchor_source_snapshot_sha256=sha(OUT/'source_snapshot.json'),
        anchors=len(plan['anchors']),all_declared_anchors_retained=True,threshold_metres=1000,
        hypotheses=summary,official_NGR_nominal_resolutions_metres=sorted(set(resolutions)),
        EPSG3857_XY=dict(records=len(rows),latitude_min=min(mercator_lat),latitude_max=max(mercator_lat),
            records_in_source_metadata_latitude_envelope=sum(49.74<=v<=55.82 for v in mercator_lat),
            interpretation='Region plausibility rejection only, not full projected coordinate comparison'),
        operational_interpretation='OSGB-compatible X easting / Y northing, metres' if operational else None,
        official_export_CRS_certified=False,whole_source_positional_accuracy_established=False,
        whole_source_projection_performed=False,physical_places_merged=False,
        settlement_climate_model_scored=False,source_target_map_generated=False,production_adopted=False,
        limits='Named-site, exposed schema investigation. Point definitions differ. One-metre notation is not one-metre survey accuracy; all3652 places/coordinates are not independently verified. Thesis reversed axis labels do not override direct official-anchor comparisons; not a blind model test.')
    write(OUT/'audit.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
