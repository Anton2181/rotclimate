"""Publish experimental finite requests and all conditional role diagnostics."""
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
    out=ROOT/'output/settlement_service_demand_20261111';plan=ROOT/'calibration/settlement_service_demand_20261111/plan.json'
    result=json.loads((out/'results.json').read_text());manifest=json.loads((out/'fields.json').read_text());review=json.loads((out/'review.json').read_text())
    checks={'plan_sha256':plan,'fields_manifest_sha256':out/'fields.json','fields_sha256':out/'fields.npz',
        'producer_sha256':ROOT/'scripts/evaluate_settlement_service_demand.py',
        'frozen_context_module_sha256':ROOT/'polity/observed_role_contrast.py'}
    for key,path in checks.items():
        if result[key]!=sha(path):raise ValueError('Changed service evidence: '+key)
    for path,digest in manifest['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed service source: '+path)
    if review['status']!='passed' or review['source_result_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_settlement_service_demand.py'):
        raise ValueError('Stale service review')
    if review['direct_pairwise_AUC_checks']!=378 or len(review['full_window_crop_checks'])!=18:
        raise ValueError('Incomplete service review')
    if result['adopt'] or result['fitted_parameters'] or result['physical_population_food_staff_control_changed']:
        raise ValueError('Diagnostic unexpectedly became fitting/adoption')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','settlement_service_demand.json'),(out/'fields.json','settlement_service_fields.json'),
                     (out/'review.json','settlement_service_review.json'),(plan,'settlement_service_plan.json')]:shutil.copyfile(src,data/name)
    scenarios=[(f'{roads}_B{b:g}_per_centre',f'{"No roads" if roads=="no_roads" else "Recorded roads"}, {b:g} days')
        for roads in ['no_roads','recorded_roads'] for b in [.5,1.,2.]]
    rows=[]
    for key,label in scenarios+[('environment','Existing suitability'),('history_L450_intensity','Existing history intensity')]:
        values=[result['subsets'][s]['results'][0]['predictors'][key]['AUC'] for s in ['full','strict_nonroadside']]
        values += [result['subsets'][s]['spatial_blocks']['equal_block_mean_AUC'][key] for s in ['full','strict_nonroadside']]
        rows.append('<tr><th>'+label+'</th>'+''.join(f'<td>{v:.4f}</td>' for v in values)+'</tr>')
    figures=[]
    for name,alt in [('scores','Full and strict non-roadside service comparisons; local diagnostics limit the apparent gain.'),
                     ('maps','One-day recorded-road illustration: request drivers, not settlements or control. Hatched areas are unmodelled, not sea.')]:
        path=ROOT/f'reports/figures/settlement_service_demand_{name}_20261111.png'
        with Image.open(path) as img:w,h=img.size
        figures.append(f'<img src="../../reports/figures/{path.name}" style="max-width:100%;height:auto" width="{w}" height="{h}" alt="{alt}">')
    section='''<!--settlement-service-demand-start--><section><h2>Finite service demand: a new mechanism, still experimental</h2><details id="settlement-service-demand" class="panel"><summary>Conserved potential requests · land routes · strict non-roadside check</summary>
<p>Each reference-resident equivalent contributes one potential request. Reachable candidate opportunities share it through normalized destination choice. Both directed walking legs must fit the budget; sea and corner crossings are blocked. Requests are not extra residents, food, staff or completed services.</p>
<p>Six scenarios compare no roads/recorded roads and 0.5/1/2 one-way walking-days. Full and strict non-roadside contrasts retain all nine coordinate cases and source strata. Strict central support is 97 nucleated and 797 farm/villa cell/class units, including 45 mixed cells.</p>
<div class="table"><table id="service-demand-results"><thead><tr><th>Per-centre scenario/reference</th><th>Full AUC</th><th>Strict AUC</th><th>Full 50 km blocks</th><th>Strict 50 km blocks</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>Per-centre demand scores about 0.64–0.65 overall on the strict subset, but the two-day cases fall to about 0.55–0.56 within 50 km blocks, below existing suitability’s 0.575 locally. A broad geography/opportunity-mass effect may explain much of the apparent gain. No predictor or default is selected. AUC is conditional ranking discrimination, not a reconstruction accuracy percentage.</p>
'''+figures[0]+'''<p>The fixed recorded-road/one-day illustration shows request drivers, not town sizes or control. Fractional candidate opportunities are not staffed places. Conservation is checked over the full crop before halo values are masked from displayed core fields.</p>'''+figures[1]+'''
<p>All six request budgets conserve demand. Independent review checks 378 AUCs, 27 exact previous references and 18 cases against the full original transport graph. Walking is a dry annual scenario, not the monthly network or a fitted ancient market schedule. Next: candidate-mass, zero-travel and inverse-mass controls; qualified roles must feed the same population/food/staff/control ledger.</p>
<p><a href="../../reports/SETTLEMENT_SERVICE_DEMAND_20261111.md">Equations, academic sources and limits</a> · <a href="data/settlement_service_demand.json" download>Every contrast, coordinate case and stratum</a> · <a href="data/settlement_service_fields.json" download>Field provenance and request ledgers</a> · <a href="data/settlement_service_review.json" download>Independent review</a> · <a href="data/settlement_service_plan.json" download>Protocol before fields/scores</a> · <a href="../../output/settlement_service_demand_20261111/fields.npz" download>Model request fields</a></p></details></section><!--settlement-service-demand-end-->'''
    html=page.read_text();pattern=r'<!--settlement-service-demand-start-->[\s\S]*?<!--settlement-service-demand-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-role-contrast-start-->'
        if marker not in html:raise ValueError('Publish original context diagnostic first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='settlement_service_demand_20261111',status='exposed_service_demand_context_diagnostic',evidence='reports/SETTLEMENT_SERVICE_DEMAND_20261111.md',
        note='Finite potential requests and full/strict-nonroadside conditional contrasts scored. No fitting/adoption. Global gains limited by local diagnostics; no dated roles/census/authority or independent transfer.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published service request machinery and diagnostics; no production adoption.')


if __name__=='__main__':main()
