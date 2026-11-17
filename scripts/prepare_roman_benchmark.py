"""Freeze the AD200 target masks and catalogue coverage before new scores."""
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_hierarchy as SH

OUT=ROOT/'output/roman_benchmark_20261117'
PLAN=ROOT/'calibration/roman_benchmark_20261117/plan.json'
DESIGN=ROOT/'output/urban_measurement_pilot_20261116'
HIERARCHY=ROOT/'output/urban_hierarchy_refresh_20261116'
R5=ROOT/'output/settlement_provisional_release5_20261117'
CACHE=ROOT/'data/cache/roman_city_source_recovery_20261113'
BACKGROUND=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared/low_central.npz'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def table(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def date(value):
    try:return float(value)
    except ValueError:return None


def compatible(city,year):
    start,end=date(city['Start Date']),date(city['End Date'])
    return start is not None and start<=year and (end is None or end>=year)


def parents():
    """Preserve old source receipts and the actual current publication separately."""
    allowed=read(R5/'baseline.json')['archived_live_sha256'];protected={};remaps={};sources={}
    for folder,name in [(DESIGN,'eligibility.json'),(HIERARCHY,'results.json')]:
        path=folder/name;r=read(path);sources[str(path.relative_to(ROOT))]=sha(path)
        for section in ['sources_sha256','producers','protected_sha256']:
            for n,digest in r.get(section,{}).items():
                actual=sha(ROOT/n)
                if actual!=digest:
                    assert allowed.get(n)==digest,n
                    archived=R5/'baseline'/n;assert sha(archived)==digest,n
                    remaps[n]=dict(historical_sha256=digest,archive=str(archived.relative_to(ROOT)),current_sha256=actual)
                protected[n]=actual
        for n,digest in r['files_sha256'].items():assert sha(folder/n)==digest,n
    for folder in [DESIGN,HIERARCHY]:
        review=read(folder/'review.json');assert review['status']=='passed'
        assert review['results_sha256']==sha(folder/'results.json')
        for path in [folder/'results.json',folder/'review.json']:sources[str(path.relative_to(ROOT))]=sha(path)
    for n,digest in read(R5/'publication.json')['files_sha256'].items():
        assert sha(ROOT/n)==digest,n;protected[n]=digest
    for n in allowed:protected[n]=sha(ROOT/n)
    return sources,protected,remaps


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (out/'preparation.json').exists(),'Preserve frozen target preparation'
    sources,protected,remaps=parents()
    cities=list(csv.DictReader(io.StringIO((CACHE/'cities.csv').read_bytes().decode('cp1252'))))
    areas={r['Primary Key']:r for r in csv.DictReader(io.StringIO((CACHE/'areas.csv').read_bytes().decode('utf-8-sig')))}
    bykey={c['Primary Key']:i for i,c in enumerate(cities)}
    rows,lat,lon,capital=SH.cohort()
    with np.load(DESIGN/'design.npz') as z:d=dict(z)
    with np.load(HIERARCHY/'model.npz') as z:old=dict(z)
    np.testing.assert_array_equal([r['area'] for r in rows],d['area'])
    np.testing.assert_array_equal(capital,d['capital']);np.testing.assert_array_equal(capital,old['capital'])
    np.testing.assert_array_equal(d['fold'],old['fold'])
    indices=np.array([bykey[r['key']] for r in rows],dtype=np.int64)
    selected=[cities[i] for i in indices];year200=np.array([compatible(c,200) for c in selected]);endknown=np.array([date(c['End Date']) is not None for c in selected])
    assert len(rows)==664 and len(set(indices.tolist()))==664
    assert all(compatible(c,150) for c in selected)
    assert np.array_equal(d['strict'],[areas[c['Primary Key']]['Estimate Basis']=='Inhabited area' for c in selected])
    names=sorted(set(r['province'] for r in rows));assert np.array_equal(d['province'],[names.index(r['province']) for r in rows])
    coverage=[]
    for name in sorted(set(c['Province'] for c in cities)):
        source=[c for c in cities if c['Province']==name];at150=[c for c in source if compatible(c,150)];at200=[c for c in source if compatible(c,200)]
        positive=[c for c in at200 if c['Primary Key'] in areas and date(areas[c['Primary Key']]['Area']) is not None and date(areas[c['Primary Key']]['Area'])>0]
        defaults=[c for c in positive if date(areas[c['Primary Key']]['Area']) in [20.,30.]]
        inherited=np.array([r['province']==name for r in rows]);use=inherited&year200
        coverage.append(dict(province=name,catalogue_records=len(source),occupation_AD150_compatible=len(at150),occupation_AD200_compatible=len(at200),
            AD200_unknown_end=sum(date(c['End Date']) is None for c in at200),AD200_known_end=sum(date(c['End Date']) is not None for c in at200),
            AD200_positive_area_records=len(positive),AD200_exact20_or30_area_records=len(defaults),
            AD200_exact_inhabited_basis_records=sum(areas[c['Primary Key']]['Estimate Basis']=='Inhabited area' for c in positive),
            inherited_model_records=int(inherited.sum()),AD200_model_targets=int(use.sum()),AD200_strict_targets=int((use&d['strict']).sum()),
            AD200_measured_extent_phases_certified=0,survey_footprint_qualified=False,population_measurements_qualified=0))
    out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'design.npz',**d,source_indices=indices,lat=lat,lon=lon,year200=year200,end_known=endknown,centre=old['centre'])
    table(out/'coverage.csv',coverage)
    readiness=dict(occupation_interval_available=True,city_catalogue_epoch=150,benchmark_target_year=200,
        city_occupation_does_not_date_extent=True,extent_phase_certifications=0,independent_survey_footprints=0,
        observed_city_populations=0,blind_or_independent_validation=False,conditional_extent_comparison_ready=True,
        settlement_count_or_location_forecast_ready=False,AD200_demographic_validation_ready=False,
        no_new_source_pool=True,training_cohort_unchanged=True,
        inherited_area_rules='Exact20/30 exclusion and Greek wall corrections preserved; not requalified as AD200 measurements.',
        targets=dict(all664=len(rows),AD200_compatible=int(year200.sum()),AD200_strict=int((year200&d['strict']).sum()),AD200_known_end=int((year200&endknown).sum())),
        survey_coverage_note='Catalogue area availability is not surveyed-land completeness or a missing-town detection rate.')
    write(out/'readiness.json',readiness)
    for path in [Path(__file__),PLAN,CACHE/'cities.csv',CACHE/'areas.csv',DESIGN/'design.npz',HIERARCHY/'model.npz',BACKGROUND,ROOT/'scripts/settlement_hierarchy.py',ROOT/'scripts/settlement_release2_earth.py']:
        sources[str(path.relative_to(ROOT))]=sha(path)
    for n,digest in protected.items():assert sha(ROOT/n)==digest,n
    write(out/'preparation.json',dict(status='frozen_evidence_targets_before_new_baseline_scores',sources_sha256=sources,protected_sha256=protected,
        historical_publication_remappings=remaps,files_sha256={n:sha(out/n) for n in ['design.npz','coverage.csv','readiness.json']},
        province_names=names,rows=664,targets=readiness['targets'],new_scores=False,new_fit=False,new_blind_test=False,adopt=False,main_atlas_changed=False))
    print(json.dumps(readiness['targets']),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=OUT);main(parser.parse_args().out)
