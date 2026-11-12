"""Publish the reviewed town-size shape diagnostic without changing defaults."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write


def main():
    out=ROOT/'output/settlement_size_shape_20261112'
    result=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text())
    replay=json.loads((out/'replay.json').read_text())
    assert review['status']==replay['status']=='passed'
    assert review['results_sha256']==replay['results_sha256']==sha(out/'results.json')
    for path,digest in result['sources_sha256'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed reviewed source: '+path)
    assert result['support']['conclusion']=='allocator_more_equal_than_every_reference' and result['adopt'] is False
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for p,name in [(out/'results.json','settlement_size_shape.json'),(out/'review.json','settlement_size_shape_review.json'),
        (out/'replay.json','settlement_size_shape_replay.json'),
        (ROOT/'calibration/settlement_size_shape_20261112/plan.json','settlement_size_shape_plan.json')]:
        shutil.copyfile(p,data/name)
    town=result['allocator']['corrected_h600_f0.075']['quantities']['town_total']['all_places']
    roman=result['roman']['all_measured']['scenarios'];low,high=result['reference_band']['all_places']['gini']
    constant,steep=roman['density_exponent_0']['all_places'],roman['density_exponent_0.5']['all_places']
    request=result['civilian_requests_before_finite_budget']['corrected']['all_places']
    section=f'''<!--settlement-size-shape-start--><section><h2>Town sizes: the allocator has no large centres</h2><details id="settlement-size-shape" class="panel"><summary>Allocator town sizes are more equal than every Roman reference · development diagnostic, no fit</summary>
<p>Relative town sizes in the eight coupled scenarios were compared with conditional references built from {result['cohort']['measured']} measured Roman places of AD150 (area times an assumed density). The comparison, its support rule and the expected outcome were declared before any metric was computed. Only relative sizes are compared; household size and density constants cancel.</p>
<p><strong>The allocator is more equal than every reference.</strong> Its Gini coefficient is {town['gini']:.2f}, against {constant['gini']:.2f} to {steep['gini']:.2f} for all measured Roman places and {low:.2f} to {high:.2f} over every declared set. Its largest town is {town['largest_over_median']:.0f} times the median; the Roman references reach {constant['largest_over_median']:.0f} to {steep['largest_over_median']:.0f}. The same holds for the largest half and the largest quarter of places, in both climates.</p>
<p>The flatness is already in what towns request before the food and labour ledger applies (Gini {request['gini']:.2f}), and the transfer share cannot change it. No parameter was tuned. A market hierarchy, supply of large centres from beyond one catchment and administrative concentration are now explicit dependencies before any size fit.</p>
<img src="../../reports/figures/settlement_size_shape_20261112.png" alt="Rank-size curves relative to the median for Roman references and allocator towns, and Gini coefficients at three tail levels">
<p>Hanson (2016), <a href="https://doi.org/10.5287/bodleian:eqapevAn8">Cities Database</a>, OxREP: exposed development evidence with mixed extent bases; {result['cohort']['unmeasured_not_filled']} cohort places have no area and are not filled. Allocator towns are generated hypotheses. Only aggregate metrics are published. Model defaults are unchanged.</p>
<p><a href="../../reports/SETTLEMENT_SIZE_SHAPE_20261112.md">Methods and limits</a> · <a href="data/settlement_size_shape.json" download>Metrics for all sets and scenarios</a> · <a href="data/settlement_size_shape_review.json" download>Independent review</a> · <a href="data/settlement_size_shape_replay.json" download>Fresh replay</a> · <a href="data/settlement_size_shape_plan.json" download>Prior declaration</a></p></details></section><!--settlement-size-shape-end-->'''
    html=page.read_text();pattern=r'<!--settlement-size-shape-start-->[\s\S]*?<!--settlement-size-shape-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-size-identity-start-->'
        if marker not in html:raise ValueError('Publish the identity audit first')
        html=html.replace(marker,section+'\n'+marker,1)
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text())
    entry=dict(id='settlement_size_shape_20261112',status='exposed_development_size_shape_diagnostic_no_fit',
        evidence='reports/SETTLEMENT_SIZE_SHAPE_20261112.md',
        note='862 measured AD150 catalogue areas as conditional relative-size references under three density scenarios versus eight coupled allocator scenarios. Declared before metrics. Allocator more equal than every reference at all tail levels. No absolute sizes, no fit, no blind claim, no default.')
    usage['datasets']=[r for r in usage['datasets'] if r['id']!=entry['id']]+[entry]
    write(registry,usage);shutil.copyfile(registry,data/'dataset_usage.json')
    write(out/'presentation.json',dict(status='published',page_sha256=sha(page),publisher_sha256=sha(Path(__file__))))
    print('Published reviewed size-shape diagnostic; model defaults unchanged.')


if __name__=='__main__':main()
