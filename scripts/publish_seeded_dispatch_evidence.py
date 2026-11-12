"""Publish the repaired search version while preserving the original map record."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write


def main():
    out = ROOT / 'output/settlement_dispatch_seeded_20261112'; page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    replay = json.loads((out / 'replay.json').read_text()); publication = json.loads((out / 'atlas_publication.json').read_text())
    assert replay['status'] == 'passed' and len(replay['byte_exact_cases']) == 16
    assert publication['manifest_sha256'] == sha(ROOT / 'atlases/earth_fit/data/settlement_dispatch_seeded.json')
    rows = []; reviews = []
    for key, files in replay['byte_exact_cases'].items():
        folder = out / key
        for name, digest in files.items(): assert sha(folder / name) == digest
        r = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
        assert review['status'] == 'passed' and review['results_sha256'] == sha(folder / 'results.json')
        rows.append(r); reviews.append(dict(key=key, **review))
    write(out / 'summary.json', dict(status='sixteen_threshold_checked_joint_map_cases', adopt=False, rows=rows,
        atlas_publication_sha256=sha(out / 'atlas_publication.json'), replay_sha256=sha(out / 'replay.json')))
    write(out / 'review.json', dict(status='passed', cases=reviews,
        reach_reviews={mode: json.loads((out / f'{mode}_reach_review.json').read_text()) for mode in ('raw', 'corrected')}))
    for src, name in [(out / 'summary.json', 'dispatch_seeded_results.json'), (out / 'review.json', 'dispatch_seeded_review.json'),
        (out / 'replay.json', 'dispatch_seeded_replay.json'), (out / 'atlas_publication.json', 'dispatch_seeded_publication.json'),
        (ROOT / 'calibration/settlement_dispatch_seeded_20261112/plan.json', 'dispatch_seeded_plan.json')]:
        shutil.copyfile(src, data / name)
    table = ''.join(f'<tr><td>{r["climate"].title()}</td><td>{r["hours_worker_year"]}</td><td>{r["load_kcal"]:,.0f}</td>'
        f'<td>{"All open" if r["availability"] == "all_open" else "Bins 7–9 closed"}</td><td>{r["town_people"]:,.0f}</td><td>{r["active_sources"]}</td></tr>' for r in rows)
    section = '''<!--dispatch-seeded-start--><section><h2>Threshold-checked joint settlement and collection maps</h2><details id="dispatch-seeded" class="panel"><summary>16 corrected search versions · physical budgets unchanged</summary>
<p><strong>The narrow staffed ranges missed by the first map search are now checked explicitly.</strong> The 64-interval search additionally probes the existing 100-staff plus 50-civilian transition and refines its feasible branch. Every positive result still passes the same finite people, rural/field work, source meals, grain inventories and monthly collector-hour gates.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Farm hours</th><th>kcal / trip</th><th>Collection</th><th>Town residents</th><th>Conditional sources</th></tr></thead><tbody>''' + table + '''</tbody></table></div>
<p>Open-bin source sets now match the original food-only sets exactly: raw 861/725 and corrected 889/755 at 600/300 farm hours. The corrected 300-hour, 120,000-load case has 282,045 modeled town residents. Resident sizes and deliveries remain constrained by collection; the earlier source losses included numerical misses. All eight closed-bin cases remain zero under the supplied store capacity.</p>
<img src="../../reports/figures/settlement_dispatch_seeded_corrected_maps_20261112.png" alt="Threshold-checked corrected-climate town sizes and unchanged potential source travel access">
<img src="../../reports/figures/settlement_dispatch_seeded_raw_maps_20261112.png" alt="Threshold-checked raw-climate joint settlement and potential-access maps">
<img src="../../reports/figures/settlement_dispatch_seeded_scenarios_20261112.png" alt="All open-bin corrected-search scenarios versus original food-only and fixed-plan audit results">
<p>All sixteen physical reviews and fresh result/field byte replays pass. This repairs a known numerical transition; finite search and proportional dispatch still do not prove global optimality. Loads, diets, roles and work remain supplied scenarios. Colored reach is potential travel access, not funded geographic patrol coverage or political authority. Missing providers do not establish absent communities.</p>
<p><a href="../earth_fit/#layer=reach_towns&amp;variant=dispatchv2600_120000_open&amp;climate=corrected&amp;all=1">Open threshold-checked settlements</a> · <a href="../earth_fit/#layer=reach_defacto&amp;variant=dispatchv2300_120000_open&amp;climate=corrected&amp;all=1">Open their potential source access</a> · <a href="../../reports/SETTLEMENT_DISPATCH_SEEDED_20261112.md">Methods and next duty-destination work</a> · <a href="data/dispatch_seeded_results.json" download>All corrected search results</a> · <a href="data/dispatch_seeded_review.json" download>Independent physical/source reviews</a> · <a href="data/dispatch_seeded_replay.json" download>Fresh replay</a> · <a href="data/dispatch_seeded_publication.json" download>Original-map preservation</a> · <a href="data/dispatch_seeded_plan.json" download>Prior declaration</a></p>
<p>Choose “Threshold-checked food + collection” behind Experimental &amp; diagnostics in the existing map selectors. Earlier versions and the normal defaults remain available; the earlier-search limitation is explicit. Site CSVs retain monthly collection, gross and unused staff hours and full cell downloads.</p></details></section><!--dispatch-seeded-end-->'''
    html = page.read_text(); pattern = r'<!--dispatch-seeded-start-->[\s\S]*?<!--dispatch-seeded-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        marker = '<!--dispatch-search-start-->'
        if marker not in html: raise ValueError('Preserve the explicit search-error record first')
        html = html.replace(marker, section + '\n' + marker, 1)
    html = html.replace('A separately declared threshold-seeded solver will publish corrected optional versions.',
        'The separately declared threshold-seeded solver now provides corrected optional versions above.')
    html = html.replace('corrected solver versions are developed separately.', 'corrected threshold-checked versions are now available above.')
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='settlement_dispatch_seeded_20261112', status='model_only_threshold_checked_joint_resource_maps',
        evidence='reports/SETTLEMENT_DISPATCH_SEEDED_20261112.md',
        note='Knownstaffactivationseed repairs finitegridmisses;all16physicalcases/replays reviewed,no newEarthdata,globaloptimum,geographicpatrol or empiricaladoptionclaim.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(out / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__))))
    print('Published threshold-checked joint map versions and explicit earlier-search correction.')


if __name__ == '__main__': main()
