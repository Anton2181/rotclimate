"""Publish the feasible spare-provider diagnostic without changing point maps."""
import json
from pathlib import Path
import re
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_spare_assignment_20261112'


def main():
    result = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text()); replay = json.loads((OUT / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_spare_visit_assignment.py')
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for name, digest in replay['byte_exact_files'].items(): assert sha(OUT / name) == digest
    rows = result['rows']; labels = [f'{r["climate"].title()} · {r["hours_worker_year"]}h · crew {r["crew"]}' for r in rows]; y = np.arange(8)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.8)); added = [r['added_visits'] for r in rows]
    axes[0].barh(y, added, color='#487e70'); axes[0].set_xlabel('Additional whole point visits / year'); axes[0].set_title('Feasible gains from spare same-actor providers')
    recovered = [100 * r['added_visits'] / r['original_capacity_unmet'] for r in rows]
    axes[1].barh(y, recovered, color='#ab8350'); axes[1].set_xlabel('% of original assigned-capacity deficit recovered'); axes[1].set_title('Remaining deficits are not proved unavoidable')
    for ax, values in zip(axes, (added, recovered)):
        ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(0, max(values) * 1.22); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
        for i, value in enumerate(values): ax.text(value + max(values) * .025, i, f'{value:,.0f}' if ax is axes[0] else f'{value:.1f}%', va='center', fontsize=9)
    fig.suptitle('An assign-once restriction misses some feasible visits;the original maps remain intact', fontsize=12)
    fig.text(.5, .025, 'All original completions and providers retained · ONLY unspent patrol reservations used · overall task completion rises 0.07–0.43 percentage points.\n'
        'Constructive lower bound,not a global optimum,observed patrols,individual rosters,territory or authority.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.19, right=.99, top=.87, bottom=.20, wspace=.80)
    figure = ROOT / 'reports/figures/network_visit_spare_assignment_20261112.png'; fig.savefig(figure, dpi=160); plt.close(fig)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    for src, name in [(OUT / 'results.json', 'spare_visits_results.json'), (OUT / 'review.json', 'spare_visits_review.json'),
        (OUT / 'replay.json', 'spare_visits_replay.json'), (ROOT / 'calibration/network_visit_spare_assignment_20261112/plan.json', 'spare_visits_plan.json')]: shutil.copyfile(src, data / name)
    table = ''.join(f'<tr><td>{r["climate"].title()}</td><td>{r["hours_worker_year"]}</td><td>{r["crew"]}</td><td>{r["original_completed"]:,}</td>'
        f'<td>+{r["added_visits"]:,}</td><td>{r["final_completed"]:,}</td><td>{r["remaining_capacity_unmet"]:,}</td></tr>' for r in rows)
    section = '''<!--spare-visits-start--><section><h2>Spare-provider assignment diagnostic</h2><details id="spare-visits" class="panel"><summary>8 feasible-extension tests · original point maps preserved</summary>
<p><strong>Some visits missed by the assign-once rule can be completed using spare providers.</strong> Keep every original completed task and provider immutable. Offer only original assigned-capacity-unmet tasks to other same-actor,crew-supported providers on already-checked walking routes. Tasks are ordered by their cheapest eligible crew-hour cost,then actor and target;choose the cheapest provider whose current unspent patrol slice affords the whole task. Collection,other services and gross unused hours remain unavailable.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Farm hours</th><th>Crew</th><th>Original visits</th><th>Additional</th><th>Feasible extended visits</th><th>Capacity still unmet</th></tr></thead><tbody>''' + table + '''</tbody></table></div>
<img src="../../reports/figures/network_visit_spare_assignment_20261112.png" alt="Eight constructive spare-provider visit gains and recovered shares of original capacity deficits">
<p>Gains are 192–1,117 visits,or 0.07–0.43 percentage points of all requested tasks. One-person crews recover 19.7–22.8% of their smaller capacity deficits;four-person crews recover 4.9–6.9%. Walking-unreachable and initially-unaffordable-crew partitions stay unchanged. All actor/bin partitions and monthly provider ledgers pass independent scalar review;fresh results and fields are byte exact. Zero spare budgets add zero visits.</p>
<p>This is a constructive feasible lower bound,not a global optimum or proof that remaining deficits are unavoidable. It does not qualify observed visits,individual daily rosters,territory or authority. The original eight point maps remain unchanged;the extension is a diagnostic,not a silently replaced map family.</p>
<p><a href="../../reports/NETWORK_VISIT_SPARE_ASSIGNMENT_20261112.md">Methods and next target-grid audit</a> · <a href="data/spare_visits_results.json" download>All extension results</a> · <a href="data/spare_visits_review.json" download>Independent review</a> · <a href="data/spare_visits_replay.json" download>Fresh byte replay</a> · <a href="data/spare_visits_plan.json" download>Prior declaration</a></p></details></section><!--spare-visits-end-->'''
    html = page.read_text(); pattern = r'<!--spare-visits-start-->[\s\S]*?<!--spare-visits-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--network-visits-start-->' in html
        html = html.replace('<!--network-visits-start-->', section + '\n<!--network-visits-start-->', 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='network_visit_spare_assignment_20261112', status='model_only_constructive_assignment_diagnostic', evidence='reports/NETWORK_VISIT_SPARE_ASSIGNMENT_20261112.md',
        note='Eightspare-provider extensions keep alloriginalvisits/maps,spend onlyunusedpatrolslice;no newdata,globaloptimum,observed demand,territory ordefault.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]; write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__)), figure_sha256=sha(figure),
        unchanged_map_files=len(result['unchanged_map_sha256']), original_point_maps_unchanged=True))
    print(figure); print('Published eight feasible spare-provider diagnostics;original point maps unchanged.')


if __name__ == '__main__': main()
