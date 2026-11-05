"""Prepare, select and independently evaluate one modern manual-task comparator."""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
PLAN=ROOT/'calibration/earth_components_20261105/plan.json'
SOURCE=ROOT/'calibration/earth_components_20261105/vdsa_source.json'


def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def committed(path):
    relative=str(path.relative_to(ROOT));result=subprocess.run(['git','show','HEAD:'+relative],cwd=ROOT,capture_output=True)
    if result.returncode or result.stdout!=path.read_bytes():raise ValueError('Commit exact preregistration/selection before this stage: '+relative)


def main():
    from harvest.earth_reaping import prepare,select_scale,metrics
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',choices=['prepare','select','evaluate'],required=True);ap.add_argument('--cache',type=Path,default=ROOT/'data/cache/vdsa_8224522');ap.add_argument('--out',type=Path,default=ROOT/'output/earth_components_20261105/reaping');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    plan=json.loads(PLAN.read_text());committed(PLAN);committed(SOURCE);source=json.loads(SOURCE.read_text())
    producer=['harvest/earth_reaping.py','scripts/benchmark_earth_reaping.py'];identity=dict(plan_sha256=hashfile(PLAN),source_manifest_sha256=hashfile(SOURCE),sources_sha256={p:hashfile(ROOT/p) for p in producer},inputs_sha256={f['name']:hashfile(a.cache/f['name']) for f in source['files']})
    if any(identity['inputs_sha256'][f['name']]!=f['sha256'] for f in source['files']):raise ValueError('Survey source identity changed')
    cached=a.cache/'prepared_reaping.json';selection=a.out/'selection.json'
    def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    if a.stage=='prepare':
        cases,excluded,counts=prepare(a.cache,plan);write(cached,dict(identity=identity,cases=cases))
        splits={s:dict(cases=sum(c['split']==s for c in cases),districts=len({c['district_id'] for c in cases if c['split']==s}),households=len({c['household_id'] for c in cases if c['split']==s}),crops=dict(Counter(c['crop'] for c in cases if c['split']==s)),strict_input_cases=sum(c['split']==s and c['strict_recorded_input_subgroup'] for c in cases)) for s in ['training','evaluation']}
        write(a.out/'preparation.json',dict(status='prepared_without_target_scoring',identity=identity,splits=splits,excluded=excluded,source_rows_considered=counts,prepared_sha256=hashfile(cached),evaluation_targets_published=False,ancient_default_adoption=False));print(json.dumps(splits,indent=2));return
    data=json.loads(cached.read_text())
    if data['identity']!=identity:raise ValueError('Preparation or producer changed; rerun preparation under the same declared rules')
    cases=data['cases'];rule=plan['selection'];train=[c for c in cases if c['split']=='training'];evaluation=[c for c in cases if c['split']=='evaluation']
    train_ok=len(train)>=rule['minimum_training_cases'] and len({c['district_id'] for c in train})>=rule['minimum_training_districts']
    eval_ok=len(evaluation)>=rule['minimum_evaluation_cases'] and len({c['district_id'] for c in evaluation})>=rule['minimum_evaluation_districts']
    if a.stage=='select':
        scale=select_scale(cases,rule['scale_bounds']) if train_ok else None
        write(selection,dict(status='selected_modern_comparator' if train_ok else 'insufficient_training_evidence',identity=identity,prepared_sha256=hashfile(cached),scale=scale,training_baseline=metrics(train,1),training_candidate=metrics(train,scale) if scale is not None else None,training_case_ids=[c['case_id'] for c in train],evaluation_targets_accessed=False,ancient_default_adoption=False));print(json.dumps(dict(training_qualified=train_ok,scale=scale),indent=2));return
    committed(selection);chosen=json.loads(selection.read_text())
    if chosen['identity']!=identity or chosen['prepared_sha256']!=hashfile(cached):raise ValueError('Selection identity differs')
    if not train_ok or not eval_ok or chosen['scale'] is None:
        write(a.out/'evaluation.json',dict(status='insufficient_evidence_no_qualification',identity=identity,training_qualified=train_ok,evaluation_qualified=eval_ok,evaluation_targets_scored=False,ancient_default_adoption=False));print('Insufficient evidence; no qualification');return
    base=metrics(evaluation,1);candidate=metrics(evaluation,chosen['scale']);qualified=candidate['equal_district_abs_log10_error']<=.95*base['equal_district_abs_log10_error']
    subgroups={k:dict(baseline=metrics([c for c in evaluation if condition(c)],1),candidate=metrics([c for c in evaluation if condition(c)],chosen['scale'])) for k,condition in [('wheat',lambda c:c['crop']=='WHEAT'),('barley',lambda c:c['crop']=='BARLEY'),('strict_recorded_inputs',lambda c:c['strict_recorded_input_subgroup'])]}
    write(a.out/'evaluation.json',dict(status='evaluated_modern_manual_reaping_only',identity=identity,selection_sha256=hashfile(selection),baseline=base,candidate=candidate,qualified_for_modern_comparator=qualified,subgroups=subgroups,evaluation_targets_scored=True,evaluation_pool_now_spent=True,ancient_default_adoption=False,production_atlas_changed=False));print(json.dumps(dict(baseline=base,candidate=candidate,modern_qualification=qualified),indent=2))


if __name__=='__main__':main()
