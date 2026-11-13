"""Publish every collector omission/phase outcome without changing visit maps."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from plot_continuous_collection_calendar import plot
from settlement_locations_earth import sha,write
OUT=ROOT/'output/continuous_collection_calendar_20261112'
PLAN=ROOT/'calibration/continuous_collection_calendar_20261112/plan.json'


def cells(v):
    return [v['climate'].title(),str(v['hours_worker_year']),v['accounting'],str(v['scored_providers']),str(v['mandatory_complete']),str(v['food_no_shortage']),str(v['mandatory_and_food']),f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/v["needed"]:.6f}']


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());exports=json.loads((OUT/'exports.json').read_text());er=json.loads((OUT/'export_review.json').read_text());replay=json.loads((OUT/'replay.json').read_text())
    assert review['status']==er['status']==replay['status']=='passed' and review['results_sha256']==er['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_collection_calendar.py') and er['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_collection_exports.py')
    assert er['exports_sha256']==sha(OUT/'exports.json') and exports['producer_sha256']==sha(ROOT/'scripts/export_continuous_collection_calendar.py')
    for name,digest in {**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for case in r['cases']:
        for name,digest in case['sources'].items():assert sha(ROOT/name)==digest,name
        for name,digest in case['files_sha256'].items():assert sha(OUT/name)==digest,name
    for name,digest in replay['byte_exact_files'].items():assert sha(OUT/name)==digest,name
    figures=plot();headers=['Climate','Farm h','Inventory','Scored providers','Mandatory twelve-bin','Food pass','Both gates','Unmet kcal','Unmet %']
    table='|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(cells(v))+'|\n' for v in r['rows'])
    report=ROOT/'reports/CONTINUOUS_COLLECTION_CALENDAR_20261112.md'
    text='''# New collector calendars and destination food: omissions versus phase

Declaration `4b42b703` preceded outputs. All four continuous-resident source
plans are retained. EVERY active provider is scored in all three food tests,
including incomplete and partially delivered sources. Inactive providers remain
explicitly unscored. Source exclusions are not absence-of-community claims.

## Actual jobs and three matched food tests

Use the unchanged collection-first worker policy with the NEW source shipments,
100 supplied institutional workers where funded,50 duty hours per person/bin
and7*365/12 calendar coordinates. Funded home-service hours come from the new
plan's secondary groups1 and2 and are equally shared/divisible,as before.
These are funded commitments,not a claim that every requested service or actual
institutional function is supplied. There are NO geographic visit jobs here.

Every whole collector trip retains its original owner,origin/month/serial and
directed journey plus handling duration. Greedy jobs are packed in descending
duration,then origin/serial order. Work and home services remain charged for
actual intervals;unpacked jobs remain explicit and consume no invented hours.

* A:all planned cargo at the original lagged destination-bin starts.
* B:ONLY packed cargo at those same bin starts. A-to-B isolates omissions.
* C:the SAME packed cargo as B,at its recorded return phase within the SAME
  already one-bin-lagged arrival bin. B-to-C isolates phase under that imposed lag.

All inventories use the same NEW resident counts including staff once,2500
kcal/day,90 days of original new-case physical storage,365-day years and5%
stored-food loss. Stocks are minimum nonnegative repeating reserves,not a free
external loan. Periodicity is distinct from meeting meals. The unchanged food
diagnostic is unmet <=1e-8*max(1,annual needed kcal),not a fitted famine threshold.

## Every declared outcome

'''+table+'\n'+'''Across four alternative scenarios,A passes food at all 3,228 active provider
entries. B passes 2,892. C passes 2,706,of which 2,700 also complete every funded
mandatory bin. Six C entries pass food while missing mandatory work. Totals refer
to entries across alternative scenarios. They remain
visible rather than being dropped or given fictitious completed commitments.

All four cases have a SMALLER aggregate energy gap in C than B,while MORE
individual providers fail the numerical food check. Improving a total therefore
does not establish food sufficiency at every source. These are scenario energy
gaps,not observed hunger,mortality,abandonment or authority.

'''+ '\n'.join(f'![Collection calendar and food](figures/{p.name})' for p in figures)+'''

## Cargo and source accounting

Raw cargo=min(120000,max(0,new departures-120000*serial)). Packed raw cargo plus
missing raw cargo equals the original planned departure at every origin/month.
Every missing serial and partial final load is retained. Apply0.95 retention
ONCE to packed deliveries. Clock=((origin month+1)*365/12+job end hours/7) modulo
365 days retains the original imposed one-bin lag;this does not remove the lag
or reconstruct actual historical transport dates. B/C have identical cargo.

Unshipped raw grain stays identified at source/uncollected. The exported
“missing destination potential kcal” is the COUNTERFACTUAL retained supply had
that raw cargo been transported. It is not actual transport loss on unshipped
grain. Source production,monthly availability and planned source export ledgers
remain frozen;this is not a new event-time source-stock or harvest validation.
Missing grain is never silently added to destination food or reused elsewhere.

## Independent review and complete exports

Seven new partition/lag/partial-delivery/work-charge controls ran before outputs,
alongside ten event-inventory and seven worker controls. Independent review
imports neither worker packer,cargo partition nor food-event primitive. A sorted
list replays every worker choice and interval;nonoverlap,duty caps,services and
missing trip identities are checked. Separate scalar stocks and bracketed roots
check every active provider in A/B/C,all conservation channels and all216actor
summaries. Food and twelve-bin work flags stay separate before their conjunction.

'''+(f'Review checked {review["packed_trip_identities_checked"]:,} packed and {review["missing_trip_identities_checked"]:,} missing trip identities, '
        f'{review["worker_bins_checked"]:,} worker-bins and {review["active_provider_food_inventories_checked"]:,} food inventories.\n')+'''

All12522provider/accounting records are exported,including explicit unscored
sources. Four ZIP files contain every one of the56monthly calendar,event and
field packets. Archive entry bytes and every provider CSV field are independently
checked. All63model/calendar/export/CSV/manifest outputs are fresh byte exact.
Extract the four archives beside downloaded metadata to restore relative case
paths. Actual raw missing cargo and counterfactual retained arrival deficits
are separately labelled. No previous Earth atlas packet,map or default changed.

## Remaining programme

This is COLLECTOR-ONLY necessary work and destination cereal accounting. It does
not qualify geographic visits or a new control map. Next,new point-task funding
must use these new source budgets,then baseline and joint calendars must include
actual visit jobs. A provider-year must pass BOTH twelve mandatory bins and its
OWN full-year return-phase food test. Whole calendars cannot be combined by job
success. Every old/new outcome and failure must remain explicit.

Source within-bin crop/export availability,crew-carried food and food location,
complete diets and household/draft work,actual provider roles,dated occupation
and compatible size evidence,prospective transfer and mobile/nonstate/unaffiliated
resources remain open across release1–4/S1–S5. This is exposed development,not
empirical calibration or adoption. The historical full publisher still needs
the omitted private Vidarbha cache;the reviewed direct publisher preserves all
earlier research panels and does not claim a historical full rebuild.
'''
    report.write_text(text);page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data/continuous_collection_calendar';data.mkdir(parents=True,exist_ok=True)
    downloads=[]
    for source,name,label in [(OUT/'results.json','results.json','All twelve results and216 actor summaries'),(OUT/'review.json','review.json','Independent worker,cargo and food review'),
        (OUT/'export_review.json','export_review.json','Independent archive and provider checks'),(OUT/'replay.json','replay.json','Fresh byte replay'),(OUT/'controls.json','controls.json','Controls before production'),
        (PLAN,'plan.json','Prior declaration'),(OUT/'exports.json','exports.json','Archive hashes and cargo units'),(OUT/'providers.csv.gz','providers.csv.gz','Every provider CSV')]:
        shutil.copyfile(source,data/name);downloads.append((name,label))
    for case in r['cases']:
        name=case['key']+'.zip';shutil.copyfile(OUT/name,data/name);downloads.append((name,case['key'].split('_load')[0].replace('_',' ')+' complete calendars,events and fields ZIP'))
    section='''<!--continuous-collection-start--><section><h2>New collector calendars: missing cargo versus arrival phase</h2><details id="continuous-collection" class="panel"><summary>Twelve outcomes · every active provider retained,including partial delivery</summary>
<p><strong>NEW actual shipments and funded home services,unchanged collection-first worker rule.</strong> A supplies all planned cargo at original lagged bin starts. B supplies only packed cargo at the same starts. C supplies the SAME packed cargo at recorded return phases,retaining the imposed one-bin lag. A-to-B isolates missing loads;B-to-C isolates phase. Same people,staff,stores and meals;retention0.95 applied ONCE to packed deliveries. These calendars contain NO geographic visit jobs.</p>
<div class="table"><table><thead><tr>'''+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in cells(row))+'</tr>' for row in r['rows'])+'</tbody></table></div>\n'
    section+='\n'.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All twelve food and mandatory-work outcomes with every active provider retained','Aggregate food gaps improve while individual food failures increase under changed arrival phase']))
    section+='''<p>Across four alternative scenarios,A passes food at 3,228 provider entries,B at 2,892,and C at 2,706. Exactly 2,700 C entries pass both gates. Six C entries pass food while missing mandatory work. Totals refer to entries across alternative scenarios. All active providers remain scored. Aggregate C energy gaps shrink in every case even though more individual providers fail food. Numeric scenario gaps are not observed hunger or authority;greedy failure is not physical impossibility.</p>
<p>Independent sorted-list workers,services,intervals and all packed/missing trip identities pass. Scalar periodic stocks,grain ledgers and all216actor summaries checked. All56archive entries and12522provider records are independently verified;63fresh model/export files byte exact. Unshipped raw cargo stays identified at source;“missing destination potential” is counterfactual retained supply,NOT actual transport loss on unshipped grain.</p>
<p><strong>Collector-only schedules do not qualify new visit maps.</strong> New point jobs,whole calendars and each selected calendar's OWN return-food test remain next. Earlier maps/defaults stay byte unchanged. Source within-bin availability,crew-carried food/location,complete diets/work,dated occupation/size/provider roles,transfer and mobile/nonstate/unaffiliated resources remain open. No calibrated adoption.</p>
<p><a href="../../reports/CONTINUOUS_COLLECTION_CALENDAR_20261112.md">Methods,all outcomes and remaining programme</a> · '''
    section+=' · '.join(f'<a href="data/continuous_collection_calendar/{name}" download>{label}</a>' for name,label in downloads)+'</p></details></section><!--continuous-collection-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--continuous-collection-start-->[\s\S]*?<!--continuous-collection-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--continuous-destination-start-->' in html;html=html.replace('<!--continuous-destination-start-->',section+'\n<!--continuous-destination-start-->',1)
    for name,body in old:
        if name!='continuous-collection':assert f'<!--{name}-start-->{body}<!--{name}-end-->' in html,name
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text());entry=dict(id='continuous_collection_calendar_20261112',status='model_only_new_collector_work_and_food_audit',evidence=str(report.relative_to(ROOT)),
        note='All12planned/packed/return comparisons retain partial delivery providers. Mandatory work and food flags separate;no new visit-map,source timing/ration/location or calibrated adoption.')
    usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,page.parent/'data/dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',results_sha256=sha(OUT/'results.json'),evidence_page_sha256=sha(page),
        producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'scripts/plot_continuous_collection_calendar.py']},
        figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={str((data/name).relative_to(page.parent)):sha(data/name) for name,_ in downloads},original_atlas_unchanged=True,default_adoption=False))
    for p in figures:print(p)
    print('Published12collector outcomes,2figures and12data downloads;no map changes.')


if __name__=='__main__':main()
