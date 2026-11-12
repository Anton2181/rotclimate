"""Publish empirical calibration status inside the normal offline atlas hub."""
from pathlib import Path
import csv
import gzip
import hashlib
from html import escape
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    origin=ROOT/'output/earth_components_20261105';out=ROOT/'atlases/earth_evidence';data=out/'data';data.mkdir(parents=True,exist_ok=True)
    refreshed=ROOT/'output/earth_components_refresh_20261111'
    inventory=refreshed if (refreshed/'refresh.json').exists() else origin
    panel=json.loads((origin/'reaping/panel_audit.json').read_text());ledger=json.loads((inventory/'ledger.json').read_text());prep=json.loads((origin/'reaping/preparation.json').read_text());selection=json.loads((origin/'reaping/selection.json').read_text());evaluation=json.loads((origin/'reaping/evaluation.json').read_text())
    if ledger['specification_sha256']!=hashlib.sha256((ROOT/'calibration/earth_components_20261105/evidence_spec.json').read_bytes()).hexdigest():raise ValueError('Evidence specification changed')
    for p,h in {**ledger['sources_sha256'],**ledger['evidence_sha256']}.items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Evidence inventory stale: '+p)
    if evaluation['selection_sha256']!=hashlib.sha256((origin/'reaping/selection.json').read_bytes()).hexdigest():raise ValueError('Calibration selection mismatch')
    for p,h in evaluation['identity']['sources_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:
            archived=subprocess.check_output(['git','show',panel['producer_snapshot_commit']+':'+p],cwd=ROOT)
            if hashlib.sha256(archived).hexdigest()!=h:raise ValueError('Historical benchmark producer identity changed: '+p)
    for src,dst in [(inventory/'ledger.json','ledger.json'),(inventory/'parameters.csv','parameters.csv'),(origin/'reaping/preparation.json','preparation.json'),(origin/'reaping/selection.json','selection.json'),(origin/'reaping/evaluation.json','evaluation_original.json'),(origin/'reaping/panel_audit.json','panel_audit.json'),(ROOT/'calibration/earth_components_20261105/plan.json','benchmark_plan.json'),(ROOT/'calibration/earth_components_20261105/vdsa_source.json','survey_source.json'),(ROOT/'calibration/earth_components_20261105/dataset_usage.json','dataset_usage.json')]:shutil.copyfile(src,data/dst)
    prepared=ROOT/'data/cache/vdsa_8224522/prepared_reaping.json'
    prepared_bytes=prepared.read_bytes() if prepared.exists() else gzip.decompress((data/'reaping_cases.json.gz').read_bytes())
    if hashlib.sha256(prepared_bytes).hexdigest()!=selection['prepared_sha256']:raise ValueError('Prepared observation identity changed')
    if not evaluation['evaluation_targets_scored']:raise ValueError('Do not publish held-out targets before evaluation')
    (data/'reaping_cases.json.gz').write_bytes(gzip.compress(prepared_bytes,mtime=0))
    if panel['original_evaluation_sha256']!=hashlib.sha256((origin/'reaping/evaluation.json').read_bytes()).hexdigest():raise ValueError('Panel audit is stale')
    (data/'evaluation.json').write_text(json.dumps(dict(status='post_audit_restricted_diagnostic',baseline=panel['baseline'],candidate=panel['candidate'],prospective_qualification=False,ancient_default_adoption=False,training_scale=selection['scale'],scope=panel['restricted_interpretation']),indent=2)+'\n')
    base=panel['baseline'];candidate=panel['candidate'];training=[selection['training_baseline']['equal_district_abs_log10_error'],selection['training_candidate']['equal_district_abs_log10_error']]
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),layout='constrained');fig.patch.set_facecolor('#f1f3ef')
    axes[0].bar([-.17,.83],[training[0],base['equal_district_abs_log10_error']],.34,label='Fixed task baseline',color='#ad7c54');axes[0].bar([.17,1.17],[training[1],candidate['equal_district_abs_log10_error']],.34,label='Training-fitted scale',color='#367a71');axes[0].set_xticks([0,1],['Training · 8 labels','Restricted check · 4 districts']);axes[0].set(ylabel='Mean absolute log10 error · equal district weights',title='Observed manual-harvest hours / cropped hectare');axes[0].legend(fontsize=8)
    names=list(base['per_district']);x=list(range(len(names)))
    axes[1].bar([i-.17 for i in x],[base['per_district'][n]['abs_log10_error'] for n in names],.34,color='#ad7c54');axes[1].bar([i+.17 for i in x],[candidate['per_district'][n]['abs_log10_error'] for n in names],.34,color='#367a71');axes[1].set_xticks(x,['E'+str(i+1)+' · n='+str(base['per_district'][n]['cases']) for i,n in enumerate(names)],rotation=15,fontsize=8);axes[1].set(title='Every retained evaluation district reported',ylabel='Mean absolute log10 error')
    for ax in axes:ax.grid(axis='y',alpha=.15)
    fig.suptitle('Modern Earth task benchmark · original split failed the panel audit',fontsize=13)
    fig.supxlabel('Restricted check: 1,606 wheat observations / 4 districts; entire affected district removed after detecting overlapping panels.\nPost-audit diagnostic, not a new untouched validation. Strict low-input analogues: 0. No AD200 default changes.',fontsize=9)
    figure=data/'manual_reaping.png';fig.savefig(figure,dpi=140);plt.close(fig);shutil.copyfile(figure,origin/'manual_reaping.png')
    components=''.join(f'<article><h3>{escape(c["label"])}</h3><p>{escape(c["validation"])}</p><p><strong>Observable:</strong> {escape(c["observables"])}</p><p><strong>Next:</strong> {escape(c["next_test"])}</p></article>' for c in ledger['components'])
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Earth calibration evidence · Rotclimate</title>
<style>:root{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif}.wrap{max-width:1200px;margin:auto;padding:24px 18px 60px}a{color:var(--accent)}h1{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}h2{font:600 1.65rem Georgia,serif}h3{margin:0 0 10px}section{margin-top:38px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));gap:16px}article,.panel{border:1px solid var(--rule);background:var(--plate);padding:18px;border-radius:6px}.grid article{min-width:0;overflow-wrap:anywhere}.table{overflow:auto;max-height:560px;border:1px solid var(--rule)}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}thead{position:sticky;top:0;background:var(--plate)}code{overflow-wrap:anywhere}.filters{display:flex;gap:14px;flex-wrap:wrap;margin:15px 0}.filters label{display:flex;flex-direction:column;min-width:0;max-width:100%}select,input,button{max-width:100%;font:inherit;padding:7px}img{width:100%;height:auto}.note{font-size:.9rem}button{cursor:pointer}@media(prefers-color-scheme:dark){:root{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}</style>
<div class="wrap"><nav><a href="../">Atlas hub</a> · <a href="../climate_accuracy/">Climate accuracy</a> · <a href="../economy_lab/">Food and society</a></nav>
<header><p>EARTH EVIDENCE · 5 NOVEMBER 2026</p><h1>What is calibrated, and what still needs evidence</h1><p>11 components · 551 numeric configuration records. Published equations, fitted coefficients, scenario choices and audit gaps remain distinct. These counts are not independent degrees of freedom or a percentage of the model validated.</p><p class="note">This first inventory covers selected JSON settings and literal top-level constants. It does not yet trace every numeric expression inside model functions. “Unreviewed” means evidence has not been traced here; it does not mean the coefficient has never been studied.</p></header>
<section aria-labelledby="benchmark-h"><h2 id="benchmark-h">First new test: manual cereal harvesting on Earth</h2><div class="panel"><p>Independent survey records supply household size, plot area and reported human task hours. Crop revenue is not treated as grain, wages are not treated as hours, animal hours are excluded and bundled harvesting/threshing records are excluded.</p>'''+f'''<div class="table"><table id="benchmark"><thead><tr><th>Restricted diagnostic</th><th>Fixed baseline</th><th>Training-fitted comparator</th></tr></thead><tbody><tr><th>Mean absolute log10 error</th><td>{base['equal_district_abs_log10_error']:.3f}</td><td>{candidate['equal_district_abs_log10_error']:.3f}</td></tr><tr><th>Within factor two · equal district weights</th><td>{base['equal_district_within_factor_two']*100:.1f}%</td><td>{candidate['equal_district_within_factor_two']*100:.1f}%</td></tr></tbody></table></div><p>Selected shared scale: {selection['scale']:.3f}, fitted only on 603 observations in eight districts. Post-audit check: 1,606 observations in four retained districts. The full split failed: source spelling variants put five households into both folds. The entire affected district was removed without refitting.</p>'''+'''<p><strong>Transfer limit:</strong> these are 2009–2014 observations, the retained evaluation cases are wheat only, and no eligible case passes the strict recorded low-input screen. A manual-task label does not establish ancient technology. No prospective qualification is claimed after the panel-audit failure. AD200 defaults remain unchanged. This test does not validate total subsistence work, household availability, stored food or sovereignty.</p><img src="data/manual_reaping.png" alt="Training and restricted diagnostic harvesting errors; original split invalidated; no ancient default adoption"><p><a href="../../reports/EARTH_COMPONENT_CALIBRATION_20261105.md">Methods and next steps</a> · <a href="https://doi.org/10.5281/zenodo.8224522">ICRISAT/IFPRI source · CC BY 4.0</a> · <a href="data/evaluation.json" download>Restricted diagnostic</a> · <a href="data/panel_audit.json" download>Panel failure audit</a> · <a href="data/evaluation_original.json" download>Archived computation · independence failed</a> · <a href="data/reaping_cases.json.gz" download>Pseudonymous task records</a> · <a href="data/benchmark_plan.json" download>Predeclared plan</a></p></div></section>
<section aria-labelledby="modules-h"><h2 id="modules-h">Evidence by component</h2><div class="grid">'''+components+'''</div></section>
<section aria-labelledby="parameters-h"><h2 id="parameters-h">Configured values and evidence</h2><p>Local Earth tests and historical fits do not identify every coefficient independently. Reported literature values remain distinct from empirical fits in this project.</p><div class="filters"><label>Component <select id="component"><option value="">All components</option></select></label><label>Evidence <select id="status"><option value="">All evidence classes</option></select></label><label>Find <input id="search" type="search" placeholder="Parameter or source"></label></div><p id="count" aria-live="polite"></p><div class="table"><table><thead><tr><th>Component / parameter</th><th>Value</th><th>Evidence</th><th>Interpretation</th></tr></thead><tbody id="rows"></tbody></table></div><p><button id="previous">Previous</button> <span id="page"></span> <button id="next">Next</button></p><p><a href="data/parameters.csv" download>Complete parameter CSV</a> · <a href="data/ledger.json" download>Evidence ledger and identities</a> · <a href="data/dataset_usage.json" download>Dataset exposure register</a> · <a href="data/survey_source.json" download>Survey identities and licence</a></p></section></div>
<script>const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let records=[],offset=0;function render(){const q=$('search').value.toLowerCase(),filtered=records.filter(r=>(!$('component').value||r.component===$('component').value)&&(!$('status').value||r.status===$('status').value)&&JSON.stringify([r.source,r.pointer,r.note]).toLowerCase().includes(q));offset=Math.min(offset,Math.max(0,Math.floor((filtered.length-1)/40)*40));$('rows').innerHTML=filtered.slice(offset,offset+40).map(r=>`<tr><td>${esc(r.component)}<br><code>${esc(r.source+r.pointer)}</code></td><td>${esc(r.value)}</td><td>${esc(r.status)}</td><td>${esc(r.note)}<br><small>${esc((r.evidence||[]).join(' · '))}</small></td></tr>`).join('');$('count').textContent=filtered.length+' matching numeric records';$('page').textContent=filtered.length?`${offset+1}–${Math.min(offset+40,filtered.length)}`:'0';$('previous').disabled=offset===0;$('next').disabled=offset+40>=filtered.length;}fetch('data/ledger.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Ledger HTTP '+r.status);return r.json()}).then(m=>{records=m.parameters;for(const c of m.components)$('component').add(new Option(c.label,c.id));for(const s of [...new Set(records.map(r=>r.status))].sort())$('status').add(new Option(s,s));render();}).catch(e=>{$('count').textContent='Detailed inventory unavailable. The component summaries and downloads remain available.';console.error(e);});for(const id of ['component','status','search'])$(id).addEventListener('input',()=>{offset=0;render()});$('previous').onclick=()=>{offset-=40;render()};$('next').onclick=()=>{offset+=40;render()};</script></html>'''
    if inventory!=origin:
        refresh=json.loads((inventory/'refresh.json').read_text())
        if refresh['current_ledger_sha256']!=hashlib.sha256((inventory/'ledger.json').read_bytes()).hexdigest():raise ValueError('Stale inventory refresh receipt')
        shutil.copyfile(inventory/'refresh.json',data/'inventory_refresh.json')
        html=html.replace('EARTH EVIDENCE · 5 NOVEMBER 2026','EARTH EVIDENCE · 11 NOVEMBER 2026')
        html=html.replace('</header>','<p class="note" id="inventory-refresh">Configuration inventory refreshed 11 November: 551 records retained; the single-crop sown share now reflects the already-active 0.60 value rather than the historical 0.68 snapshot. Evidence categories are unchanged; this is not a new fit. <a href="data/inventory_refresh.json" download>Inventory version comparison</a></p></header>',1)
    (out/'index.html').write_text(html)
    if (ROOT/'output/low_input_yields_20261105/evaluation.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_earth_yields.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_locations_20261110/results.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_locations.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_intensity_20261110/results.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_intensity.py')],cwd=ROOT,check=True)
    if (ROOT/'output/roman_rural_preparation_20261110/audit.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_roman_rural_preparation.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_history_boundary_20261111/review.json').exists() and (ROOT/'output/settlement_phase_evidence_20261111/audit.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_continuation.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_role_contrast_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_role_contrast.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_service_demand_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_service_demand.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_service_controls_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_service_controls.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_role_composition_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_role_composition.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_service_capacity_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_service_capacity.py')],cwd=ROOT,check=True)
    if (ROOT/'output/institution_evidence_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_institution_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/institution_scope_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_institution_scope.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_vidarbha_transfer_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_vidarbha_transfer.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_counts_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_counts.py')],cwd=ROOT,check=True)
    if (ROOT/'output/earth_population_extension_20261111/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_population_extension.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_joint_locations_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_joint_locations.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_residents_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_residents.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_feedback_20261112/atlas_publication.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_feedback_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_size_evidence_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_sizes.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_housing_diagnostic_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_housing_density.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_monthly_work_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_monthly_work.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_dispatch_20261112/atlas_publication.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_dispatch_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_dispatch_search_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_dispatch_search.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_dispatch_seeded_20261112/atlas_publication.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_seeded_dispatch_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_duty_visits_20261112/atlas_publication.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_network_visits_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_visit_spare_assignment_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_spare_visit_assignment.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_visit_target_grid_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_visit_target_grid.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_visit_calendar_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_visit_calendars.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_visit_joint_order_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_joint_visit_order.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_visit_year_complete_20261112/atlas_publication.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_provider_year_visits.py')],cwd=ROOT,check=True)
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_provider_year_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_visit_delivery_timing_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_delivery_timing.py')],cwd=ROOT,check=True)
    if (ROOT/'output/network_visit_meal_headroom_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_meal_headroom.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_continuous_destination_20261112/comparison_review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_continuous_destination.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_market_range_20261112/atlas_publication.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_market_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_cohort_forwarding_20261112/replay.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_cohort_evidence.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_size_identity_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_size_identity.py')],cwd=ROOT,check=True)
    if (ROOT/'output/settlement_size_shape_20261112/review.json').exists():
        subprocess.run([sys.executable,'-I',str(ROOT/'scripts/publish_settlement_size_shape.py')],cwd=ROOT,check=True)
    (origin/'presentation.json').write_text(json.dumps(dict(status='published',page='atlases/earth_evidence/index.html',page_sha256=hashlib.sha256((out/'index.html').read_bytes()).hexdigest(),publisher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    print('Published Earth evidence dashboard; production map values unchanged')


if __name__=='__main__':main()
