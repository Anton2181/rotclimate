"""Publish both frozen job orders and necessary delivery gates without adoption."""
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from plot_joint_visit_order import plot

OUT = ROOT / 'output/network_visit_joint_order_20261112'
PLAN = ROOT / 'calibration/network_visit_joint_order_20261112/plan.json'


def main():
    r = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text()); replay = json.loads((OUT / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_joint_visit_order.py')
    assert len(r['rows']) == len(review['cases']) == 16 and len(replay['byte_exact_files']) == 98
    for path, digest in {**r['sources'], **r['producers'], **r['unchanged_map_sha256'], **r['unchanged_baseline_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for name, digest in replay['byte_exact_files'].items(): assert sha(OUT / name) == digest, name
    gates = dict(np.load(OUT / 'qualification_fields.npz')); figures, example = plot(r, gates)
    keys = list(dict.fromkeys(v['key'] for v in r['rows'])); deltas = []
    for key in keys:
        old = next(v for v in r['rows'] if v['key'] == key and v['policy'] == 'collection_first')
        joint = next(v for v in r['rows'] if v['key'] == key and v['policy'] == 'joint_duration_first')
        deltas.append(dict(key=key, climate=old['climate'], hours_worker_year=old['hours_worker_year'], crew=old['crew'],
            bin_qualified_gain=joint['bin_qualified_visits'] - old['bin_qualified_visits'], twelve_bin_gated_gain=joint['twelve_bin_gated_visits'] - old['twelve_bin_gated_visits'],
            additional_unpacked_collector_trips=joint['unpacked_collector_trips'] - old['unpacked_collector_trips']))
    write(OUT / 'summary.json', dict(status='all_sixteen_fixed_policy_rows_reported', paired_deltas=deltas, adopt=False,
        twelve_bin_gate_is_necessary_only=True, original_schedules_and_maps_unchanged=True))
    table = '|Climate|Farm h|Crew|Order|Physical visits|Bin-qualified|Twelve-bin-gated|Collector trips unpacked|Providers passing twelve bins|\n|---|---:|---:|---|---:|---:|---:|---:|---:|\n'
    for v in r['rows']:
        label = 'Collection first' if v['policy'] == 'collection_first' else 'Joint duration first'
        table += f'|{v["climate"]}|{v["hours_worker_year"]}|{v["crew"]}|{label}|{v["physically_scheduled_visits"]:,}|{v["bin_qualified_visits"]:,}|{v["twelve_bin_gated_visits"]:,}|{v["unpacked_collector_trips"]:,}|{v["twelve_bin_mandatory_providers"]} / {v["active_providers"]}|\n'
    report = '''# Fixed job-order comparison and necessary delivery gates

Declaration `e4d274da` preceded outputs. Eight original scenarios are compared
under two fixed policies,all sixteen rows retained. Original targets,visits,
providers,collector trips,food plans,staff,worker caps and maps are unchanged.
This is a constructive scheduling experiment with no winning-policy adoption.

## Frozen alternative and distinct gates

Home services remain divisible and equally shared first. The alternative
merges collection and visit jobs by decreasing per-worker duration;collection
wins equal-duration ties,then origin/trip serial or actor/target resolves ties.
Workers have the original fifty duty hours per bin and212.92 working-hour
calendar horizon. Collector jobs use the earliest available eligible worker;
visits synchronize the earliest eligible supported crew. All jobs are whole.
Grouping identical-origin jobs preserves exact serial order and only saves
memory/runtime. Calendar idle is not additional duty time.

A visit can be physically scheduled before collection later fails. Its actual
worker intervals and hours remain charged. Bin qualification requires ALL
mandatory collection/home work at that provider in the bin. The twelve-bin gate
additionally requires an originally active provider to complete every mandatory
bin. It is a necessary delivery-scheduling test,not daily provisioning,within-bin
grain timing,complete annual food validation or evidence of observed staffing.
Inactive/missing-inventory,unaffiliated and mobile contexts remain unscored.

## All outcomes

''' + table + '''
The mixed order raises bin-qualified visits in all eight scenarios,but leaves
more required collector trips unpacked. For raw600h/four-person crews,the
bin-qualified count rises137,796→141,624 while the twelve-bin-gated count falls
129,049→118,884. Corrected600h/four-person counts similarly rise145,972→150,104
within bins but fall137,822→126,369 through the twelve-bin gate. With one-person
crews,the gated visit count increases even though fewer providers complete all
twelve mandatory bins. These are different quantities;none can substitute for
the other. Every gain and loss is preserved rather than selecting a policy.

''' + '\n'.join(f'![Fixed job-order comparison](figures/{p.name})' for p in figures) + '''

## Review,publication and remaining work

Nine manufactured controls cover collection-first fragmentation recovery,
scheduled visits with later collection failure,equal-duration priority,
synchronized crews,idle/duty separation,post-idle collector eligibility,
empty/zero-resource cases,deterministic ties,nonmutation and invalid inputs.
The earlier seven worker-calendar controls also pass.

The independent reviewer imports no new allocator. It reproduces the mixed
order using scalar sorted worker lists and checks every collector job identity,
worker interval,crew,provider,task duration,calendar/duty cap and monthly channel
ledger. Physically scheduled work remains charged when mandatory collection
fails. Both policies' twelve-bin flags and all actor/bin summaries are derived
again from individual bins. Original baseline schedules remain byte exact;
all96mixed monthly packets plus results and qualification fields replay freshly
byte for byte. Failure under either greedy rule is not proof of impossibility.

The normal evidence atlas includes all sixteen rows,three figures and the
result/review/replay/prior-declaration and matched-worker CSV downloads. The
illustration selects the first eligible four-person case/bin and lowest
provider with both policies scheduling visits and collection,workers0–11.
The CSV preserves bin and twelve-bin flags alongside each worker interval.
This illustrative subset is not a selected evaluation cohort.

Next predeclare any provider-wise combination or other construction before its
outputs. A complete year must use a coherent schedule at each provider;mixing
individual job successes from different calendars can double-use workers. Keep
annual mandatory-delivery gates explicit and retain original results. No
combined-policy map or default is part of this experiment.

The entire release1–4/S1–S5 programme remains active. Dated provider functions,
occupation/resident sizes,prospective transfer,complete diets/household/draft
work,daily provisioning and mobile/nonstate/unaffiliated resources remain open.
No new Earth observations or empirical authority qualification are introduced.
The historical full evidence rebuild still needs an omitted private Vidarbha
cache;this reviewed direct publisher preserves all earlier panels.
'''
    (ROOT / 'reports/NETWORK_VISIT_JOINT_ORDER_20261112.md').write_text(report)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    downloads = [(OUT / 'results.json', 'joint_order_results.json'), (OUT / 'review.json', 'joint_order_review.json'),
        (OUT / 'replay.json', 'joint_order_replay.json'), (PLAN, 'joint_order_plan.json'), (OUT / 'example_policy_calendars.csv', 'joint_order_example.csv')]
    for source, name in downloads: shutil.copyfile(source, data / name)
    html_rows = ''.join(f'<tr><td>{v["climate"].title()}</td><td>{v["hours_worker_year"]}</td><td>{v["crew"]}</td><td>{"Collection first" if v["policy"] == "collection_first" else "Joint duration first"}</td><td>{v["physically_scheduled_visits"]:,}</td><td>{v["bin_qualified_visits"]:,}</td><td>{v["twelve_bin_gated_visits"]:,}</td><td>{v["unpacked_collector_trips"]:,}</td></tr>' for v in r['rows'])
    section = '''<!--joint-order-start--><section><h2>Job order and necessary twelve-bin delivery gates</h2><details id="joint-order" class="panel"><summary>16 fixed-policy outcomes · monthly visit gains and delivery losses both retained</summary>
<p><strong>A better monthly visit count can accompany worse collection scheduling.</strong> The alternative mixes the SAME collector and visit jobs by decreasing per-worker duration,with collection winning equal-duration ties. It keeps the original workers,providers,crews,home services,food plans and duty/calendar caps. All eight scenarios and both policies are reported;no winning policy or map default is adopted.</p>
<p>Physically scheduled visits retain their actual intervals and work even if collection later fails. Bin qualification requires all mandatory work in that provider/bin. The twelve-bin gate also requires the originally active provider to finish ALL twelve mandatory collection/service bins. This is a necessary delivery-scheduling test,not complete annual food validation,daily provisioning,within-bin grain timing or observed staffing.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Farm hours</th><th>Crew</th><th>Fixed order</th><th>Physical visits</th><th>Bin-qualified</th><th>Twelve-bin-gated</th><th>Collector trips unpacked</th></tr></thead><tbody>''' + html_rows + '</tbody></table></div>\n' + '\n'.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p, alt in zip(figures, [
        'All eight paired job-order changes:monthly visits,twelve-bin-gated visits and collection omissions',
        'Both fixed policies under separate monthly and twelve-bin mandatory-delivery gates',
        'The same twelve model workers under collection-first and mixed-duration schedules'])) + '''
<p>All eight mixed-order cases raise bin-qualified visits,but more collector trips are left unpacked. With four-person crews,the twelve-bin-gated visit count falls in all four cases. With one-person crews,it rises while the number of twelve-bin-complete providers falls. The matched worker illustration uses the first eligible four-person case/bin/provider and workers0–11;its CSV retains all shown intervals and both gate flags.</p>
<p>Nine new controls and seven earlier calendar controls pass. Independent scalar mixed-order replay verifies collector identities,worker intervals,distinct synchronized crews,no overlap,duty/calendar limits and the original monthly channel budgets. Both annual flags are recomputed from bins. All98fresh output files are byte exact;earlier schedules/maps are preserved. Neither greedy rule proves optimality or physical impossibility. Unaffiliated,mobile and missing-inventory contexts remain unscored;no political authority or calibrated default is inferred.</p>
<p><a href="../../reports/NETWORK_VISIT_JOINT_ORDER_20261112.md">Methods,all outcomes and remaining dependencies</a> · <a href="data/joint_order_results.json" download>All16 outcomes</a> · <a href="data/joint_order_review.json" download>Independent review</a> · <a href="data/joint_order_replay.json" download>Fresh byte replay</a> · <a href="data/joint_order_plan.json" download>Prior declaration</a> · <a href="data/joint_order_example.csv" download>Matched worker calendars</a></p></details></section><!--joint-order-end-->'''
    html = page.read_text(); old = re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->', html)
    pattern = r'<!--joint-order-start-->[\s\S]*?<!--joint-order-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--visit-calendar-start-->' in html; html = html.replace('<!--visit-calendar-start-->', section + '\n<!--visit-calendar-start-->', 1)
    for name, body in old:
        if name != 'joint-order': assert f'<!--{name}-start-->{body}<!--{name}-end-->' in html, name
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='network_visit_joint_order_20261112', status='model_only_fixed_order_and_necessary_delivery_gate_comparison', evidence='reports/NETWORK_VISIT_JOINT_ORDER_20261112.md',
        note='Both fixed policies/all16outcomes retained;physical work,bin completion and necessary12bin gate distinct. No new Earth data,annualfood validation,observed staffing ordefault adoption.')
    usage['datasets'] = [v for v in usage['datasets'] if v['id'] != entry['id']] + [entry]; write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(OUT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page),
        producers={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'scripts/plot_joint_visit_order.py')},
        figures_sha256={str(p.relative_to(ROOT)): sha(p) for p in figures}, downloads_sha256={name: sha(data / name) for _, name in downloads}, example=example,
        unchanged_original_maps=len(r['unchanged_map_sha256']), unchanged_original_calendar_files=len(r['unchanged_baseline_sha256']), earlier_panels_unchanged=True,
        adopt=False, complete_annual_food_validation=False))
    for p in figures: print(p)
    print('Published both fixed policies and all16 outcomes;no schedule or map replacement.')


if __name__ == '__main__': main()
