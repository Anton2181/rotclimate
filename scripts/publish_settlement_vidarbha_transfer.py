"""Publish the frozen regional diagnostic, including its failed outcome."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from settlement_vidarbha_transfer import DEFAULT_OUT, CONFIG, METHODS


def main():
    out=DEFAULT_OUT;result=json.loads((out/'results.json').read_text());review=json.loads((out/'review.json').read_text())
    for key,path in {'plan_sha256':CONFIG/'plan.json','methods_sha256':METHODS,
        'producer_sha256':ROOT/'scripts/settlement_vidarbha_transfer.py'}.items():
        if result[key]!=sha(path):raise ValueError('Stale transfer identity: '+key)
    for path,digest in {**result['parent_artifacts'],**result['input_sources']}.items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed transfer parent/input: '+path)
    if review['status']!='passed' or review['source_result_sha256']!=sha(out/'results.json') or review['reviewer_sha256']!=sha(ROOT/'scripts/review_settlement_vidarbha_transfer.py'):
        raise ValueError('Stale transfer review')
    replay=json.loads((out/'replay.json').read_text())
    if replay['status']!='passed' or not replay['results_byte_exact'] or result['adopt']:raise ValueError('Replay/adoption gate failed')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'results.json','vidarbha_transfer.json'),(out/'review.json','vidarbha_transfer_review.json'),
        (out/'replay.json','vidarbha_transfer_replay.json'),(CONFIG/'plan.json','vidarbha_transfer_plan.json'),
        (METHODS,'vidarbha_survey_methods.json'),(ROOT/'output/vidarbha_survey_20261111/preparation.json','vidarbha_survey_preparation.json'),
        (ROOT/'output/vidarbha_survey_20261111/review.json','vidarbha_survey_review.json')]:shutil.copyfile(src,data/name)
    guard=result['guard'];rows=[]
    for grid,g in result['grids'].items():
        metrics=[r for r in g['metrics'] if r['cohort']=='EH-S_yes' and r['offset']=='central']
        for r in metrics:
            lead=sum(r['captures'][f'lead_L450_seed{s}']['10'] for s in [1,7,19,43,97])/5
            rows.append(f'<tr><th>{grid} km · {r["zone"]}</th><td>{r["distinct_cells"]}</td>'
                f'<td>{r["opportunity"]["fixed_L800"]["mean_percentile"]:.3f} / {r["opportunity"]["lead_L450"]["mean_percentile"]:.3f}</td>'
                f'<td>{100*r["captures"]["fixed_L800_seed1"]["10"]:.1f}% / {100*lead:.1f}%</td></tr>')
    status='Passed' if guard['diagnostic_guard_pass'] else 'Failed'
    section='''<!--vidarbha-transfer-start--><section><h2>New geographic check: central India</h2><details id="vidarbha-transfer" class="panel"><summary>Frozen settlement transfer · '''+status.lower()+''' diagnostic · no map adoption</summary>
<p>The primary 2016 Vidarbha field survey supplies a new regional test of the frozen Han/Rome placement parameters. Its targeted, partial coverage supports known-site comparisons; unrecorded land is not absence. Broad Satavahana phase evidence is not exact AD200 occupation or a city census.</p>
'''+f'<p id="vidarbha-verdict"><strong>{status} the predeclared diagnostic.</strong> Primary 3 km opportunity rank changes by {guard["rank_delta"]:+.4f}, but known-site capture within 10 km changes by {100*guard["capture_delta"]:+.2f} percentage points against the declared −10 point margin. All 24 placement constraints pass. The adaptive lead averages {100*guard["lead_mean10km_capture"]:.2f}% capture across five fixed seeds, versus {100*guard["mean10km_capture"]["fixed_L800_seed1"]:.2f}% for the selected fixed-spacing control. These are engineering margins, not confidence bounds.</p>'+'''
<div class="table"><table id="vidarbha-transfer-results"><thead><tr><th>Grid and frame</th><th>Distinct source cells</th><th>Mean local percentile · control / lead</th><th>10 km known-site capture · control / lead</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>The primary cohort retains 74 records as 53 cell–frame units. Across all 134 settlement records, 13 outside their assigned nominal frame remain excluded without reassignment. All three cohorts, nine offsets, five seeds, the no-history ablation and the coarse 9 km grid remain in the download. No best seed or grid is selected. Opportunity mass is not an exact sampler inclusion probability or resident density.</p>
<img src="../../reports/figures/settlement_vidarbha_transfer_20261111.png" width="1950" height="870" alt="The frozen lead improves local opportunity ranks slightly but fails the declared ten kilometre capture margin; all seeds shown.">
<img src="../../reports/figures/settlement_vidarbha_geography_20261111.png" width="1950" height="900" alt="Model-only central India opportunity and generated centres: the stronger historical prior shifts placement northwest.">
<p>Source preparation and comparison rules were frozen before model lookup. This survey is now spent for tuning. Existing global climate/density predictors and earlier broad India city work were already exposed; the prospective claim applies only to this frozen parameter comparison. Independent review reconstructs 2,412 matches, 7,290 scalar metrics and all 24 placement constraints; a fresh replay is exact. No fantasy population, food, tracks, staffing or control defaults change.</p>
<p>Next: audit counts and resident sizes separately from rural-site locations, then fit/test the shared-budget fantasy rebuild. Detailed institutions remain on the later roadmap; they do not block every first-map improvement.</p>
<p><a href="../../reports/SETTLEMENT_VIDARBHA_TRANSFER_20261111.md">Methods, limitations and next step</a> · <a href="../../reports/VIDARBHA_SURVEY_20261111.md">Primary survey preparation</a> · <a href="https://doi.org/10.5281/zenodo.3670055">Abbas, Toraskar &amp; Hawkes 2020 · source CC BY 4.0</a> · <a href="https://doi.org/10.5334/joad.61">Survey methods paper</a> · <a href="data/vidarbha_transfer.json" download>Every metric and constraint</a> · <a href="data/vidarbha_transfer_review.json" download>Independent review</a> · <a href="data/vidarbha_transfer_replay.json" download>Fresh replay</a> · <a href="data/vidarbha_transfer_plan.json" download>Protocol before prediction scores</a> · <a href="data/vidarbha_survey_methods.json" download>Published frames and methods</a> · <a href="data/vidarbha_survey_preparation.json" download>Source joins and phase preparation</a> · <a href="data/vidarbha_survey_review.json" download>Source review</a></p></details></section><!--vidarbha-transfer-end-->'''
    html=page.read_text();pattern=r'<!--vidarbha-transfer-start-->[\s\S]*?<!--vidarbha-transfer-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--institution-scope-start-->'
        if marker not in html:raise ValueError('Publish scope comparison first')
        html=html.replace(marker,section+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';usage=json.loads(path.read_text())
    entries=[dict(id='vidarbha_field_survey2016',status='exposed_frozen_regional_transfer_failed_guard',
        evidence='reports/SETTLEMENT_VIDARBHA_TRANSFER_20261111.md',
        note='Primary2016field survey Zenodo3670055,v2;134exactsettlementjoins,74inside-frame EH-Srecords/53primarycell-frameunits. Frozenparameters scored prospectively;source now spent. Partialtargetedcoverage,notcensusabsence;no adoption. Separate from failed3667657catalogue.'),
        dict(id='reba2016_modelski_ad100_200',status='exposed_historical_city_checks_20261023',evidence='reports/POPULATION_20261023.md',
        note='Exposure register corrected after finding prior great_cities_check.py and population_density_research_20261023.md usage;absence from old register was not evidence of freshness. Includes broadIndia city work. No new untouched transfer claim.')]
    for entry in entries:usage['datasets']=[e for e in usage['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,usage);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published frozen transfer failure, all sensitivities, source exposure and unchanged model status.')


if __name__=='__main__':main()
