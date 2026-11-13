"""Publish every fixed source pickup failure and full two-store fields."""
import json,re,shutil,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_food_events_20261113'

def cells(v):return [v['climate'].title(),str(v['hours_worker_year']),str(v['crew']),v['policy'],str(v['active_providers']),str(v['export_request_pass_providers']),str(v['both_providers']),f'{v["raw_requested"]:,.3f}',f'{v["raw_unfilled"]:,.3f}',f'{100*v["raw_unfilled"]/v["raw_requested"]:.6f}',f'{v["rural_unmet"]:,.3f}']
def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());er=json.loads((OUT/'export_review.json').read_text());assert review['status']==er['status']=='passed' and review['results_sha256']==er['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_source_pickup_calendars.py') and er['reviewer_sha256']==sha(ROOT/'scripts/review_source_pickup_exports.py')
    for n,d in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/n)==d,n
    for receipt in ('replay','export_replay'):
        replay=json.loads((OUT/(receipt+'.json')).read_text());assert replay['status']=='passed'
        for n,d in replay['byte_exact_files'].items():assert sha(OUT/n)==d,n
    figures=[];fig,axes=plt.subplots(1,2,figsize=(13,6));colors=dict(baseline='#b88b5a',joint='#6a9e96',selected='#426b85')
    for ax,hours in zip(axes,(600,300)):
        keys=[v['key'] for v in r['rows'] if v['policy']=='selected' and v['hours_worker_year']==hours];y=np.arange(4)
        for offset,policy in [(-.23,'baseline'),(0.,'joint'),(.23,'selected')]:
            values=[100*next(v for v in r['rows'] if v['key']==k and v['policy']==policy)['raw_unfilled']/next(v for v in r['rows'] if v['key']==k and v['policy']==policy)['raw_requested'] for k in keys];ax.barh(y+offset,values,height=.22,color=colors[policy],label=policy)
            for j,v in enumerate(values):ax.text(v+max(values)*.015,j+offset,f'{v:.6f}%',va='center',fontsize=7)
        ax.set_yticks(y,[k.replace('corrected','Corr.').replace('raw','Raw').replace('_h'+str(hours),'').replace('_crew',' · crew ') for k in keys]);ax.invert_yaxis();ax.set_title(f'{hours} farm hours · axis scale differs',fontsize=11);ax.set_xlim(0,max(v['raw_unfilled']/v['raw_requested']*100 for v in r['rows'] if v['hours_worker_year']==hours)*1.3);ax.set_xlabel('Raw request unfilled at source · percent');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.91),ncol=3,frameon=False,fontsize=9);fig.suptitle('Raw source pickup availability across all 24 fixed collector calendars',fontsize=12)
    fig.text(.5,.025,'Source overflow quota, physical export stores and pickup times are explicit. No source transport retention.\nRural food failures remain visible; these diagnostic withdrawals do not qualify shipments or replace destination food.',ha='center',fontsize=9);fig.subplots_adjust(left=.1,right=.99,top=.78,bottom=.2,wspace=.38);figures.append(ROOT/'reports/figures/source_pickup_calendars_gaps_20261113.png');fig.savefig(figures[-1],dpi=160);plt.close(fig)
    groups=[(mode,hours) for mode in ('raw','corrected') for hours in (600,300)];example=[]
    for mode,hours in groups:
        matched=[v for v in r['rows'] if v['climate']==mode and v['hours_worker_year']==hours];assert len({v['export_request_pass_providers'] for v in matched})==1;assert all(v['both_providers']==v['rural_food_pass_providers']==0 for v in matched);example.append(matched[0])
    fig,ax=plt.subplots(figsize=(11,5.4));y=np.arange(4);ax.barh(y-.16,[v['active_providers'] for v in example],height=.3,color='#bbbcb2',label='Parent active providers');ax.barh(y+.16,[v['export_request_pass_providers'] for v in example],height=.3,color='#426b85',label='Export requests pass · rural meals still fail')
    for i,v in enumerate(example):ax.text(v['active_providers']+8,i-.16,str(v['active_providers']),va='center',fontsize=9);ax.text(v['export_request_pass_providers']+8,i+.16,str(v['export_request_pass_providers']),va='center',fontsize=9)
    ax.set_yticks(y,[v['climate'].title()+' · '+str(v['hours_worker_year'])+'h' for v in example]);ax.invert_yaxis();ax.set_xlim(0,1050);ax.set_xlabel('Affiliated provider scenarios · not observed institutions');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.legend(frameon=False,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.01));fig.suptitle('Small aggregate cargo gaps can leave many individual providers short',fontsize=12)
    fig.text(.5,.025,'Export-pass counts are identical across all three policies and both crews within each parent; all 24 rows remain published.\nRural-meal AND export-request provider passes are ZERO in every case at the frozen one-year rural capacity.',ha='center',fontsize=9);fig.subplots_adjust(left=.18,right=.99,top=.76,bottom=.2);figures.append(ROOT/'reports/figures/source_pickup_calendars_providers_20261113.png');fig.savefig(figures[-1],dpi=160);plt.close(fig)
    headers=['Climate','Farm h','Crew','Calendar','Parent providers','Export pass','Rural AND export','Raw requested kcal','Raw unfilled kcal','Unfilled %','Rural unmet kcal'];rows=[cells(v) for v in r['rows']]
    body=f'''Declaration `049ba98e` preceded these source event outcomes. All eight NEW point
plans retain baseline, joint and the previously selected whole-provider-year
calendars: 24 fixed cases. Every actual packed collector request remains in the
audit, including jobs at rural-food-failed and calendar-unqualified sources.
There is no new job ordering, capacity/date adjustment or resident reallocation.

Harvest fills the physical rural store first; continuous local meals and decay
use the SAME fixed rural people, first eligible harvest-bin start and 365-day
capacity. ONLY actual rural overflow ×0.1 enters a separate physical export
store. Its capacity is the unchanged parent export_harvested field: the original
annual quota input under its365-day export reserve convention. Remaining rural
overflow and export-store overflow are explicit uncollected grain. Both stores
lose 5% annually. Grain in rural storage is never available to pickup requests.

Pickup time = origin bin start + (recorded collection start +7*outward graph
days +0.25handling hours)/7. All handling is placed before departure from source;
this is a supplied assumption, not a recovered historical location. Every pickup
occurs by the recorded job end. It is distinct from the destination's still
imposed one-bin lag. Equal-time harvest precedes requests; stable ascending
(month,origin,serial) IDs determine equal-time pickup priority. Raw request
min(120000,planned origin departure-120000*serial) is unchanged. No 0.95 transport
retention is applied at source. The earlier cargo/worker IDs remain exact.

Each origin has minimum repeating rural stock, its actual overflow quota pulses,
and minimum repeating export stock with discrete withdrawals. Request = withdrawn
+ unfilled exactly. Each store and their combined raw-grain ledger conserve mass.
An unfilled source request is counterfactual demand, not actual transport loss
or newly created unshipped grain. Diagnostic withdrawals are not shipment
qualification when rural meals fail. Destination food and every earlier map
remain unchanged; propagating source-filled cargo requires a separate audit.

Export request pass uses unfilled<=1e-8*max(1,annual raw request); rural food uses
the same fixed annual-energy-scaled numerical no-shortage diagnostic. These are
numerical ledger flags, not fitted famine thresholds. Every positive-population
origin still fails rural meals under the exposed one-year store convention.
Thus ZERO provider entries pass BOTH source gates in every case. Export-only
passes are840/861raw600h,44/724raw300h,869/889corrected600h and31/754corrected300h,
identical across both crews/all three fixed policies in each parent. Raw unfilled
volume nevertheless differs with pickup timing, ranging0.000342–0.035840% of
requests. A small aggregate deficit does not qualify every source.

Twenty-one new primitive controls cover local grain priority, exact quota/raw
mass, export capacity, same-time priority, partial/empty pickups, decay and
minimum periodic stocks without loans. Combined source/event/chronology suite:
37 passes BEFORE cohort outputs. Independent bisection/scalar two-store review
checks 200 synthetic cases/1539pickups, not historical observations. Full review
checks{review['pickup_requests_checked']:,}actual request IDs/clocks/cargo,
{review['origin_two_store_years_checked']:,}origin two-store years and
{review['actor_rows_checked']:,}actor summaries. Rural accounts match the prior
independently reviewed continuous-source audit. Separate compiled scalar export
ledgers check every raw withdrawal and partial request. All 25model/results files
and3origin/provider export files freshly reproduce byte for byte.

Full NPZs retain fixed origin/provider/actor IDs, people, harvest bin, capacities,
every annual rural/export mass channel and pass flag, and every pickup ID, origin,
month/serial, time, raw request, withdrawal and deficit. CSVs retain every origin
and provider, including failed and inactive flags. Harvest-bin and pickup-month
indices in the full fields/origin CSV are zero-based. No actor or source is removed
to improve reported totals; outside rural contexts remain in the preceding audit.

Next recompute destination inventory with source-filled raw cargo×0.95 ONCE,
keeping exactly the existing jobs, return phases and imposed lag. Keep source
rural failures separate and visible; no resulting destination pass can repair
them. Crew-carried rations/food location, complete diets and household/draft work,
dated occupation/sizes/roles, prospective transfer, mobile/nonstate/unaffiliated
integration and the independent physics queue remain open across release1–4/S1–S5.
No calibrated/default/map adoption, observed famine or authority inference.
'''
    report=ROOT/'reports/SOURCE_PICKUP_CALENDARS_20261113.md';report.write_text('# Fixed source pickups: physical grain availability and rural meals stay separate\n\n'+body+'\n## All 24declared outcomes\n\n|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(v)+'|\n' for v in rows)+'\n'+ '\n'.join(f'![Source pickup diagnostic](figures/{p.name})' for p in figures)+'\n')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data/source_pickup_calendars';data.mkdir(parents=True,exist_ok=True);names=['results.json','controls.json','review.json','replay.json','prototype_review.json','exports.json','export_review.json','export_replay.json','origins.csv.gz','providers.csv.gz',*r['files_sha256']]
    for n in names:shutil.copyfile(OUT/n,data/n)
    shutil.copyfile(ROOT/'calibration/source_food_events_20261113/plan.json',data/'plan.json');names+=['plan.json']
    section='<!--source-pickup-calendars-start--><section><details id="source-pickup-calendars"><summary>Source pickup timing: packed requests do not prove grain was available</summary><p>All 24 fixed baseline, joint and selected plans remain, including rural-food failures. Rural harvest fills its physical store first. ONLY overflow quota×0.1 enters the separate export store; raw pickups never take rural grain. Same frozen people, harvest bins and capacities. No new resident or destination solve.</p><div class="table"><table><thead><tr>'+''.join('<th>'+v+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'+''.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All 24source pickup gaps with unchanged calendar jobs','Export-only pass counts and zero combined source qualification']))
    section+='<p>ZERO providers pass rural meals AND source export requests in every case at the original365-day rural capacity. Export-only counts are 840/861 (raw, 600h), 44/724 (raw, 300h), 869/889 (corrected, 600h) and 31/754 (corrected, 300h). Small aggregate gaps do not certify every provider. This diagnoses model stores and chronology, not observed famine, institutions or authority.</p><p>Pickup=start+outward travel+0.25handling, distinct from the destination one-bin lag. No transport retention at source. Raw requested=withdrawn+unfilled; unfilled requests are not actual transport loss. Full request IDs and partial cargo are downloadable. Earlier destination inventories and all791 Earth assets remain unchanged. Source-filled destination effects and crew-carried food/location remain next; no map/default adoption.</p><p>37 controls precede outputs;200 independent synthetic controls, full request/scalar stock review and every origin/provider CSV field pass. All 25model and 3 export files are fresh byte exact. Dated occupation/roles/sizes, failed transfer, complete resources/work and mobile/nonstate/unaffiliated contexts remain open.</p><p><a href="../../reports/SOURCE_PICKUP_CALENDARS_20261113.md">Methods, all outcomes and remaining programme</a> · '+' · '.join(f'<a href="data/source_pickup_calendars/{n}" download>{n.replace("_fields.npz"," fields (NPZ)").replace("_"," ")}</a>' for n in names)+'</p></details></section><!--source-pickup-calendars-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--source-pickup-calendars-start-->[\s\S]*?<!--source-pickup-calendars-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--source-continuous-meals-start-->' in html;html=html.replace('<!--source-continuous-meals-start-->',section+'\n<!--source-continuous-meals-start-->',1)
    for n,b in old:
        if n!='source-pickup-calendars':assert f'<!--{n}-start-->{b}<!--{n}-end-->' in html,n
    page.write_text(html);registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text());entry=dict(id='source_pickup_calendars_20261113',status='fixed_source_event_availability_diagnostic',evidence=str(report.relative_to(ROOT)),note='All 24 fixedplans;explicit raw source requests and deficits,quota-only transfers and rural food failures. No destination replacement,capacity/date tuning or calibrated adoption.');usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,page.parent/'data/dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',results_sha256=sha(OUT/'results.json'),producer_sha256=sha(Path(__file__)),figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={n:sha(data/n) for n in names},prior_atlas_assets_byte_exact=len(r['unchanged_atlas_sha256']),destination_food_unchanged=True,default_adoption=False));print('Published24source pickup rows,2figures,',len(names),'downloads.')
    for p in figures:print(p)
if __name__=='__main__':main()
