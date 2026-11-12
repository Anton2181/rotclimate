"""Publish the checked worker-calendar experiment in the existing evidence atlas."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from plot_visit_calendars import plot

OUT = ROOT / 'output/network_visit_calendar_20261112'
PLAN = ROOT / 'calibration/network_visit_calendar_20261112/plan.json'


def main():
    result = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text()); replay = json.loads((OUT / 'replay.json').read_text())
    if review['status'] != 'passed' or replay['status'] != 'passed' or review['results_sha256'] != sha(OUT / 'results.json'):
        raise ValueError('Current independent calendar review and fresh replay required')
    if review['reviewer_sha256'] != sha(ROOT / 'scripts/review_visit_calendars.py'): raise ValueError('Calendar reviewer changed')
    if len(result['collection_rows']) != 4 or len(result['visit_rows']) != 8 or len(review['cases']) != 8 or len(replay['byte_exact_files']) != 145:
        raise ValueError('All declared calendar cases and schedule replays required')
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items():
        if sha(ROOT / path) != digest: raise ValueError('Changed calendar input or earlier map: ' + path)
    for path, digest in {**result['files_sha256'], **replay['byte_exact_files']}.items():
        if sha(OUT / path) != digest: raise ValueError('Changed calendar schedule or replay: ' + path)
    figures, example = plot(result)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    downloads = [(OUT / 'results.json', 'visit_calendar_results.json'), (OUT / 'review.json', 'visit_calendar_review.json'),
        (OUT / 'replay.json', 'visit_calendar_replay.json'), (PLAN, 'visit_calendar_plan.json'),
        (OUT / 'example_worker_calendar.csv', 'visit_calendar_example.csv')]
    for source, name in downloads: shutil.copyfile(source, data / name)
    collections = ''.join(f'<tr><td>{r["climate"].title()}</td><td>{r["hours_worker_year"]}</td><td>{r["required_trips"]:,}</td>'
        f'<td>{r["unpacked_trips"]:,}</td><td>{r["mandatory_failed_provider_bins"]:,} / {r["relevant_provider_bins"]:,}</td></tr>' for r in result['collection_rows'])
    visits = ''.join(f'<tr><td>{r["climate"].title()}</td><td>{r["hours_worker_year"]}</td><td>{r["crew"]}</td><td>{r["original_planned_visits"]:,}</td>'
        f'<td>{r["packed_visits"]:,}</td><td>{r["blocked_by_mandatory_collection"]:,}</td><td>{r["greedy_crew_unpacked_visits"]:,}</td></tr>' for r in result['visit_rows'])
    section = '''<!--visit-calendar-start--><section><h2>Individual worker calendars for collector trips and visits</h2><details id="visit-calendar" class="panel"><summary>4 collection plans and 8 visit scenarios · whole jobs and synchronized crews</summary>
<p><strong>Passing a shared hour budget does not guarantee a schedule of whole trips.</strong> These are the original food/collection plans and point visits. Each integer supported worker has 50 duty hours per bin and a shared month calendar of 212.92 working-hour coordinates,at seven hours per day. Divisible home services are shared equally first;whole collector trips are assigned longest-first to the earliest available worker. Visits retain their original providers and require simultaneous supported crews. Synchronization gaps consume calendar time,not additional duty hours.</p>
<h3>Mandatory collection</h3><div class="table"><table data-calendar-collection><thead><tr><th>Climate</th><th>Farm hours</th><th>Required trips</th><th>Greedy trips unpacked</th><th>Mandatory-failed / relevant provider-bins</th></tr></thead><tbody>''' + collections + '''</tbody></table></div>
<h3>Original planned visits</h3><div class="table"><table data-calendar-visits><thead><tr><th>Climate</th><th>Farm hours</th><th>Crew</th><th>Planned</th><th>Packed within bin</th><th>Blocked by mandatory collection</th><th>Greedy crew shortfall</th></tr></thead><tbody>''' + visits + '''</tbody></table></div>
<p><strong>These are per-bin packing results,not annual food-supported visit counts.</strong> Any missing mandatory collector trip leaves the unchanged annual delivery plan uncertified. A failed collection bin blocks its provider's visits in that bin. Greedy failure does not prove that no schedule exists:collection-first assignment can fragment workers' remaining hours. Alternative ordering requires a separate prior declaration. These gaps do not establish abandonment,political collapse or lost authority.</p>
''' + '\n'.join(f'<img src="../../reports/figures/{p.name}" alt="{alt}">' for p, alt in zip(figures, [
        'Four collection plans:unpacked trip fractions and provider-bin mandatory-work gaps',
        'Eight original visit plans partitioned into per-bin packed tasks,mandatory collection blocks and greedy crew shortfalls',
        'Recorded worker intervals showing home services,collector trips,synchronized four-person visits and calendar gaps'])) + '''
<p>The calendar illustration uses the first eligible four-person case/bin and lowest provider with both job types. It shows the first twelve visit participants,filled with the lowest remaining worker IDs. The CSV records every shown worker/task interval;one visit appears once per crew member to account for each worker's hours. This illustration is not a selected evaluation cohort.</p>
<p>Seven manufactured controls pass. Independent sorted-list replay checks 10,812,121 collector trips,1,259,374 original planned visits and 7,752,000 worker-bins,including task identities,distinct crews,nonoverlapping intervals,calendar bounds and duty caps. All 145 fresh schedule/result files are byte exact. Availability and divisible services remain supplied assumptions. Actual provider roles,complete service-job rosters,daily provisioning,observed patrols and annual delivery qualification remain open. Unaffiliated,mobile and missing-inventory contexts remain unscored. Earlier point maps and defaults retain their previous scope.</p>
<p><a href="../../reports/NETWORK_VISIT_CALENDAR_20261112.md">Methods,scope and remaining dependencies</a> · <a href="data/visit_calendar_results.json" download>All collection and visit results</a> · <a href="data/visit_calendar_review.json" download>Independent review</a> · <a href="data/visit_calendar_replay.json" download>Fresh byte replay</a> · <a href="data/visit_calendar_plan.json" download>Prior declaration</a> · <a href="data/visit_calendar_example.csv" download>Shown worker/task intervals</a></p></details></section><!--visit-calendar-end-->'''
    html = page.read_text()
    old_panels = re.findall(r'<!--([\w-]+)-start-->([\s\S]*?)<!--\1-end-->', html)
    pattern = r'<!--visit-calendar-start-->[\s\S]*?<!--visit-calendar-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        if '<!--visit-grid-start-->' not in html: raise ValueError('Existing target-grid research panel required')
        html = html.replace('<!--visit-grid-start-->', section + '\n<!--visit-grid-start-->', 1)
    for name, body in old_panels:
        if name != 'visit-calendar' and f'<!--{name}-start-->{body}<!--{name}-end-->' not in html:
            raise ValueError('Earlier evidence panel changed: ' + name)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='network_visit_calendar_20261112', status='model_only_constructive_worker_calendar_diagnostic', evidence='reports/NETWORK_VISIT_CALENDAR_20261112.md',
        note='Original four collection/eight visit plans;whole trips and synchronized worker intervals independently reviewed. Per-bin packing does not certify annual deliveries;no new Earth data,observed staffing,authority or default adoption.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    for path, digest in result['unchanged_map_sha256'].items():
        if sha(ROOT / path) != digest: raise ValueError('Earlier map changed during publication: ' + path)
    write(OUT / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page),
        producer_sha256={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'scripts/plot_visit_calendars.py')},
        figures_sha256={str(p.relative_to(ROOT)): sha(p) for p in figures}, downloads_sha256={name: sha(data / name) for _, name in downloads},
        example=example, original_map_files_unchanged=len(result['unchanged_map_sha256']), original_evidence_panels_unchanged=True,
        default_adoption=False, annual_food_delivery_qualification=False))
    for p in figures: print(p)
    print('Published four collection/eight visit calendar results with three figures and five downloads.')


if __name__ == '__main__': main()
