"""Independently verify institution preparation and all-actor provider accounting."""
import collections
import gzip
import json
import math
from pathlib import Path
import subprocess
import sys
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from prepare_institution_evidence import OUT,CONFIG,TARGETS


def main():
    earth=json.loads((OUT/'earth_preparation.json').read_text());audit=json.loads((OUT/'provider_audit.json').read_text())
    assert earth['plan_sha256']==audit['plan_sha256']==sha(CONFIG/'plan.json')
    assert earth['sources_sha256']==sha(CONFIG/'sources.json')
    assert earth['producer_sha256']==audit['producer_sha256']==sha(ROOT/'scripts/prepare_institution_evidence.py')
    assert earth['evidence_module_sha256']==sha(ROOT/'polity/institution_evidence.py')
    sources=json.loads((CONFIG/'sources.json').read_text());cache=ROOT/sources['cache']
    for name,record in sources['files'].items():assert sha(cache/name)==record['sha256']
    book=openpyxl.load_workbook(cache/'Polaris2026.xlsx',read_only=True,data_only=False);all_rows={}
    for sheet in book:
        values=iter(sheet.values);headers=next(values);rows=[dict(zip(headers,r)) for r in values if any(v is not None for v in r)];all_rows[sheet.title]=rows
        assert earth['sheets'][sheet.title]['headers']==list(headers) and earth['sheets'][sheet.title]['records']==len(rows)
        assert earth['sheets'][sheet.title]['formula_cells']==sum(isinstance(v,str) and v.startswith('=') for r in rows for v in r.values())
    book.close();polities=collections.Counter((r['polity_number'],r['polity_id']) for r in all_rows['Polities'])
    parent_rows={(r['polity_number'],r['polity_id']):r for r in all_rows['Polities']}
    metadata={r['variable_name']:r for r in all_rows['Variables']}
    assert earth['polity_records']==sum(polities.values()) and earth['unique_polity_keys']==len(polities)
    state_names={'P':'coded_present','A':'coded_absent','IP':'inferred_present','IA':'inferred_absent','SU':'suspected_unknown','U':'expert_unknown'}
    checked=0
    for variable in TARGETS:
        rows=[r for r in all_rows['Social complexity'] if r['variable_name']==variable];record=earth['variables'][variable]
        states=collections.Counter();times=collections.Counter();keys=collections.Counter();payloads=collections.defaultdict(set);codes=collections.Counter();identities=set();compat=set()
        for r in rows:
            a,b=r['value_from'],r['value_to']
            state='unresolved_value_shape'
            if a is None and b is None:state='missing_export_value'
            elif isinstance(a,str) and b is None:state=state_names.get(a,'unresolved_code');codes[a]+=1
            elif all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in [a,b]):
                state='reversed_numeric_bounds' if a>b else 'numeric_point' if a==b else 'numeric_interval'
            states[state]+=1
            start,end=r['year_from'],r['year_to'];valid=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and int(v)==v
            time='missing_time_bounds' if start is None or end is None else 'invalid_time_bounds' if not valid(start) or not valid(end) else 'reversed_time_bounds' if start>end else 'ordered_exported_interval'
            times[time]+=1;identity=(r['polity_number'],r['polity_id']);identities.add(identity)
            if time=='ordered_exported_interval' and start<=200<=end:compat.add(identity)
            key=identity+(variable,start,end);keys[key]+=1;payloads[key].add(json.dumps([a,b,r['is_disputed'],r['is_uncertain']]))
            checked+=1
        assert record['records']==len(rows) and record['represented_polities']==len(identities)
        assert record['metadata']==metadata[variable]
        assert record['value_states']==dict(states) and record['time_states']==dict(times) and record['raw_code_counts']==dict(codes)
        assert record['exported_intervals_covering_positive_year200_polities']==len(compat)
        assert record['missing_polity_join_records']==sum((r['polity_number'],r['polity_id']) not in polities for r in rows)
        assert record['repeated_observation_keys']==sum(v>1 for v in keys.values())
        assert record['additional_records_in_repeated_keys']==sum(v-1 for v in keys.values() if v>1)
        assert record['repeated_keys_with_different_values_or_flags']==sum(len(v)>1 for v in payloads.values())
        for flag,counts in record['flags'].items():assert counts==dict(collections.Counter(json.dumps(r[flag]) for r in rows))
        assert record['records_with_zero_year']==sum(r['year_from']==0 or r['year_to']==0 for r in rows)
        outside=negative=0
        for r in rows:
            p=parent_rows.get((r['polity_number'],r['polity_id']))
            if p and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and int(v)==v for v in [r['year_from'],r['year_to'],p['start_year'],p['end_year']]):
                if r['year_from']<=r['year_to'] and p['start_year']<=p['end_year'] and (r['year_from']<p['start_year'] or r['year_to']>p['end_year']):outside+=1
            a,b=r['value_from'],r['value_to']
            if all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in [a,b]) and a<=b and a<0:negative+=1
        assert record['intervals_outside_exported_parent_span']==outside and record['negative_numeric_intervals']==negative
    assert not earth['model_scores_computed'] and not earth['model_prediction_matching'] and not earth['independent_or_sealed']
    actor_checks=0;source_paths=[]
    for climate,record in audit['atlases'].items():
        folder=ROOT/'atlases/earth_fit/data'/('corrected' if climate=='corrected' else '');p=folder/'settled_reach.json.gz'
        model=json.loads(gzip.decompress(p.read_bytes()));case=next(c for c in model['cases'] if c['id']=='joint365');sites=model['sites']
        registry={r['id']:r for r in json.loads((folder/'coverage_sources.json').read_text())['records']}
        assert record['sites']==len(sites) and record['marked_sites']==sum(s['marked'] for s in sites)
        assert record['unresolved_affiliations']==sum(s['actor_index']<0 for s in sites)
        assert set(record['actors'])=={r['name'] for r in model['actors']}|{'unresolved'}
        for name,row in record['actors'].items():
            indices=[i for i,s in enumerate(sites) if (s['actor'] or 'unresolved')==name]
            assert row['sites']==len(indices) and row['marked_sites']==sum(sites[i]['marked'] for i in indices)
            assert row['generated_sites']==sum(not sites[i]['marked'] for i in indices)
            assert row['legacy_staff']==sum(case['institutional_people'][i] for i in indices)
            assert row['staff_at_marked_sites']==sum(case['institutional_people'][i] for i in indices if sites[i]['marked'])
            assert row['staff_at_generated_sites']==sum(case['institutional_people'][i] for i in indices if not sites[i]['marked'])
            assert math.isclose(row['legacy_residents'],sum(case['civilian_people'][i]+case['institutional_people'][i] for i in indices),rel_tol=1e-12)
            assert row['affiliation_bases']==dict(collections.Counter(sites[i]['affiliation_basis'] for i in indices))
            assert row['mapped_symbol_channels']==dict(collections.Counter(registry[marker]['kind'] for i in indices for marker in sites[i]['evidence_ids']))
            actor_checks+=1
        total=sum(r['legacy_staff'] for r in record['actors'].values());hyp=sum(r['staff_at_generated_sites'] for r in record['actors'].values())
        assert total==record['legacy_staff'] and hyp==record['staff_at_generated_sites']
        assert record['fraction_of_staff_at_generated_sites']==hyp/total
    for path,digest in audit['sources'].items():
        p=ROOT/path;assert sha(p)==digest
        assert subprocess.check_output(['git','show','d27700b2:'+path],cwd=ROOT)==p.read_bytes();source_paths.append(path)
    write(OUT/'review.json',dict(status='passed',earth_preparation_sha256=sha(OUT/'earth_preparation.json'),provider_audit_sha256=sha(OUT/'provider_audit.json'),
        reviewer_sha256=sha(Path(__file__)),sheet_counts_checked=len(all_rows),target_records_checked=checked,
        uncertainty_and_duplicate_summaries_checked=True,actor_cohort_records_checked=actor_checks,
        unchanged_source_atlas_packets=source_paths,baseline='d27700b2',model_scores_computed=False,adopt=False))
    print('Reviewed',checked,'Earth records,',len(all_rows),'sheets,',actor_checks,'actor cohorts;4atlas inputs unchanged,no model scores.')


if __name__=='__main__':main()
