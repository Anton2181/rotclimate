"""Publish all conditional meal bounds without changing population maps."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from plot_meal_headroom import plot
from settlement_locations_earth import sha,write

OUT=ROOT/'output/network_visit_meal_headroom_20261112'
PLAN=ROOT/'calibration/network_visit_meal_headroom_20261112/plan.json'


def cells(v):
    return [v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['accounting'],str(v['scored_providers']),str(v['staff_infeasible']),str(v['full_demand_passes']),
        f'{v["civilian_meal_equivalent_reduction"]:,.3f}',f'{100*v["civilian_meal_equivalent_reduction"]/v["parent_civilian"]:.5f}']


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());replay=json.loads((OUT/'replay.json').read_text())
    assert review['status']==replay['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_meal_headroom.py') and review['scalar_reviewer_sha256']==sha(ROOT/'scripts/review_delivery_timing.py')
    for name,digest in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in replay['byte_exact_files'].items():assert sha(OUT/name)==digest,name
    figures=plot();headers=['Climate','Farm h','Crew','Pulse model','Providers','Staff infeasible','Full demand passes','Civilian meal-equivalent reduction','Reduction %']
    table='|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(cells(v))+'|\n' for v in r['rows'])
    staff_failures=sum(v['staff_infeasible'] for v in r['rows']);full_passes=sum(v['full_demand_passes'] for v in r['rows'])
    report=ROOT/'reports/NETWORK_VISIT_MEAL_HEADROOM_20261112.md'
    text='''# Fixed-staff civilian meal bounds under unchanged shipments

Declaration `ed6ae653` preceded production outputs. The destination timing
audit exposed small continuous-inventory cereal gaps in the existing resident
plans. This follow-up bounds civilian meal demand under those SAME shipments;
it does not replan residents, production or worker jobs.

## What stays fixed

Every provider already qualified by a complete worker calendar remains in
scope for all eight scenarios and both pulse calendars B/C (16 rows). B pulses
at the original destination-bin starts;C retains selected collector return
phases inside the already-lagged arrival bins. The original one-bin lag and
0.95 transport retention stay unchanged;cargo is not retained a second time.

Institutional residents and their meals stay fixed. Only original civilian
meals are multiplied by alpha in [0,1]. Trial demand is
2500*(original institutional residents + alpha*original civilians) kcal/day.
Storage keeps its ORIGINAL physical capacity: 90 days of the parent total
resident meals. It is not reduced as alpha decreases. Stored-food loss stays
5%/year;the year stays 365 days. No grain,source production,staff,job,provider
assignment or policy is added or removed.

The two population components are checked against the original total;staff
meals are included exactly once. Sources retain monthly availability assumptions.
No crew-carried food or food location is tracked. A bound on destination meals
does not validate source within-bin availability or complete provisioning.

## Frozen numeric rule and all outcomes

Score alpha=0 and1 first. A staff-only failure has NO feasible civilian bound;
it remains explicit,not a fictitious zero-population solution. Full-demand
success keeps alpha=1. Otherwise,48 deterministic bisections retain a passing
and failing alpha. Each trial finds the smallest repeating nonnegative stock,
without an externally borrowed initial reserve. The same parent diagnostic is
used throughout: unmet <=1e-8*max(1,annual needed kcal).

These fine brackets are numeric solver bounds,not historical precision or
population confidence intervals. The independent scalar review uses a separate
24-step bracket and reports its resolution and floating-point ledger tolerance.
It explicitly records final endpoints that lie within scalar grain roundoff
of the no-shortage threshold;no independent bit-level agreement is claimed.

'''+f'There are {staff_failures} staff-only failures and {full_passes} full-demand passes across the 16 rows.\n\n'+table+'\n'+'\n'.join(f'![Conditional civilian meal bounds](figures/{p.name})' for p in figures)+'''

“Civilian meal-equivalent reduction” sums original civilian count*(1-alpha)
where a feasible staff-preserving bound exists. It is not a census reduction,
migration,mortality or a valid revised population estimate. Staff-infeasible
providers are counted separately and never assigned a fabricated feasible bound.

## Verification and reproducibility

Six new controls ran before production alongside the ten continuous inventory
controls:fixed staff,unchanged physical stores,staff-only failure,full-demand
pass,tight intermediate bounds,minimum repeating reserve,determinism and input
preservation are covered. Every output retains the staff/full-demand/final
passing/final failing inventory fields and validity flags. All actor summaries
retain their complete scored cohorts. Unqualified sources remain unscored.

The independent reviewer imports neither meal solver nor food-event primitive.
It uses scalar continuous integration and a separate stock root search to
bracket each demand bound;it checks every final inventory,cargo/staff/capacity
input,provider CSV field and actor summary. Conservation and periodicity are
separate from food sufficiency. Fresh results,fields and provider CSV are byte
exact. Existing atlas packets,point maps and defaults remain unchanged.

'''+(f'Independent review checked {review["provider_accounting_bounds_checked"]:,} provider/accounting bounds '
        f'and {review["endpoint_inventories_checked"]:,} endpoint inventories.\n')+'''

## What this does and does not advance

The bound shows how small a destination-only meal adjustment can close the
declared numeric accounting gaps while preserving staff meals. It is NOT a
valid resident rebuild:changing actual civilian residents also changes field
work,rural meals,source exports and integer collector jobs. Those remain frozen
here,so the meal equivalents cannot be exported as a new population map.

The next model step is a versioned continuous destination-bin inventory inside
the finite source/food/work resident feedback,with all previous code preserved.
Its own controls and declared comparison must precede production outputs.
Any later map needs fresh source/cargo/calendar checks and a return-phase audit;
a bin-start food pass alone cannot qualify a different arrival calendar.

The whole release1–4/S1–S5 programme remains open:dated occupation,compatible
settlement sizes/provider functions,prospective transfer,source within-bin
availability,crew food/location,complete diets and household/draft work,and
mobile/nonstate/unaffiliated resources remain unresolved. No calibrated default
or empirical population/authority adoption is made. Normal research publishes
all outcomes and downloads;the direct publisher preserves earlier panels.
The full historical publisher still needs the omitted private Vidarbha cache.
'''
    report.write_text(text)
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data';downloads=[]
    for source,name,label in [(OUT/'results.json','meal_headroom_results.json','All 16 outcomes'),(OUT/'review.json','meal_headroom_review.json','Independent bounds and inventory review'),
        (OUT/'replay.json','meal_headroom_replay.json','Fresh byte replay'),(OUT/'controls.json','meal_headroom_controls.json','Controls before production'),
        (PLAN,'meal_headroom_plan.json','Prior declaration'),(OUT/'fields.npz','meal_headroom_fields.npz','All endpoint fields'),(OUT/'providers.csv.gz','meal_headroom_providers.csv.gz','Every provider bound CSV')]:
        shutil.copyfile(source,data/name);downloads.append((name,label))
    section='''<!--meal-headroom-start--><section><h2>Continuous civilian meal bounds with staff and shipments fixed</h2><details id="meal-headroom" class="panel"><summary>16 matched bounds · conditional meals,not a revised population map</summary>
<p><strong>Staff meals and ORIGINAL physical storage stay fixed.</strong> Every calendar-qualified provider is retained under both bin-start pulses B and selected collector return phases C. Only civilian meals are multiplied by alpha between 0 and 1. Cargo,one-bin lag,0.95 retention,5% stored-food loss and every worker job remain unchanged. No extra grain or borrowed initial reserve is inserted.</p>
<div class="table"><table><thead><tr>'''+''.join(f'<th>{v}</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in cells(row))+'</tr>' for row in r['rows'])+'</tbody></table></div>\n'
    section+='\n'.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All sixteen fixed-staff civilian meal bounds under matched pulse calendars','Every provider meal reduction bound and explicit staff-only failures']))
    section+=f'<p>{staff_failures} staff-only failures;{full_passes} full-demand passes across the 16 rows. Staff-only failures stay explicit with no fictitious feasible population. “Meal-equivalent reduction” is conditional accounting,not a census,migration,mortality or a valid revised population estimate. Source production,field work,exports and jobs are frozen. Existing maps/defaults remain byte unchanged;other providers remain explicitly unscored.</p>'
    section+='''<p>Forty-eight deterministic bisections retain passing/failing endpoints using the unchanged parent numerical tolerance. Independent scalar integration and 24-step brackets check every bound and endpoint,all provider CSV fields and actor rows. Near-threshold floating-point uncertainty is explicit;the bracket is not historical precision. Six new controls and ten event-inventory controls ran before production. Fresh results/fields/provider CSV are byte exact.</p>
<p>Actual resident replanning must recouple the finite source/food/work ledger,shipments and worker calendars. Destination cereal accounting alone does not qualify source within-bin food,crew-carried food/location,complete diets or authority. No calibrated adoption.</p>
<p><a href="../../reports/NETWORK_VISIT_MEAL_HEADROOM_20261112.md">Methods,all outcomes and remaining programme</a> · '''
    section+=' · '.join(f'<a href="data/{name}" download>{label}</a>' for name,label in downloads)+'</p></details></section><!--meal-headroom-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--meal-headroom-start-->[\s\S]*?<!--meal-headroom-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--delivery-timing-start-->' in html;html=html.replace('<!--delivery-timing-start-->',section+'\n<!--delivery-timing-start-->',1)
    for name,body in old:
        if name!='meal-headroom':assert f'<!--{name}-start-->{body}<!--{name}-end-->' in html,name
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text())
    entry=dict(id='network_visit_meal_headroom_20261112',status='model_only_fixed_staff_civilian_meal_bound',evidence=str(report.relative_to(ROOT)),
        note='All16fixed-shipment meal bounds keep institutional meals and original physical stores. Conditional destination accounting only;source work/exports frozen. No revised population map or calibrated adoption.')
    usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,data/'dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',results_sha256=sha(OUT/'results.json'),evidence_page_sha256=sha(page),
        producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'scripts/plot_meal_headroom.py']},
        figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={name:sha(data/name) for name,_ in downloads},original_atlas_unchanged=True,default_adoption=False))
    for p in figures:print(p)
    print('Published all 16 conditional meal bounds,2 figures,7 data downloads;no population map changes.')


if __name__=='__main__':main()
