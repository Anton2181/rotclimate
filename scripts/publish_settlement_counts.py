"""Publish the count development result and its unresolved coverage failure."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write


def main():
    out=ROOT/'output/settlement_counts_20261111';config=ROOT/'calibration/settlement_counts_20261111'
    r=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text());replay=json.loads((out/'replay.json').read_text())
    for key,path in {'plan_sha256':config/'plan.json','correction_sha256':config/'multiplicity_correction.json',
        'coverage_plan_sha256':config/'coverage_domain.json','producer_sha256':ROOT/'scripts/settlement_counts_earth.py',
        'module_sha256':ROOT/'polity/settlement_counts.py','coverage_module_sha256':ROOT/'polity/population_coverage.py',
        'blocks_sha256':out/'blocks.npz','predictions_sha256':out/'predictions.npz'}.items():
        if r[key]!=sha(path):raise ValueError('Stale count evidence: '+key)
    if review['status']!='passed' or review['source_results_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_settlement_counts.py'):
        raise ValueError('Stale count review')
    for path,digest in r['parent_artifacts'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen count parent')
    for name,digest in replay['byte_exact_outputs'].items():
        if sha(out/name)!=digest:raise ValueError('Stale replay')
    if r['adopt'] or r['chosen_for_production'] is not None or review['full_region_fit_qualified']:raise ValueError('Unexpected count adoption')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','settlement_counts.json'),(out/'review.json','settlement_counts_review.json'),
        (out/'replay.json','settlement_counts_replay.json'),(config/'plan.json','settlement_counts_plan.json'),
        (config/'multiplicity_correction.json','settlement_counts_multiplicity.json'),(config/'coverage_domain.json','settlement_counts_coverage_plan.json'),
        (out/'blocks.npz','settlement_count_blocks.npz'),(out/'predictions.npz','settlement_count_predictions.npz')]:shutil.copyfile(src,data/name)
    rows=[]
    for a in sorted(r['ranking']['covered_only'],key=lambda a:a['beta']):
        rows.append(f'<tr><th>{a["beta"]:g}</th><td>{a["pool_deviance_per_source_record"]["han"]:.4f}</td>'
            f'<td>{a["pool_deviance_per_source_record"]["rome"]:.4f}</td><td>{a["equal_pool_deviance_per_source_record"]:.4f}</td></tr>')
    section='''<!--settlement-counts-start--><section><h2>Count budgets: missing input is not empty land</h2><details id="settlement-counts" class="panel"><summary>Count and resident-size audit · missing Han coverage · restricted development fit</summary>
<p id="settlement-counts-verdict"><strong>The full-region count fit is unqualified.</strong> The old population raster stops at 125°E. In the frozen Han window, 1,586 allowed land cells (128,466 km²) and 13 source cells lack population input. Six blocks with eleven records stored zero population because they are wholly outside that raster. These are missing inputs, not established ecological limits. The new coverage guard rejects required missing input.</p>
<p>A separate, predeclared supported-domain sensitivity retains all covered difficult regions. It trains count scales on three geographic quadrants and predicts the fourth. The 0.5 population exponent improves the equal-pool deviance by 1.86% over 0.7, but geographic count-mass errors remain about 64% for Han and 51% for Rome. The thirteen unsupported records remain unresolved; they are not silently removed from the full-region result.</p>
<div class="table"><table id="settlement-counts-results"><thead><tr><th>Population exponent</th><th>Han administrative seats</th><th>Roman urban catalogue</th><th>Equal-pool mean deviance / record</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>Supported-domain primary counts: 1,267 Han / 1,115 Roman records, with separate distinct-cell sensitivities. The archive had already deduplicated coordinates; original multiplicity was reconstructed and checked before fitting. All 176 comparisons, 99/297 km blocks, four folds and shared-scale controls remain available. This is exposed development, not fresh validation or a new calibrated fantasy map. Archived point-count maps are descriptive references, not Poisson expected-rate estimators.</p>
<img src="../../reports/figures/settlement_counts_20261111.png" width="1800" height="855" alt="Supported-domain count fits modestly prefer exponent 0.5; Roman area availability remains separate from town residents.">
<img src="../../reports/figures/settlement_population_coverage_20261111.png" width="1425" height="1200" alt="Northeastern Han allowed land beyond the population raster is explicitly marked as missing input.">
<p><strong>Resident sizes need different labels.</strong> The operational AD150 Roman cohort has 862 supplied positive areas and 492 missing area records; 56 supplied values equal 20 or 30 ha. Other numeric values are not automatically certified measured or contemporary. The old reader filled missing areas by rank medians. Han CountyPOP measures districts, not residents of their seats. No such value becomes an observed town population here.</p>
<p>Independent review rebuilds 2,780 blocks, 704 held-fold cases and 9,680 scalar metrics. A fresh run is byte-exact. No fantasy people, food, positions, tracks, staffing, control or r44 physics change. Next: extend ecological input coverage consistently, then continue role-specific count and resident allocation on the same finite population/food ledger.</p>
<p><a href="../../reports/SETTLEMENT_COUNTS_20261111.md">Methods, source units and next work</a> · <a href="data/settlement_counts.json" download>All fits, source support and failures</a> · <a href="data/settlement_counts_review.json" download>Independent review</a> · <a href="data/settlement_counts_replay.json" download>Fresh replay</a> · <a href="data/settlement_counts_plan.json" download>Original count protocol</a> · <a href="data/settlement_counts_multiplicity.json" download>Multiplicity correction</a> · <a href="data/settlement_counts_coverage_plan.json" download>Coverage sensitivity protocol</a> · <a href="data/settlement_count_blocks.npz" download>Aggregate blocks</a> · <a href="data/settlement_count_predictions.npz" download>Held-quadrant predictions</a></p></details></section><!--settlement-counts-end-->'''
    html=page.read_text();pattern=r'<!--settlement-counts-start-->[\s\S]*?<!--settlement-counts-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--vidarbha-transfer-start-->'
        if marker not in html:raise ValueError('Publish transfer first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entry=dict(id='settlement_counts_20261111',status='exposed_count_development_full_domain_coverage_failure',evidence='reports/SETTLEMENT_COUNTS_20261111.md',
        note='OldHan/Rome development records;raw multiplicity recovered and size units audited.13Han records lack frozen population input. Full-domain fit unqualified;covered-only sensitivity explicitly restricted,no new blind claim or productionadoption.')
    usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry];write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published count development, missing-input failure and resident-size support;no map adoption.')


if __name__=='__main__':main()
