"""Publish all declared food-checked visit comparisons, methods and downloads."""
import json,re,shutil,sys
from html import escape
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
from plot_food_checked_visits import plot
OUT=ROOT/'output/continuous_food_visit_calendars_20261112'

def visit_cells(v):
    return [v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['stage'],v['policy'],str(v['funded_visits']),str(v.get('physically_scheduled_visits') if v.get('physically_scheduled_visits') is not None else 'Unscored'),str(v.get('qualified_visits') if v.get('qualified_visits') is not None else 'Unscored'),str(v.get('qualified_providers') if v.get('qualified_providers') is not None else 'Unscored')]
def food_cells(v):
    return [v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['policy'],v['accounting'],str(v['scored_providers']),str(v['food_no_shortage']),f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/v["needed"]:.6f}']
def table(headers,rows):
    return '<div class="table"><table><thead><tr>'+''.join('<th>'+escape(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def mdtable(headers,rows):return '|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(v)+'|\n' for v in rows)

def main():
    r=json.loads((OUT/'results.json').read_text());digest=sha(OUT/'results.json')
    for name in ('review','summary_review','map_review','download_review'):
        q=json.loads((OUT/(name+'.json')).read_text());assert q['status']=='passed' and q['results_sha256']==digest
    for name in ('replay','map_replay','download_replay'):
        q=json.loads((OUT/(name+'.json')).read_text());assert q['status']=='passed'
        for file,d in q['byte_exact_files'].items():assert sha((ROOT if file.startswith('atlases/') else OUT)/file)==d
    for file,d in r['unchanged_map_sha256'].items():assert sha(ROOT/file)==d
    figures=plot();vh=['Climate','Farm h','Crew','Stage','Policy','Funded tasks','Physical tasks','BOTH-qualified tasks','BOTH providers'];fh=['Climate','Farm h','Crew','Policy','Food test','Active providers','Food passes','Unmet kcal','Unmet %'];vr=[visit_cells(v) for v in r['visit_rows']];fr=[food_cells(v) for v in r['food_rows']]
    report=ROOT/'reports/FOOD_CHECKED_VISITS_20261112.md'
    methods='''Declaration `4d496baf` preceded every output in this phase. Eight NEW point-job plans
use the four continuous-resident parents, exact recorded directed b3_p0 paths,
600/300 farm hours and crew1/4. The unchanged allocator spends ONLY the new
reserved patrol slice. Unpacked mandatory collection never finances extra visits.
The conditional resident plans differ from the older point-map parents; task
preservation below refers to the NEW baseline, not to those older allocations.

Each plan is packed with unchanged collection-first and joint-duration-first
worker policies: 50 duty hours/person/bin, 7*365/12 calendar hours, actual integer
collector trips, synchronized crews and funded divisible home commitments.
Actual physical visits remain charged even when mandatory work or food fails.
Greedy failure is not evidence that every possible schedule is impossible.

A supplies every planned load at the original lagged bin starts; B supplies only
packed loads at the same starts; C supplies the SAME packed loads at return
phases within the imposed one-bin lag. Retention 0.95 applies ONCE. All active
providers stay in each A/B/C inventory, including partial delivery. Baseline
collection prefixes and all A/B/C food fields equal the collector-only audit,
including duplicated baseline results between crews. Food passes use the fixed
unmet<=1e-8*max(1,annual needed kcal) diagnostic, not a fitted famine threshold.
Each inventory has 365 days, uniform 2500 kcal/person/day, staff included once,
90-day physical stores, 5% annual stored loss and minimum repeating reserves.

Choose exactly ONE complete policy per provider for all 12 bins. It qualifies
only when active, every mandatory bin completes AND its OWN C food passes.
Retain a BOTH-qualified baseline unless the alternate also passes BOTH gates,
contains every baseline (month,actor,target) identity and adds at least one.
Equal sets and any lost identity retain baseline. A sole qualified alternate
can recover a failed baseline; neither-qualified providers retain the baseline
physical trace with zero qualified tasks. No job-by-job or food/calendar union.
Physical completion, own food and their conjunction remain separate fields.

The point CSV partitions every request into qualified, schedule-unqualified,
route-unreachable, provider-work-unavailable or capacity-unmet. It additionally
retains funded/physical/baseline-BOTH masks and physical/nonphysical failure
subchannels. Provider and policy IDs by bin permit exact task identity checking.

The eight optional experimental maps under Supply-supported reach display ONLY
qualified point tasks. Their provider table and CSV show actual selected-calendar
arrivals, return-phase stocks and food gaps. The displayed planning ceiling is
explicitly the parent continuous BIN-START cereal ceiling, not a newly solved
return-phase resident maximum. Parent dispatch scale and source gate are likewise
labelled as planned before omissions. Failed qualification does not move residents.
Background, intervening land, mobile and unaffiliated contexts remain unscored.
'''
    validation='''Independent directed-path and scalar allocation review checks every funded job.
Separate sorted-list worker replays check all choices, services, crew intervals,
nonoverlap and duty limits; all raw packed/missing serials and event cargo are
checked. Independent scalar food roots and conservation check all 48 policy
outcomes and every active inventory, before strict whole-year reconstruction.
Six new selector controls and the retained allocator, worker, joint, year, cargo
and event controls ran before production. Four trace controls verify display bins.

Fresh replay matches 244 model files, 22 map exports and 12 download exports.
Independent map review checks every case, exact NEW-parent residents and work,
all point CSV rows, binary masks, selected food/physical flags, scalar stock paths
and visited pixels. Download review checks 240 archive entries, all 58,436
provider outcomes and all 80 typed comparison rows. Eight ZIPs contain complete
monthly worker/crew/cargo calendars, policy food/events, selected fields and case
metadata. Extract them beside results.json to restore the recorded paths.
All earlier data/maps remain byte identical; three UI integration files are
explicitly tracked before/after to add the optional family. Earlier defaults stay.
'''
    limits='''This is a necessary calendar/destination-cereal conjunction under supplied work,
uniform destination meals and MONTHLY source availability. It does not locate
crew meals in transit, issue carried rations, validate within-bin source crops
and exports, or complete diets, household and draft work. Unshipped raw grain
stays identified at source; missing destination potential is counterfactual,
not transport loss on unshipped grain. Actual provider roles, dated occupation,
compatible size/extent/sampling evidence, prospective transfer, central fiscal
and military functions, mobile/nonstate/unaffiliated resources remain open.
Release1–4/S1–S5 remain a whole programme; these are not historical population
calibration, observed visits, held blocks or authority. No default adoption.

Next audit the chronology of source food availability and crew food location
before treating destination stocks as complete annual provisioning. Keep the
physics queue independent. The historical all-evidence publisher still lacks
the private Vidarbha cache; this direct reviewed publication exposes its scope.
'''
    text='# NEW point visits with whole-calendar and OWN destination cereal checks\n\n'+methods+'\n## Every declared visit outcome\n\n'+mdtable(vh,vr)+'\n## Every declared policy food outcome\n\n'+mdtable(fh,fr)+'\n'+ '\n'.join(f'![Food-checked visit comparison](figures/{p.name})' for p in figures)+'\n\n## Independent review and reproduction\n\n'+validation+'\n## Remaining whole programme\n\n'+limits
    report.write_text(text)
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data/food_checked_visits';data.mkdir(parents=True,exist_ok=True)
    names=['results.json','funded_results.json','funded_fields.npz','selected_fields.npz','review.json','summary_review.json','funded_review.json','replay.json','map_review.json','map_replay.json','map_exports.json','atlas_publication.json','download_review.json','download_replay.json','exports.json','providers.csv.gz','visit_comparisons.csv','food_comparisons.csv','calendar_controls.json','funded_controls.json']
    names=[n for n in names if (OUT/n).exists()]+[c['key']+'.zip' for c in r['cases']]
    for name in names:shutil.copyfile(OUT/name,data/name)
    shutil.copyfile(ROOT/'calibration/continuous_food_visit_calendars_20261112/plan.json',data/'plan.json');names+=['plan.json']
    section='<!--food-checked-visits-start--><section><details id="food-checked-visits"><summary>New point visits: whole provider calendar AND its OWN destination cereal</summary><p>All 32 visit comparisons and 48 policy food outcomes are retained, including failures and partial delivery. Each provider selects ONE whole calendar for every bin. Both mandatory work and that calendar’s OWN destination cereal must pass. Conditional parent residents remain unchanged.</p>'+table(vh,vr)+table(fh,fr)
    section+=''.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All new funded, baseline, joint and whole-year qualified point tasks','All 48 planned, packed and return-phase policy food outcomes']))
    section+='<p>Eight OPTIONAL experimental point maps are available under Supply-supported reach. Every baseline task passing BOTH gates is retained. This preservation applies within the NEW plans, not the older unaudited allocations. Actual provider tables show selected return-phase stocks and unmet cereal; the planning ceiling is the parent bin-start ceiling. Physical completion, own food and conjunction remain distinct. Points are tasks, not held blocks or authority. Earlier map bytes and defaults stay unchanged.</p><p>A-to-B isolates omissions; B-to-C isolates phase for the SAME packed cargo. Original one-bin lag and retention 0.95 ONCE remain. All active providers are scored, including partial delivery; missing raw grain stays at source. Source within-bin availability, crew-carried rations and food location, complete diets/work, dated occupation/size/roles, prospective transfer and mobile/nonstate/unaffiliated contexts remain open.</p><p>Independent full workers, cargo, scalar food, strict task identities, point masks, CSVs and map pixels pass. Fresh 244 model files, 22 map files and 12 download files match byte for byte. Every one of 240 archived packets and 58,436 provider outcomes is checked.</p><p><a href="../../reports/FOOD_CHECKED_VISITS_20261112.md">Methods, all outcomes and remaining programme</a> · <a href="../earth_fit/#layer=reach_defacto&amp;climate=corrected&amp;experimental=1&amp;variant=foodvisits600_crew1">Open optional point map</a> · '
    section+=' · '.join(f'<a href="data/food_checked_visits/{n}" download>{escape(n)}</a>' for n in names)+'</p></details></section><!--food-checked-visits-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--food-checked-visits-start-->[\s\S]*?<!--food-checked-visits-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--continuous-collection-start-->' in html;html=html.replace('<!--continuous-collection-start-->',section+'\n<!--continuous-collection-start-->',1)
    for name,body in old:
        if name!='food-checked-visits':assert f'<!--{name}-start-->{body}<!--{name}-end-->' in html,name
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text());entry=dict(id='food_checked_visits_20261112',status='model_only_own_destination_food_and_whole_calendar_points',evidence=str(report.relative_to(ROOT)),note='All32visit/48food rows;8 optional maps. Necessary calendar/destination-cereal conjunction only. Source timing,crew rations/location,roles,complete diets and calibrated adoption unresolved.');usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,page.parent/'data/dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',results_sha256=digest,evidence_page_sha256=sha(page),producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'scripts/plot_food_checked_visits.py']},figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={n:sha(data/n) for n in names},visit_rows=32,food_rows=48,default_adoption=False))
    print('Published32visit/48food rows,2figures and',len(names),'complete downloads.')
if __name__=='__main__':main()
