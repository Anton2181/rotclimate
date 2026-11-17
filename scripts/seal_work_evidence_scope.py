"""Independent quote/metadata arithmetic and available old receipt identities."""
import csv
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import OUT,MANIFEST,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified evidence audit'
    r=read(OUT/'results.json');assert r['status']=='completed_read_only_archived_work_evidence_and_scheduler_interface_audit'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    rows=list(csv.DictReader((OUT/'evidence.csv').open()));assert len(rows)==22
    for row in rows:assert row['exact_quote'] in ' '.join((ROOT/row['source']).read_text().split())
    tasks=read(OUT/'task_counts.json');assert len(tasks)==10
    manifest=read(MANIFEST)
    for crop in ['wheat','barley']:
        selected={t['task']:t['prescribed_days_per_iugerum_as_archived'] for t in tasks if t['crop']==crop}
        assert selected==manifest['workdays_per_iugerum'][crop]
        assert sum(selected.values())==manifest['published_totals_workdays_per_iugerum'][crop]
    statuses=[];extra_sources={}
    for folder in ['farm_labour_20261103','farm_work_targets_20261103','cereal_work_maps_20261103','settlement_monthly_work_20261112']:
        path=ROOT/'output'/folder/'review.json'
        if not path.exists():statuses.append(dict(receipt=str(path.relative_to(ROOT)),present=False));continue
        old=read(path);available=[];missing=[];mismatch=[]
        identities=dict(old.get('sources_sha256',{}))
        if 'source_manifest_sha256' in old:identities[str(MANIFEST.relative_to(ROOT))]=old['source_manifest_sha256']
        if 'results_sha256' in old:identities[f'output/{folder}/results.json']=old['results_sha256']
        for name,digest in identities.items():
            p=ROOT/name
            if not p.exists():missing.append(name);continue
            actual=sha(p)
            if actual!=digest:mismatch.append(dict(path=name,recorded=digest,current=actual))
            else:available.append(name);extra_sources[name]=actual
        extra_sources[str(path.relative_to(ROOT))]=sha(path)
        statuses.append(dict(receipt=str(path.relative_to(ROOT)),present=True,available_identities_checked=available,
            missing_inputs=missing,mismatched_inputs=mismatch,exact_old_recipe_identity_passed=not missing and not mismatch,source_body_not_reverified=True))
    write(OUT/'old_receipt_status.json',statuses)
    assert r['old_source_caches_missing']==2
    for key in ['new_source_bodies_opened','labour_LP_calls','component_work_calls','food_kernel_calls','stock_solves','graph_rebuilds','dijkstra_calls','new_Earth_food_scenarios','new_staff_allocations']:assert r[key]==0
    paths=[Path(__file__),ROOT/'reports/WORK_EVIDENCE_SCOPE_20261117.md',ROOT/'calibration/urban_diagnosis_20261117/columella_calendar_source.json']
    mismatches=sum(len(s.get('mismatched_inputs',[])) for s in statuses)
    assert mismatches==1 and statuses[2]['mismatched_inputs'][0]['path']=='scripts/land_people.py'
    write(OUT/'qualification.json',dict(status='passed_faithful_work_evidence_audit_with_primary_cache_and_old_recipe_identity_limits',
        sources_sha256={**r['sources_sha256'],**extra_sources,**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        exact_quote_rows=22,archived_task_count_rows=10,old_source_caches_missing=2,old_recipe_source_mismatches=mismatches,
        old_cereal_map_recipe_current_identity_passed=False,new_source_bodies_opened=0,
        complete_Earth_monthly_schedule_qualified=False,warehouse_handling_intensity_qualified=False,
        labour_LP_calls=0,component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/columella_calendar_source.json'))
    print('Qualified faithful22-row evidence audit;2missing primary caches and1old builder identity mismatch retained',flush=True)


if __name__=='__main__':main()
