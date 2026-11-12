"""Publish reviewed housing measurement evidence without changing model defaults."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write


def main():
    out=ROOT/'output/settlement_size_evidence_20261112';source=ROOT/'data/source/roman_housing_2023'
    result=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text())
    replay=json.loads((out/'replay.json').read_text())
    assert review['status']==replay['status']=='passed'
    assert review['results_sha256']==replay['results_sha256']==sha(out/'results.json')
    for path,digest in result['sources_sha256'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed reviewed source: '+path)
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for p,name in [(out/'results.json','settlement_sizes.json'),(out/'review.json','settlement_sizes_review.json'),
        (out/'replay.json','settlement_sizes_replay.json'),(source/'table2.csv','settlement_sizes_source.csv'),
        (source/'source.json','settlement_sizes_source.json'),
        (ROOT/'calibration/settlement_size_evidence_20261112/plan.json','settlement_sizes_plan.json'),
        (ROOT/'calibration/settlement_size_evidence_20261112/source_access_amendment.json','settlement_sizes_amendment.json')]:
        shutil.copyfile(p,data/name)
    section='''<!--settlement-sizes-start--><section><h2>Housing evidence for resident sizes</h2><details id="settlement-sizes" class="panel"><summary>50 housing samples reviewed · measurement preparation, no new fit</summary>
<p>Observed properties, investigated area and whole-site extent are now separate typed inputs. All 50 records match the published source table, with independent decimal checks of 150 conditional household scenarios and a byte-exact fresh compilation. Median investigated coverage is 1.11%; 24 samples cover less than 1% of their stated extent.</p>
<p><strong>No AD150 size target yet clears all gates.</strong> Sample phase, contemporaneous extent and whole-site representativeness require evidence. Three reported phases explicitly exclude AD150; the other 47 remain unresolved. Missing dates and missing houses cannot become census zeros. Household scenarios of 3, 5 and 7 people are sensitivity assumptions, not confidence intervals.</p>
<img src="../../reports/figures/settlement_size_evidence_20261112.png" alt="Coverage of 50 housing samples and three different evidence paths at Silchester">
<p>Ortman and Hanson (2023), <a href="https://doi.org/10.1017/S0068113X23000375">Estimating the ‘Missing’ Houses of Silchester</a>, Britannia 54:167–187, Table 2, CC BY 4.0. This is an exposed mixed-period source, not the unrecovered original 52-case table or independent geographic transfer. Author-supplied city keys are retained; the unavailable original catalogue prevents certifying its joins. No allocator scores or default changes follow from this preparation.</p>
<p><a href="../../reports/SETTLEMENT_SIZE_EVIDENCE_20261112.md">Methods and limits</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Living whole-programme plan</a> · <a href="data/settlement_sizes.json" download>Conditional references</a> · <a href="data/settlement_sizes_source.csv" download>Attributed source table</a> · <a href="data/settlement_sizes_source.json" download>Source and phase notes</a> · <a href="data/settlement_sizes_review.json" download>Independent review</a> · <a href="data/settlement_sizes_replay.json" download>Fresh replay</a> · <a href="data/settlement_sizes_plan.json" download>Prior declaration</a> · <a href="data/settlement_sizes_amendment.json" download>Source-access amendment</a></p></details></section><!--settlement-sizes-end-->'''
    html=page.read_text();pattern=r'<!--settlement-sizes-start-->[\s\S]*?<!--settlement-sizes-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-feedback-start-->'
        if marker not in html:raise ValueError('Publish coupled feedback evidence first')
        html=html.replace(marker,section+'\n'+marker,1)
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text())
    entry=dict(id='settlement_size_evidence_20261112',status='exposed_housing_measurement_preparation_no_size_scores',
        evidence='reports/SETTLEMENT_SIZE_EVIDENCE_20261112.md',
        note='50 attributed2023housing samples,independent extraction/arithmetic review;allAD150phase/extent/representativeness gates retained. Original52case source and workbook unavailable. No new fit,blind claim or default.')
    usage['datasets']=[r for r in usage['datasets'] if r['id']!=entry['id']]+[entry]
    write(registry,usage);shutil.copyfile(registry,data/'dataset_usage.json')
    write(out/'presentation.json',dict(status='published',page_sha256=sha(page),publisher_sha256=sha(Path(__file__))))
    print('Published reviewed housing measurement evidence; model defaults unchanged.')


if __name__=='__main__':main()
