"""Publish the reviewed conditional point-task maps in the normal evidence atlas."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write


def main():
    out = ROOT / 'output/network_duty_visits_20261112'; page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    result = json.loads((out / 'results.json').read_text()); review = json.loads((out / 'review.json').read_text())
    replay = json.loads((out / 'replay.json').read_text()); publication = json.loads((out / 'atlas_publication.json').read_text())
    assert review['status'] == replay['status'] == 'passed' and review['results_sha256'] == sha(out / 'results.json')
    assert publication['manifest_sha256'] == sha(ROOT / 'atlases/earth_fit/data/network_duty_visits.json')
    for src, name in [(out / 'results.json', 'network_visits_results.json'), (out / 'review.json', 'network_visits_review.json'),
        (out / 'replay.json', 'network_visits_replay.json'), (out / 'atlas_publication.json', 'network_visits_publication.json'),
        (ROOT / 'calibration/network_duty_visits_20261112/plan.json', 'network_visits_plan.json')]: shutil.copyfile(src, data / name)
    table = ''.join(f'<tr><td>{r["climate"].title()}</td><td>{r["hours_worker_year"]}</td><td>{r["crew"]}</td>'
        f'<td>{r["completed_visits"]:,} / {r["requested_visits"]:,}</td><td>{100*r["completed_fraction"]:.1f}%</td>'
        f'<td>{r["route_unreachable"]:,}</td><td>{r["provider_work_unavailable"]:,}</td><td>{r["capacity_unmet"]:,}</td></tr>' for r in result['rows'])
    section = '''<!--network-visits-start--><section><h2>Walking visits funded from the existing patrol-hour slice</h2><details id="network-visits" class="panel"><summary>8 conditional point-task maps · no whole-block territorial claim</summary>
<p><strong>Visits now have specific destinations and directed walking round trips.</strong> A fixed grid places 27,843 land target points about 11.04 km apart. For each actor, points within its original all-source access in at least one bin receive one supplied request in every bin. This is a conditional task landscape, not evidence of actual demand or occupation. Crew scenarios use one or four supported institutional residents.</p>
<p>Only the SAME already-reserved patrol hours are spent. Collection and other services retain their commitments;unused hours elsewhere are not borrowed. Each accepted whole visit costs crew × [7 × (outward + inward graph days) + 1 on-site hour]. Both directed legs must be at most two days, with round trip plus on-site work at most four days. Routes walk the original roads/tracks and seasonal terrain;ferries,sea and river transport are excluded. Conditions are frozen within each bin.</p>
<div class="table"><table><thead><tr><th>Climate</th><th>Farm hours</th><th>Crew</th><th>Completed / requested</th><th>Completed</th><th>No walking route</th><th>No initially affordable crew</th><th>Assigned capacity unmet</th></tr></thead><tbody>''' + table + '''</tbody></table></div>
<p>Per actor/target/bin,choose the cheapest initially affordable provider once;each provider completes assigned tasks in cost order until its patrol slice is exhausted. No task is counted twice. Spare hours can coexist with unmet tasks;this greedy allocation does not prove global coverage optimality. Unrequested points,missing inventories,and unaffiliated/mobile communities remain unscored.</p>
<img src="../../reports/figures/network_duty_visits_corrected_20261112.png" alt="Four corrected-climate scenarios showing visited target points,not filled territorial blocks">
<img src="../../reports/figures/network_duty_visits_raw_20261112.png" alt="Four raw-climate conditional walking point-visit maps">
<img src="../../reports/figures/network_duty_visits_scenarios_20261112.png" alt="Eight request partitions and used versus unspent patrol-hour reservations">
<p>Independent target geometry,directed route edges,scalar assignment,integer completion,all-actor request partitions and whole-provider ledgers pass. All zero-patrol-budget controls complete zero visits. Fresh path/result/field files are byte exact. This checks monthly staff hours,not complete individual rosters,daily provisioning,observed patrols,political authority or empirically qualified resident sizes and roles.</p>
<p><a href="../earth_fit/#layer=reach_defacto&amp;variant=visits600_crew1&amp;climate=corrected&amp;all=1">Open funded walking point visits</a> · <a href="../earth_fit/#layer=reach_defacto&amp;variant=visits300_crew4&amp;climate=raw&amp;all=1">Open lower-field-work/four-person scenario</a> · <a href="../../reports/NETWORK_DUTY_VISITS_20261112.md">Methods,scope and next dependencies</a> · <a href="data/network_visits_results.json" download>All task/hour results</a> · <a href="data/network_visits_review.json" download>Independent review</a> · <a href="data/network_visits_replay.json" download>Fresh byte replay</a> · <a href="data/network_visits_publication.json" download>Earlier-map preservation</a> · <a href="data/network_visits_plan.json" download>Prior declaration</a></p>
<p>Experimental &amp; diagnostics → Supply-supported reach → “Funded walking point visits”. Selected-provider CSVs show monthly completed tasks and reserved/used/unused patrol hours. Point downloads preserve every requested actor/target and all four bin masks;full work arrays remain downloadable. Earlier maps and normal defaults are preserved.</p></details></section><!--network-visits-end-->'''
    html = page.read_text(); pattern = r'<!--network-visits-start-->[\s\S]*?<!--network-visits-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        assert '<!--dispatch-seeded-start-->' in html
        html = html.replace('<!--dispatch-seeded-start-->', section + '\n<!--dispatch-seeded-start-->', 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='network_duty_visits_20261112', status='model_only_conditional_walking_point_tasks', evidence='reports/NETWORK_DUTY_VISITS_20261112.md',
        note='Eightreservedpatrol-slice point-visit scenarios;originalfood/workprovidersandtransportinputs,no newEarthdata,observed demand,territory,rosters ordefaultadoption.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(out / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__))))
    print('Published eight conditional walking point-task results and maps in the normal research atlas.')


if __name__ == '__main__': main()
