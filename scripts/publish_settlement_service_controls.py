"""Publish all declared service-opportunity controls without model adoption."""
import json
from pathlib import Path
import re
import shutil
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write


def main():
    out=ROOT/'output/settlement_service_controls_20261111';plan=ROOT/'calibration/settlement_service_controls_20261111/plan.json'
    result=json.loads((out/'results.json').read_text());manifest=json.loads((out/'fields.json').read_text());review=json.loads((out/'review.json').read_text())
    for key,path in {'plan_sha256':plan,'fields_manifest_sha256':out/'fields.json','fields_sha256':out/'fields.npz',
        'prior_service_results_sha256':ROOT/'output/settlement_service_demand_20261111/results.json',
        'producer_sha256':ROOT/'scripts/evaluate_settlement_service_controls.py',
        'frozen_context_module_sha256':ROOT/'polity/observed_role_contrast.py'}.items():
        if result[key]!=sha(path):raise ValueError('Changed opportunity evidence: '+key)
    for path,digest in manifest['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed opportunity source: '+path)
    if review['status']!='passed' or review['source_result_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_settlement_service_controls.py'):
        raise ValueError('Stale opportunity review')
    if review['direct_pairwise_AUC_checks']!=1188 or len(review['full_window_cases'])!=54:
        raise ValueError('Incomplete opportunity review')
    if result['adopt'] or result['fitted_parameters'] or result['chosen_predictor'] or result['population_food_staff_control_changed']:
        raise ValueError('Diagnostic unexpectedly adopted')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','settlement_service_controls.json'),(out/'fields.json','settlement_service_controls_fields.json'),
        (out/'review.json','settlement_service_controls_review.json'),(plan,'settlement_service_controls_plan.json')]:shutil.copyfile(src,data/name)
    rows=[]
    for mass,label in [('uniform','Uniform opportunities'),('environment','Suitability opportunities'),('history_L450','History opportunities')]:
        for suffix,desc in [('__recorded_roads_B1__per_centre','one-day recorded-road interaction'),
                            ('__zero_travel_per_centre','zero-travel D / m'),('__inverse_mass','inverse opportunities only')]:
            key=mass+suffix
            values=[result['subsets'][s]['results'][0]['predictors'][key]['AUC'] for s in ['full','strict_nonroadside']]
            values += [result['subsets'][s]['spatial_blocks']['equal_block_mean_AUC'][key] for s in ['full','strict_nonroadside']]
            rows.append('<tr><th>'+label+' · '+desc+'</th>'+''.join(f'<td>{v:.4f}</td>' for v in values)+'</tr>')
    fig=ROOT/'reports/figures/settlement_service_controls_20261111.png'
    with Image.open(fig) as img:w,h=img.size
    section='''<!--settlement-service-controls-start--><section><h2>Service demand: what comes from opportunity assumptions?</h2><details id="settlement-service-controls" class="panel"><summary>Uniform, suitability and historical opportunities · zero-travel controls</summary>
<p>All three opportunity scenarios share 1,292 expected-centre equivalents. Potential requests are conserved through the same land routes and destination choices. Local demand, demand divided by opportunities and inverse opportunities separate travel interaction from its denominator. These are experimental drivers, not actual residents, staffed towns or control.</p>
<div class="table"><table id="service-controls-results"><thead><tr><th>Fixed illustration and explanatory controls</th><th>Full AUC</th><th>Strict AUC</th><th>Full 50 km blocks</th><th>Strict 50 km blocks</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>The strict global historical interaction scores 0.6453, versus 0.6462 for inverse opportunities alone. Local interaction in this illustration remains below existing suitability (full 0.6015; strict 0.5748). Travel improves on some local nulls, but the global gain does not establish functional roles. No predictor is selected or adopted.</p>
'''+f'<img src="../../reports/figures/{fig.name}" width="{w}" height="{h}" alt="Global service rankings depend on opportunity assumptions; local comparisons remain weaker than suitability.">'+'''
<p>This table fixes one-day recorded-road travel and central coordinates; downloads retain all 66 predictors, nine coordinate cases, both road assumptions, all budgets and source strata. The archive contains whole-record contexts, not dated AD200 roles or true absences. Independent review checks 1,188 AUCs, 18 budgets and 54 comparisons with the full original transport window. Next: source-role composition and observation effects, then qualification for the same population, food, staffing and control ledger.</p>
<p><a href="../../reports/SETTLEMENT_SERVICE_CONTROLS_20261111.md">Methods, literature and limits</a> · <a href="data/settlement_service_controls.json" download>All contrasts and strata</a> · <a href="data/settlement_service_controls_fields.json" download>Field provenance and request ledgers</a> · <a href="data/settlement_service_controls_review.json" download>Independent review</a> · <a href="data/settlement_service_controls_plan.json" download>Protocol before fields and scores</a> · <a href="../../output/settlement_service_controls_20261111/fields.npz" download>Model fields</a></p></details></section><!--settlement-service-controls-end-->'''
    html=page.read_text();pattern=r'<!--settlement-service-controls-start-->[\s\S]*?<!--settlement-service-controls-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-service-demand-start-->'
        if marker not in html:raise ValueError('Publish service demand first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='settlement_service_controls_20261111',status='exposed_service_opportunity_controls',
        evidence='reports/SETTLEMENT_SERVICE_CONTROLS_20261111.md',note='All availability and zero-travel controls scored on exposed full/strict archive contexts; no fitting/adoption/independent transfer or dated roles.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published service opportunity controls; production maps unchanged.')


if __name__=='__main__':main()
