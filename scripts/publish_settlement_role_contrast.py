"""Publish conditional role diagnostics, retaining explicit source exposure."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_locations_earth import sha,write


def main():
    out=ROOT/'output/settlement_role_contrast_20261111';plan=ROOT/'calibration/settlement_role_contrast_20261111/plan.json'
    result=json.loads((out/'results.json').read_text());prep=json.loads((out/'preparation.json').read_text());review=json.loads((out/'review.json').read_text())
    for path,digest in result['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed role diagnostic source')
    if result['plan_sha256']!=sha(plan) or result['preparation_sha256']!=sha(out/'preparation.json'):
        raise ValueError('Changed role protocol/preparation')
    if result['roman_input_sha256']!=sha(ROOT/'output/settlement_locations_20261110/rome_inputs.npz'):
        raise ValueError('Changed Roman input')
    if review['status']!='passed' or review['source_result_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_settlement_role_contrast.py') or review['direct_pairwise_AUC_checks']!=27:
        raise ValueError('Stale/incomplete diagnostic review')
    if result['adopt'] or result['fitted_parameters'] or result['production_maps_changed']:
        raise ValueError('Diagnostic unexpectedly became fitting/adoption')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','settlement_role_contrast.json'),(out/'preparation.json','settlement_role_contrast_preparation.json'),
                     (out/'review.json','settlement_role_contrast_review.json'),(plan,'settlement_role_contrast_plan.json')]:shutil.copyfile(src,data/name)
    labels={'uniform':'Uniform ranking','environment':'Existing suitability','history_L450_intensity':'History-weighted intensity'}
    rows=''.join(f'<tr><th>{labels[key]}</th><td>{value["AUC"]:.4f}</td><td>{result["spatial_blocks"]["equal_block_mean_AUC"][key]:.4f}</td></tr>' for key,value in result['results'][0]['predictors'].items())
    section='''<!--settlement-role-contrast-start--><section><h2>Recorded settlement contexts: weak separation</h2><details id="settlement-role-contrast" class="panel"><summary>Conditional ranking diagnostic · no fitting or production adoption</summary>
<p>Among investigated domestic contexts, the existing suitability score weakly distinguishes recorded nucleated from farm/villa labels. Adding the selected history prior reduces this discrimination. AUC 0.5 means no ranking discrimination; these are not percentages of correctly reconstructed settlements, dated AD200 roles or political authority.</p>
<div class="table"><table id="role-contrast-results"><thead><tr><th>Predictor</th><th>All represented cell/class units</th><th>Equal 50 km-block mean</th></tr></thead><tbody>'''+rows+'''</tbody></table></div>
<img id="role-contrast-figure" src="../../reports/figures/settlement_role_contrast_20261111.png" style="max-width:100%;height:auto" width="1800" height="750" alt="Suitability AUC 0.548 and history-weighted intensity0.519 are weak; all coordinate scenarios retained. Selected-archive contexts, not census accuracy.">
<p>The central sample retains 797 farm/villa and 249 nucleated cell/class units, including 155 mixed cells. Repeat excavations do not add weight; mixed cells retain both classes/ties. Unsurveyed space is never a negative label. Coverage exclusions, all nine ±2/±5 km coordinate scenarios, source fieldwork/AREA/region strata and transform limitations are exported. The unavailable best datum grid is reported; numerical transform accuracy is not source survey precision.</p>
<p>Within-block results cover 63 blocks with both classes out of 81 observed blocks and are not held-out validation. Source selection and whole-record timing remain limitations. Next: explicit role/service-demand mechanisms and observation bias, including a contrast without roadside labels before road-based role predictions. Qualified changes must feed the same population/food/staff/control ledger.</p>
<p><a href="../../reports/SETTLEMENT_ROLE_CONTRAST_20261111.md">Source scope, geometry and interpretation</a> · <a href="data/settlement_role_contrast.json" download>All contrasts and strata</a> · <a href="data/settlement_role_contrast_preparation.json" download>Coverage and coordinate scenarios</a> · <a href="data/settlement_role_contrast_review.json" download>Independent pairwise review</a> · <a href="data/settlement_role_contrast_plan.json" download>Protocol before matching/scores</a></p></details></section><!--settlement-role-contrast-end-->'''
    html=page.read_text();pattern=r'<!--settlement-role-contrast-start-->[\s\S]*?<!--settlement-role-contrast-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-continuation-start-->'
        if marker not in html:raise ValueError('Publish continuation research first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='settlement_role_contrast_20261111',status='exposed_conditional_context_diagnostic',evidence='reports/SETTLEMENT_ROLE_CONTRAST_20261111.md',note='Selected-archive role-label contrast scored on exposed Roman Earth inputs; no fitting, datedAD200 roles, true-absence census, independent transfer or adoption. Preserve source exposure.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    for e in usage['datasets']:
        if e['id']=='rural_roman_britain':
            e['status']='exposed_conditional_context_diagnostic';e['note']='Initial preparation remains immutable; source whole-record context labels now scored conditionally against existing Earth predictors. Not sealed/independent; no dated roles, population, institution or control assignment. Public outputs aggregate only.'
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published weak conditional role contrast and updated source exposure; no production adoption.')


if __name__=='__main__':main()
