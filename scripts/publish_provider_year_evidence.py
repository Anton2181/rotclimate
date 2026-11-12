"""Publish coherent provider-year point maps with preserved task and gate evidence."""
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from plot_provider_year_visits import plot

OUT = ROOT / 'output/network_visit_year_complete_20261112'
PLAN = ROOT / 'calibration/network_visit_year_complete_20261112/plan.json'
DATA = ROOT / 'atlases/earth_fit/data'


def main():
    r = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    exported = json.loads((OUT / 'export_review.json').read_text()); publication = json.loads((OUT / 'atlas_publication.json').read_text())
    replay = json.loads((OUT / 'replay.json').read_text()); export_replay = json.loads((OUT / 'export_replay.json').read_text())
    assert review['status'] == exported['status'] == replay['status'] == export_replay['status'] == 'passed'
    assert review['results_sha256'] == exported['results_sha256'] == sha(OUT / 'results.json')
    assert exported['manifest_sha256'] == publication['manifest_sha256'] == sha(DATA / 'network_visit_year_complete.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_provider_year_visits.py') and exported['reviewer_sha256'] == sha(ROOT / 'scripts/review_provider_year_exports.py')
    for path, digest in {**r['sources'], **r['producers'], **r['unchanged_map_sha256'], **r['unchanged_schedule_sha256'], **publication['producers'], **publication['exported_files_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for name, digest in replay['byte_exact_files'].items(): assert sha(OUT / name) == digest
    for name, digest in export_replay['byte_exact_files'].items(): assert sha(DATA / name) == digest
    figures = plot(); fields = dict(np.load(OUT / 'fields.npz')); original = dict(np.load(ROOT / 'output/network_visit_joint_order_20261112/qualification_fields.npz'))
    same_providers = all(np.array_equal(fields[row['key'] + '__mandatory_complete'], original['collection_first__' + row['key'] + '__annual']) for row in r['rows'])
    table = '|Climate|Farm h|Crew|Original funded|Baseline twelve-bin|Selected qualified|Added|Qualified providers|Joint-order provider-years|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for row in r['rows']:
        table += f'|{row["climate"]}|{row["hours_worker_year"]}|{row["crew"]}|{row["original_funded_visits"]:,}|{row["baseline_twelve_bin_visits"]:,}|{row["qualified_visits"]:,}|+{row["added_visits"]:,}|{row["qualified_providers"]}|{row["joint_policy_providers"]}|\n'
    report = '''# Point visits from coherent provider-year calendars

Declaration `00d70d62` preceded outputs. This is development on exposed resource
scenarios,not a blind Earth test or a calibrated policy choice. All eight
original b3_p0 scenarios,food plans,people,staff,roads,requests and jobs remain
fixed. A provider uses ONE checked calendar across ALL twelve bins;individual
job successes from conflicting calendars are never combined.

## Frozen selection and necessary gate

Keep a baseline provider-year that completes all mandatory work unless the
joint-duration year also completes it,contains EVERY baseline packed
actor/target/bin identity,and adds at least one task. Equal sets or any lost
baseline identity retain the baseline. If only the joint year completes all
mandatory work,choose it. If neither passes,retain the baseline as an unqualified
physical trace and map no qualified visits from that provider. Inactive sources
cannot pass through empty obligations.

Qualified visits must be physically scheduled by the chosen provider-year and
belong to the original funded point plan. Every mandatory collector trip and
home-service bin must be packed for that source across all twelve bins.
Selected physical work remains charged even at unqualified providers. Worker
caps,patrol reservations,collection/service commitments and original source-food
gates remain intact. The year flag is a NECESSARY delivery-scheduling gate under
the unchanged monthly food model,not daily provisioning,within-bin grain timing,
complete annual food validation,observed provider roles or political authority.

## All eight cases

''' + table + '\n' + ('The qualified-provider flags happen to equal the baseline flags in all eight\ncases. Gains are additional tasks within the same qualified cohorts;this is\nnot a general invariance theorem or evidence of additional institutions.\n\n' if same_providers else '') + '''
Gains range from2,810 to9,846 point visits. Every baseline twelve-bin-gated task
is retained elementwise,and every final task is already in the original funded
plan. The selected counts remain below that pooled-hour plan:whole worker jobs
and mandatory collection still constrain the result. Candidate residents and
their parent food ledgers are not reallocated when calendar qualification fails.

''' + '\n'.join(f'![Coherent provider-year point tasks](figures/{p.name})' for p in figures) + '''

## Review and exports

Nine new controls check strict-superset choice,rejection of higher counts that
lose a baseline identity,ties,baseline failure/joint recovery,neither year
complete,inactive providers,original funded-task bounds,twelve-bin coherence
and input preservation. Independent review imports no selector. It reconstructs
policy choices from task identities and individual completion bins,checks both
source physical certificates and selected worker-ledger blocks,and verifies all
actor/bin request partitions. Original calendar files and maps remain unchanged.
Fresh result/field files and22point-map/model/CSV/field exports are byte exact.

The independent export review checks all actor/target masks,visited-point pixel
colors,provider policies,worker hours,unchanged conditional resident/food ledgers
and every point CSV record. Requests partition into qualified visits,calendar
unqualified originally funded jobs,and the unchanged route/initial-crew/capacity
deficits. Baseline masks are subsets of final masks;final masks are subsets of
the original funded plan. Each point CSV preserves original funded providers
by bin,their single year policy and mandatory-year flag. Providers may differ
between a point's bins under the original assignment rule;none are reassigned.

## Atlas and remaining programme

Under Experimental & diagnostics → Supply-supported reach,choose “Complete-year
collection schedule”. Eight distinct optional maps show qualified POINTS,not
blocks or intervening territory. Fourteen provider readouts include selected
year policy and the twelve-bin flag. Provider CSVs retain monthly physical work
even when unqualified;point CSVs retain all requests and five deficit masks.
Full choices/point fields are downloadable. All earlier map families and defaults
remain available. Unaffiliated,mobile and missing-inventory contexts stay
unscored;unrostered providers do not establish absent communities.

The normal research atlas publishes all eight rows,three figures and the
result/selection-review/export-review/fresh-replay/prior-declaration downloads.
Further scheduling diagnostics do not replace dated size/occupation/provider
evidence,prospective transfer,complete diets/household/draft work,daily food or
mobile/nonstate/unaffiliated resource integration. The whole release1–4/S1–S5
programme remains open and no calibrated default is adopted.

The historical full evidence publisher still needs an omitted private Vidarbha
Earth cache. This reviewed direct publisher preserves every earlier panel and
does not claim a full historical rebuild.
'''
    (ROOT / 'reports/NETWORK_VISIT_YEAR_COMPLETE_20261112.md').write_text(report)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    downloads = [(OUT / 'results.json', 'year_visits_results.json'), (OUT / 'review.json', 'year_visits_review.json'),
        (OUT / 'export_review.json', 'year_visits_export_review.json'), (OUT / 'replay.json', 'year_visits_replay.json'),
        (OUT / 'export_replay.json', 'year_visits_export_replay.json'), (PLAN, 'year_visits_plan.json')]
    for source, name in downloads: shutil.copyfile(source, data / name)
    rows = ''.join(f'<tr><td>{v["climate"].title()}</td><td>{v["hours_worker_year"]}</td><td>{v["crew"]}</td><td>{v["original_funded_visits"]:,}</td><td>{v["baseline_twelve_bin_visits"]:,}</td><td>{v["qualified_visits"]:,}</td><td>+{v["added_visits"]:,}</td><td>{v["qualified_providers"]}</td></tr>' for v in r['rows'])
    section = '''<!--provider-year-start--><section><h2>Point visits from coherent provider-year calendars</h2><details id="provider-year" class="panel"><summary>8 optional point maps · every baseline twelve-bin-gated task retained</summary>
<p><strong>Choose one checked calendar per provider for all twelve bins.</strong> A complete baseline year stays unless a complete alternate year contains EVERY baseline task identity and adds at least one. If only the alternate completes mandatory work,choose it. If neither passes,no qualified points are mapped from that provider. Individual job successes are never merged across calendars. Every mapped task already belongs to the original funded plan.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Farm hours</th><th>Crew</th><th>Original funded</th><th>Baseline twelve-bin</th><th>Selected qualified</th><th>Added</th><th>Qualified providers</th></tr></thead><tbody>''' + rows + '</tbody></table></div>\n' + '\n'.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p, alt in zip(figures, [
        'Raw-climate original pooled-hour points,baseline twelve-bin points and coherent provider-year qualified points',
        'Corrected-climate point tasks with every baseline gated task retained',
        'All eight provider-year scenarios and additional visits without baseline task loss'])) + '''
<p>Gains are2,810–9,846 visits,with zero baseline task identities lost and no new people,food,staff,jobs or reassigned providers. Mandatory collection/home work must complete in ALL twelve bins;selected physical work remains charged even at unqualified sources. This is a necessary delivery-scheduling gate,not daily provisioning,within-bin grain timing,complete annual food validation,observed staffing or authority. Conditional parent residents remain unchanged. Dots are point tasks,not held blocks or intervening territory;unaffiliated/mobile/missing-inventory contexts remain unscored.</p>
<p>Nine new controls pass. Independent whole-year policy/task/worker-ledger review and independent map/mask/pixel/point-CSV checks pass for all eight cases. Fresh result/fields and22export files are byte exact. The old route/initial-crew/capacity deficits remain;calendar-unqualified funded tasks form a separate partition. Earlier schedules,maps and normal defaults are preserved.</p>
<p><a href="../earth_fit/#layer=reach_defacto&amp;variant=yearvisits600_crew1&amp;climate=corrected&amp;all=1">Open coherent provider-year points</a> · <a href="../earth_fit/#layer=reach_defacto&amp;variant=yearvisits300_crew4&amp;climate=raw&amp;all=1">Open lower-field-work/four-person points</a> · <a href="../../reports/NETWORK_VISIT_YEAR_COMPLETE_20261112.md">Methods and remaining programme</a> · <a href="data/year_visits_results.json" download>All8results</a> · <a href="data/year_visits_review.json" download>Independent selection review</a> · <a href="data/year_visits_export_review.json" download>Independent map/CSV review</a> · <a href="data/year_visits_replay.json" download>Fresh model replay</a> · <a href="data/year_visits_export_replay.json" download>Fresh export replay</a> · <a href="data/year_visits_plan.json" download>Prior declaration</a></p>
<p>Experimental &amp; diagnostics → Supply-supported reach → “Complete-year collection schedule”. Provider readouts and CSVs expose the one year policy,mandatory-year flag and actual physical monthly work. Point CSVs identify each original provider by bin,all request partitions and retained baseline masks. Full choices/point fields are downloadable.</p></details></section><!--provider-year-end-->'''
    html = page.read_text(); old = re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->', html); pattern = r'<!--provider-year-start-->[\s\S]*?<!--provider-year-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--joint-order-start-->' in html; html = html.replace('<!--joint-order-start-->', section + '\n<!--joint-order-start-->', 1)
    for name, body in old:
        if name != 'provider-year': assert f'<!--{name}-start-->{body}<!--{name}-end-->' in html, name
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='network_visit_year_complete_20261112', status='model_only_coherent_provider_year_point_schedule', evidence='reports/NETWORK_VISIT_YEAR_COMPLETE_20261112.md',
        note='One checked calendar per provider/year preserves every baseline gated task;all8point maps retain original jobs/people/food. Necessary delivery gate only,no new Earth observations,annual food validation,roles ordefault adoption.')
    usage['datasets'] = [v for v in usage['datasets'] if v['id'] != entry['id']] + [entry]; write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page),
        producers={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'scripts/plot_provider_year_visits.py', ROOT / 'scripts/publish_network_duty_visits.py')},
        figures_sha256={str(p.relative_to(ROOT)): sha(p) for p in figures}, downloads_sha256={name: sha(data / name) for _, name in downloads},
        qualified_provider_flags_equal_baseline_in_all_eight_cases=same_providers, baseline_tasks_lost=0, original_maps_unchanged=True, default_adoption=False))
    for p in figures: print(p)
    print('Published coherent provider-year research results and optional point maps.')


if __name__ == '__main__': main()
