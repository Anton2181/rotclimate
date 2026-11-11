"""Expose every gated/ungated source-role composition case in Earth evidence."""
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
    out=ROOT/'output/settlement_role_composition_20261111';config=ROOT/'calibration/settlement_role_composition_20261111'
    result=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text())
    for key,path in {'plan_sha256':config/'plan.json','semantic_sources_sha256':config/'semantic_sources.json',
        'parent_results_sha256':ROOT/'output/settlement_service_controls_20261111/results.json',
        'parent_fields_manifest_sha256':ROOT/'output/settlement_service_controls_20261111/fields.json',
        'parent_fields_sha256':ROOT/'output/settlement_service_controls_20261111/fields.npz',
        'producer_sha256':ROOT/'scripts/evaluate_settlement_role_composition.py',
        'partition_module_sha256':ROOT/'polity/role_composition.py','scorer_sha256':ROOT/'polity/observed_role_contrast.py'}.items():
        if result[key]!=sha(path):raise ValueError('Changed composition evidence: '+key)
    if review['status']!='passed' or review['source_result_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_settlement_role_composition.py'):
        raise ValueError('Stale composition review')
    if result['adopt'] or result['chosen_predictor'] or result['fitted_parameters'] or result['population_food_staff_control_changed']:
        raise ValueError('Composition unexpectedly adopted')
    if len(result['cases'])!=10 or review['direct_global_AUC_checks']!=result['global_AUCs_computed']:
        raise ValueError('Incomplete composition review')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','settlement_role_composition.json'),(out/'review.json','settlement_role_composition_review.json'),
        (config/'plan.json','settlement_role_composition_plan.json'),(config/'semantic_sources.json','settlement_role_composition_sources.json')]:shutil.copyfile(src,data/name)
    labels={'village_only':'Village','vicus_only':'Vicus','small_town_only':'Unwalled small town',
        'mixed_nonroadside_labels':'Multiple non-roadside labels','roadside_only':'Roadside only'};rows=[]
    key='history_L450__recorded_roads_B1__per_centre'
    for case in result['cases'].values():
        units=case['central_support']['represented_cell_class_units']['1']
        if case['results']:
            values=f"<td>{case['results'][0]['predictors'][key]['AUC']:.4f}</td><td>{case['spatial_blocks']['equal_block_mean_AUC'][key]:.4f}</td>"
        else:values='<td colspan="2">Not scored: fixed support gate fails</td>'
        rows.append('<tr><th>'+labels[case['source_group']]+' · '+('full' if case['cohort']=='full' else 'strict non-roadside')+'</th>'+f'<td>{case["source_positive_records"]}</td><td>{units}</td>'+values+'</tr>')
    fig=ROOT/'reports/figures/settlement_role_composition_20261111.png'
    with Image.open(fig) as img:w,h=img.size
    section='''<!--settlement-role-composition-start--><section><h2>Villages and vici: different source contexts</h2><details id="settlement-role-composition" class="panel"><summary>Source-label composition · five scored cases · five unresolved cases</summary>
<p>Separating the pooled archive changes the interpretation. The fixed one-day recorded-road historical-opportunity service predictor scores about 0.39 globally for village labels and 0.89 for vicus labels. Both weaken locally. No predictor, garrison or control centre is selected from these results.</p>
<div class="table"><table id="role-composition-results"><thead><tr><th>Source context and cohort</th><th>Source positives</th><th>Positive cell/class units</th><th>Illustrative service AUC</th><th>50 km block mean</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>The comparator is the same farm/villa archive: 797 represented cell/class units. Every case needs at least 30 units in each class before scores are computed. Small-town and mixed-label groups remain unscored; the strict roadside-only group is empty by definition. Mixed cells and all nine coordinate cases are retained.</p>
'''+f'<img src="../../reports/figures/{fig.name}" width="{w}" height="{h}" alt="Village and vicus labels have different global rankings; local comparisons are much weaker.">'+'''
<p>The source authors distinguish civilian fort-origin vici from other nucleated contexts and warn of different functions. That supports separate demand and observation channels, not automatic contemporary garrisons, markets or authority. Source labels span whole records rather than dated AD200 roles. Downloads retain all 66 predictors and coverage/effort strata. Independent review checks 2,970 global AUCs, 6,270 stratum AUCs and 330 local block means.</p>
<p>Next: capacity-limited services with explicit staffing, hours, food-supported inputs and unmet requests. Qualified settlement and control consumers must share the same finite population and resource ledger.</p>
<p><a href="../../reports/SETTLEMENT_ROLE_COMPOSITION_20261111.md">Methods, source literature and limits</a> · <a href="data/settlement_role_composition.json" download>Every scored and unscored case</a> · <a href="data/settlement_role_composition_review.json" download>Independent review</a> · <a href="data/settlement_role_composition_plan.json" download>Protocol before subclass scores</a> · <a href="data/settlement_role_composition_sources.json" download>Source classification evidence</a></p></details></section><!--settlement-role-composition-end-->'''
    html=page.read_text();pattern=r'<!--settlement-role-composition-start-->[\s\S]*?<!--settlement-role-composition-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-service-controls-start-->'
        if marker not in html:raise ValueError('Publish opportunity controls first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='settlement_role_composition_20261111',status='exposed_source_role_composition',evidence='reports/SETTLEMENT_ROLE_COMPOSITION_20261111.md',
        note='Five support-qualified source-context cases scored, five explicitly unscored; no dated role/census,independent transfer,fitting or production adoption.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published all ten source-composition cases; production maps unchanged.')


if __name__=='__main__':main()
