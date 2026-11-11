"""Publish dated reference coverage for the next settlement-map release."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write


def main():
    out=ROOT/'output/institution_scope_20261111';config=ROOT/'calibration/institution_scope_20261111'
    result=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text())
    for key,path in {'plan_sha256':config/'plan.json','policy_sources_sha256':config/'sources.json',
        'producer_sha256':ROOT/'scripts/prepare_institution_scope.py','scope_module_sha256':ROOT/'polity/institution_scope.py',
        'frozen_evidence_module_sha256':ROOT/'polity/institution_evidence.py'}.items():
        if result[key]!=sha(path):raise ValueError('Changed scope source: '+key)
    for path,digest in result['parent_artifacts'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed scope parent')
    if review['status']!='passed' or review['source_result_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_institution_scope.py') or review['row_policy_cases_checked']!=10014:
        raise ValueError('Stale or incomplete scope review')
    if result['adopt'] or result['model_scores_computed'] or result['chosen_policy'] is not None:raise ValueError('Preparation unexpectedly became calibration')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','institution_scope.json'),(out/'review.json','institution_scope_review.json'),
        (config/'plan.json','institution_scope_plan.json'),(config/'sources.json','institution_scope_sources.json')]:shutil.copyfile(src,data/name)
    rows=[]
    for key,label in [('settlement_hierarchy','Settlement hierarchy'),('population_of_the_largest_settlement','Largest settlement population')]:
        a=result['policies']['explicit_only'][key];b=result['policies']['documented_parent_scope'][key]
        numeric=sum(b['positive_year200_value_states'].get(k,0) for k in ['numeric_point','numeric_interval'])
        rows.append(f'<tr><th>{label}</th><td>{a["positive_year200_polity_variable_groups"]}</td><td>{b["positive_year200_polity_variable_groups"]}</td><td>{numeric}</td></tr>')
    section='''<!--institution-scope-start--><section><h2>Earth references for the next settlement map</h2><details id="institution-scope" class="panel"><summary>Documented date scopes · settlement hierarchy and population references</summary>
<p>The linked Seshat analysis package documents fully undated single values and explicitly disputed/uncertain alternatives as spanning the parent polity duration. We compare that convention with complete explicit row intervals. Original dates and competing values remain separate; there is no value imputation or model fitting.</p>
<div class="table"><table id="institution-scope-results"><thead><tr><th>Year-200 reference</th><th>Polity-variable groups, explicit only</th><th>Groups with documented parent scope</th><th>Numeric source rows with parent scope</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>These are source support counts, not accuracy, independent settlements or observed staff. Parent scope is a documented analysis convention, not directly dated continuous operation. Both policies and all ten variables remain in the download. Mixed-date groups, unflagged alternatives, partial/outside dates and unknown codes retain review flags; no clipping, nearest-date rescue, random sampling or range midpoints.</p>
<p>Independent review reconstructs all 10,014 row-policy cases. This advances the first of four map-release milestones: Earth references, fitting/transfer checks, a shared-budget fantasy rebuild, and normal atlas publication. A located transfer pool and frozen comparison rules remain open; Seshat attributes do not supply settlement coordinates. Detailed institution/control calibration follows on the full roadmap.</p>
<p><a href="../../reports/INSTITUTION_SCOPE_20261111.md">Source policy, coverage and next steps</a> · <a href="data/institution_scope.json" download>All policies and variables</a> · <a href="data/institution_scope_review.json" download>Independent review</a> · <a href="data/institution_scope_plan.json" download>Protocol before new counts</a> · <a href="data/institution_scope_sources.json" download>Pinned author-policy provenance</a></p></details></section><!--institution-scope-end-->'''
    html=page.read_text();pattern=r'<!--institution-scope-start-->[\s\S]*?<!--institution-scope-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--institution-evidence-start-->'
        if marker not in html:raise ValueError('Publish initial institution evidence first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='seshat_polaris2026',status='prepared_institution_date_scopes_no_model_scores',evidence='reports/INSTITUTION_SCOPE_20261111.md',
        note='Explicit versus documented parent-duration scopes prepared. Raw dates,uncertainty/ranges/conflicts retained;no predictions,fitting or independent validation. Raw workbook private;located transfer still open.')
    previous=next((e for e in usage['datasets'] if e['id']==entry['id']),None)
    if previous and previous['status'].startswith('exposed_'):entry=previous
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published date-scope reference comparison;no model scores or map adoption.')


if __name__=='__main__':main()
