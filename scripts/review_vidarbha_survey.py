"""Independent CSV reconstruction of the primary field-survey preparation."""
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from prepare_vidarbha_survey import CACHE,CONFIG,OUT,KINDS,PHASES


def main():
    result=json.loads((OUT/'preparation.json').read_text());snapshot=CACHE/'source_snapshot.json'
    for key,path in {'plan_sha256':CONFIG/'plan.json','methods_sha256':CONFIG/'methods.json','source_snapshot_sha256':snapshot,
        'producer_sha256':ROOT/'scripts/prepare_vidarbha_survey.py','module_sha256':ROOT/'polity/survey_observations.py',
        'table_reader_sha256':ROOT/'scripts/audit_roman_rural_preparation.py','csv_reader_sha256':ROOT/'scripts/audit_vidarbha_preparation.py'}.items():assert result[key]==sha(path)
    for f in result['source_snapshot']['files']:
        body=(CACHE/f['name']).read_bytes();assert hashlib.sha256(body).hexdigest()==f['sha256']
        algorithm,digest=f['source_checksum'].split(':');assert hashlib.new(algorithm,body).hexdigest()==digest
    tables={};normalize=lambda x:re.sub('[^a-z0-9]','',x.lower())
    with zipfile.ZipFile(CACHE/'Vidarbha_2016Survey_SiteRecords.zip') as archive:
        for kind in KINDS:
            meta=result['archive_members'][kind];body=archive.read(meta['path']);assert hashlib.sha256(body).hexdigest()==meta['sha256']
            spec=result['tables'][kind];raw=csv.reader(io.StringIO(body.decode(spec['format']['encoding']),newline=''),dialect='excel');headers=next(raw)
            values=[r for r in raw if any(v.strip() for v in r)]
            rows=[{normalize(h):r[i].strip() if i<len(r) else '' for i,h in enumerate(headers) if h.strip()} for r in values]
            assert len(rows)==spec['rows'];keys=[r['sitecode'] for r in rows]
            assert len(set(keys)-{''})==spec['unique_primary_keys'] and sum(bool(k) for k in keys)-len(set(keys)-{''})==spec['duplicate_primary_key_rows']
            malformed=sum(any(v.strip() for v in r[len(headers):]) or any(v.strip() for v,h in zip(r,headers) if not h.strip()) for r in values)
            assert malformed==spec['malformed_rows'];tables[kind]=rows
    parents=collections.defaultdict(list)
    for r in tables['AllSites']:
        if r['sitecode']:parents[r['sitecode']].append(r)
    assert result['site_types']==dict(collections.Counter(r['sitetype'] for r in tables['AllSites']))
    assert result['survey_zones']==dict(collections.Counter(r['surveyzone'] for r in tables['AllSites']))
    numeric=valid=regional=0
    for r in tables['AllSites']:
        try:a,b=float(r['north']),float(r['east'])
        except ValueError:continue
        if not math.isfinite(a) or not math.isfinite(b):continue
        numeric+=1;valid+=-90<=a<=90 and -180<=b<=180
        regional+=18.7566<=a<=21.735785 and 75.295495<=b<=80.950312
    assert result['coordinate_checks']==dict(numeric_pair=numeric,documented_latitude_longitude_valid=valid,inside_declared_vidarbha_envelope=regional,coordinate_swap_applied=0)
    matched=[]
    for kind in KINDS[1:]:
        matches=[parents.get(r['sitecode'],[]) for r in tables[kind]];published=result['child_joins'][kind]
        assert published['records']==len(matches) and published['exact_single_master_matches']==sum(len(m)==1 for m in matches)
        assert published['missing_master_records']==sum(not m for m in matches) and published['ambiguous_master_records']==sum(len(m)>1 for m in matches)
        assert published['master_type_counts']==dict(collections.Counter(m[0]['sitetype'] for m in matches if len(m)==1))
        if kind=='Settlements':matched=[m[0] for m in matches if len(m)==1]
    checks=0
    for rows,key in [(tables['AllSites'],'phase_flags'),(matched,'matched_settlement_phase_flags')]:
        for phase in PHASES:
            field=normalize(phase);raw=collections.Counter(r[field] for r in rows);states=collections.Counter()
            for value,n in raw.items():states[{'yes':'recorded_yes','no':'recorded_no'}.get(value.casefold(),'missing' if not value else 'unresolved')]+=n
            assert result[key][phase]==dict(raw_values=dict(raw),evidence_states=dict(states));checks+=len(rows)
    old_path='output/vidarbha_preparation_20261110/audit.json'
    assert subprocess.check_output(['git','show','2ef81095:'+old_path],cwd=ROOT)==(ROOT/old_path).read_bytes()
    old_tables={}
    for path,digest in result['old_source_inputs'].items():
        body=(ROOT/path).read_bytes();assert hashlib.sha256(body).hexdigest()==digest
        text=body.decode('utf-8-sig')
        reader=csv.DictReader(io.StringIO(text,newline=''));old_tables[Path(path).name]=[r for r in reader if (r.get('SiteCode') or '').strip()]
    old_master=old_tables['Vidarbha_SiteMasterList.csv'];old_sites=old_tables['Vidarbha_SettlementSites.csv'];overlap=result['old_source_overlap']
    assert overlap['shared_master_IDs']==len(set(parents)&{r['SiteCode'].strip() for r in old_master})
    assert overlap['shared_census_settlement_IDs']==len(set(parents)&{r['SiteCode'].strip() for r in old_sites})
    pairs=reverse_pairs=0
    for r in old_master:
        match=parents.get(r['SiteCode'].strip(),[])
        if len(match)!=1:continue
        try:a,b,lat,lon=float(r['XCoord']),float(r['YCoord']),float(match[0]['north']),float(match[0]['east'])
        except (KeyError,ValueError):continue
        pairs+=(a,b)==(lat,lon);reverse_pairs+=(b,a)==(lat,lon)
    assert overlap['old_readme_coordinate_pairs_equal_to_field']==pairs and overlap['old_reversed_documentation_pairs_equal_to_field']==reverse_pairs
    assert result['preparation_checks']['settlement_subset_joins_coordinates_types_valid']
    assert not result['environmental_or_model_lookup_performed'] and not result['model_scores_computed'] and not result['raw_rows_redistributed']
    write(OUT/'review.json',dict(status='passed',preparation_sha256=sha(OUT/'preparation.json'),reviewer_sha256=sha(Path(__file__)),
        source_tables_checked=5,coordinate_records_checked=len(tables['AllSites']),settlement_joins_checked=len(matched),
        phase_record_cases_checked=checks,old_failed_source_audit_unchanged=True,model_scores_computed=False))
    print('Reviewed5tables,268coordinates,134settlementjoins and',checks,'phase cases;old failed-source audit unchanged.')


if __name__=='__main__':main()
