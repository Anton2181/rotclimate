"""Document the actual cell-feedback consumer beside its earlier partial steps."""
import csv
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT, PLAN
from settlement_locations_earth import sha, write


def main():
    plan = json.loads(PLAN.read_text()); rows = []
    for mode in plan['climate_modes']:
        for c in plan['scenarios']:
            key = f'{mode}_h{c["hours_worker_year"]}_f{c["transfer_fraction"]:g}'; folder = OUT / key
            r = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
            if review['status'] != 'passed' or review['results_sha256'] != sha(folder / 'results.json'):
                raise ValueError('Current cell review required')
            rows.append(r)
    replay = json.loads((OUT / 'replay.json').read_text()); publication = json.loads((OUT / 'atlas_publication.json').read_text())
    if replay['status'] != 'passed' or not publication['defaults_unchanged']:
        raise ValueError('Fresh replay and preserved atlas publication required')
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    write(OUT / 'results.json', dict(status='reviewed_cell_feedback_and_same_plan_reach', adopt=False, rows=rows,
        plan_sha256=sha(PLAN), limits='Partial cereal scenarios, not an Earth resident-size fit or all-world diet qualification.'))
    for source, name in [(OUT/'results.json','settlement_feedback.json'),(PLAN,'settlement_feedback_plan.json'),
        (OUT/'replay.json','settlement_feedback_replay.json'),(OUT/'atlas_publication.json','settlement_feedback_publication.json')]:
        shutil.copyfile(source,data/name)
    scan_note = ''
    scan_dir = OUT / 'scan_check'
    if (scan_dir / 'results.json').exists():
        scan = json.loads((scan_dir / 'results.json').read_text())
        scan_replay = json.loads((scan_dir / 'replay.json').read_text())
        for name, digest in scan_replay['files'].items():
            if sha(scan_dir / name) != digest:raise ValueError('Finer scan replay changed')
        if scan_replay['status'] != 'passed' or scan['total_exact_overlap_points'] != 132:
            raise ValueError('Complete finer scan and fresh replay required')
        for name, target in [('results.json','settlement_feedback_scan.json'),('replay.json','settlement_feedback_scan_replay.json')]:
            shutil.copyfile(scan_dir / name, data / target)
        shutil.copyfile(PLAN.parent/'scan_check.json',data/'settlement_feedback_scan_plan.json')
        difference = max(abs(r['difference_people']) for r in scan['rows'])
        switches = sum(r['source_flags_changed'] for r in scan['rows'])
        scan_note = f'<p id="settlement-feedback-scan">The declared finer scan doubles intervals from 32 to 64 for the four 7.5% scenarios. All 132 overlapping trial points replay exactly; the largest total change is {difference:.7f} people, with {switches} source switches changed. Final work and food checks and a byte-exact fresh replay pass. This checks the tested grid, not every possible feasible branch or a global optimum. <a href="data/settlement_feedback_scan.json" download>Finer-scan results</a> · <a href="data/settlement_feedback_scan_plan.json" download>Prior scan declaration</a> · <a href="data/settlement_feedback_scan_replay.json" download>Scan replay</a></p>'
    table = ''.join(f'<tr><th>{r["climate"].capitalize()}</th><td>{r["hours_worker_year"]}</td><td>{r["transfer_fraction"]:.1%}</td><td>{r["town_people"]:,.0f}</td><td>{r["active_sources"]:,}</td></tr>' for r in rows)
    section = f'''<!--settlement-feedback-start--><section><h2>Cell people, workers and rural meals now change settlements and reach together</h2><details id="settlement-feedback" class="panel"><summary>Eight coupled scenarios · independently audited · optional maps in the normal atlas</summary>
<p><strong>Actual rural-food feedback is now recomputed.</strong> Moving a resident changes remaining workers, cereal output, rural meals and export inventories before that same person's destination food and institutional availability are accepted. Every positive town passes its origin catchment's source-food gate. Deficit rural cells export nothing and remain visible in the ledger.</p>
<div class="table"><table id="settlement-feedback-results"><thead><tr><th>Climate</th><th>Field hours / worker</th><th>Transfer ceiling</th><th>Town residents</th><th>Conditional sources</th></tr></thead><tbody>{table}</tbody></table></div>
<p>These use the checked local food-collection origins, not the preceding wide trade catchments. Independent monthly inventory and work checks pass; all eight fresh result/cell files are byte-exact. The SAME audited cohorts select seasonal reach sources. All-source transport reproduces the original actor/cell/season reference exactly; all18 actors remain represented.</p>
<img src="../../reports/figures/settlement_feedback_maps_20261112.png" alt="The same resident, field-work and grain allocation changes both settlements and reach on corrected climate">
<img src="../../reports/figures/settlement_feedback_scenarios_20261112.png" alt="All eight transfer and work scenarios, conditional sources, retained grain and unhidden rural deficits">
<p><strong>Research scenarios, not calibrated city sizes.</strong> Reference populations, work availability, diets and cohorts remain assumptions. Rural cereal deficits elsewhere persist; these results do not establish a complete food system, real famine or sovereignty. Missing/mobile/nonstate communities are not declared empty. The finite scan certifies examined feasible allocations and does not prove a global optimum.</p>
<p><a href="../earth_fit/#layer=reach_towns&amp;variant=feedback600_75&amp;climate=corrected&amp;all=1">Open the coupled settlement map</a> · <a href="../earth_fit/#layer=reach_defacto&amp;variant=feedback600_75&amp;climate=corrected&amp;all=1">Open its SAME-cohort reach</a> · <a href="../../reports/SETTLEMENT_FEEDBACK_20261112.md">Methods and next checks</a> · <a href="data/settlement_feedback.json" download>All eight results</a> · <a href="data/settlement_feedback_plan.json" download>Prior declaration</a> · <a href="data/settlement_feedback_replay.json" download>Fresh replay</a> · <a href="data/settlement_feedback_publication.json" download>Original-packet preservation</a></p>
{scan_note}
<p>The original defaults and parent model packets are unchanged. Enable Experimental &amp; diagnostics to compare the new entries inside Settlements and Supply-supported reach. Site CSVs and per-case cell inventories are available in those existing panels.</p></details></section><!--settlement-feedback-end-->'''
    html = page.read_text(); pattern = r'<!--settlement-feedback-start-->[\s\S]*?<!--settlement-feedback-end-->'
    if re.search(pattern,html):html = re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-residents-start-->'
        if marker not in html:raise ValueError('Publish the preceding resident-budget result first')
        html=html.replace(marker,section+'\n'+marker,1)
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json'; usage=json.loads(registry.read_text())
    entry=dict(id='settlement_feedback_20261112',status='cell_population_work_food_scenario_not_empirically_calibrated',
        evidence='reports/SETTLEMENT_FEEDBACK_20261112.md',note='Eight coupled local cereal scenarios; current published map inputs, no new Earth targets. Real cell-level source food/worker feedback and same-cohort reach audited. Rural deficits elsewhere and empirical resident-size/occupation gaps remain. Original defaults unchanged.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry];write(registry,usage);shutil.copyfile(registry,data/'dataset_usage.json')
    write(OUT/'presentation.json',dict(status='published',page_sha256=sha(page),publisher_sha256=sha(Path(__file__))))
    print('Published actual coupled feedback and existing-mode map links in normal Earth evidence.')


if __name__=='__main__':main()
