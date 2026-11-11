"""Publish the boundary experiment and source chronology without map adoption."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_locations_earth import sha,write


def verify(result,checks):
    for key,path in checks.items():
        if result[key]!=sha(ROOT/path):raise ValueError('Stale settlement continuation evidence: '+key)


def main():
    history='output/settlement_history_boundary_20261111'
    phase='output/settlement_phase_evidence_20261111'
    hp='calibration/settlement_history_boundary_20261111/plan.json'
    pp='calibration/settlement_phase_evidence_20261111/plan.json'
    semantics='calibration/settlement_phase_evidence_20261111/semantic_sources.json'
    h=json.loads((ROOT/history/'results.json').read_text());p=json.loads((ROOT/phase/'audit.json').read_text())
    review=json.loads((ROOT/history/'review.json').read_text())
    verify(h,dict(plan_sha256=hp,driver_sha256='scripts/settlement_history_boundary_earth.py',
        positions_sha256=history+'/positions.npz',prior_adaptive_results_sha256='output/settlement_intensity_20261110/results.json',
        prior_adaptive_positions_sha256='output/settlement_intensity_20261110/positions.npz',
        original_results_sha256='output/settlement_locations_20261110/results.json'))
    for path,digest in h['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen source: '+path)
    verify(review,dict(source_result_sha256=history+'/results.json',reviewer_sha256='scripts/review_settlement_history_boundary.py'))
    verify(p,dict(plan_sha256=pp,semantic_sources_sha256=semantics,producer_sha256='scripts/audit_settlement_phase_evidence.py',
        phase_module_sha256='polity/settlement_phase_evidence.py',frozen_role_module_sha256='polity/role_evidence.py',
        parser_sha256='scripts/audit_vidarbha_preparation.py',table_reader_sha256='scripts/audit_roman_rural_preparation.py',
        original_source_snapshot_sha256='output/roman_rural_preparation_20261110/source_snapshot.json'))
    if h['adopt'] or p['adopt'] or p['model_scores_computed'] or p['production_maps_changed']:
        raise ValueError('Research unexpectedly became adoption/source evaluation')
    if review['status']!='passed' or review['rows_checked']!=100 or review['overlap_controls_exact']!=20:
        raise ValueError('Incomplete boundary review')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(history+'/results.json','settlement_history_boundary.json'),(history+'/review.json','settlement_history_boundary_review.json'),
                     (hp,'settlement_history_boundary_plan.json'),(phase+'/audit.json','settlement_phase_evidence.json'),
                     (pp,'settlement_phase_evidence_plan.json'),(semantics,'settlement_phase_semantics.json')]:
        shutil.copyfile(ROOT/src,data/name)
    rows=''.join(f'<tr><th>{r["variant"]}</th><td>{r["Q"]:.4f}</td><td>{r["pools"]["han"]["unique_F1"]:.4f}</td><td>{r["pools"]["rome"]["unique_F1"]:.4f}</td><td>{r["pools"]["han"]["M3"]:.4f}</td><td>{r["pools"]["rome"]["M3"]:.4f}</td></tr>'
        for r in h['ranking'])
    history_html='''<section><h2>History-scale robustness: the old edge is now inside the grid</h2><details id="settlement-history-boundary" class="panel"><summary>100 development evaluations · no new adoption</summary>
<p>Spatial history scales of 150, 225, 300, 450 and 650 km were compared at two spacing settings and five seeds on the same exposed Han/Roman inputs. Centre budgets remain 1,202 and 1,292. All 20 overlapping 450 km draws replay their old metrics and coordinates exactly.</p>
<p>The combined lead remains c=0.35/L450, Q=0.6214. Shorter scales do not improve Q; 450 km is now inside the tested range. The new c=0.5/L300 alternative joins the location/spacing Pareto frontier. This is sensitivity of a spatial prior, not occupation-age calibration, a global-optimum proof or independent transfer.</p>
<img id="history-boundary-figure" src="../../reports/figures/settlement_history_boundary_20261111.png" style="max-width:100%;height:auto" width="2100" height="720" alt="Combined development quality peaks at450km within the tested range. Matching and spacing show different tradeoffs; no adoption.">
<div class="table"><table id="history-boundary-results"><thead><tr><th>Draw variant</th><th>Q ↑</th><th>Han unique F1 ↑</th><th>Roman unique F1 ↑</th><th>Han spacing KS ↓</th><th>Roman spacing KS ↓</th></tr></thead><tbody>'''+rows+'''</tbody></table></div>
<p>Numbers are five-seed development means. Q is a declared tradeoff, not percentage accuracy; pool scores may move differently. All counts, eligibility, pair separation and target-intensity normalization pass. S1 history, credible transfer and the coupled population/food/staff/control rebuild remain open; production maps are unchanged.</p>
<p><a href="../../reports/SETTLEMENT_HISTORY_BOUNDARY_20261111.md">Method and tradeoffs</a> · <a href="data/settlement_history_boundary.json" download>All results and combined frontier</a> · <a href="data/settlement_history_boundary_review.json" download>Independent invariant review</a> · <a href="data/settlement_history_boundary_plan.json" download>Protocol declared before new outcomes</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Full roadmap</a></p></details></section>'''
    states=p['phase_status'];groups=p['identity']['extended_review_blocks']
    phase_rows=[('Consistent recorded change order',states['consistent_changes']),('Change records requiring review',states['changes_require_review']),
        ('No recorded change dates',states['no_recorded_changes']),('Records carrying both farm and villa labels',p['records_with_farm_and_villa_labels']),
        ('Observations in extended related-record blocks',groups['records_in_nontrivial_components'])]
    table=''.join(f'<tr><th>{name}</th><td>{count:,}</td></tr>' for name,count in phase_rows)
    phase_html='''<section><h2>Settlement functions can change through time</h2><details id="settlement-phase-evidence" class="panel"><summary>Source-methodology audit · related records and changing roles</summary>
<p>The authors’ published methodology says phase-date fields record major settlement changes. A farmstead that developed into a villa can carry both labels; multiple labels need not be contemporary. General change dates do not identify a function’s interval, prove uninterrupted occupation or date an AD200 garrison.</p>
<div class="table"><table id="phase-evidence-results"><thead><tr><th>Source observation check</th><th>Records</th></tr></thead><tbody>'''+table+'''</tbody></table></div>
<p>Among the 1,041 change-bearing records, 1,031 have consistent internal dates; 10 require review because of missing site bounds, reversed changes or changes outside the recorded span. Dates are not sorted, clipped or assigned to roles. No recorded change is not proof that nothing changed. Specific role intervals remain unassigned for all 3,652 records.</p>
<p>Exact-point and county/name evidence extends the old association blocks from 153 to 189 related observations, while retaining every source record. The 83 nontrivial blocks constrain future validation; they do not merge physical places. A shared name can describe a villa and nearby cemetery, and a shared centroid can describe separate investigations. The published approximate settlement total is not imposed as a de-duplication target.</p>
<p>Next: define role-specific, temporally defensible targets and grouped/spatial coverage treatment. Qualified roles must enter the same resident, food, staffing and control consumers. No population, staff, affiliation or control is inferred from these source checks.</p>
<p><a href="../../reports/SETTLEMENT_PHASE_EVIDENCE_20261111.md">Source methods and review cases</a> · <a href="data/settlement_phase_evidence.json" download>Aggregate chronology/identity audit</a> · <a href="data/settlement_phase_evidence_plan.json" download>Exposed-audit protocol</a> · <a href="data/settlement_phase_semantics.json" download>Academic source identities</a> · <a href="../../reports/SETTLEMENT_ROLE_CONTRACT_20261110.md">Population/control consumer contract</a></p></details></section>'''
    section='<!--settlement-continuation-start-->'+history_html+phase_html+'<!--settlement-continuation-end-->'
    html=page.read_text();pattern=r'<!--settlement-continuation-start-->[\s\S]*?<!--settlement-continuation-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--rural-preparation-start-->'
        if marker not in html:raise ValueError('Publish rural evidence first')
        html=html.replace(marker,section+marker,1)
    card_style='.grid article{min-width:0;overflow-wrap:anywhere}'
    if card_style not in html:html=html.replace('</style>',card_style+'</style>',1)
    html=re.sub(r'RESEARCH UPDATED \d+ [A-Z]+ \d{4}','RESEARCH UPDATED 11 NOVEMBER 2026',html,count=1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='settlement_history_boundary_20261111',status='exposed_development_only',
        evidence='reports/SETTLEMENT_HISTORY_BOUNDARY_20261111.md',note='100 declared exposed evaluations,20 exact overlap controls. Old lead retained; no global-optimum, occupation-age, transfer or production-adoption claim.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    for e in usage['datasets']:
        if e['id']=='rural_roman_britain':e['note']='Prepared source only, unscored. Published methodology documents successive roles and major change dates; no role intervals imputed.1031 consistent change records/10 requiring review; exact-name/point review blocks include189 observations, not place merges. Operational grid interpretation retained; precision/coverage and dated-role targets remain open.'
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published100-evaluation boundary study and chronology/identity evidence; no production map change.')


if __name__=='__main__':main()
