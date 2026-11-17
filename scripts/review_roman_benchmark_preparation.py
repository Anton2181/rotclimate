"""Independent raw-table joins, date masks, basis and province coverage checks."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/roman_benchmark_20261117'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())
def number(v):
    try:return float(v)
    except ValueError:return None


def eligible(c,y):
    start,end=number(c['Start Date']),number(c['End Date'])
    return start is not None and start<=y and (end is None or end>=y)


def main():
    assert not (OUT/'preparation_review.json').exists(),'Preserve checked preparation'
    r=read(OUT/'preparation.json')
    for n,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/n)==digest,n
    for n,digest in r['files_sha256'].items():assert sha(OUT/n)==digest,n
    for mapping in r['historical_publication_remappings'].values():assert sha(ROOT/mapping['archive'])==mapping['historical_sha256']
    cache=ROOT/'data/cache/roman_city_source_recovery_20261113'
    cities=list(csv.DictReader(io.StringIO((cache/'cities.csv').read_bytes().decode('cp1252'))))
    areas={a['Primary Key']:a for a in csv.DictReader(io.StringIO((cache/'areas.csv').read_bytes().decode('utf-8-sig')))}
    with np.load(OUT/'design.npz') as z:d=dict(z)
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:old=dict(z)
    for key,value in old.items():np.testing.assert_array_equal(value,d[key])
    selected=[cities[int(i)] for i in d['source_indices']]
    for i,c in enumerate(selected):
        a=areas[c['Primary Key']];raw=float(a['Area']);expected=raw
        assert raw not in [20.,30.] and eligible(c,150)
        if c['Province'] in ['Achaea','Macedonia','Epirus'] and a['Estimate Basis'].startswith('Walls'):
            expected/=3 if raw>=100 else 2
        assert math.isclose(expected,float(d['area'][i]),rel_tol=1e-15,abs_tol=1e-12)
        assert d['strict'][i]==(a['Estimate Basis']=='Inhabited area')
        assert d['year200'][i]==eligible(c,200)
        assert d['end_known'][i]==(number(c['End Date']) is not None)
        assert d['lat'][i]==float(c['Latitude (Y)']) and d['lon'][i]==float(c['Longitude (X)'])
        assert r['province_names'][int(d['province'][i])]==c['Province']
        assert d['fold'][i]==hashlib.sha256(c['Province'].encode()).digest()[0]%4
    with (OUT/'coverage.csv').open() as f:coverage=list(csv.DictReader(f))
    assert len(coverage)==len(set(c['Province'] for c in cities))
    values_checked=0
    for row in coverage:
        name=row['province'];members=[c for c in cities if c['Province']==name];at200=[c for c in members if eligible(c,200)]
        positive=[c for c in at200 if c['Primary Key'] in areas and number(areas[c['Primary Key']]['Area']) is not None and number(areas[c['Primary Key']]['Area'])>0]
        positions=[i for i,c in enumerate(selected) if c['Province']==name]
        targets=[i for i in positions if eligible(selected[i],200)]
        expected=dict(catalogue_records=len(members),occupation_AD150_compatible=sum(eligible(c,150) for c in members),occupation_AD200_compatible=len(at200),
            AD200_unknown_end=sum(number(c['End Date']) is None for c in at200),AD200_known_end=sum(number(c['End Date']) is not None for c in at200),
            AD200_positive_area_records=len(positive),AD200_exact20_or30_area_records=sum(float(areas[c['Primary Key']]['Area']) in [20.,30.] for c in positive),
            AD200_exact_inhabited_basis_records=sum(areas[c['Primary Key']]['Estimate Basis']=='Inhabited area' for c in positive),
            inherited_model_records=len(positions),AD200_model_targets=len(targets),AD200_strict_targets=sum(d['strict'][i] for i in targets),
            AD200_measured_extent_phases_certified=0,population_measurements_qualified=0)
        for key,value in expected.items():assert int(row[key])==value,(name,key);values_checked+=1
        assert row['survey_footprint_qualified']=='False'
    ready=read(OUT/'readiness.json')
    expected=dict(all664=len(selected),AD200_compatible=sum(eligible(c,200) for c in selected),AD200_strict=sum(eligible(c,200) and d['strict'][i] for i,c in enumerate(selected)),
                  AD200_known_end=sum(eligible(c,200) and number(c['End Date']) is not None for c in selected))
    expected={key:int(value) for key,value in expected.items()}
    assert ready['targets']==expected and r['targets']==expected
    assert ready['extent_phase_certifications']==ready['independent_survey_footprints']==ready['observed_city_populations']==0
    assert not ready['AD200_demographic_validation_ready'] and not ready['settlement_count_or_location_forecast_ready']
    receipt=dict(status='passed_independent_source_dates_basis_masks_and_coverage',reviewer_sha256=sha(Path(__file__)),
                 preparation_sha256=sha(OUT/'preparation.json'),source_rows=664,province_aggregate_values_checked=values_checked,
                 targets=expected,geometry_from_qualified_legacy_design=True,new_scores=False,new_fit=False,new_blind_test=False,adopt=False)
    (OUT/'preparation_review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(expected))


if __name__=='__main__':main()
