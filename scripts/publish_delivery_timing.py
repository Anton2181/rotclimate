"""Publish every declared destination inventory outcome without changing maps."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from plot_delivery_timing import plot
from settlement_locations_earth import sha,write

OUT=ROOT/'output/network_visit_delivery_timing_20261112'
PLAN=ROOT/'calibration/network_visit_delivery_timing_20261112/plan.json'


def cells(v):
    return [v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['accounting'],str(v['scored_providers']),str(v['no_shortage_providers']),
            f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/v["needed"]:.6f}',f'{v["provider_shortfall_days"]/v["scored_providers"]:.4f}']


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());replay=json.loads((OUT/'replay.json').read_text())
    assert review['status']==replay['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_delivery_timing.py')
    for path,digest in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/path)==digest,path
    for path,digest in replay['byte_exact_files'].items():assert sha(OUT/path)==digest,path
    figures=plot();table='|Climate|Farm h|Crew|Inventory|Providers|No-shortage|Unmet kcal|Unmet %|Mean empty days|\n|---|---:|---:|---|---:|---:|---:|---:|---:|\n'
    table+=''.join('|'+ '|'.join(cells(v))+'|\n' for v in r['rows'])
    text='''# Destination inventories under fixed collector delivery times

Declaration `970bd428` preceded production outputs. This is a destination-only
cereal accounting audit on exposed development scenarios. It does not supply
new historical observations or qualify source food timing,crew-carried rations,
food location,complete diets,actual hunger or political authority.

## Matched comparison and actual finding

All eight coherent provider-year scenarios retain EVERY already-qualified
provider. Other providers remain explicitly unscored;their exclusion is not an
absence-of-community claim. Original residents,staff,origin owners,shipments,
selected calendars,90-day destination storage,2500 kcal/person/day,365-day year
and 5% annual stored-food loss stay fixed. Institutional people are included in
the same parent resident count once. The original imposed ONE-BIN dispatch lag
and 0.95 transport retention remain;retention is applied ONCE.

* A replays the exact original twelve-bin inventory:all of a bin's meals are
  eaten immediately after supply,capacity is applied to what remains,then
  storage loss is charged. Its residual energy gaps satisfy the original
  parent no-shortage tolerance for every scored provider.
* B uses continuous constant meals and exponential stored-food decay,with the
  same shipments pulsed at their original destination-bin starts. Capacity
  clips immediately after supply. A-to-B changes the inventory convention;
  it is NOT a pure delivery-phase effect.
* C keeps B's continuous inventory but pulses cargo at the selected collector
  job's return phase INSIDE its already-lagged destination bin. Only B-to-C
  isolates the declared delivery-phase change.

Every provider fails the same numerical no-shortage diagnostic in B and C.
Aggregate unmet cereal is about 0.2083% of annual meals in B and0.1909–0.1964%
in C. Recorded phases reduce the accounting gaps in all eight cases but do
not eliminate them. A complete twelve-bin worker calendar therefore does not
establish destination food sufficiency under this continuous accounting.
This does not prove an unavoidable physical shortfall:shipments/residents and
the parent's meal/stock convention were frozen,not jointly replanned here.

The source plans are tightly matched to the original meals-first recurrence.
Continuous meals keep cereal in storage during the bin and charge decay on
that stock. Later delivery can reduce storage exposure. This explains why
A-to-B must be shown separately from B-to-C. No extra supplies or externally
borrowed initial reserve are inserted to repair the result.

## All 24 declared rows

No-shortage means unmet <=1e-8*max(1,annual needed kcal),the unchanged parent
numeric diagnostic. This is not a fitted famine or historical significance
threshold. Empty days in B/C integrate time after stock depletion;A's days
remain its original coarse-bin diagnostic. Summed peak stocks and empty days
are per-provider quantities,not a simultaneous regional stock or outage.

'''+table+'\n'+'\n'.join(f'![Destination timing audit](figures/{p.name})' for p in figures)+'''

## Cargo,periodicity and independent review

For each selected collector trip,original origin/month/serial identifies
cargo=min(120000,max(0,original departures-120000*serial)). Retained cargo is
0.95 times that amount. Delivery time=((origin month+1)*365/12+recorded return
hours/7) modulo365days. Every original trip identity,cargo remainder,owner,
arrival-bin total and annual destination total is checked. Event downloads
combine simultaneous deliveries at the same provider/time and retain their
trip counts;source schedule hashes retain the underlying trip identities.

Between pulses,ds/dt=-daily meals-hazard*s until depletion,with
hazard=-log(0.95)/365. Pulses spill immediately above the unchanged capacity.
The annual inventory map is a clipped affine map;its smallest repeating stock
is calculated without assuming a free inherited reserve. A periodic shortage
can repeat,so convergence is distinct from sufficiency.

Ten manufactured controls ran before production:closed-form decay/depletion,
zero loss/demand/capacity,minimum repeating reserve,periodic shortage,overflow,
split/combined simultaneous pulses,meal/capacity convention,input preservation,
retained delay/year wrap/retention once,and invalid cargo/serial/clock inputs.
Random controls compare the analytic fixed point against scalar bisection.
The independent production reviewer imports neither inventory nor cargo model.
It reconstructs every original trip,uses scalar integration and independently
solves all periodic stocks by bracketing. It checks consumed+unmet=needed and
initial+supply=consumed+spoilage+overflow+final,every provider CSV field,all 18
actor rows in each scenario,and the matched inputs. Fresh results,fields,
provider CSV and eight aggregated event exports are byte exact.

'''+(f'Independent review checked {review["original_trip_identities_checked"]:,} original trip identities, '
         f'{review["aggregated_delivery_events_checked"]:,} aggregated events and '
         f'{review["scalar_provider_inventories_checked"]:,} provider/accounting inventories.\n')+'''

## Publication and remaining programme

All existing atlas packets,point maps and defaults stay byte unchanged.
The coherent-year maps describe a necessary worker scheduling gate;they are
not retroactively replaced by this separate destination accounting audit.
Normal research publishes all 24rows,the figures and all output downloads.

Replanning must keep the same finite source/food/work ledger and then recheck
source availability,integer collector jobs and actual worker intervals.
An unchanged-shipments demand-headroom diagnostic is a bounded next step;it
would not reallocate people or qualify actual populations. Dated occupancy,
settlement sizes/provider functions,prospective transfer,mobile/nonstate and
unaffiliated resources,source within-bin availability,crew rations/location,
complete diets and household/draft work remain open across release1–4/S1–S5.
No calibrated default or empirical adoption is made. The full historical
publisher still needs an omitted private Vidarbha cache;this direct publisher
preserves the earlier research page and does not claim a full rebuild.
'''
    report=ROOT/'reports/NETWORK_VISIT_DELIVERY_TIMING_20261112.md';report.write_text(text)
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data';downloads=[]
    for source,name in [(OUT/'results.json','timed_food_results.json'),(OUT/'review.json','timed_food_review.json'),(OUT/'replay.json','timed_food_replay.json'),
                        (OUT/'controls.json','timed_food_controls.json'),(PLAN,'timed_food_plan.json'),(OUT/'fields.npz','timed_food_fields.npz'),(OUT/'providers.csv.gz','timed_food_providers.csv.gz')]:
        shutil.copyfile(source,data/name);downloads.append((name,name))
    for source in sorted(OUT.glob('*_events.npz')):
        name='timed_food_'+source.name;shutil.copyfile(source,data/name);downloads.append((name,source.stem.replace('_',' ')))
    headers=['Climate','Farm hours','Crew','Inventory','Providers','No-shortage','Unmet kcal','Unmet %','Mean empty days']
    section='''<!--delivery-timing-start--><section><h2>Destination food inventories under fixed delivery times</h2><details id="delivery-timing" class="panel"><summary>24 matched outcomes · continuous inventories expose small cereal gaps</summary>
<p><strong>Every calendar-qualified provider is retained.</strong> A replays the original twelve-bin model,which eats all bin meals immediately after supply and applies capacity and decay afterwards. B uses continuous meals/decay with the same supply at destination-bin starts. C uses the same continuous model at the selected collector return phases. A-to-B changes the inventory convention;only B-to-C isolates the declared delivery phase.</p>
<p>All providers pass the original A numerical food check;zero pass B or C. Aggregate B gaps are about 0.2083% of annual cereal meals;C gaps are 0.1909–0.1964%. Recorded phases reduce gaps in every case but do not remove them. Same residents,shipments,90-day stores,5% annual storage loss, one-bin dispatch lag and 0.95 retention ONCE. No extra grain or borrowed initial reserve is inserted. This is destination-only cereal accounting,not observed hunger,source timing,crew ration/location validation,complete diets or authority.</p>
<div class="table"><table><thead><tr>'''+''.join(f'<th>{v}</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in cells(row))+'</tr>' for row in r['rows'])+'</tbody></table></div>\n'
    section+='\n'.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All eight inventory convention and delivery phase comparisons','All scored provider food gaps retained by scenario','Deterministic stock examples and recorded delivery phase distributions']))
    section+='''<p>No-shortage uses the unchanged parent tolerance,unmet ≤1e-8×max(1,annual needed kcal). This is a numerical diagnostic,not a fitted famine threshold. Empty days are a provider average;A retains its coarse-bin diagnostic. A repeating inventory can still be insufficient. Complete worker calendars alone do not establish continuous destination provisioning. All earlier maps/defaults remain unchanged;other providers remain explicitly unscored.</p>
<p>Ten controls ran before production. Independent original-trip/owner/cargo/bin/clock review,scalar inventory integration,bracketed periodic stocks,grain conservation,every provider CSV field and all actor rows pass. Eleven fresh result/field/CSV/event files are byte exact. Event exports combine simultaneous provider deliveries and retain trip counts. Source monthly food assumptions and crew food location remain unresolved.</p>
<p><a href="../../reports/NETWORK_VISIT_DELIVERY_TIMING_20261112.md">Methods,all outcomes and remaining programme</a> · '''
    section+=' · '.join(f'<a href="data/{name}" download>{label}</a>' for name,label in downloads)
    section+='</p></details></section><!--delivery-timing-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--delivery-timing-start-->[\s\S]*?<!--delivery-timing-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--provider-year-start-->' in html;html=html.replace('<!--provider-year-start-->',section+'\n<!--provider-year-start-->',1)
    for name,body in old:
        if name!='delivery-timing':assert f'<!--{name}-start-->{body}<!--{name}-end-->' in html,name
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text())
    entry=dict(id='network_visit_delivery_timing_20261112',status='model_only_destination_food_inventory_audit',evidence=str(report.relative_to(ROOT)),
        note='All 24matched accountings retain fixed people/cargo/calendars/lag. Continuous inventories expose small cereal gaps;no source intrabin validation,crew rations/location,observed hunger or map/default adoption.')
    usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,data/'dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),
        evidence_page_sha256=sha(page),producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'scripts/plot_delivery_timing.py']},
        figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={name:sha(data/name) for name,_ in downloads},original_atlas_unchanged=True,default_adoption=False))
    for p in figures:print(p)
    print('Published all 24destination timing rows,3figures and 15 data downloads;no map changes.')


if __name__=='__main__':main()
