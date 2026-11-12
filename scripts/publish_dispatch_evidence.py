"""Publish the joint map milestone and its numerical/source certificates."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write


def main():
    out = ROOT / 'output/settlement_dispatch_20261112'; page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    publication = json.loads((out / 'atlas_publication.json').read_text()); replay = json.loads((out / 'replay.json').read_text())
    assert replay['status'] == 'passed' and publication['defaults_unchanged']
    assert publication['manifest_sha256'] == sha(ROOT / 'atlases/earth_fit/data/settlement_dispatch.json')
    rows = []; reviews = []
    for key, files in replay['byte_exact_cases'].items():
        folder = out / key
        for name, digest in files.items(): assert sha(folder / name) == digest
        r = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
        assert review['status'] == 'passed' and review['results_sha256'] == sha(folder / 'results.json')
        rows.append(r); reviews.append(dict(key=key, **review))
    assert len(rows) == 16
    write(out / 'summary.json', dict(status='sixteen_checked_joint_dispatch_map_cases', adopt=False, rows=rows,
        atlas_publication_sha256=sha(out / 'atlas_publication.json'), replay_sha256=sha(out / 'replay.json')))
    write(out / 'review.json', dict(status='passed', cases=reviews,
        reach_reviews={mode: json.loads((out / f'{mode}_reach_review.json').read_text()) for mode in ('raw', 'corrected')}))
    for src, name in [(out / 'summary.json', 'settlement_dispatch_results.json'), (out / 'review.json', 'settlement_dispatch_review.json'),
        (out / 'replay.json', 'settlement_dispatch_replay.json'), (out / 'atlas_publication.json', 'settlement_dispatch_publication.json'),
        (ROOT / 'calibration/settlement_dispatch_20261112/plan.json', 'settlement_dispatch_plan.json')]:
        shutil.copyfile(src, data / name)
    table = ''.join(f'<tr><td>{r["climate"].title()}</td><td>{r["hours_worker_year"]}</td><td>{r["load_kcal"]:,.0f}</td>'
        f'<td>{"All open" if r["availability"] == "all_open" else "Bins 7–9 closed"}</td><td>{r["town_people"]:,.0f}</td><td>{r["active_sources"]}</td></tr>' for r in rows)
    section = '''<!--settlement-dispatch-start--><section><h2>Joint dispatch, collection work and residents</h2><details id="settlement-dispatch" class="panel"><summary>16 checked scenarios · new settlement and potential-access maps</summary>
<p>Each resident trial changes remaining rural workers, cereal production and meals before dispatch is limited by monthly collector hours. Smaller shipments remove surplus deliveries while preserving source food and destination stocks. The same food-supported staff then share remaining hours across neutral patrol and service requests.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Farm hours</th><th>kcal / trip</th><th>Collection</th><th>Town residents</th><th>Conditional sources</th></tr></thead><tbody>''' + table + '''</tbody></table></div>
<p>Corrected climate, 600 farm hours and 120,000 kcal per collector trip: 378,281 town residents and 889 staffed sources, versus 95,359 residents at 368 sources passing the prior fixed-shipment audit. Those fixed shipments included avoidable surplus; the original food-only total of 419,264 is also retained as a separate comparison. All eight closed-bin cases remain visible zeros under the supplied 90-day destination stores.</p>
<img src="../../reports/figures/settlement_dispatch_corrected_maps_20261112.png" alt="Paired corrected-climate settlements and potential-access maps before and after joint collection work">
<img src="../../reports/figures/settlement_dispatch_raw_maps_20261112.png" alt="Raw-climate settlement and potential-access map comparison">
<img src="../../reports/figures/settlement_dispatch_scenarios_20261112.png" alt="All open-bin joint scenarios compared with original food-only totals and fixed-plan work qualification">
<p><strong>Experimental resource scenarios.</strong> All positive cases pass population, rural food, destination food and monthly collection checks, with sixteen byte-exact fresh result/field replays. Proportional dispatch and the finite resident search do not establish a global optimum. Loads, diets, work availability and roles remain supplied assumptions. Maps show potential travel access from qualified sources; geographic patrol work and political authority remain unqualified. Failed cases do not establish empty land or absent communities.</p>
<p><a href="../earth_fit/#layer=reach_towns&amp;variant=dispatch600_120000_open&amp;climate=corrected&amp;all=1">Open joint settlements</a> · <a href="../earth_fit/#layer=reach_defacto&amp;variant=dispatch300_120000_open&amp;climate=corrected&amp;all=1">Open potential source access</a> · <a href="../../reports/SETTLEMENT_DISPATCH_20261112.md">Methods and next checks</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Living whole-programme plan</a> · <a href="data/settlement_dispatch_results.json" download>All results</a> · <a href="data/settlement_dispatch_review.json" download>Independent cell/work/reach reviews</a> · <a href="data/settlement_dispatch_replay.json" download>Fresh replay</a> · <a href="data/settlement_dispatch_publication.json" download>Earlier-map preservation</a> · <a href="data/settlement_dispatch_plan.json" download>Prior declaration</a></p>
<p>The normal defaults and earlier experimental maps are unchanged. Enable Experimental &amp; diagnostics to compare the new entries in Settlements and Supply-supported reach. Site CSVs now include monthly collection, gross and unused staff hours; full cell arrays are available alongside the existing food ledger.</p></details></section><!--settlement-dispatch-end-->'''
    html = page.read_text(); pattern = r'<!--settlement-dispatch-start-->[\s\S]*?<!--settlement-dispatch-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        marker = '<!--monthly-work-start-->'
        if marker not in html: raise ValueError('Preserve the preceding monthly-work evidence first')
        html = html.replace(marker, section + '\n' + marker, 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='settlement_dispatch_20261112', status='model_only_joint_dispatch_food_work_scenarios',
        evidence='reports/SETTLEMENT_DISPATCH_20261112.md',
        note='16same-input proportional-dispatch cases;newoptional settlement/potential-travel maps,no newEarthdata,sizefit,patrolschedule,authority or defaultadoption.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(out / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), producer_sha256=sha(Path(__file__))))
    print('Published checked joint dispatch maps,all16cases and numerical/source certificates in normal evidence atlas.')


if __name__ == '__main__': main()
