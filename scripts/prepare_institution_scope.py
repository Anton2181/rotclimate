"""Compare explicit and documented parent scopes; no value or model fitting."""
import collections
import json
from pathlib import Path
import sys
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity.institution_scope import group_scopes
from polity.institution_evidence import value_evidence
from prepare_institution_evidence import TARGETS

CONFIG=ROOT/'calibration/institution_scope_20261111'
OUT=ROOT/'output/institution_scope_20261111'
PARENT=ROOT/'output/institution_evidence_20261111/earth_preparation.json'


def main():
    OUT.mkdir(parents=True,exist_ok=True);parent=json.loads(PARENT.read_text())
    old_config=ROOT/'calibration/institution_evidence_20261111/sources.json'
    if sha(old_config)!=parent['sources_sha256']:raise ValueError('Changed parent source identity')
    inputs=json.loads(old_config.read_text());cache=ROOT/inputs['cache']
    for name,record in inputs['files'].items():
        if sha(cache/name)!=record['sha256']:raise ValueError('Changed parent source')
    policy_sources=json.loads((CONFIG/'sources.json').read_text());policy_cache=ROOT/policy_sources['cache']
    for name,record in policy_sources['files'].items():
        if sha(policy_cache/name)!=record['sha256']:raise ValueError('Changed author scope source')
    text=(policy_cache/'seshatdatasetanalysis/Template.py').read_text()
    if not all(anchor in text for anchor in policy_sources['documented_policy_anchors']):raise ValueError('Missing scope-policy source anchor')
    book=openpyxl.load_workbook(cache/'Polaris2026.xlsx',read_only=True,data_only=False)
    def rows(name):
        values=iter(book[name].values);headers=next(values)
        return [dict(zip(headers,r)) for r in values if any(v is not None for v in r)]
    parents=collections.defaultdict(list)
    for p in rows('Polities'):parents[(p['polity_number'],p['polity_id'])].append(p)
    groups=collections.defaultdict(list)
    for row in rows('Social complexity'):
        if row['variable_name'] in TARGETS:groups[(row['polity_number'],row['polity_id'],row['variable_name'])].append(row)
    book.close();policies={}
    for policy in ['explicit_only','documented_parent_scope']:
        summaries={key:dict(total_rows=0,eligible_rows=0,scope_counts=collections.Counter(),review_reasons=collections.Counter(),
            positive_year200_rows=0,positive_year200_polity_variable_groups=0,positive_year200_value_states=collections.Counter(),
            positive_year200_groups_with_multiple_rows=0,positive_year200_groups_with_dispute_flag=0,positive_year200_groups_with_uncertainty_flag=0) for key in TARGETS}
        for identity,records in groups.items():
            matches=parents[identity[:2]];p=matches[0] if len(matches)==1 else {}
            scopes=group_scopes(records,p.get('start_year'),p.get('end_year'),policy);s=summaries[identity[2]];selected=[]
            for row,scope in zip(records,scopes):
                s['total_rows']+=1
                if scope['eligible']:s['eligible_rows']+=1;s['scope_counts'][scope['scope']]+=1
                else:s['review_reasons'][scope['review_reason']]+=1
                if scope['compatible_with_positive_year200']:
                    selected.append(row);s['positive_year200_rows']+=1
                    s['positive_year200_value_states'][value_evidence(row['value_from'],row['value_to'])['state']]+=1
            if selected:
                s['positive_year200_polity_variable_groups']+=1
                s['positive_year200_groups_with_multiple_rows']+=len(selected)>1
                s['positive_year200_groups_with_dispute_flag']+=any(r['is_disputed'] is True for r in selected)
                s['positive_year200_groups_with_uncertainty_flag']+=any(r['is_uncertain'] is True for r in selected)
        for s in summaries.values():
            assert s['total_rows']==s['eligible_rows']+sum(s['review_reasons'].values())
        policies[policy]=summaries
    checks={str(PARENT.relative_to(ROOT)):sha(PARENT)}
    for name in ['provider_audit.json','review.json']:checks['output/institution_evidence_20261111/'+name]=sha(PARENT.parent/name)
    result=dict(status='prepared_institution_scope_comparison_no_model_scores',adopt=False,chosen_policy=None,
        plan_sha256=sha(CONFIG/'plan.json'),policy_sources_sha256=sha(CONFIG/'sources.json'),parent_source_manifest_sha256=sha(old_config),
        parent_artifacts=checks,producer_sha256=sha(Path(__file__)),scope_module_sha256=sha(ROOT/'polity/institution_scope.py'),
        frozen_evidence_module_sha256=sha(ROOT/'polity/institution_evidence.py'),target_rows=sum(len(g) for g in groups.values()),
        polity_variable_groups=len(groups),policies=policies,model_predictions_matched=False,model_scores_computed=False,
        values_or_source_rows_changed=False,population_food_staff_control_changed=False,
        limits='Documented parent scope is an analysis convention,not direct role dates or continuous operation. All alternatives/unknowns/ranges retained. No sampling/interpolation/clipping or independent validation. Seshat polity attributes do not supply site coordinates or staffing quantities.')
    assert result['target_rows']==5007
    write(OUT/'results.json',result)
    for key in ['settlement_hierarchy','population_of_the_largest_settlement','full_time_bureaucrat']:
        print(key,{policy:summaries[key]['positive_year200_polity_variable_groups'] for policy,summaries in policies.items()},flush=True)


if __name__=='__main__':main()
