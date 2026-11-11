"""Publish a finite-work consumer diagnostic without adopting service rates."""
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
    out=ROOT/'output/settlement_service_capacity_20261111';plan=ROOT/'calibration/settlement_service_capacity_20261111/plan.json'
    result=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text());figure=json.loads((out/'figure_provenance.json').read_text())
    if result['plan_sha256']!=sha(plan) or result['fields_sha256']!=sha(out/'fields.npz'):raise ValueError('Changed capacity inputs/fields')
    for path,digest in {**result['sources'],**result['producers'],**figure['source_models_and_land_lookup']}.items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed capacity source: '+path)
    if review['status']!='passed' or review['source_result_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_settlement_service_capacity.py'):
        raise ValueError('Stale capacity review')
    if review['shared_hour_cases']!=60 or review['periodic_food_cases']!=20 or result['adopt'] or result['earth_calibrated_service_rates'] or result['population_food_staff_control_changed']:
        raise ValueError('Incomplete or unexpectedly adopted capacity diagnostic')
    fig=ROOT/'reports/figures/settlement_service_capacity_20261111.png'
    if sha(fig)!=figure['figure_sha256'] or sha(ROOT/'scripts/plot_settlement_service_capacity.py')!=figure['producer_sha256']:raise ValueError('Stale capacity figure')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','settlement_service_capacity.json'),(out/'review.json','settlement_service_capacity_review.json'),
        (plan,'settlement_service_capacity_plan.json'),(out/'figure_provenance.json','settlement_service_capacity_figure.json')]:shutil.copyfile(src,data/name)
    rows=[]
    for row in result['scenarios']:
        if row['case']!='joint365':continue
        value='No demand' if row['fulfilled_request_fraction'] is None else f"{100*row['fulfilled_request_fraction']:.2f}%"
        rows.append(f'<tr><th>{row["climate"].capitalize()} · {100*row["committed_fraction"]:g}% other duties</th><td>{sum(row["requested_by_channel"]):,.0f}</td><td>{value}</td><td>{row["used_staff_hours"]:,.0f}</td><td>{row["unused_staff_hours"]:,.0f}</td></tr>')
    with Image.open(fig) as img:w,h=img.size
    section='''<!--settlement-service-capacity-start--><section><h2>Service work shares the settlement food and staffing ledger</h2><details id="settlement-service-capacity" class="panel"><summary>Finite multi-service hours · 20 food replays · 60 work-budget cases</summary>
<p>Services now share one explicit labour budget across request types. Staff come from the existing food-supported resident cohort; other duties are reserved first. Unreachable requests, capacity deficits and unused hours stay visible. This consumer does not add residents, staff or food, and does not reroute requests automatically.</p>
<p>The fixed illustration uses two neutral annual requests per resident, costing one and two hours, 600 gross hours per supported cohort member and 0/50/100% prior commitments. These are stress units, not Earth-calibrated ancient productivity. Choice is local to the original site; this is not a new travel-access or control map.</p>
<div class="table"><table id="service-capacity-results"><thead><tr><th>Year-store case</th><th>Potential requests</th><th>Modelled fulfilled</th><th>Used hours</th><th>Unused hours</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>The workload is mostly nonbinding under both 0% and 50% prior commitments; reserving all hours leaves no service capacity. These percentages measure the declared requests, not reconstruction accuracy or actual historical welfare. Every existing food-constrained case and all three commitments remain in the download. Zero demand is reported as null, not perfect fulfilment.</p>
'''+f'<img src="../../reports/figures/{fig.name}" width="{w}" height="{h}" alt="Local-only work diagnostic at unchanged marked/proposed atlas sites; not calibrated service access or political control.">'+'''
<p>Independent checks replay 20 original food cases and all 60 work scenarios, including every origin request and provider-hour budget. Both source atlas packets remain byte-identical. Existing staff affiliation and food assumptions are still scenarios; source labels and map icons do not establish current institutions. Next: monthly supported-provider access and explicit labour commitments shared with collection and patrol.</p>
<p><a href="../../reports/SETTLEMENT_SERVICE_CAPACITY_20261111.md">Equations, literature context and limits</a> · <a href="data/settlement_service_capacity.json" download>All work cases and food replays</a> · <a href="data/settlement_service_capacity_review.json" download>Independent review</a> · <a href="data/settlement_service_capacity_plan.json" download>Protocol before results</a> · <a href="data/settlement_service_capacity_figure.json" download>Map provenance</a> · <a href="../../output/settlement_service_capacity_20261111/fields.npz" download>Model service-work arrays</a></p></details></section><!--settlement-service-capacity-end-->'''
    html=page.read_text();pattern=r'<!--settlement-service-capacity-start-->[\s\S]*?<!--settlement-service-capacity-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-role-composition-start-->'
        if marker not in html:raise ValueError('Publish source composition first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='settlement_service_capacity_20261111',status='implementation_work_budget_diagnostic_not_calibrated',evidence='reports/SETTLEMENT_SERVICE_CAPACITY_20261111.md',
        note='Frozen atlas residents and food support consumed once by shared service hours. Stress rates,identity choice only; no new Earth calibration,role/political adoption or independent transfer.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published shared-work implementation diagnostic; no calibrated service rates or production adoption.')


if __name__=='__main__':main()
