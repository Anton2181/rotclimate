"""Publish adaptive-location development and an unscored source-quality audit."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_intensity_earth import OUT,PLAN,ORIGINAL
from settlement_locations_earth import sha,write


def main():
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    if result['adopt'] or result['plan_sha256']!=sha(PLAN) or len(result['rows'])!=108:
        raise ValueError('Wrong/incomplete adaptive development result')
    if sha(ORIGINAL/'results.json')!=result['original_results_sha256']:
        raise ValueError('Changed fixed-spacing reference evidence')
    if review['status']!='passed' or review['source_result_sha256']!=sha(OUT/'results.json'):
        raise ValueError('Stale proposal review')
    for path,digest in result['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed producer source')
    if sha(OUT/'positions.npz')!=result['positions_sha256']:raise ValueError('Changed locations')
    for receipt in result['inputs'].values():
        if sha(ROOT/receipt['path'])!=receipt['sha256']:raise ValueError('Changed Earth input')
    ap=ROOT/'output/vidarbha_preparation_20261110/audit.json';audit=json.loads(ap.read_text())
    if audit['model_scores_computed'] or audit['model_predictions_loaded']:
        raise ValueError('Source audit unexpectedly includes model evaluation')
    if audit['plan_sha256']!=sha(ROOT/'calibration/vidarbha_preparation_20261110/plan.json') or audit['source_sha256']!=sha(ROOT/'scripts/audit_vidarbha_preparation.py'):
        raise ValueError('Changed preparation protocol/source')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data';data.mkdir(exist_ok=True)
    files=[(OUT/'results.json','settlement_intensity.json'),(OUT/'review.json','settlement_intensity_review.json'),
        (PLAN,'settlement_intensity_plan.json'),(ap,'vidarbha_preparation.json'),
        (ROOT/'reports/figures/settlement_intensity_maps_20261110.png','settlement_intensity_maps.png'),
        (ROOT/'reports/figures/settlement_intensity_tradeoffs_20261110.png','settlement_intensity_tradeoffs.png')]
    for source,name in files:shutil.copyfile(source,data/name)
    lead=next(r for r in result['ranking'] if r['variant']==result['development_lead'])
    reference=result['references'][0];baseline=next(r for r in result['references'] if r['family']=='production')
    rows=[]
    for pool,label in [('han','Han AD2'),('rome','Rome AD150')]:
        for title,row in [('Production',baseline['pools'][pool]),('Fixed18km reference',reference['pools'][pool]),('Adaptive · five-seed mean',lead['pools'][pool])]:
            rows.append(f'<tr><th>{label}</th><td>{title}</td>'+''.join(f'<td>{row[k]:.3f}</td>' for k in ['unique_F1','M1','M3'])+'</tr>')
    section='''<!--settlement-intensity-start--><section id="settlement-intensity" aria-labelledby="settlement-intensity-h"><h2 id="settlement-intensity-h">Locally varying spacing: a better location/spacing compromise</h2><div class="panel">
<p><strong>Exposed Earth development · no production adoption.</strong> We completed108 evaluations across18 adaptive variants, comparing history lengths450/800/1500km and deterministic/stochastic placement. All retain1,202 Han /1,292 Roman proposals; people, food and environmental eligibility remain unchanged. Relative centre intensity determines local spacing; it is not an estimate of population or occupation age.</p>
<div class="table"><table id="settlement-intensity-results"><thead><tr><th>Pool</th><th>Placement</th><th>Unique-site F1 ↑</th><th>100km block rank ↑</th><th>Spacing KS ↓</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>The new development lead uses coefficient0.35 and a450km history prior. It improves unique matching and spacing over production in both pools. Compared with the strongest fixed18km alternative it sacrifices some exact-location gains for much better spacing. The declared diagnostic score is0.621 versus0.570; this is not a percentage accuracy or independent transfer result.</p>
<figure><img src="data/settlement_intensity_maps.png" alt="Observed Han and Roman centres, fixed18km reference and adaptive spacing with unchanged counts"><figcaption>Maps always use seed1; table shows five-seed means where stochastic. Dense areas can have nearer centres. The9km grid still cannot validate every village or exact historical population.</figcaption></figure>
<figure><img src="data/settlement_intensity_tradeoffs.png" alt="Unique matching versus spacing error for fixed and adaptive candidate families"><figcaption>Both location and spacing alternatives remain visible. We tested declared location weights0.4,0.6,0.8; adaptive variants lead at those weights, but the chosen parameters differ. The earlier study and its original winner remain unchanged.</figcaption></figure>
<p><strong>Transfer-source audit:</strong> Vidarbha's supplied coordinate master has60 records and the settlement table390 records/389 unique IDs, with zero ID joins. Its values conflict with the readme's coordinate-axis definitions. Source checksums pass; no prediction or model accuracy score was computed. This version is not ready for a geolocated transfer test; it is not a failed calibration of our model.</p>
<p><strong>Next:</strong> occupation-history dynamics and role/coverage-appropriate transfer remain unfinished. A qualified candidate must still pass through the shared resident/food/staffing ledger and recomputed control. Settlement hierarchy, differentiated authority, institutional resources and mobile/nonstate communities remain on the full roadmap.</p>
<p><a href="../../reports/SETTLEMENT_INTENSITY_20261110.md">Mechanism, results and limits</a> · <a href="../../reports/VIDARBHA_PREPARATION_20261110.md">Source-quality audit</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Full programme</a> · <a href="data/settlement_intensity.json" download>All108 development results</a> · <a href="data/settlement_intensity_plan.json" download>Frozen protocol</a> · <a href="data/settlement_intensity_review.json" download>Count/eligibility/pair review</a> · <a href="data/vidarbha_preparation.json" download>Unscored preparation receipt</a></p></div></section><!--settlement-intensity-end-->'''
    html=page.read_text();pattern=r'<!--settlement-intensity-start-->[\s\S]*?<!--settlement-intensity-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-locations-start-->'
        if marker not in html:raise ValueError('Publish original settlement evidence first')
        html=html.replace(marker,section+'\n'+marker,1)
    page.write_text(html)
    registry=ROOT/'calibration/earth_components_20261105/dataset_usage.json'
    exposure=json.loads(registry.read_text());exposure['date']='2026-11-10'
    entries=[dict(id='settlement_intensity_20261110',status='exposed_development_only',evidence='reports/SETTLEMENT_INTENSITY_20261110.md',
        note='108 adaptive-spacing/prior-sensitivity evaluations on previously exposed Han/Roman data. No occupation-age, population or control adoption; old fixed study preserved.'),
        dict(id='vidarbha_2020',status='prepared_unscored_source_quality_failure',evidence='reports/VIDARBHA_PREPARATION_20261110.md',
        note='Master/settlement CSVs read only for frozen schema/join/axis/chronology audit. Zero joins and conflicting coordinate documentation; no target maps, predictions or model scores. No independent/sealed status granted.')]
    exposure['datasets']=[e for e in exposure['datasets'] if e['id'] not in {r['id'] for r in entries}]+entries
    write(registry,exposure);shutil.copyfile(registry,data/'dataset_usage.json')
    print('Published108 adaptive development evaluations and unscored source audit; production unchanged.')


if __name__=='__main__':main()
