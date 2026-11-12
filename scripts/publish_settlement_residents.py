"""Expose the finite resident consumer and its explicit remaining food gap."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_settlement_residents import OUT
from settlement_locations_earth import sha, write


def main():
    r = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    replay = json.loads((OUT / 'replay.json').read_text())
    if r['adopt'] or r['earth_calibrated_resident_sizes'] or len(r['rows']) != 60:
        raise ValueError('Wrong resident implementation diagnostic')
    if review['status'] != 'passed' or review['results_sha256'] != sha(OUT / 'results.json'):
        raise ValueError('Stale independent resident review')
    if review['reviewer_sha256'] != sha(ROOT / 'scripts/review_settlement_residents.py'):
        raise ValueError('Changed resident reviewer')
    for path, digest in {**r['sources'], **r['producers']}.items():
        if sha(ROOT / path) != digest:
            raise ValueError('Changed resident source: ' + path)
    if replay['status'] != 'passed':
        raise ValueError('Fresh resident replay required')
    for name, digest in replay['byte_exact_outputs'].items():
        if sha(OUT / name) != digest:
            raise ValueError('Stale resident replay')
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    for name, target in [('results.json', 'settlement_residents.json'), ('review.json', 'settlement_residents_review.json'),
        ('replay.json', 'settlement_residents_replay.json'), ('fields.npz', 'settlement_residents_fields.npz')]:
        shutil.copyfile(OUT / name, data / target)
    rows = []
    for row in r['rows']:
        if row['case'] != 'joint365':
            continue
        rows.append(f'<tr><th>{row["climate"].capitalize()}</th><td>{row["transfer_fraction"]:.1%}</td>'
            f'<td>{row["old_town_people"]:,.0f}</td><td>{row["town_people"]:,.0f}</td>'
            f'<td>{row["rural_people"]:,.0f}</td><td>{row["active_sources"]:,}</td></tr>')
    section = f'''<!--settlement-residents-start--><section><h2>Resident budgets feed the same food-supported settlements</h2>
<details id="settlement-residents" class="panel"><summary>One population allowance for civilians and staff · 60 conditional scenarios reviewed</summary>
<p id="settlement-residents-verdict"><strong>Implementation diagnostic, not calibrated resident sizes or a new production map.</strong> A finite allowance from each existing model catchment now caps civilians and institutional residents together. Unused allowances stay rural. Neither a minimum town size nor a staff request can create people, and catchments cannot contribute the same population twice.</p>
<p>We replayed 20 existing destination-food allocations and tested 5%, 7.5% and 10% resident-transfer limits: 60 scenarios, 62,610 site/scenario checks. Existing catchment people are a conditional population envelope, not observed inhabitants. The supplied shares remain assumptions.</p>
<div class="table"><table id="settlement-residents-results"><thead><tr><th>Climate</th><th>Transfer limit</th><th>Earlier town total</th><th>Budget-capped town total</th><th>Rural remainder</th><th>Staffed sources</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>The table uses the year-store food case; all 60 cases are downloadable. The corrected 7.5% case retains 812,204 town residents and 1,010 conditional sources, compared with 812,546 / 1,011 before the population cap. Those residents belong to the same finite catchment pool; they are not additional people on top of a rural census.</p>
<p><strong>Remaining integration gap:</strong> these atlas sensitivities reuse food arrivals generated under the earlier rural-food claim. They have not recomputed rural meals, production labour, collection or reach after relocation. They must not replace the main map. A new source-food gate requires declared shipments to match destination arrivals and still leave enough for the remaining rural residents. Manufactured examples conserve both people and grain, including transport loss; a rural-meal shortfall is rejected. These examples verify accounting, not Earth accuracy.</p>
<p><a href="../../reports/SETTLEMENT_RESIDENTS_20261112.md">Allocation, source-food gate and next integration</a> · <a href="data/settlement_residents.json" download>All60 scenarios and manufactured gates</a> · <a href="data/settlement_residents_fields.npz" download>Resident and destination-food arrays</a> · <a href="data/settlement_residents_review.json" download>Independent scalar-cap review</a> · <a href="data/settlement_residents_replay.json" download>Fresh byte-exact replay</a></p>
</details></section><!--settlement-residents-end-->'''
    html = page.read_text(); pattern = r'<!--settlement-residents-start-->[\s\S]*?<!--settlement-residents-end-->'
    if re.search(pattern, html):
        html = re.sub(pattern, lambda m: section, html)
    else:
        marker = '<!--settlement-joint-start-->'
        if marker not in html:
            raise ValueError('Publish the location comparison before the resident consumer')
        html = html.replace(marker, section + '\n' + marker, 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'
    usage = json.loads(registry.read_text())
    entry = dict(id='settlement_residents_20261112', status='conditional_population_budget_implementation_not_calibrated',
        evidence='reports/SETTLEMENT_RESIDENTS_20261112.md',
        note='60conditional sensitivities on20existing atlas destination-food cases. Model catchment people and transfer shares are scenarios. Source-food gate verified on manufactured cases; actual rural-food/production feedback remains pending. No new Earth fit or default adoption.')
    usage['datasets'] = [e for e in usage['datasets'] if e['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', page_sha256=sha(page), publisher_sha256=sha(Path(__file__))))
    print('Published60resident budget sensitivities with the remaining source-food gap explicit.')


if __name__ == '__main__':
    main()
