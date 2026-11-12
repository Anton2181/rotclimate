"""Publish a reviewed fixed-plan work audit without changing settlement/reach maps."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write


def main():
    out = ROOT / 'output/settlement_monthly_work_20261112'
    result = json.loads((out / 'results.json').read_text()); review = json.loads((out / 'review.json').read_text())
    replay = json.loads((out / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed'
    assert review['results_sha256'] == replay['results_sha256'] == sha(out / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_monthly_work.py')
    assert review['fields_sha256'] == result['fields_sha256'] == sha(out / 'fields.npz')
    for path, digest in {**result['sources_sha256'], **result['unchanged_atlas_sha256']}.items():
        if sha(ROOT / path) != digest:
            raise ValueError('Changed reviewed input: ' + path)
    for path, digest in replay['sha256'].items():
        assert sha(out / path) == digest, path
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    for name in ('results.json', 'review.json', 'replay.json', 'fields.npz', 'raw_paths.npz', 'corrected_paths.npz'):
        shutil.copyfile(out / name, data / ('monthly_work_' + name))
    shutil.copyfile(ROOT / 'calibration/settlement_monthly_work_20261112/plan.json', data / 'monthly_work_plan.json')
    lines = []
    for row in result['rows']:
        label = 'All open' if row['availability'] == 'all_open' else 'Bins 7–9 closed'
        lines.append(f'<tr><td>{row["climate"].title()} / {row["field_worker_hours"]}</td><td>{row["load_kcal"]:,.0f}</td>'
            f'<td>{label}</td><td>{row["qualified_active_sites"]} / {row["original_active_sites"]}</td></tr>')
    section = '''<!--monthly-work-start--><section><h2>Monthly collection and competing staff duties</h2><details id="monthly-work" class="panel"><summary>16 fixed-plan work audits · shared staff hours · no new control map</summary>
<p>The same supported staff must collect the declared grain before spending hours on patrol and services. Original collection owners and all twelve seasonal access masks replay exactly. Collector trips use explicit load assumptions, both directed walking legs and handling time; walking access creates no free freight.</p>
<p>With corrected climate and 600 farm hours, 368 of 889 staffed sites pass every month's collection requirement at 120,000 kcal per trip; 72 pass at 60,000. Closing bins 7–9 refuses every fixed case. These are supplied staff-only collection scenarios, not estimated historical labour rates.</p>
<div class="table"><table><thead><tr><th>Climate / farm hours</th><th>kcal / trip</th><th>Availability</th><th>Qualified / original staff sites</th></tr></thead><tbody>''' + ''.join(lines) + '''</tbody></table></div>
<img src="../../reports/figures/settlement_monthly_work_20261112.png" alt="Fixed-plan work qualification across four food scenarios and monthly collector-hour requirements">
<p><strong>Refused fixed plans keep their food and work gaps visible.</strong> Shipments can include unused destination food; these refusals do not show that fewer residents are necessary after a new joint allocation. No shipment was cut while retaining its old food claim. Only whole-year qualified sites share remaining monthly hours across all three secondary channels. Unreachable and capacity-unmet requests stay separate.</p>
<p>Independent ancestor and scalar ledgers check 463,992 path bins, 1,855,968 origin-trip bins and 200,352 provider bins. Six numerical/source packets replay byte for byte. All original population, grain and atlas inputs remain unchanged. No new census, institution, patrol footprint or authority is inferred.</p>
<p><a href="../../reports/SETTLEMENT_MONTHLY_WORK_20261112.md">Methods and next coupling</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Whole-programme plan</a> · <a href="data/monthly_work_results.json" download>All scenarios and actor totals</a> · <a href="data/monthly_work_fields.npz" download>Monthly work and requests</a> · <a href="data/monthly_work_raw_paths.npz" download>Raw collection paths</a> · <a href="data/monthly_work_corrected_paths.npz" download>Corrected collection paths</a> · <a href="data/monthly_work_review.json" download>Independent review</a> · <a href="data/monthly_work_replay.json" download>Fresh replay</a> · <a href="data/monthly_work_plan.json" download>Prior declaration</a></p>
</details></section><!--monthly-work-end-->'''
    html = page.read_text(); pattern = r'<!--monthly-work-start-->[\s\S]*?<!--monthly-work-end-->'
    if re.search(pattern, html):
        html = re.sub(pattern, lambda match: section, html)
    else:
        marker = '<!--housing-density-start-->'
        if marker not in html:
            raise ValueError('Publish existing housing evidence first')
        html = html.replace(marker, section + '\n' + marker, 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'
    usage = json.loads(registry.read_text())
    entry = dict(id='settlement_monthly_work_20261112', status='model_only_fixed_plan_work_diagnostic_no_new_earth_data',
        evidence='reports/SETTLEMENT_MONTHLY_WORK_20261112.md',
        note='16workscenarios on4existingcoupledfoodplans;explicitloads/monthlyhours,noEarthrates,foodreallocation,patrolfootprints or authorityadoption. All sourcefood and population gates retained.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(out / 'presentation.json', dict(status='published', page_sha256=sha(page), publisher_sha256=sha(Path(__file__))))
    print('Published monthly work audit; original settlement/reach maps unchanged.')


if __name__ == '__main__':
    main()
