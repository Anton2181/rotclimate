"""Prepare primary 2016 field-survey tables without environmental/model lookups."""
import collections
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,sha,write
from audit_vidarbha_preparation import number
from polity.survey_observations import yes_no_evidence,north_east_evidence

CONFIG=ROOT/'calibration/vidarbha_survey_20261111'
CACHE=ROOT/'data/cache/vidarbha_survey_2016'
OUT=ROOT/'output/vidarbha_survey_20261111'
KINDS=['AllSites','Settlements','Megaliths','Religious','Others']
PHASES=['IA','EEH','EH-S','LEH-V','EM','LM']


def load_tables():
    result={};stats={};members={}
    with zipfile.ZipFile(CACHE/'Vidarbha_2016Survey_SiteRecords.zip') as archive:
        selected=[i for i in archive.infolist() if i.filename.lower().endswith('.csv') and not i.filename.startswith('__MACOSX/')]
        if len(selected)!=5 or sum(i.file_size for i in selected)>32*1024*1024:raise ValueError('Unexpected record archive')
        for kind in KINDS:
            name='Vidarbha_2016Survey_'+kind+'.csv';matches=[i for i in selected if Path(i.filename).name==name]
            if len(matches)!=1:raise ValueError('Missing/ambiguous declared CSV: '+kind)
            info=matches[0];body=archive.read(info)
            required=['SiteCode']+(['North','East','SiteType','SurveyZone']+PHASES if kind=='AllSites' else [])
            rows,metadata=table(body,required,primary_key='SiteCode')
            result[kind]=rows;stats[kind]=metadata
            import hashlib
            members[kind]=dict(path=info.filename,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
    return result,stats,members


def main():
    OUT.mkdir(parents=True,exist_ok=True);snapshot=CACHE/'source_snapshot.json';source=json.loads(snapshot.read_text())
    for item in source['files']:
        if sha(CACHE/item['name'])!=item['sha256']:raise ValueError('Changed field-survey source')
    data,stats,members=load_tables();master=data['AllSites'];byid=collections.defaultdict(list)
    for row in master:
        if row['sitecode']:byid[row['sitecode']].append(row)
    types=collections.Counter(r['sitetype'] for r in master);zones=collections.Counter(r['surveyzone'] for r in master)
    coords=collections.Counter();phases={}
    for r in master:
        for k,v in north_east_evidence(r['north'],r['east']).items():coords[k]+=int(v)
    for field in PHASES:
        key=field.lower().replace('-','')
        phases[field]=dict(raw_values=dict(collections.Counter(r.get(key,'') for r in master)),
            evidence_states=dict(collections.Counter(yes_no_evidence(r.get(key))['state'] for r in master)))
    joins={};settlements=[]
    for kind in KINDS[1:]:
        rows=data[kind];keys=[r['sitecode'] for r in rows]
        matches=[byid.get(k,[]) for k in keys]
        joins[kind]=dict(records=len(rows),exact_single_master_matches=sum(len(m)==1 for m in matches),
            missing_master_records=sum(not m for m in matches),ambiguous_master_records=sum(len(m)>1 for m in matches),
            master_type_counts=dict(collections.Counter(m[0]['sitetype'] for m in matches if len(m)==1)),
            coordinate_valid_records=sum(len(m)==1 and north_east_evidence(m[0]['north'],m[0]['east'])['documented_latitude_longitude_valid'] for m in matches),
            inside_declared_region_records=sum(len(m)==1 and north_east_evidence(m[0]['north'],m[0]['east'])['inside_declared_vidarbha_envelope'] for m in matches))
        if kind=='Settlements':settlements=[m[0] for m in matches if len(m)==1]
    settlement_phases={field:dict(raw_values=dict(collections.Counter(r.get(field.lower().replace('-',''),'') for r in settlements)),
        evidence_states=dict(collections.Counter(yes_no_evidence(r.get(field.lower().replace('-','')))['state'] for r in settlements))) for field in PHASES}
    old=ROOT/'data/cache/vidarbha_2020';legacy_master,_=table((old/'Vidarbha_SiteMasterList.csv').read_bytes(),['SiteCode'],primary_key='SiteCode')
    legacy_sites,_=table((old/'Vidarbha_SettlementSites.csv').read_bytes(),['SiteCode'],primary_key='SiteCode')
    old_ids={r['sitecode'] for r in legacy_master};site_ids={r['sitecode'] for r in legacy_sites}
    overlap=dict(old_master_records=len(legacy_master),old_census_settlement_records=len(legacy_sites),
        shared_master_IDs=len(set(byid)&old_ids),shared_census_settlement_IDs=len(set(byid)&site_ids),
        old_readme_coordinate_pairs_equal_to_field=0,old_reversed_documentation_pairs_equal_to_field=0,
        no_old_coordinates_reassigned=True,old_source_failure_not_rewritten=True)
    for row in legacy_master:
        match=byid.get(row['sitecode'],[])
        if len(match)!=1:continue
        a,b=number(row.get('xcoord')),number(row.get('ycoord'));lat,lon=number(match[0]['north']),number(match[0]['east'])
        if None not in (a,b,lat,lon):
            overlap['old_readme_coordinate_pairs_equal_to_field']+=int((a,b)==(lat,lon))
            overlap['old_reversed_documentation_pairs_equal_to_field']+=int((b,a)==(lat,lon))
    quality=dict(master_IDs_unique=stats['AllSites']['duplicate_primary_key_rows']==0 and stats['AllSites']['nonempty_primary_keys']==len(master),
        all_child_rows_have_single_parent=all(v['missing_master_records']==v['ambiguous_master_records']==0 for v in joins.values()),
        all_documented_coordinates_global_valid=coords['documented_latitude_longitude_valid']==len(master),
        all_coordinates_inside_declared_region=coords['inside_declared_vidarbha_envelope']==len(master),
        no_malformed_rows=all(s['malformed_rows']==0 for s in stats.values()))
    quality['settlement_subset_joins_coordinates_types_valid']=(len(settlements)==len(data['Settlements']) and
        all(r['sitetype'].casefold()=='settlement' and north_east_evidence(r['north'],r['east'])['inside_declared_vidarbha_envelope'] for r in settlements)
        and stats['Settlements']['duplicate_primary_key_rows']==0 and stats['Settlements']['nonempty_primary_keys']==len(settlements))
    write(OUT/'preparation.json',dict(status='primary_field_survey_preparation_no_model_scores',adopt=False,
        plan_sha256=sha(CONFIG/'plan.json'),methods_sha256=sha(CONFIG/'methods.json'),source_snapshot_sha256=sha(snapshot),source_snapshot=source,archive_members=members,
        old_source_inputs={str((old/name).relative_to(ROOT)):sha(old/name) for name in ['Vidarbha_SiteMasterList.csv','Vidarbha_SettlementSites.csv']},
        producer_sha256=sha(Path(__file__)),module_sha256=sha(ROOT/'polity/survey_observations.py'),
        table_reader_sha256=sha(ROOT/'scripts/audit_roman_rural_preparation.py'),csv_reader_sha256=sha(ROOT/'scripts/audit_vidarbha_preparation.py'),
        tables=stats,site_types=dict(types),survey_zones=dict(zones),coordinate_checks=dict(coords),phase_flags=phases,
        child_joins=joins,matched_settlement_phase_flags=settlement_phases,old_source_overlap=overlap,preparation_checks=quality,
        environmental_or_model_lookup_performed=False,model_scores_computed=False,raw_rows_redistributed=False,
        limits='Primary targeted survey,not a city census;about7.5%frame area covered. Type/phase/coverage/cell-resolution need a frozen protocol before comparisons. EH-S is broad Satavahana-compatible context,not exactAD200occupation. Shared ID strings across source versions are not confirmed shared physical sites;no cross-source joins or coordinate transfers. Old exposed coordinates remain exposed;not blind by newDOI alone.'))
    print('All-site records',len(master),'matched settlement records',len(settlements),flush=True)
    print('Types',dict(types),'zones',dict(zones),flush=True)
    print('Checks',quality,'overlap',overlap,flush=True)
    print('Settlement phase states',{k:v['evidence_states'] for k,v in settlement_phases.items()},flush=True)


if __name__=='__main__':main()
