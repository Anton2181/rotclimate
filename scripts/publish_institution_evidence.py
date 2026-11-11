"""Publish provider assumptions and aggregate Earth-source preparation only."""
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
    out=ROOT/'output/institution_evidence_20261111';config=ROOT/'calibration/institution_evidence_20261111'
    earth=json.loads((out/'earth_preparation.json').read_text());audit=json.loads((out/'provider_audit.json').read_text());review=json.loads((out/'review.json').read_text())
    if earth['plan_sha256']!=sha(config/'plan.json') or audit['plan_sha256']!=sha(config/'plan.json') or earth['sources_sha256']!=sha(config/'sources.json'):
        raise ValueError('Changed institution source plan')
    if earth['producer_sha256']!=sha(ROOT/'scripts/prepare_institution_evidence.py') or earth['evidence_module_sha256']!=sha(ROOT/'polity/institution_evidence.py'):
        raise ValueError('Changed institution evidence producer')
    if review['status']!='passed' or review['earth_preparation_sha256']!=sha(out/'earth_preparation.json') or review['provider_audit_sha256']!=sha(out/'provider_audit.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_institution_evidence.py'):
        raise ValueError('Stale institution review')
    for path,digest in audit['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed provider source')
    if earth['model_scores_computed'] or earth['model_prediction_matching'] or earth['independent_or_sealed'] or audit['physical_population_food_staff_control_changed']:
        raise ValueError('Preparation unexpectedly became fitting/adoption')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'earth_preparation.json','institution_earth_preparation.json'),(out/'provider_audit.json','institution_provider_audit.json'),
        (out/'review.json','institution_review.json'),(config/'plan.json','institution_plan.json'),(config/'sources.json','institution_sources.json')]:shutil.copyfile(src,data/name)
    providers=[]
    for climate,row in audit['atlases'].items():
        providers.append(f'<tr><th>{climate.capitalize()}</th><td>{row["sites"]}</td><td>{row["marked_sites"]}</td><td>{row["legacy_staff"]:,.0f}</td><td>{row["staff_at_generated_sites"]:,.0f} ({100*row["fraction_of_staff_at_generated_sites"]:.2f}%)</td></tr>')
    rows=[]
    for variable,row in earth['variables'].items():
        issues=sum(row['value_states'].get(k,0) for k in ['unresolved_code','unresolved_value_shape','reversed_numeric_bounds'])
        rows.append(f'<tr><th>{variable.replace("_"," ")}</th><td>{row["records"]}</td><td>{row["time_states"].get("missing_time_bounds",0)}</td><td>{issues}</td></tr>')
    fig=ROOT/'reports/figures/institution_provider_audit_20261111.png'
    with Image.open(fig) as img:w,h=img.size
    section='''<!--institution-evidence-start--><section><h2>Before more service maps: which providers are evidence?</h2><details id="institution-evidence" class="panel"><summary>All-actor staffing assumptions · new Seshat source preparation · no fit</summary>
<p>About 86% of the year-store institutional cohort comes from proposed settlements with painted-claim affiliations. Food support does not prove a staffed institution or operational authority. Better routes alone would preserve that assumption. Marked affiliation is not a measured workforce either.</p>
<div class="table"><table id="institution-provider-results"><thead><tr><th>Climate input</th><th>Sites</th><th>Marked</th><th>Legacy staff</th><th>At proposed-site hypotheses</th></tr></thead><tbody>'''+''.join(providers)+'''</tbody></table></div>
'''+f'<img src="../../reports/figures/{fig.name}" width="{w}" height="{h}" alt="Staff provenance for every actor: most legacy staff are assigned to proposed-site hypotheses, not measured institutions.">'+'''
<p>All 18 actors and unresolved affiliations remain visible, including tribal and non-imperial groups. Missing marked sources does not mean missing governance. A monastery is not automatically a garrison; a fortified town does not establish professional soldiers; map icons do not supply staff quantities or dated roles.</p>
<p>We pinned the Seshat Polaris 2026 release and prepared 5,007 institution/hierarchy records across 626 polity keys. The codebook separates specialist bureaucracy, military, religious and settlement hierarchies, and distinguishes unknown or inferred evidence from absence. Generalists can govern without full-time bureaucrats. This is source preparation only: no model predictions, scores or ancient staff calibration.</p>
<div class="table"><table id="institution-source-results"><thead><tr><th>Earth observable</th><th>Records</th><th>Missing explicit time bounds</th><th>Value review items</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>4,511 records lack a complete explicit row-level time interval; whether null means whole-polity scope still needs source/API confirmation. Six unmapped codes, malformed/ranged values and repeated keys remain visible. A suspicious legacy officer/lawyer alias is not used for joins. We do not silently fill dates, turn missing values into absence or replace intervals with midpoints.</p>
<p>Next: resolve source semantics, separate provider roles/evidence from staffing quantities, then declare institutional development/transfer checks. Monthly staffed-provider access and shared patrol/collection/service hours must feed the same population and food ledger. No current map or physics changed.</p>
<p><a href="../../reports/INSTITUTION_EVIDENCE_20261111.md">Findings, academic sources and next gates</a> · <a href="data/institution_provider_audit.json" download>All-actor provider audit</a> · <a href="data/institution_earth_preparation.json" download>Earth schema/uncertainty preparation</a> · <a href="data/institution_review.json" download>Independent review</a> · <a href="data/institution_plan.json" download>Declared preparation plan</a> · <a href="data/institution_sources.json" download>Pinned source provenance</a></p></details></section><!--institution-evidence-end-->'''
    html=page.read_text();pattern=r'<!--institution-evidence-start-->[\s\S]*?<!--institution-evidence-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-service-capacity-start-->'
        if marker not in html:raise ValueError('Publish service capacity first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='seshat_polaris2026',status='prepared_institution_schema_no_model_scores',evidence='reports/INSTITUTION_EVIDENCE_20261111.md',
        note='Pinned release;aggregate schema/time/uncertainty preparation only,no model matching/scores or staffing fit. Raw data private;not sealed/independent. Null dates,codes,aliases and interval review gates remain.')
    previous=next((e for e in usage['datasets'] if e['id']==entry['id']),None)
    if previous and previous['status'].startswith('exposed_'):entry=previous
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published provider assumptions and Earth institution preparation;no scores/adoption.')


if __name__=='__main__':main()
