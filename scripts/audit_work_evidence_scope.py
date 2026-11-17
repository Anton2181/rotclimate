"""Read-only archived work assumptions and reusable scheduler interfaces."""
import csv
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_work_evidence_20261117'
PARENT=ROOT/'output/urban_warehouse_coupling_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_work_evidence_scope.json'
MANIFEST=ROOT/'research_notes/farm_labour_20261103.json'


def sha(path):
    import hashlib
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')


QUOTES=[
 ('task_counts','prescribed_as_archived','reports/FARM_LABOUR_20261103.md','These are prescriptive Roman agronomic counts to the threshing floor.','Archived primary prescription,not a measured full occupation.'),
 ('windows','assumed','research_notes/farm_labour_20261103.json','Operation windows are manufactured and not inferred from climate or Columellas calendar','No historical monthly placement supplied by these windows.'),
 ('day_and_area','assumed','research_notes/farm_labour_20261103.json','0.25ha is an approximate iugerum conversion; eight-hour workday is our unit-conversion scenario, not known Roman day length','Unit assumptions are distinct from primary days/iugerum.'),
 ('omitted_tasks','unknown','research_notes/farm_labour_20261103.json','no threshing, processing, storage, water/fuel collection, care, draft animals feed or maintenance','No complete postharvest/household work schedule.'),
 ('food_coefficients','required_input','harvest/labour.py','Output may be net food energy only when the caller supplies validated net food coefficients.','LP cannot turn arbitrary demo outputs into funded grain.'),
 ('one_land','implemented','harvest/labour.py','Activities are complete annual land-use sequences, not independent crops that may each claim the same hectare.','Reuse full-activity land accounting;do not copy hectares per crop.'),
 ('task_windows','implemented','harvest/labour.py','Nonempty boolean operation window required','Operation timing is required input,not inferred from spare hours.'),
 ('resources','implemented','harvest/labour.py','Its human and animal requirements are simultaneous','Reuse simultaneous period resource constraints.'),
 ('scheduler_limits','unknown','harvest/labour.py','No task precedence, whole-worker integer constraint, travel, overtime, labour exchange or food storage is inferred.','Does not establish physical staff transfers or food stock feasibility.'),
 ('model_calendar','model_output','reports/CEREAL_WORK_MAPS_20261103.md','It is the current monthly crop response, **not** the experimental daily phenology clock or an independently validated crop calendar.','Harvest masks are model alternatives,not observed agronomic dates.'),
 ('map_limits','unknown','reports/CEREAL_WORK_MAPS_20261103.md','not jointly imposed on the maps','Do not claim full LP task/resource feasibility for existing work maps.'),
 ('collector_load','assumed','reports/SETTLEMENT_MONTHLY_WORK_20261112.md','60,000 / 120,000 kcal loads are supplied stress scenarios','Not measured porter mass or ancient productivity.'),
 ('collector_handling','assumed','calibration/settlement_monthly_work_20261112/plan.json','plus0.25handlinghours pertrip','A supplied old scenario does not qualify warehouse handling intensity.'),
 ('staff_envelope','assumed','calibration/settlement_monthly_work_20261112/plan.json','supplied600hours/year split equally across12bins','Same supported staff,not an empirically complete occupation schedule.'),
 ('fixed_case_refusal','implemented','polity/monthly_work.py','Failure refuses the fixed food/work case.','Reuse refusal semantics,not shipment cuts while retaining old population.'),
 ('same_staff','implemented','polity/monthly_work.py','these annual hours are never a second pool','Do not duplicate institutional staff as extra warehouse staff.'),
 ('shared_secondary','implemented','polity/monthly_work.py','Reserve fixed collection; ration all remaining claims together per month.','Reuse one pool across competing roles.'),
 ('roundtrip_scope','required_input','polity/monthly_work.py','Shipment outside checked two-way collection access','Original cost road-km does not supply these physical roundtrip days.'),
 ('partial_field_work','unknown','harvest/work_maps.py','Neither these ratios nor their inverse estimate total subsistence labour/population.','No complete baseline occupation claim.'),
 ('same_source_workforce','implemented','polity/earth_component_work.py','workers=rural*.4','One physical source population supplies the declared crop-work scenario.'),
 ('handling_toy_rates','assumed','reports/WAREHOUSE_GRAIN_WORK_COUPLING_20261117.md','engineering inputs with no empirical qualification','New converter is an engineering bridge,not a rate estimate.'),
 ('nonreaping_timing','unknown','reports/WAREHOUSE_WORK_READINESS_20261117.md','84.62% of listed work has no monthly placement','A complete monthly baseline is still missing.')]


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists(),'Preserve completed evidence audit'
    q=read(PARENT/'qualification.json');assert q['status'].startswith('passed_')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in q[key].items():assert sha(prefix/name)==digest,name
    sources={};rows=[]
    for name,classification,path,quote,meaning in QUOTES:
        assert quote in ' '.join((ROOT/path).read_text().split()),(name,path)
        sources[path]=sha(ROOT/path);rows.append(dict(id=name,classification=classification,source=path,locator='exact normalized quote',
            exact_quote=quote,interpretation=meaning,new_coefficient_adopted=False))
    manifest=read(MANIFEST)
    cache=[]
    for name,digest in manifest['cached_sources_sha256'].items():
        exists=(ROOT/name).exists();actual=sha(ROOT/name) if exists else None
        if exists:assert actual==digest,name
        cache.append(dict(path=name,recorded_sha256=digest,present=exists,current_sha256=actual,
            original_source_body_opened=False,fetch_attempted=False,identity_reverified=exists))
    OUT.mkdir(exist_ok=True)
    with (OUT/'evidence.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    # Metadata-only extraction;the missing fulltexts are not fetched in this scope.
    task_counts=[]
    for crop,tasks in manifest['workdays_per_iugerum'].items():
        assert sum(tasks.values())==manifest['published_totals_workdays_per_iugerum'][crop]
        for task,days in tasks.items():task_counts.append(dict(crop=crop,task=task,prescribed_days_per_iugerum_as_archived=days,
            source_locator=f'workdays_per_iugerum.{crop}.{task}',source='research_notes/farm_labour_20261103.json',
            monthly_window_observed=False,currently_reverified_in_primary=False))
    write(OUT/'task_counts.json',task_counts);write(OUT/'source_cache_status.json',cache)
    write(OUT/'reuse.json',dict(farm_scheduler=dict(module='harvest/labour.py',reuse=['complete annual activities','operation window masks',
        'simultaneous period resource accounting'],missing=['sourced operation windows','complete task list','validated output/material coefficients','physical affiliation/travel']),
        monthly_staff=dict(module='polity/monthly_work.py',reuse=['fixed-case refusal','same food-supported staff','one shared remainder'],
        missing=['empirical load/handling intensity','authenticated staff assignment','physical travel compatible with original warehouse routes']),
        complete_Earth_monthly_baseline_qualified=False,warehouse_handling_intensity_qualified=False,
        next_primary_target='Columella,De re rustica11.2,the agricultural calendar:qualify task/season prescriptions and spatial/calendar limits;do not fill Earth bins automatically.'))
    for p in [Path(__file__),PLAN,MANIFEST,PARENT/'qualification.json']:sources[str(p.relative_to(ROOT))]=sha(p)
    for name,digest in q['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_read_only_archived_work_evidence_and_scheduler_interface_audit',
        sources_sha256=sources,protected_sha256=q['protected_sha256'],files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
        exact_quote_rows=len(rows),archived_task_count_rows=len(task_counts),observed_complete_monthly_schedules=0,
        old_source_caches_missing=sum(not c['present'] for c in cache),new_source_bodies_opened=0,
        labour_LP_calls=0,component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))
    print(len(rows),'source/interface rows;',len(task_counts),'archived task counts;',sum(not c['present'] for c in cache),'missing source caches',flush=True)


if __name__=='__main__':main()
