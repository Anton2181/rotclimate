"""Reconstruct declared source-time policies independently from raw workbook."""
import collections
import json
import math
from pathlib import Path
import sys
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity.institution_evidence import value_evidence
from prepare_institution_scope import OUT,CONFIG,PARENT
from prepare_institution_evidence import TARGETS


def main():
    result=json.loads((OUT/'results.json').read_text())
    for key,path in {'plan_sha256':CONFIG/'plan.json','policy_sources_sha256':CONFIG/'sources.json',
        'parent_source_manifest_sha256':ROOT/'calibration/institution_evidence_20261111/sources.json',
        'producer_sha256':ROOT/'scripts/prepare_institution_scope.py','scope_module_sha256':ROOT/'polity/institution_scope.py',
        'frozen_evidence_module_sha256':ROOT/'polity/institution_evidence.py'}.items():assert result[key]==sha(path),key
    for path,digest in result['parent_artifacts'].items():assert sha(ROOT/path)==digest
    sources=json.loads((ROOT/'calibration/institution_evidence_20261111/sources.json').read_text());cache=ROOT/sources['cache']
    for name,record in sources['files'].items():assert sha(cache/name)==record['sha256']
    author=json.loads((CONFIG/'sources.json').read_text())
    for name,record in author['files'].items():assert sha(ROOT/author['cache']/name)==record['sha256']
    book=openpyxl.load_workbook(cache/'Polaris2026.xlsx',read_only=True,data_only=False)
    def records(name):
        values=iter(book[name].values);headers=next(values)
        return [dict(zip(headers,v)) for v in values if any(x is not None for x in v)]
    parents=collections.defaultdict(list)
    for r in records('Polities'):parents[(r['polity_number'],r['polity_id'])].append(r)
    groups=collections.defaultdict(list)
    for r in records('Social complexity'):
        if r['variable_name'] in TARGETS:groups[(r['polity_number'],r['polity_id'],r['variable_name'])].append(r)
    book.close();valid=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and int(v)==v
    checked=0
    for policy,published in result['policies'].items():
        reconstructed={v:dict(total_rows=0,eligible_rows=0,scope_counts=collections.Counter(),review_reasons=collections.Counter(),
            positive_year200_rows=0,positive_year200_polity_variable_groups=0,positive_year200_value_states=collections.Counter(),
            positive_year200_groups_with_multiple_rows=0,positive_year200_groups_with_dispute_flag=0,positive_year200_groups_with_uncertainty_flag=0) for v in TARGETS}
        for identity,rows in groups.items():
            match=parents[identity[:2]];p=match[0] if len(match)==1 else {};lo,hi=p.get('start_year'),p.get('end_year')
            active=[r['year_from'] is not None or r['year_to'] is not None for r in rows]
            mixed=any(active) and not all(active);unflagged=len(rows)>1 and not any(r.get(k) is True for r in rows for k in ['is_disputed','is_uncertain'])
            s=reconstructed[identity[2]];at200=[]
            for r,dated in zip(rows,active):
                a,b=r['year_from'],r['year_to'];scope=None;reason=None
                if not valid(lo) or not valid(hi) or lo>hi:reason='invalid_parent_interval'
                elif policy=='documented_parent_scope' and mixed:reason='mixed_time_scope_review'
                elif policy=='documented_parent_scope' and not any(active) and unflagged:reason='ambiguous_multiple_undated'
                elif policy=='documented_parent_scope' and not dated:a,b=lo,hi;scope='documented_parent_scope'
                elif a is None and b is None:reason='missing_explicit_interval'
                elif a is None or b is None:reason='partial_date_review'
                elif not valid(a) or not valid(b):reason='invalid_time_bounds'
                elif a>b:reason='reversed_time_bounds'
                elif a<lo or b>hi:reason='outside_parent_interval'
                else:scope='explicit_interval'
                s['total_rows']+=1;checked+=1
                if scope:
                    s['eligible_rows']+=1;s['scope_counts'][scope]+=1
                    if a<=200<=b:
                        at200.append(r);s['positive_year200_rows']+=1
                        s['positive_year200_value_states'][value_evidence(r['value_from'],r['value_to'])['state']]+=1
                else:s['review_reasons'][reason]+=1
            if at200:
                s['positive_year200_polity_variable_groups']+=1
                s['positive_year200_groups_with_multiple_rows']+=len(at200)>1
                s['positive_year200_groups_with_dispute_flag']+=any(r['is_disputed'] is True for r in at200)
                s['positive_year200_groups_with_uncertainty_flag']+=any(r['is_uncertain'] is True for r in at200)
        # JSON round-trip normalizes Counter containers only; no source values change.
        assert json.loads(json.dumps(reconstructed))==published,policy
    assert checked==10014 and result['target_rows']==5007 and result['polity_variable_groups']==len(groups)
    assert not result['model_scores_computed'] and not result['values_or_source_rows_changed'] and result['chosen_policy'] is None
    write(OUT/'review.json',dict(status='passed',source_result_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        row_policy_cases_checked=checked,policies_checked=2,variables_checked=len(TARGETS),all_scope_and_positive_year200_summaries_reconstructed=True,
        original_parent_artifacts_unchanged=True,foreign_code_executed=False,model_scores_computed=False))
    print('Reviewed10014row-policy cases,all10variables and both200CE summaries;no model fitting.')


if __name__=='__main__':main()
