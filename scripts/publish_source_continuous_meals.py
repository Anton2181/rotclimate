"""Expose fixed source-meal convention failures without changing atlas maps."""
import json,re,shutil,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_continuous_meals_20261113'

def cells(v):return [v['climate'].title(),str(v['hours_worker_year']),v['context'],v['accounting'],str(v['origins']),str(v['positive_people_origins']),str(v['positive_people_food_pass']),f'{v["unmet"]:,.3f}',f'{100*v["unmet"]/max(1,v["needed"]):.6f}']
def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());replay=json.loads((OUT/'replay.json').read_text());assert review['status']==replay['status']=='passed' and review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_source_continuous_meals.py')
    for n,d in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/n)==d,n
    for n,d in replay['byte_exact_files'].items():assert sha(OUT/n)==d,n
    keys=[(k,c) for k in r['cases'] for c in ('local','outside')];y=np.arange(8);fig,ax=plt.subplots(figsize=(12,6.4))
    for delta,account,label,color in [(-.17,'A','A: old monthly meals before capacity clip','#b98a5b'),(.17,'B','B: continuous meals, immediate physical clip','#467b91')]:
        values=[100*next(v for v in r['rows'] if v['key']==k and v['context']==c and v['accounting']==account)['unmet']/next(v for v in r['rows'] if v['key']==k and v['context']==c and v['accounting']==account)['needed'] for k,c in keys];ax.barh(y+delta,values,height=.31,label=label,color=color)
        for j,v in enumerate(values):ax.text(v+.03,j+delta,f'{v:.3f}%',fontsize=8,va='center')
    ax.set_yticks(y,[k.replace('corrected','Corr.').replace('raw','Raw').replace('_h',' · ')+'h · '+c for k,c in keys]);ax.invert_yaxis();ax.set_xlim(0,3.8);ax.set_xlabel('Unmet cereal / annual rural meals · percent');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.legend(loc='lower center',bbox_to_anchor=(.5,1.01),frameon=False,fontsize=9);fig.suptitle('Fixed rural sources: meal order and physical storage change the result',fontsize=13)
    fig.text(.5,.025,'Same harvests, people and 365-day rural capacity in ALL local and outside origins; no new export or resident solve.\nAll positive-population origins fail B. This diagnoses a model convention, not observed famine or abandonment.',ha='center',fontsize=9);fig.subplots_adjust(left=.27,right=.99,top=.80,bottom=.16);figures=[ROOT/'reports/figures/source_continuous_meals_gap_20261113.png'];fig.savefig(figures[0],dpi=160);plt.close(fig)
    h=-np.log(.95)/365;days=np.linspace(0,365,731);fed=np.log1p(365*h)/h;stock=np.maximum(0.,(365+1/h)*np.exp(-h*days)-1/h);required=np.expm1(h*365)/h
    fig,axes=plt.subplots(1,2,figsize=(12,5.2));axes[0].plot(days,stock,color='#467b91',label='Continuous meals + 5% annual stored loss');axes[0].plot(days,365-days,color='#99998b',linestyle='--',label='Zero-loss comparison');axes[0].axvline(fed,color='#b56b4c',linestyle=':');axes[0].set_ylabel('Stored cereal · days of supplied meals');axes[0].legend(frameon=False,fontsize=8);axes[0].set_title('Control: start with 365 days of food')
    axes[1].plot(days,np.maximum(0.,days-fed),color='#b56b4c');axes[1].set_ylabel('Unmet cereal · days of supplied meals');axes[1].set_title(f'Stock empties at day {fed:.2f}; gap {365-fed:.2f} days')
    for ax in axes:ax.set_xlabel('Days since one annual harvest');ax.grid(alpha=.15);ax.set_xlim(0,365)
    fig.suptitle('A year of meals in storage does not include the food lost while storing it',fontsize=12);fig.text(.5,.025,f'Analytic control only: one harvest, constant meals, immediate clip, no exports or new harvest dates.\nAt 5% loss, a capacity-only full-year reserve would need {required:.2f} meal-days; no new capacity is adopted.',ha='center',fontsize=9);fig.subplots_adjust(left=.08,right=.99,top=.82,bottom=.22,wspace=.28);figures.append(ROOT/'reports/figures/source_continuous_meals_control_20261113.png');fig.savefig(figures[-1],dpi=160);plt.close(fig)
    headers=['Climate','Farm h','Context','Inventory','All origins','Positive-person origins','Positive-person food passes','Unmet kcal','Unmet %'];rows=[cells(v) for v in r['rows']]
    body='''Declaration `38d918bd` preceded all scores. All four continuous-destination resident
parents retain their exact rural/outside people, produced cereal, harvest-boundary
bits and 365-day rural store. The first eligible harvest bin is the same as the
old fixed_rural_food rule. The audit includes every origin, including existing
source deficits and outside origins; outside owners and actor identities remain
explicitly unscored (-1). No new food, exports, residents, workers, dates or maps.

A exactly reproduces the old rural ledger: annual cereal at its declared bin,
monthly meals immediately, then storage capacity clip and stored decay.
B uses the SAME harvests and meals with immediate physical capacity clip,
continuous meals and decay. This changes the inventory convention as a whole;
A-to-B is not attributed solely to shipment timing. Both use 2500 kcal/day,
365 days, 5% annual stored loss and minimum repeating reserves. Food pass uses
the unchanged unmet<=1e-8*max(1,annual needed kcal) diagnostic. All zero-population
and zero-production origins stay visible and are not inferred communities.

Every positive-population origin fails B. The 365-day capacity stores exactly
a year of meals without allowance for decay. With one annual pulse and immediate
clip, even unlimited harvest cannot fill a store above that capacity. The
analytic control empties after %.6f days and leaves %.6f meal-days unmet.
A full-year capacity-only bound is %.6f meal-days at the same loss; it is NOT
a fitted or adopted new capacity. Production deficits add to this limitation.
This does not show observed famine, abandonment or historical impossibility.

Old monthly A channels exactly match all saved parent rural channels and outside
unmet fields. Independent one-pulse fixed-point equations and scalar monthly/
continuous ledgers review every origin/account, every stock path and unmet bin,
all 16 summary rows and local actor summaries. All origin CSV rows are checked.
Path tolerance is 1e-9 of annual meals; the old periodic solver itself uses an
annual-energy-scaled convergence tolerance. Thirty-two controls pass before
production; all nine model/field/CSV outputs reproduce byte for byte. Test
wall-clock timings are audit logs rather than deterministic data outputs.

Full NPZs retain every annual conservation channel and all 13 boundary stocks,
12 unmet bins, fixed node/owner/actor IDs and harvest choices for A and B. CSVs
provide one auditable origin row with fixed IDs, people, production, both gaps
and flags. Outside contexts receive no invented provider or actor affiliation.

No new exportable stream is computed here. The earlier point maps remain
conditional on monthly source availability; the destination-calendar/food gate
cannot repair source food or qualify complete provisioning. Next declare an
explicit shared rural/export chronology with actual withdrawal events before
new source-stock scores. Crew-carried food/location, complete diets and work,
dated occupation/roles/sizes, prospective transfer and mobile/nonstate/unaffiliated
resources remain open across release1–4/S1–S5. Keep the physics queue separate.
'''
    body=body.replace('%.6f',f'{fed:.6f}',1).replace('%.6f',f'{365-fed:.6f}',1).replace('%.6f',f'{required:.6f}',1)
    report=ROOT/'reports/SOURCE_CONTINUOUS_MEALS_20261113.md';report.write_text('# Fixed rural meals: monthly convention versus continuous physical storage\n\n'+body+'\n## All declared outcomes\n\n|'+'|'.join(headers)+'|\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('|'+'|'.join(v)+'|\n' for v in rows)+'\n'+ '\n'.join(f'![Source meal diagnostic](figures/{p.name})' for p in figures)+'\n')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data/source_continuous_meals';data.mkdir(parents=True,exist_ok=True);names=['results.json','controls.json','review.json','replay.json',*r['files_sha256']]
    for n in names:shutil.copyfile(OUT/n,data/n)
    shutil.copyfile(ROOT/'calibration/source_continuous_meals_20261113/plan.json',data/'plan.json');names+=['plan.json']
    section='<!--source-continuous-meals-start--><section><details id="source-continuous-meals"><summary>Rural source food: a year of meals in storage does not cover storage loss</summary><p>All16fixed-plan outcomes include every local AND outside origin. A preserves monthly meals before clipping. B uses the SAME one annual harvest, people and365-day capacity with immediate physical clip and continuous meals/decay. The entire convention changes; this is not a shipment-timing-only comparison.</p><div class="table"><table><thead><tr>'+''.join('<th>'+v+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
    section+=''.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p,alt in zip(figures,['All16old and continuous rural source meal outcomes','Analytic one-harvest capacity and storage-loss control']))
    section+='<p>Every positive-population origin fails B: one year of meal capacity cannot also pay storage loss between annual harvests. This diagnoses the storage convention, not observed famine or abandonment. No new capacity, exports, residents, calendars or map qualification is adopted. Outside owners and actors remain explicitly unscored.</p><p>All origin scalar ledgers, repeating stocks, paths, CSV rows and actor summaries independently checked;32controls and9fresh byte-exact files. Earlier optional point maps still assume monthly source availability. Destination food and mandatory work do not establish source-event food, crew rations/location, complete diets/work, dated roles/occupation/sizes, prospective transfer or authority.</p><p><a href="../../reports/SOURCE_CONTINUOUS_MEALS_20261113.md">Methods, all outcomes and remaining programme</a> · '+ ' · '.join(f'<a href="data/source_continuous_meals/{n}" download>{n}</a>' for n in names)+'</p></details></section><!--source-continuous-meals-end-->'
    html=page.read_text();old=re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->',html);pattern=r'<!--source-continuous-meals-start-->[\s\S]*?<!--source-continuous-meals-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda _:section,html)
    else:assert '<!--food-checked-visits-start-->' in html;html=html.replace('<!--food-checked-visits-start-->',section+'\n<!--food-checked-visits-start-->',1)
    for n,b in old:
        if n!='source-continuous-meals':assert f'<!--{n}-start-->{b}<!--{n}-end-->' in html,n
    page.write_text(html);registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text());entry=dict(id='source_continuous_meals_20261113',status='fixed_model_source_meal_convention_diagnostic',evidence=str(report.relative_to(ROOT)),note='All16local/outside outcomes;all positive-person origins fail immediate physical clip plus continuous meals at original365day capacity. Not observed famine,new export plan or calibrated adoption.');usage['datasets']=[v for v in usage['datasets'] if v['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,page.parent/'data/dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',results_sha256=sha(OUT/'results.json'),producer_sha256=sha(Path(__file__)),figures_sha256={str(p.relative_to(ROOT)):sha(p) for p in figures},downloads_sha256={n:sha(data/n) for n in names},original_maps_unchanged=True,default_adoption=False));print('Published16source meal outcomes,2figures and',len(names),'downloads.')
    for p in figures:print(p)
if __name__=='__main__':main()
