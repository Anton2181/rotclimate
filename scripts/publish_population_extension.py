"""Expose source repairs and complete-input count results in the normal atlas."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write


def main():
    out=ROOT/'output/earth_population_extension_20261111';count=ROOT/'output/settlement_count_extension_20261111'
    config=ROOT/'calibration/earth_population_extension_20261111'
    r=json.loads((out/'correction.json').read_text());review=json.loads((out/'review.json').read_text())
    c=json.loads((count/'results.json').read_text());cr=json.loads((count/'review.json').read_text())
    if review['status']!='passed' or review['correction_sha256']!=sha(out/'correction.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_population_extension.py'):
        raise ValueError('Stale source correction review')
    if cr['status']!='passed' or cr['results_sha256']!=sha(count/'results.json') or cr['reviewer_sha256']!=sha(ROOT/'scripts/review_count_population_extension.py'):
        raise ValueError('Stale complete-input count review')
    for key,path in {'correction_plan_sha256':config/'nodata_correction.json','current_decoder_sha256':ROOT/'scripts/land_people_earth.py',
        'producer_sha256':ROOT/'scripts/correct_population_extension.py','global_patch_sha256':out/'global_nodata_patch.npz',
        'new_han_input_sha256':out/'han_corrected_inputs.npz','parent_global_sha256':ROOT/'output/land_people/earth/earth.npz',
        'original_overlap_sha256':out/'overlap.json','original_tile_sha256':out/'tile.npz'}.items():
        if r[key]!=sha(path):raise ValueError('Stale correction: '+key)
    initial=json.loads((out/'overlap.json').read_text())
    archived=subprocess.check_output(['git','show',r['baseline_snapshot']+':scripts/land_people_earth.py'],cwd=ROOT)
    if hashlib.sha256(archived).hexdigest()!=initial['frozen_sources']['scripts/land_people_earth.py']:raise ValueError('Historical source decoder not recoverable')
    for directory in [out,count]:
        replay=json.loads((directory/'replay.json').read_text())
        if replay['status']!='passed':raise ValueError('Replay did not pass')
        for name,digest in replay['byte_exact_outputs'].items():
            if sha(directory/name)!=digest:raise ValueError('Stale source/count replay')
    if r['adopt'] or c['adopt'] or not r['compatibility_reproduction']['passed'] or not r['corrected_reference_overlap']['passed']:raise ValueError('Unexpected adoption or failed correction guard')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    files=[(out/'correction.json','population_extension.json'),(out/'review.json','population_extension_review.json'),
        (out/'replay.json','population_extension_replay.json'),(out/'sources.json','population_extension_sources.json'),
        (out/'overlap.json','population_extension_original_overlap.json'),(config/'nodata_correction.json','population_extension_correction_plan.json'),
        (out/'global_nodata_patch.npz','population_extension_patch.npz'),(count/'results.json','population_extension_counts.json'),
        (count/'review.json','population_extension_counts_review.json'),(count/'replay.json','population_extension_counts_replay.json')]
    for src,name in files:shutil.copyfile(src,data/name)
    rows=[]
    for a in sorted(c['ranking']['full_corrected'],key=lambda a:a['beta']):
        rows.append(f'<tr><th>{a["beta"]:g}</th><td>{a["pools"]["han"]:.4f}</td><td>{a["pools"]["rome"]:.4f}</td><td>{a["equal_pool_deviance_per_source_record"]:.4f}</td></tr>')
    section='''<!--population-extension-start--><section><h2>Complete population inputs and coastal terrain repair</h2><details id="population-extension" class="panel"><summary>Source repair · complete Han population coverage · count replay checked</summary>
<p id="population-extension-verdict"><strong>All 1,586 missing required population cells now have input.</strong> The ecological extension also exposed a source bug: the old elevation reader treated the sea’s declared −32,768 NoData value as terrain, creating false coastal cliffs. The decoder now respects NoData and preserves valid below-sea-level ground.</p>
<p>The original overlap test remains failed. Exact legacy reproduction and an explicitly corrected reference both pass the original eight-field thresholds across all 1,370 control land cells. Temperature, rainfall, PET and aridity are exact; no threshold was loosened and no physics or population-scale coefficient was fitted.</p>
<img src="../../reports/figures/population_nodata_correction_20261111.png" width="1800" height="810" alt="All five coastal fallback failures: false 32,800 metre cliffs and reduced farmland disappear after correct NoData decoding.">
<img src="../../reports/figures/population_extension_han_20261111.png" width="1950" height="1050" alt="The required Han benchmark land now has complete ecological population inputs; missing eastern coverage is filled.">
<p>The sparse global patch changes 1,274 arable/density cells and 17,903 relief cells. The new Han family changes 128 previously covered density cells, all outside its allowed mask, and fills 1,586 required cells. Other input arrays remain fixed. Original archives remain unchanged. The old core-history field needs rebuilding for corrected relief and eastern coverage before new town-placement qualification.</p>
<div class="table"><table id="population-extension-count-results"><thead><tr><th>Population exponent</th><th>Han deviance / record</th><th>Roman control</th><th>Equal-pool mean</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>Full-region counts retain 1,280 Han and 1,115 Roman source records. All positive source-count blocks now have positive predictions under these development models. On the original supported domain every comparison reproduces the previous result; the wider-domain score is not presented as a direct accuracy gain over a smaller domain. The modest preference for exponent 0.5 persists, with large geographic errors still unresolved. Roman inputs remain the original paired control.</p>
<p>Independent source review checks 21,920 overlap field/cell cases; count review checks 2,780 blocks, 640 held-fold cases and 8,800 scalar metrics. Both fresh replays are byte-exact. This is a benchmark input repair; the fantasy map, finite food/population ledger, roads, staffing, control and r44 climate packet remain unchanged. Next: rebuild supported core-travel inputs, then continue point placement and resident-size/shared-ledger work.</p>
<p><a href="../../reports/EARTH_POPULATION_EXTENSION_20261111.md">Source cause, methods and next work</a> · <a href="data/population_extension.json" download>Correction and both reference checks</a> · <a href="data/population_extension_review.json" download>Source correction review</a> · <a href="data/population_extension_replay.json" download>Source correction replay</a> · <a href="data/population_extension_sources.json" download>Official sources and hashes</a> · <a href="data/population_extension_original_overlap.json" download>Original failed overlap</a> · <a href="data/population_extension_correction_plan.json" download>Correction protocol</a> · <a href="data/population_extension_patch.npz" download>Sparse global field patch</a> · <a href="data/population_extension_counts.json" download>All complete-input count comparisons</a> · <a href="data/population_extension_counts_review.json" download>Count review</a> · <a href="data/population_extension_counts_replay.json" download>Count replay</a></p></details></section><!--population-extension-end-->'''
    core=ROOT/'output/core_population_inputs_20261111'
    if (core/'review.json').exists() and (core/'replay.json').exists():
        k=json.loads((core/'results.json').read_text());kr=json.loads((core/'review.json').read_text())
        if kr['status']!='passed' or kr['results_sha256']!=sha(core/'results.json') or kr['reviewer_sha256']!=sha(ROOT/'scripts/review_core_population_inputs.py'):raise ValueError('Stale core-input review')
        for path,digest in k['sources'].items():
            if sha(ROOT/path)!=digest:raise ValueError('Changed core-input source: '+path)
        for name,target in [('results.json','core_population_inputs.json'),('review.json','core_population_inputs_review.json'),('replay.json','core_population_inputs_replay.json')]:shutil.copyfile(core/name,data/target)
        section=section.replace('The old core-history field needs rebuilding for corrected relief and eastern coverage before new town-placement qualification.','The original core-history field is preserved; a checked rebuild now supplies complete supported histories for the next point comparison.')
        section=section.replace('Next: rebuild supported core-travel inputs, then continue point placement and resident-size/shared-ledger work.','Next: compare point-placement mechanisms on these checked core inputs, then continue resident-size/shared-ledger work.')
        addition=f'''<div id="core-population-inputs"><h3>Supported core-travel inputs are now checked</h3><p>The new kernel exactly reproduces the old kernel on old inputs. The same forest, sea and relief costs are retained; an explicit mask excludes geography without input support. Independent edge-bound and predecessor checks certify shortest paths within this known domain across {kr['total_directed_edge_constraints']:,} directed edges. Both source grids are fully covered and connected where required.</p><p>The old eastern edge had been copied outward: Han routes change by −79.8 to +671.3 effective km; Roman routes shorten by up to 136.3 km after coastal relief correction. These are input and geometry checks, not dated occupation or a new point-fit qualification. The next comparison tests density-power and historical-prior mixtures on the checked inputs.</p><p><a href="data/core_population_inputs.json" download>All core-input checks</a> · <a href="data/core_population_inputs_review.json" download>Independent optimality certificate</a> · <a href="data/core_population_inputs_replay.json" download>Fresh core replay</a></p></div>'''
        section=section.replace('</details></section><!--population-extension-end-->',addition+'</details></section><!--population-extension-end-->')
    html=page.read_text();pattern=r'<!--population-extension-start-->[\s\S]*?<!--population-extension-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-counts-start-->'
        if marker not in html:raise ValueError('Publish initial count audit first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    usage_path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(usage_path.read_text())
    entry=dict(id='earth_population_extension_20261111',status='exposed_source_correction_complete_input_count_development',
        evidence='reports/EARTH_POPULATION_EXTENSION_20261111.md',note='Official regionalclimate/ETOPOsources,strict original/legacy/correctedoverlap gates,NoDatadecoderfix. FullrequiredHanpopulationcoverage restored;160countcomparisons on exposed records. Originalfailure retained;no blindtransfer,history-point qualification,residentsize fit or fantasy adoption.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry];write(usage_path,usage);shutil.copyfile(usage_path,data/'dataset_usage.json')
    print('Published complete population coverage,coastal NoData source repair and checked count replay.')


if __name__=='__main__':main()
