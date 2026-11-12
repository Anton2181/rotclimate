"""Publish all four old/four continuous resident cases and full field packets."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from plot_continuous_destination import plot
from settlement_locations_earth import sha,write
OUT=ROOT/'output/settlement_continuous_destination_20261112'
PLAN=ROOT/'calibration/settlement_continuous_destination_20261112/plan.json'


def cells(v):
    return [v['climate'].title(),str(v['hours_worker_year']),v['accounting'],f'{v["town_people"]:,.3f}',f'{v["civilian_people"]:,.3f}',f'{v["staff_people"]:,.0f}',str(v['active_sources']),f'{v["town_unmet"]:,.3f}',f'{v["collection_hours"]:,.1f}']


def main():
    r=json.loads((OUT/'comparison.json').read_text());review=json.loads((OUT/'comparison_review.json').read_text());replay=json.loads((OUT/'replay.json').read_text());summary=json.loads((OUT/'summary.json').read_text())
    assert review['status']==replay['status']=='passed' and review['comparison_sha256']==sha(OUT/'comparison.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_comparison.py')
    for name,digest in {**r['sources'],**r['producers'],**summary['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in replay['byte_exact_files'].items():assert sha(OUT/name)==digest,name
    physical=[]
    for row in r['rows']:
        folder=(OUT if row['accounting']=='continuous' else ROOT/'output/settlement_dispatch_seeded_20261112')/row['key'];v=json.loads((folder/'review.json').read_text())
        assert v['status']=='passed' and v['results_sha256']==sha(folder/'results.json');physical.append(dict(key=row['key'],accounting=row['accounting'],review=v))
        if row['accounting']=='continuous':assert v['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_destination.py')
    write(OUT/'physical_reviews.json',dict(status='passed',case_reviews=physical,comparison_review=review))
    figures=plot();headers=['Climate','Farm h','Inventory','Town residents','Civilian residents','Institutional residents','Active sources','Unmet kcal','Collection hours']
    table='|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(cells(v))+'|\n' for v in r['rows'])
    report=ROOT/'reports/SETTLEMENT_CONTINUOUS_DESTINATION_20261112.md'
    text='''# Continuous destination food inside finite resident feedback

Declaration `aacf2ddb` preceded resident outputs. All four parent cases behind
the eight coherent-year point maps are retained:raw/corrected climate,600/300
annual farm hours,120000 kcal trips and all bins open. Four old and four new
rows are published. This is exposed model development,not an empirical census,
a blind transfer test or calibrated adoption.

## What changed inside the shared ledger

The original model eats all destination-bin meals immediately after supply,
clips capacity afterwards and then applies stored-food loss. The new version
pulses supply at the same arrival-bin start,clips immediately to capacity and
integrates continuous meals and exponential stored loss until the next bin.
It finds the minimum repeating stock;periodicity does not establish sufficiency.

At EVERY resident trial,the same finite ledger recomputes civilian/rural meals,
field workers,crop production,source surplus/export inventories,dispatch scales,
institutional residents and integer collector trips/monthly hours. The original
geographic cells,owners,nodes,directed paths,minimum communities,source monthly
food assumptions,one-bin shipment lag and0.95 retention stay fixed. No grain,
people or free staff are added. Staff meals occur once inside total meals.
Destination physical storage is90 days of the CURRENT trial total resident
meals;unlike the headroom diagnostic,it is not frozen at the original population.

The declared64-point resident scan,known150-person staff threshold,24 resident
bracket refinements and40 work/food dispatch refinements stay fixed. Displayed
food ceilings use the new continuous convention and the parent's normalized
42-step search/downward margin. A versioned class and scoped writer factory
preserve every original model/writer byte. A failure control checks restoration.

## All old/new outcomes

'''+table+'\n'+'''Proposed town residents fall164.036–721.505 per case. The two600-hour cases
retain their active source counts;each300-hour case has one fewer active source
under the unchanged searched family. Individual reductions are retained even
when a site crosses the staff threshold. This is not proof of absent communities,
an unavoidable physical loss or globally optimal resident/logistics planning.
All positive new allocations pass their source food,continuous destination food
and monthly integer collection-hour checks within the declared numeric tolerance.
Outside rural people and their existing deficits remain in the same ledger.

'''+ '\n'.join(f'![Continuous resident feedback](figures/{p.name})' for p in figures)+'''

## Complete cohorts,review and replay

All144 actor summaries and8348 provider/accounting records are exported,including
providers at zero in both versions. Full original and new field packets retain
origin food/work,people,shipments,integer trips and monthly work. Old fields that
were never recorded (peak stock,shortfall duration,periodic residual) remain null
in the comparison CSV;they are not fabricated from the new convention.

Independent physical review imports no resident solver or new inventory primitive.
It rebuilds rural allocations,field production,rural/export inventories,origin
dispatch,cargo retention/lag,integer trip work and shared secondary-duty hours.
Destination stocks and the explicit staff-threshold trial use separate scalar
continuous integration and bracketed periodic stocks. Displayed food ceilings,
source/people/grain conservation and every actor/provider export are checked.
Eleven fresh model result/field/summary/comparison/CSV files are byte exact.
Twelve new primitive/factory controls pass,including independent scalar parity,
zero-loss/mixed-loss cases,capacity/meal order,interior periodic reserve,variable
rates/durations,finite population/work and factory restoration on writer failure.

## Publication limits and next dependency

All earlier Earth atlas files,point maps and defaults stay byte unchanged.
These are bin-start destination food results,NOT collector-return food or new
point-map qualifications. The new actual shipments and workers must be packed
into new calendars and their return times checked before new map publication.
The earlier collector/visit schedules cannot be reused against changed cargo.
Any source/return-time failure stays explicit;it cannot be repaired by combining
successes from incompatible calendars or inventing imports.

Source food remains monthly. Crew-carried rations,food location,complete diets,
household/draft work and actual provider functions remain unresolved. The whole
release1–4/S1–S5 programme also retains dated occupation/compatible size evidence,
prospective transfer and mobile/nonstate/unaffiliated resources. None is replaced
by a cereal feasibility result. Normal research publishes all rows,figures and
downloads. The historical full publisher still lacks the private Vidarbha cache;
this direct publication preserves earlier panels and does not claim a full rebuild.
'''
    report.write_text(text);page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data';downloads=[]
    for source,name,label in [(OUT/'comparison.json','continuous_destination_comparison.json','All eight outcomes and144 actor summaries'),(OUT/'physical_reviews.json','continuous_destination_reviews.json','Independent physical and export reviews'),
        (OUT/'replay.json','continuous_destination_replay.json','Fresh replay'),(PLAN,'continuous_destination_plan.json','Prior declaration'),(OUT/'controls.json','continuous_destination_controls.json','Controls before production'),
        (OUT/'providers.csv.gz','continuous_destination_providers.csv.gz','Every provider comparison CSV')]:
        shutil.copyfile(source,data/name);downloads.append((name,label))
    for row in r['rows']:
        folder=(OUT if row['accounting']=='continuous' else ROOT/'output/settlement_dispatch_seeded_20261112')/row['key'];name=f'continuous_destination_{row["accounting"]}_{row["climate"]}_h{row["hours_worker_year"]}.npz'
        shutil.copyfile(folder/'fields.npz',data/name);downloads.append((name,f'{row["accounting"]} {row["climate"]} {row["hours_worker_year"]}h full fields'))
    section='''<!--continuous-destination-start--><section><h2>Continuous destination food inside finite resident feedback</h2><details id="continuous-destination" class="panel"><summary>Four parent and four new resident cases · every source/food/work trial recomputed</summary>
<p><strong>Recompute the finite ledger at every resident trial.</strong> Rural meals,field work,crop production,source/export stocks,dispatch,staff and integer collector jobs all respond to trial residents. New destination bins pulse supply,clip capacity immediately and integrate continuous meals/decay. Original cells,owners,paths,one-bin lag,0.95 retention and search settings stay fixed. Ninety-day stores scale with CURRENT trial residents. Staff meals are counted once.</p>
<div class="table"><table><thead><tr>'''+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in cells(row))+'</tr>' for row in r['rows'])+'</tbody></table></div>\n'
    section+='\n'.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All four old and four continuous resident allocations and active source counts','All provider changes including threshold losses and zero allocations']))
    section+='''<p>Town allocations fall164.036–721.505 residents per case;each300-hour case has one fewer active source. Every provider is retained,including zeros;all144actor summaries and8348provider records are downloadable. Every positive new allocation passes its source,continuous destination food and monthly collector-hour checks. A failed searched branch is not proof of physical impossibility or absent communities.</p>
<p><strong>Collector-return food remains unqualified.</strong> Changed shipments need NEW worker calendars and NEW return-time food checks before any new point maps. All earlier Earth atlas files,maps and defaults stay byte unchanged. Source within-bin availability,crew-carried rations/location,complete diets/work,dated occupation/size/provider roles,prospective transfer and mobile/nonstate/unaffiliated integration remain open. No calibrated adoption or actual authority claim.</p>
<p>Independent source,field,food,people,dispatch,trip and work reviews pass,along with scalar destination periodic stock,threshold and ceiling checks. All actor/provider exports checked;eleven fresh output files byte exact. Original unrecorded peak/duration fields remain null. Twelve primitive/factory controls pass;source files and older panels are preserved.</p>
<p><a href="../../reports/SETTLEMENT_CONTINUOUS_DESTINATION_20261112.md">Methods,all outcomes and remaining programme</a> · '''
    section+=' · '.join(f'<a href="data/{name}" download>{label}</a>' for name,label in downloads)+'</p></details></section><!--continuous-destination-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--continuous-destination-start-->[\s\S]*?<!--continuous-destination-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--meal-headroom-start-->' in html;html=html.replace('<!--meal-headroom-start-->',section+'\n<!--meal-headroom-start-->',1)
    for name,body in old:
        if name!='continuous-destination':assert f'<!--{name}-start-->{body}<!--{name}-end-->' in html,name
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text());entry=dict(id='settlement_continuous_destination_20261112',status='model_only_continuous_destination_resident_feedback',evidence=str(report.relative_to(ROOT)),
        note='Four old/four replanned finite-ledger cases;source/work/cargo recomputed. Bin-start destination food only,not new collector-return food or map/empirical adoption.')
    usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,data/'dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',comparison_sha256=sha(OUT/'comparison.json'),producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'scripts/plot_continuous_destination.py']},
        evidence_page_sha256=sha(page),figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={name:sha(data/name) for name,_ in downloads},original_atlas_unchanged=True,default_adoption=False))
    for p in figures:print(p)
    print('Published8old/new rows,2figures,14data downloads;no map changes.')


if __name__=='__main__':main()
