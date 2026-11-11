"""Score all gated source-label partitions on frozen opportunity fields."""
import collections
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,number,sha,write
from polity.observed_role_contrast import context_auc,cell_class_summary
from polity.role_composition import GROUPS,nucleated_partition,nonroadside

OUT=ROOT/'output/settlement_role_composition_20261111'
PLAN=ROOT/'calibration/settlement_role_composition_20261111/plan.json'
PRIOR=ROOT/'output/settlement_service_controls_20261111'
PRIVATE=ROOT/'data/cache/settlement_role_contrast_20261111/matched.npz'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    semantic_path=PLAN.parent/'semantic_sources.json';semantics=json.loads(semantic_path.read_text())
    text_path=ROOT/semantics['private_text']
    if sha(text_path)!=semantics['text_sha256']:raise ValueError('Changed classification methodology')
    text=' '.join(text_path.read_text().split())
    for finding in semantics['findings']:
        if not all(' '.join(anchor.split()) in text for anchor in finding['anchors']):raise ValueError('Missing methodology anchor')
    parent=json.loads((PRIOR/'results.json').read_text());manifest=json.loads((PRIOR/'fields.json').read_text())
    if sha(PRIVATE)!=parent['private_matches_sha256'] or sha(PRIOR/'fields.npz')!=parent['fields_sha256']:
        raise ValueError('Changed composition matches/fields')
    for path,digest in manifest['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen source: '+path)
    source=ROOT/'data/cache/roman_rural_britain_2018';snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    if sha(snapshot)!=parent['source_snapshot_sha256']:raise ValueError('Changed archive snapshot')
    for item in json.loads(snapshot.read_text())['files']:
        if sha(source/item['name'])!=item['sha256']:raise ValueError('Changed archive table')
    roles,_=table((source/'rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID');labels=collections.defaultdict(set)
    for row in roles:labels[identifier(row['id'])].add(row['sitetypeminor'])
    m=dict(np.load(PRIVATE));groups=np.array([nucleated_partition(labels[str(i)]) or 'not_nucleated' for i in m['source_ids']])
    classes=m['classes'];assert np.all(groups[classes==1]!='not_nucleated') and np.all(groups[classes==0]=='not_nucleated')
    strict=np.array([nonroadside(labels[str(i)]) for i in m['source_ids']])
    rows,_=table((source/'rrs_core_data.csv').read_bytes(),['ID']);byid={identifier(r['id']):r for r in rows}
    records=[byid[str(i)] for i in m['source_ids']]
    def area(r):
        a=number(r['area'])
        return 'missing' if a is None or a<=0 else 'positive_lt0.1ha' if a<.1 else '0.1_to_lt1ha' if a<1 else 'ge1ha'
    strata_labels={'region':[r['region'] or 'unknown' for r in records],
        'fieldwork':[r['fieldworktype'] or 'unknown' for r in records],'investigated_area':[area(r) for r in records]}
    fields=dict(np.load(PRIOR/'fields.npz'));core=fields.pop('core_mask');w=core.shape[1]
    cell=float(np.load(ROOT/'output/settlement_locations_20261110/rome_inputs.npz')['cell_km'])
    cases={};scored=0;gated=0
    for cohort,cohort_mask in [('full',np.ones(len(classes),bool)),('strict_nonroadside',strict)]:
        assert sum(np.sum(cohort_mask&(classes==1)&(groups==group)) for group in GROUPS)==np.sum(cohort_mask&(classes==1))
        for group in GROUPS:
            use=cohort_mask&((classes==0)|(groups==group));support=cell_class_summary(m['cells'][0][use],classes[use],m['status'][0][use])
            positive=int(np.sum(use&(classes==1)));negative=int(np.sum(use&(classes==0)))
            case=dict(cohort=cohort,source_group=group,source_positive_records=positive,source_negative_records=negative,
                central_support=support,coordinate_support=[],results=[],spatial_blocks={},primary_strata={})
            for k,name in enumerate(m['scenario_names']):
                case['coordinate_support'].append(dict(coordinate_scenario=str(name),
                    support=cell_class_summary(m['cells'][k][use],classes[use],m['status'][k][use]),
                    statuses_by_class={str(c):{label:int(np.sum(use&(classes==c)&(m['status'][k]==code)))
                        for code,label in enumerate(['included','out_of_window','nonland','disallowed'])} for c in [0,1]}))
            if support['preparation_gate_passed']:
                gated+=1
                for k,name in enumerate(m['scenario_names']):
                    values={key:context_auc(m['cells'][k][use],classes[use],m['status'][k][use],field) for key,field in fields.items()}
                    case['results'].append(dict(coordinate_scenario=str(name),predictors=values));scored+=len(values)
                for dimension,values in strata_labels.items():
                    case['primary_strata'][dimension]=[]
                    for label in sorted(set(values)):
                        selected=use&np.array([v==label for v in values])
                        case['primary_strata'][dimension].append(dict(label=label,source_records=int(selected.sum()),predictors={key:context_auc(m['cells'][0][selected],classes[selected],m['status'][0][selected],field) for key,field in fields.items()}))
                index=m['cells'][0];rr,cc=np.divmod(index,w);blocks=collections.defaultdict(list)
                for i,block in enumerate(zip(np.floor(rr*cell/50).astype(int),np.floor(cc*cell/50).astype(int))):
                    if use[i] and m['status'][0][i]==0:blocks[block].append(i)
                scores={key:[] for key in fields}
                for selected in blocks.values():
                    selected=np.asarray(selected,int)
                    for key,field in fields.items():
                        a=context_auc(index[selected],classes[selected],m['status'][0][selected],field)['AUC']
                        if a is not None:scores[key].append(a)
                case['spatial_blocks']=dict(block_km=50,observed_blocks=len(blocks),blocks_with_both_classes=len(scores['uniform']),
                    equal_block_mean_AUC={key:float(np.mean(v)) if v else None for key,v in scores.items()},independent_or_held_out=False)
            cases[cohort+'__'+group]=case
            print(cohort,group,'source',positive,'gate',support['preparation_gate_passed'],flush=True)
    # Byte comparisons preserve old scored pools; no independence is introduced.
    old=json.loads((PRIOR/'replay.json').read_text())['prior_artifacts_unchanged']
    paths=[x['path'] for x in old]+[str((PRIOR/n).relative_to(ROOT)) for n in ['fields.npz','fields.json','results.json','review.json']]
    unchanged={}
    for path in paths:
        if subprocess.check_output(['git','show','e567dec2:'+path],cwd=ROOT)!=(ROOT/path).read_bytes():raise ValueError('Changed previous artifact: '+path)
        unchanged[path]=sha(ROOT/path)
    result=dict(status='exposed_source_composition_diagnostic',adopt=False,chosen_predictor=None,fitted_parameters=0,
        population_food_staff_control_changed=False,plan_sha256=sha(PLAN),parent_results_sha256=sha(PRIOR/'results.json'),
        semantic_sources_sha256=sha(semantic_path),
        parent_fields_manifest_sha256=sha(PRIOR/'fields.json'),parent_fields_sha256=sha(PRIOR/'fields.npz'),
        source_snapshot_sha256=sha(snapshot),private_matches_sha256=sha(PRIVATE),producer_sha256=sha(Path(__file__)),
        partition_module_sha256=sha(ROOT/'polity/role_composition.py'),scorer_sha256=sha(ROOT/'polity/observed_role_contrast.py'),
        parent_artifacts_unchanged=unchanged,parent_positive_records=int(np.sum(classes==1)),parent_negative_records=int(np.sum(classes==0)),
        gated_cases=gated,unscored_cases=10-gated,global_AUCs_computed=scored,predictors=list(fields),cases=cases,
        limits='Selected whole-record source contexts,not AD200 functions/census/absence/authority. Small classes remain unscored; no post-outcome merging,fit or adoption.')
    write(OUT/'results.json',result)
    print('Produced',scored,'AUCs;',gated,'of10cases pass support gates.')


if __name__=='__main__':main()
