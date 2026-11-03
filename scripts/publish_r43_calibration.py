"""Publish the completed r43 search/validation without relabelling atlas data."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json
from organize_climate_accuracy import organize


def main():
    adoption = json.loads((ROOT / 'calibration/local_accuracy_20261023/r43_adoption.json').read_text())
    folder = ROOT / adoption['validation']; result = json.loads((folder / 'result.json').read_text())
    if (adoption['adopted'] != 'r43' or result['outcome'] != 'qualified_for_review'
            or file_hash(folder / 'result.json') != adoption['validation_result_sha256']):
        raise ValueError('Unmatched adoption/validation evidence')
    review_folder = ROOT / 'output/r42_multistart_review_20261102'
    review = json.loads((review_folder / 'review.json').read_text())
    figure = review_folder / 'search_starts.png'
    if file_hash(figure) != review['figure_sha256']: raise ValueError('Search figure changed')
    destination = ROOT / 'atlases/climate_accuracy/data'
    shutil.copyfile(figure, destination / 'r43_search_starts.png')
    preview_folder = ROOT / 'output/r43_world_preview_20261103'
    preview = json.loads((preview_folder / 'receipt.json').read_text())
    if file_hash(preview_folder / 'raw_world_comparison.png') != preview['image_sha256']:
        raise ValueError('Raw world preview changed')
    shutil.copyfile(preview_folder / 'raw_world_comparison.png', destination / 'r43_raw_world.png')
    write_json(destination / 'r43_calibration.json', dict(adoption=adoption, validation=result, search_review=review,
        raw_world_preview=preview,
        publication_source_sha256=file_hash(Path(__file__))))
    rows = []
    for label, key in [('49-region development', 'dev49'), ('Paired 28 km', 'fine28'), ('Previously unseen e', 'sealed_e')]:
        s = result[key]
        rows.append(f'<tr><td>{label}</td><td>{s["S"]:.7f}</td><td>{100*s["T"]:+.4f}%</td><td>{100*s["P"]:+.4f}%</td></tr>')
    commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--',
        str((folder / 'result.json').relative_to(ROOT))], cwd=ROOT, text=True).strip()
    if not commit: raise ValueError('Commit the complete validation result before publishing')
    section = f'''<!--r43-calibration-start--><section aria-labelledby="r43-calibration-h">
<h2 id="r43-calibration-h">r43: a small calibration gain, with effectively tied unseen performance</h2>
<p>All three 13-evaluation starts finished before one finalist was selected: 39 evaluations, including three reproduction controls and 36 proposals. Only the nine declared physical strengths/gates, wet-sun response and rain timescale vary. Earth planet/orbit settings are fixed; winds and SST are model-generated. This is an adopted calibration step, not a new physical closure.</p>
<div class="table"><table><caption>Fresh paired error ratios versus r42; every declared gate passed unchanged</caption><thead><tr><th>Check</th><th>Combined ratio</th><th>Temperature</th><th>Rain loss</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p><strong>The unseen combined score is effectively tied.</strong> Its temperature regression and rain-loss gain remain visible above. The finer-grid combined regression is within the declared 1% allowance. No individual-region or group veto was introduced after results; all regional errors and numerical receipts are retained.</p>
<figure><a href="data/r43_search_starts.png"><img src="data/r43_search_starts.png" width="1885" height="667" loading="lazy" alt="All completed candidates from three independent calibration starts"></a><figcaption>The r42-centred basin produced the best qualifying proposal. Two generations per start in nine dimensions are sparse; this does not establish a global optimum or validate missing physics.</figcaption></figure>
<p>The descriptive development-region resampling interval spans both gains and regressions. It is not corrected for selection or spatial dependence and is not a probability of improved unseen performance. Set e is now spent. The separately reserved set f remains unopened for a later finalist; the next storm-family campaign declares 61 development regions including spent d/e and reports historical S49 separately.</p>
<p>The <a href="../earth_fit/">Earth atlas</a> and its launcher identify the actually served snapshot. A model adoption does not relabel older maps while a full verified rebuild runs. The r43 rebuild uses a pinned source worktree and new matching correction training; normal atlas publication waits for all climate, food, people, trade, language and browser/portable checks.</p>
<figure><a href="data/r43_raw_world.png"><img src="data/r43_raw_world.png" width="2295" height="1080" loading="lazy" alt="Verified raw r42 and r43 biome and rainfall maps with temperature and rainfall differences"></a><figcaption>Raw world preview on identical geometry and three surroundings layouts. Target-zone agreement rises from 34.23% to 34.47%; this is agreement with proposed zones, not measured fantasy-world accuracy. These raw maps precede Earth correction and the complete atlas exports.</figcaption></figure>
<p><a href="data/r43_calibration.json" download>Adoption, selection, uncertainty scope and validation scores</a> · <a href="../../reports/R43_20261103.md">r43 release</a> · <a href="../../reports/MULTISTART_20261103.md">Search and local-minimum limits</a> · <a href="https://github.com/Anton2181/rotclimate/tree/{commit}/{adoption['validation']}">All verified raw case packets and protocols at the validation commit</a></p>
</section><!--r43-calibration-end-->'''
    page = ROOT / 'atlases/climate_accuracy/index.html'
    text = re.sub(r'<!--r43-calibration-start-->[\s\S]*?<!--r43-calibration-end-->', '', page.read_text())
    overview = '''<!--current-earth-overview-start--><h2>Current adopted raw Earth physics: r43</h2>
<p>On the fixed 49-region development pool, monthly temperature MAE is <strong>1.8789 C</strong> and rain loss <strong>0.49315</strong>. Combined error is 0.86% below r42. Fresh paired finer-grid and previously unseen checks pass the declared rule; unseen combined performance is effectively tied. These are regional benchmarks, not a global accuracy percentage. <a href="../../reports/R43_20261103.md">Complete release evidence and regressions</a>.</p>
<p>The <a href="../earth_fit/">Earth atlas</a> identifies its actually served release and distinguishes raw from Earth-corrected climate. Atlas publication follows complete verified rebuilding; independent physical experiments are labelled separately.</p>
<h2>Historical r39 benchmark · 27 October 2026</h2><p class="note">The cards and audit immediately below retain the original r39 measurements and sample definitions. They are not r43 city accuracy.</p><!--current-earth-overview-end-->'''
    text, count = re.subn(r'<!--current-earth-overview-start-->[\s\S]*?<!--current-earth-overview-end-->', overview, text)
    if count != 1: raise ValueError('Current overview marker is missing or duplicated')
    text = text.replace('</main>', section + '\n</main>'); text, studies = organize(text)
    if organize(text)[0] != text: raise ValueError('Research navigation is not idempotent')
    text = text.replace('Updated 2 November 2026 · current results and historical benchmarks',
                        'Updated 3 November 2026 · current results and historical benchmarks')
    text = text.replace('The adopted raw Earth model is r42.', 'This historical process study uses raw r42.')
    text = text.replace('The live calibration and atlas release use unchanged production physics.',
                        'These probes did not change production physics; later calibration releases are reported separately.')
    page.write_text(text)
    write_json(review_folder / 'publication.json', dict(status='passed', newest=studies[0], page_sha256=file_hash(page)))
    print('Published', studies[0], 'with unchanged atlas data')


if __name__ == '__main__': main()
