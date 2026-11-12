"""Expose numerical source misses without relabelling original maps as final."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write


def main():
    out = ROOT / 'output/settlement_dispatch_search_20261112'; page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    result = json.loads((out / 'results.json').read_text()); review = json.loads((out / 'review.json').read_text())
    replay = json.loads((out / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed'
    assert review['results_sha256'] == replay['results_sha256'] == sha(out / 'results.json')
    for p, digest in {**result['sources'], **result['unchanged_maps_sha256']}.items(): assert sha(ROOT / p) == digest, p
    for name in ('results', 'review', 'replay'):
        shutil.copyfile(out / (name + '.json'), data / ('dispatch_search_' + name + '.json'))
    shutil.copyfile(ROOT / 'calibration/settlement_dispatch_search_20261112/plan.json', data / 'dispatch_search_plan.json')
    table = ''.join(f'<tr><td>{r["climate"].title()} / {r["hours_worker_year"]}h</td><td>{r["old_sources"]}</td><td>{r["fine_sources"]}</td><td>{r["probes"][1]["fine_zero_but_probe_feasible"]}</td></tr>' for r in result['rows'])
    section = '''<!--dispatch-search-start--><section><h2>Search check: narrow staffed ranges were missed</h2><details id="dispatch-search" class="panel"><summary>64-interval and explicit staff-threshold check · source losses need correction</summary>
<p><strong>The earlier 32-interval joint maps missed feasible staffed cases.</strong> In the 300-hour cases, the finer grid recovers ten sources in each climate. Probing the existing 150-person staff activation finds five more raw-climate and two more corrected-climate positives. These are numerical search misses, not established physical losses or a new Earth-skill gain.</p>
<div class="table"><table><thead><tr><th>Case</th><th>32-interval sources</th><th>64-interval sources</th><th>Additional at 150</th></tr></thead><tbody>''' + table + '''</tbody></table></div>
<p>All 396 overlap arrays are bit exact. All finer final allocations and threshold probes pass independent people/work/monthly-food/trip/hour checks; fresh output bytes match. The original sixteen maps remain historical examined candidates. A separately declared threshold-seeded solver will publish corrected optional versions. Neither finite search establishes a global optimum or funded geographic patrol coverage.</p>
<p><a href="../../reports/SETTLEMENT_DISPATCH_SEARCH_20261112.md">Finding and next implementation</a> · <a href="data/dispatch_search_results.json" download>Every case and missed-site index</a> · <a href="data/dispatch_search_review.json" download>Independent review</a> · <a href="data/dispatch_search_replay.json" download>Fresh replay</a> · <a href="data/dispatch_search_plan.json" download>Prior declaration</a></p></details></section><!--dispatch-search-end-->'''
    html = page.read_text(); pattern = r'<!--dispatch-search-start-->[\s\S]*?<!--dispatch-search-end-->'
    if re.search(pattern, html): html = re.sub(pattern, lambda match: section, html)
    else:
        marker = '<!--settlement-dispatch-start-->'
        if marker not in html: raise ValueError('Publish original joint maps first')
        html = html.replace(marker, section + '\n' + marker, 1)
    warning = '<p data-dispatch-search-correction><strong>Search correction:</strong> the 300-hour source losses in these original 32-interval maps include missed feasible ranges. See the search check immediately above; corrected solver versions are developed separately.</p>'
    if 'data-dispatch-search-correction' not in html:
        html = html.replace('<summary>16 checked scenarios · new settlement and potential-access maps</summary>',
            '<summary>16 checked scenarios · new settlement and potential-access maps</summary>' + warning, 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'; usage = json.loads(registry.read_text())
    entry = dict(id='settlement_dispatch_search_20261112', status='model_only_finite_search_and_staff_threshold_diagnostic',
        evidence='reports/SETTLEMENT_DISPATCH_SEARCH_20261112.md',
        note='396overlaparrays exact;300hsource losses include narrowstaffactivationbranches;no newEarthdata,physicalimpossibility or defaultadoptionclaim.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(out / 'presentation.json', dict(status='published', evidence_page_sha256=sha(page), publisher_sha256=sha(Path(__file__))))
    print('Published search misses and explicit correction note;original map files preserved.')


if __name__ == '__main__': main()
