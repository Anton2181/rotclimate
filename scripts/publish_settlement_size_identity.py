"""Publish the reviewed housing/catalogue identity audit without changing defaults."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write


def main():
    out=ROOT/'output/settlement_size_identity_20261112';plan=ROOT/'calibration/settlement_size_identity_20261112'
    result=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text())
    replay=json.loads((out/'replay.json').read_text())
    assert review['status']==replay['status']=='passed'
    assert review['results_sha256']==replay['results_sha256']==sha(out/'results.json')
    for path,digest in result['sources_sha256'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed reviewed source: '+path)
    s=result['summary'];a=result['associations']
    assert s['joined_by_author_key']==50 and s['AD150_eligible']==0
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for p,name in [(out/'results.json','settlement_size_identity.json'),(out/'review.json','settlement_size_identity_review.json'),
        (out/'replay.json','settlement_size_identity_replay.json'),(plan/'plan.json','settlement_size_identity_plan.json'),
        (plan/'key_format_amendment.json','settlement_size_identity_amendment.json')]:
        shutil.copyfile(p,data/name)
    every=a['all_rows']['density_vs_sampled_fraction']['spearman_rho'];partial=a['excluding_whole_extent_samples']['density_vs_sampled_fraction']['spearman_rho']
    section=f'''<!--settlement-size-identity-start--><section><h2>Housing samples joined to the city catalogue</h2><details id="settlement-size-identity" class="panel"><summary>50 of 50 samples joined by author key · identity settled, no size labels yet</summary>
<p>The pinned city catalogue was recovered from the project's older host with an identical SHA-256 and reproduces the earlier audit's counts. All 50 housing samples join it by the authors' key: {s['name_agreement']['exact']} names and {s['province_agreement']['exact']} provinces are identical, and no place appears twice. An independent raw-XML review, a 600-field cross-check against a separately exported CSV and a byte-exact fresh run pass.</p>
<p><strong>Still no AD150 size target.</strong> {s['area_agreement']['different']} samples state a different site extent from the catalogue (Metapontum: 150 ha against 14 ha). {s['catalogue_AD150']['excludes']} places had ended before AD150, {s['catalogue_AD150']['covers']} have a dated span covering it and {s['catalogue_AD150']['open_or_nonnumeric']} have no recorded end. Catalogue dates describe whole sites, not housing phases, so every phase, extent and representativeness gate is retained.</p>
<p>Samples covering less than 1% of a site report a median {result['sampling_classes']['below_1_percent']['median_properties_per_sampled_ha']:.0f} properties per investigated hectare; samples covering 1–10% report {result['sampling_classes']['1_to_below_10_percent']['median_properties_per_sampled_ha']:.0f}. The rank correlation between density and investigated share is {every:+.2f} across all 50 and {partial:+.2f} without the two whole-extent samples. This describes a selected sample and cannot separate denser large cities from trenches placed in dense quarters.</p>
<img src="../../reports/figures/settlement_size_identity_20261112.png" alt="Property density against investigated share for 50 housing samples, and housing-table site extent against catalogue area">
<p>Ortman and Hanson (2023), <a href="https://doi.org/10.1017/S0068113X23000375">Estimating the ‘Missing’ Houses of Silchester</a>, CC BY 4.0; Hanson (2016), <a href="https://doi.org/10.5287/bodleian:eqapevAn8">Cities Database</a>, OxREP. Both are exposed development evidence. Only the joined fields of these 50 records are published. No allocator scores or default changes follow.</p>
<p><a href="../../reports/SETTLEMENT_SIZE_IDENTITY_20261112.md">Methods and limits</a> · <a href="data/settlement_size_identity.json" download>Join and sampling audit</a> · <a href="data/settlement_size_identity_review.json" download>Independent review</a> · <a href="data/settlement_size_identity_replay.json" download>Fresh replay</a> · <a href="data/settlement_size_identity_plan.json" download>Prior declaration</a> · <a href="data/settlement_size_identity_amendment.json" download>Key-format amendment</a></p></details></section><!--settlement-size-identity-end-->'''
    html=page.read_text();pattern=r'<!--settlement-size-identity-start-->[\s\S]*?<!--settlement-size-identity-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-sizes-start-->'
        if marker not in html:raise ValueError('Publish housing measurement evidence first')
        html=html.replace(marker,section+'\n'+marker,1)
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(registry.read_text())
    entry=dict(id='settlement_size_identity_20261112',status='exposed_identity_and_sampling_audit_no_size_scores',
        evidence='reports/SETTLEMENT_SIZE_IDENTITY_20261112.md',
        note='Pinned Hanson2016 workbook recovered with identical SHA256; 50 of 50 housing samples joined by author key; 7 extents differ; 4 places ended before AD150; all AD150 gates retained. Sampling associations describe a selected exposed sample. No fit, blind claim or default.')
    usage['datasets']=[r for r in usage['datasets'] if r['id']!=entry['id']]+[entry]
    write(registry,usage);shutil.copyfile(registry,data/'dataset_usage.json')
    write(out/'presentation.json',dict(status='published',page_sha256=sha(page),publisher_sha256=sha(Path(__file__))))
    print('Published reviewed identity audit; model defaults unchanged.')


if __name__=='__main__':main()
