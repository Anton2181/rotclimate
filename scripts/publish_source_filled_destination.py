"""Publish all48matched destination results and the complete scoped grain ledger."""
import json,re,shutil,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_filled_destination_20261113'

def cells(v):return [v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['policy'],v['accounting'],str(v['scored_providers']),str(v['destination_food_pass']),str(v['mandatory_complete']),str(v['source_export_pass']),str(v['source_rural_pass']),str(v['all_gates_pass']),f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/v["needed"]:.6f}']
def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());er=json.loads((OUT/'export_review.json').read_text());assert review['status']==er['status']=='passed' and review['results_sha256']==er['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_source_filled_destination.py') and er['reviewer_sha256']==sha(ROOT/'scripts/review_source_filled_exports.py')
    for n,d in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/n)==d,n
    for receipt in ('replay','export_replay'):
        q=json.loads((OUT/(receipt+'.json')).read_text());assert q['status']=='passed'
        for n,d in q['byte_exact_files'].items():assert sha(OUT/n)==d,n
    keys=[v['key'] for v in r['rows'] if v['policy']=='selected' and v['accounting']=='A'];columns=[(p,a) for p in ('baseline','joint','selected') for a in ('A','B')];values=[[next(v for v in r['rows'] if v['key']==k and v['policy']==p and v['accounting']==a) for p,a in columns] for k in keys];figures=[]
    for field,title,filename,formatter in [('destination_food_pass','Destination food pass counts · every active provider scored','source_filled_destination_passes_20261113.png',lambda v:f'{int(v):d}'),('gap','Unmet cereal / annual destination meals · percent','source_filled_destination_gaps_20261113.png',lambda v:f'{v:.5f}')]:
        z=np.array([[v[field] if field!='gap' else 100*v['unmet']/v['needed'] for v in row] for row in values]);fig,ax=plt.subplots(figsize=(12,7));ax.imshow(z,aspect='auto',cmap='YlGnBu');ax.set_yticks(np.arange(8),[k.replace('corrected','Corr.').replace('raw','Raw').replace('_h',' · ').replace('_crew','h · crew ') for k in keys]);ax.set_xticks(np.arange(6),['Baseline A','Baseline B','Joint A','Joint B','Selected A','Selected B'],rotation=25,ha='right');mid=(z.max()+z.min())/2
        for i in range(8):
            for j in range(6):ax.text(j,i,formatter(z[i,j]),ha='center',va='center',fontsize=10,color='white' if z[i,j]>mid else '#20282b')
        ax.set_title(title,fontsize=12);fig.text(.5,.025,'A: exact previous packed-cargo C. B: SAME return times, source-withdrawn raw cargo × 0.95 once.\nAll 48 outcomes retained. Source rural failures remain: destination food alone cannot qualify complete provisioning.',ha='center',fontsize=9);fig.subplots_adjust(left=.24,right=.99,top=.92,bottom=.23);figures.append(ROOT/'reports/figures'/filename);fig.savefig(figures[-1],dpi=160);plt.close(fig)
    headers=['Climate','Farm h','Crew','Calendar','Food test','Active providers','Destination food pass','Mandatory year pass','Source export pass','Source rural pass','ALL gates','Unmet kcal','Unmet %'];rows=[cells(v) for v in r['rows']]
    body=f'''Declaration `203fc49b` preceded every output. All24fixed source/calendar plans
remain: eight point plans × baseline, joint and previously selected whole years.
Every active provider is scored, including partial deliveries and failed calendars.
Parent people, destination90-day stores, routes, actual worker jobs, return phases,
original imposed one-bin lag and numerical food threshold remain unchanged.

A EXACTLY reproduces each previous OWN-calendar C destination account: all packed
raw requests ×0.95 at their recorded lagged return phases. B uses the SAME jobs,
return times and food convention, replacing each raw load with its source-store
withdrawal ×0.95 ONCE. No extra lag, retention or food is added. Every original
(month,origin,serial) request ID joins exactly once; missing, duplicate or changed
cargo is rejected. An unfilled source request is counterfactual demand, not an
actual transport loss. Raw request=withdrawn+unfilled; retained missing potential
is explicitly a counterfactual destination amount.

Destination time=((origin month+1)*365/12+job end hours/7) modulo365 days.
Source pickup time and destination return time stay distinct. Continuous cereal
meals include staff once at2500kcal/person/day,365days,5%stored loss,90-day physical
capacity and minimum repeating reserves. Food pass remains unmet<=1e-8*max(1,annual
needed kcal). This is an unchanged numerical diagnostic, not a fitted famine
threshold. Physical mandatory-year, source-export, source-rural and destination
food flags are distinct before their conjunction.

In selected raw300h plans destination food passes decline from652 to14(crew1)
and671 to15(crew4); corrected300h from696 to16 and710 to17. These discontinuous
pass counts reflect the strict no-shortage threshold and conditional resident
plans near their earlier food bound. Aggregate selected300h gaps increase about
0.0141–0.0151percentage points. They are not mortality, abandonment or historical
hunger estimates. B creates no new food passes, and unmet energy never improves
under the same clocks. All48declared rows remain; no winning subset is promoted.

EVERY source rural conjunction remains failed under the frozen365-day source
store convention. ZERO providers pass all source, work and destination gates,
including providers whose destination food passes B. B is a diagnostic propagation
of physical export-store withdrawals, not certified provisioning or permission
to ignore local source meals. No residents, capacities, calendars, map points or
defaults are replaced. Earlier destination packets remain byte identical.

Twelve new ID/partial/zero/retention controls plus source/event/partition controls
make50passes BEFORE production. Independent review reconstructs all
{review['request_ID_joins_checked']:,}request joins and
{review['grouped_return_events_checked']:,}grouped return events. Separate scalar
stocks, bracketed minimum-periodic roots and conservation check every one of
{review['active_provider_food_inventories_checked']:,}active provider inventories
and{review['actor_rows_checked']:,}actor rows. A fields are exact prior C; B pass
sets are subsets of A. Full source-rural failures stay exposed throughout.
All49model/field/event files freshly reproduce byte for byte.

All50,088provider/account CSV records are independently checked, including inactive
sources explicitly unscored. The24source-to-active-destination raw-grain mass
ledgers close: actual diagnostic transport loss is0.05of SOURCE-WITHDRAWN raw
cargo only. No transport loss is charged on unfilled source requests. Remaining
source stores, rural meals/losses, export losses/uncollected grain and destination
stocks/meals/losses/overflow are explicit. These scoped ledgers exclude outside
cells and inactive destination meals; conservation does not establish whole-world
food sufficiency. All3CSV/chain export files freshly reproduce byte for byte.
Full NPZs preserve each provider/account/flag and every grouped return pulse,
original packed potential, source-filled cargo and retained missing potential.

The next dependency is the source reserve convention itself: one year of nominal
meal energy in storage cannot also pay storage loss between annual harvests.
Derive and expose a loss-aware minimum reserve bound with explicit units before
any new source-capacity scenario; do not tune capacities or dates to these scores.
Actual storage buildings/utilization, crew-carried food and food location, complete
diets/household/draft work, dated occupation/sizes/roles, prospective transfer and
mobile/nonstate/unaffiliated integration remain open across release1–4/S1–S5.
Keep the physics queue separate. No calibrated/default/map adoption or authority
claim follows from destination food or a balanced numerical grain ledger.
'''
    report=ROOT/'reports/SOURCE_FILLED_DESTINATION_20261113.md';report.write_text('# Fixed source withdrawals propagated to destination food\n\n'+body+'\n## All48matched outcomes\n\n|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(v)+'|\n' for v in rows)+'\n'+ '\n'.join(f'![Matched source-filled destination food](figures/{p.name})' for p in figures)+'\n')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data/source_filled_destination';data.mkdir(parents=True,exist_ok=True);names=['results.json','controls.json','review.json','replay.json','exports.json','export_review.json','export_replay.json','providers.csv.gz','transport_and_chain_mass.json',*r['files_sha256']]
    for n in names:shutil.copyfile(OUT/n,data/n)
    shutil.copyfile(ROOT/'calibration/source_filled_destination_20261113/plan.json',data/'plan.json');names+=['plan.json']
    section='<!--source-filled-destination-start--><section><details id="source-filled-destination"><summary>Destination food after source pickup deficits: all 48 matched outcomes</summary><p>A exactly reproduces the previous packed-cargo C accounts. B uses the SAME fixed jobs, return times, residents and stores, with source-withdrawn raw cargo ×0.95 ONCE. The original one-bin lag remains; no new timing or retention. Every active provider, including failed and partial calendars, stays scored.</p><div class="table"><table><thead><tr>'+''.join('<th>'+v+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'+''.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All 48 matched destination food pass counts','All 48 matched destination cereal energy gaps']))
    section+='<p>B creates no new food passes. Selected 300h cases fall to 14–17 destination food passes, while aggregate gaps rise only about 0.0141–0.0151 percentage points: strict numerical thresholds and tight conditional resident plans matter. These are not historical hunger or mortality estimates.</p><p>ZERO providers pass ALL source, work and destination gates. Source rural failures remain at the original 365-day store. A destination pass cannot repair them. No capacity, resident, calendar, map or default adoption follows. Earlier 791 Earth assets and destination packets remain unchanged.</p><p>All request IDs, retained pulses, scalar minimum repeating inventories, actor/provider rows and 24 scoped source-to-destination mass ledgers independently checked. Diagnostic transport loss applies ONLY to source-withdrawn raw cargo; unfilled source requests are not actual transport loss. All 49 model and 3 export files freshly match byte for byte. Outside cells and inactive destination meals are unscored in these scoped ledgers.</p><p>Crew-carried food/location, actual storage capacity, complete diets/work, dated occupation/sizes/roles, failed prospective transfer and mobile/nonstate/unaffiliated integration remain open.</p><p><a href="../../reports/SOURCE_FILLED_DESTINATION_20261113.md">Methods, all outcomes and remaining programme</a> · '+' · '.join(f'<a href="data/source_filled_destination/{n}" download>{n.replace("_fields.npz"," fields (NPZ)").replace("_events.npz"," events (NPZ)").replace("_"," ")}</a>' for n in names)+'</p></details></section><!--source-filled-destination-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--source-filled-destination-start-->[\s\S]*?<!--source-filled-destination-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--source-pickup-calendars-start-->' in html;html=html.replace('<!--source-pickup-calendars-start-->',section+'\n<!--source-pickup-calendars-start-->',1)
    for n,b in old:
        if n!='source-filled-destination':assert f'<!--{n}-start-->{b}<!--{n}-end-->' in html,n
    page.write_text(html);registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text());entry=dict(id='source_filled_destination_20261113',status='fixed_source_filled_destination_food_diagnostic',evidence=str(report.relative_to(ROOT)),note='All48matched source-filled destination outcomes. Source rural failures retained;zero all-gate providers. Scoped grain conservation,not certified complete provisioning or map/default adoption.');usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,page.parent/'data/dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',results_sha256=sha(OUT/'results.json'),producer_sha256=sha(Path(__file__)),figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={n:sha(data/n) for n in names},prior_assets_byte_exact=len(r['unchanged_atlas_sha256']),default_adoption=False));print('Published48matched destination rows,2figures and',len(names),'downloads.')
    for p in figures:print(p)
if __name__=='__main__':main()
