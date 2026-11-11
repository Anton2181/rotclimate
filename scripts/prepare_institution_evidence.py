"""Audit hypothetical atlas providers and prepare dated Earth institution schemas.

No model scores or fitted institutions. Raw third-party workbook remains private.
"""
import collections
import gzip
import json
from pathlib import Path
import sys
import importlib.metadata
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity.institution_evidence import value_evidence,time_evidence

CONFIG=ROOT/'calibration/institution_evidence_20261111'
OUT=ROOT/'output/institution_evidence_20261111'
TARGETS=('professional_military_officer','professional_soldier','professional_priesthood','full_time_bureaucrat',
    'specialized_government_building','administrative_level','religious_level','military_level',
    'settlement_hierarchy','population_of_the_largest_settlement')


def source_rows(sheet):
    rows=sheet.iter_rows(values_only=True);headers=next(rows)
    if len(headers)!=len(set(headers)):raise ValueError('Repeated source headers')
    return headers,[dict(zip(headers,r)) for r in rows if any(v is not None for v in r)]


def main():
    OUT.mkdir(parents=True,exist_ok=True);manifest=json.loads((CONFIG/'sources.json').read_text());cache=ROOT/manifest['cache']
    for name,record in manifest['files'].items():
        if sha(cache/name)!=record['sha256']:raise ValueError('Changed institution source: '+name)
    text=' '.join((cache/'codebook.txt').read_text().split())
    for anchor in ['Do not simply copy settlement hierarchy data here.',
        'Code this absent if administrative duties are performed by generalists such as chiefs',
        'Note that when we code [absent; present] this code is not simply']:
        if anchor not in text:raise ValueError('Missing documented institution semantics')
    book=openpyxl.load_workbook(cache/'Polaris2026.xlsx',read_only=True,data_only=False)
    sheets={};tables={}
    for sheet in book:
        headers,rows=source_rows(sheet);tables[sheet.title]=rows
        sheets[sheet.title]=dict(headers=list(headers),records=len(rows),reported_rows=sheet.max_row,
            formula_cells=sum(isinstance(v,str) and v.startswith('=') for r in rows for v in r.values()))
    book.close()
    metadata={r['variable_name']:r for r in tables['Variables']}
    polities=collections.defaultdict(list)
    for row in tables['Polities']:polities[(row['polity_number'],row['polity_id'])].append(row)
    data=[r for r in tables['Social complexity'] if r['variable_name'] in TARGETS]
    observations=collections.defaultdict(list)
    for row in data:observations[row['variable_name']].append(row)
    variables={}
    for variable in TARGETS:
        rows=observations[variable];states=collections.Counter();times=collections.Counter();raw_codes=collections.Counter()
        flags={'is_disputed':collections.Counter(),'is_uncertain':collections.Counter()};keys=collections.Counter();payloads=collections.defaultdict(set)
        compatible=set();all_polities=set();missing_joins=outside=zero_year=negative_numeric=0
        for r in rows:
            evidence=value_evidence(r['value_from'],r['value_to']);time=time_evidence(r['year_from'],r['year_to'])
            states[evidence['state']]+=1;times[time['state']]+=1
            if isinstance(r['value_from'],str):raw_codes[r['value_from']]+=1
            for flag in flags:flags[flag][json.dumps(r[flag])]+=1
            identity=(r['polity_number'],r['polity_id']);all_polities.add(identity)
            if identity not in polities:missing_joins+=1
            if time['compatible_with_positive_year200']:compatible.add(identity)
            if time['zero_year_present']:zero_year+=1
            if evidence['state'] in ['numeric_point','numeric_interval'] and r['value_from']<0:negative_numeric+=1
            if len(polities.get(identity,[]))==1 and time['state']=='ordered_exported_interval':
                p=polities[identity][0];pt=time_evidence(p['start_year'],p['end_year'])
                if pt['state']=='ordered_exported_interval' and (r['year_from']<p['start_year'] or r['year_to']>p['end_year']):outside+=1
            key=identity+(variable,r['year_from'],r['year_to']);keys[key]+=1
            payloads[key].add(json.dumps([r['value_from'],r['value_to'],r['is_disputed'],r['is_uncertain']]))
        variables[variable]=dict(records=len(rows),represented_polities=len(all_polities),value_states=dict(sorted(states.items())),
            raw_code_counts=dict(sorted(raw_codes.items())),time_states=dict(sorted(times.items())),flags={k:dict(v) for k,v in flags.items()},
            exported_intervals_covering_positive_year200_polities=len(compatible),missing_polity_join_records=missing_joins,
            intervals_outside_exported_parent_span=outside,records_with_zero_year=zero_year,negative_numeric_intervals=negative_numeric,
            repeated_observation_keys=sum(v>1 for v in keys.values()),additional_records_in_repeated_keys=sum(v-1 for v in keys.values() if v>1),
            repeated_keys_with_different_values_or_flags=sum(len(v)>1 for v in payloads.values()),
            metadata=metadata.get(variable),rows_kept_separate=True)
    write(OUT/'earth_preparation.json',dict(status='prepared_institution_schema_no_model_scores',adopt=False,
        plan_sha256=sha(CONFIG/'plan.json'),sources_sha256=sha(CONFIG/'sources.json'),producer_sha256=sha(Path(__file__)),
        evidence_module_sha256=sha(ROOT/'polity/institution_evidence.py'),openpyxl_version=importlib.metadata.version('openpyxl'),
        sheets=sheets,polity_records=len(tables['Polities']),unique_polity_keys=len(polities),
        repeated_polity_keys=sum(len(v)>1 for v in polities.values()),variables=variables,
        unmapped_codes_are_review_items=True,legacy_alias_crossrelease_join_allowed=False,
        metadata_alias_review=dict(variable='professional_military_officer',legacy_equinox_alias=metadata['professional_military_officer']['equinox_variable_name'],
            action='Do not join through legacy alias;retain canonical variable/API names,review source mapping.'),
        model_prediction_matching=False,model_scores_computed=False,independent_or_sealed=False,
        limits='Polity-level presence/hierarchy is not per-site staff/hours. Interval compatibility is as exported,not harmonized BCE/zero chronology or dated functions. Missing values,unmapped codes and duplicate keys are preserved;no midpoint,imputation or silent merge. Raw workbook stays private.'))
    atlas={};sources={}
    for climate in ['raw','corrected']:
        folder=ROOT/'atlases/earth_fit/data'/('corrected' if climate=='corrected' else '')
        path=folder/'settled_reach.json.gz';registry=folder/'coverage_sources.json'
        for p in [path,registry]:sources[str(p.relative_to(ROOT))]=sha(p)
        model=json.loads(gzip.decompress(path.read_bytes()));records=json.loads(registry.read_text())['records']
        byid={r['id']:r for r in records};sites=model['sites'];case=next(c for c in model['cases'] if c['id']=='joint365')
        actors=[r['name'] for r in model['actors']];rows={name:dict(sites=0,marked_sites=0,generated_sites=0,legacy_staff=0.,
            staff_at_marked_sites=0.,staff_at_generated_sites=0.,legacy_residents=0.,affiliation_bases=collections.Counter(),mapped_symbol_channels=collections.Counter()) for name in actors+['unresolved']}
        for site,civil,staff in zip(sites,case['civilian_people'],case['institutional_people']):
            if site['actor_index']>=0 and actors[site['actor_index']]!=site['actor']:raise ValueError('Actor index disagrees with name')
            name=site['actor'] or 'unresolved';r=rows[name];r['sites']+=1;r['marked_sites' if site['marked'] else 'generated_sites']+=1
            r['legacy_staff']+=staff;r['staff_at_marked_sites' if site['marked'] else 'staff_at_generated_sites']+=staff
            r['legacy_residents']+=civil+staff;r['affiliation_bases'][site['affiliation_basis']]+=1
            for marker in site['evidence_ids']:
                if marker not in byid:raise ValueError('Missing source marker')
                r['mapped_symbol_channels'][byid[marker]['kind']]+=1
        total_staff=sum(case['institutional_people']);generated_staff=sum(r['staff_at_generated_sites'] for r in rows.values())
        atlas[climate]=dict(sites=len(sites),marked_sites=sum(s['marked'] for s in sites),unresolved_affiliations=sum(s['actor_index']<0 for s in sites),
            actors=rows,legacy_staff=total_staff,staff_at_generated_sites=generated_staff,
            fraction_of_staff_at_generated_sites=generated_staff/total_staff if total_staff else None,
            observed_staff_quantities_available=False,provider_professionalization_known=False,
            mapped_context_channels_are_not_operational_or_dated_roles=True)
    write(OUT/'provider_audit.json',dict(status='legacy_provider_assumption_audit',adopt=False,plan_sha256=sha(CONFIG/'plan.json'),
        producer_sha256=sha(Path(__file__)),sources=sources,atlases=atlas,
        physical_population_food_staff_control_changed=False,
        gaps=['Legacy100-person institutional cohorts at eligible claimed/generated settlements are hypotheses,not measured provider staff.',
            'Binary reach has no quantified patrol-hour commitment;collection freight has no explicit crew/draft-hour budget.',
            'Professional specialization,provider dates,actual staffing and service-hour demand are not inferred from fortified towns,monasteries or painted claims.',
            'Missing affiliation/markers is not missing governance;all18actors and unresolved remain visible,includingtribal/nonstate possibilities.']))
    print('Prepared',len(data),'institution/hierarchy records;no model predictions or scores.')
    for climate,a in atlas.items():print(climate,a['sites'],'sites;',round(100*a['fraction_of_staff_at_generated_sites'],2),'% legacy staff at generated hypotheses.')


if __name__=='__main__':main()
