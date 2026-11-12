"""Publish the reviewed mixed-period diagnostic in the normal evidence atlas."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write


def main():
    out = ROOT / 'output/settlement_housing_diagnostic_20261112'
    result = json.loads((out / 'results.json').read_text())
    review = json.loads((out / 'review.json').read_text())
    replay = json.loads((out / 'replay.json').read_text())
    assert review['status'] == replay['status'] == 'passed'
    assert review['results_sha256'] == replay['results_sha256'] == sha(out / 'results.json')
    assert not result['adopt'] and result['AD150_size_fit_eligible'] == 0
    for path, digest in {**result['sources_sha256'], **result['unchanged_sha256']}.items():
        if sha(ROOT / path) != digest:
            raise ValueError('Changed reviewed input: ' + path)
    page = ROOT / 'atlases/earth_evidence/index.html'; data = page.parent / 'data'
    for name in ('results', 'review', 'replay'):
        shutil.copyfile(out / (name + '.json'), data / ('housing_density_' + name + '.json'))
    shutil.copyfile(ROOT / 'calibration/settlement_housing_diagnostic_20261112/plan.json', data / 'housing_density_plan.json')
    labels = {'constant': 'Constant density', 'area': 'Area', 'area_coverage': 'Area + coverage'}
    lines = []
    for cohort in result['cohorts']:
        label = 'All 50' if cohort['id'] == 'all' else 'Coverage ≥1%'
        for model in cohort.get('models', []):
            m = model['metrics']
            lines.append(f'<tr><td>{label}</td><td>{labels[model["id"]]}</td><td>{m["mean_absolute_log_error"]:.3f}</td>'
                         f'<td>{m["median_multiplicative_error"]:.3f}</td></tr>')
    section = '''<!--housing-density-start--><section><h2>Housing density: a blocked development comparison</h2>
<details id="housing-density" class="panel"><summary>50 cities · held-province density comparison · no resident-size adoption</summary>
<p>Predicting encountered properties per investigated hectare avoids putting whole-city area into both the target and its predictor. All coefficients are fitted without the test province. Area lowers average log error from 0.493 to 0.451, but slightly worsens median error; 15 province folds improve and eight worsen. Coverage effects change with the sampling cohort.</p>
<div class="table"><table><thead><tr><th>Cohort</th><th>Model</th><th>Mean absolute log error</th><th>Median error factor</th></tr></thead><tbody>''' + ''.join(lines) + '''</tbody></table></div>
<p>The ≥1% coverage cohort contains 26 cities; its scores refer to different targets. The ≥10% cohort retains 11 cities but is unscored under the prior minimum-training rule. Household scenarios change units, without adding observations. All city and province losses remain in the downloads.</p>
<img src="../../reports/figures/settlement_housing_diagnostic_20261112.png" alt="Held-province housing density predictions and average errors for three declared models">
<p><strong>No AD150 resident-size target qualifies.</strong> Selected mixed-period samples, coarse province blocking and unknown sample phases, detection, extent and representativeness prevent census or transfer claims. The coverage predictor shares the investigated-area denominator with density. This development comparison changes no allocator request or map default.</p>
<p>Source: Ortman and Hanson (2023), <a href="https://doi.org/10.1017/S0068113X23000375">Estimating the ‘Missing’ Houses of Silchester</a>, Table 2, CC BY 4.0. City catalogue joins remain uncertified.</p>
<p><a href="../../reports/SETTLEMENT_HOUSING_DIAGNOSTIC_20261112.md">Methods and limits</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Whole-programme plan</a> · <a href="data/housing_density_results.json" download>All folds and predictions</a> · <a href="data/housing_density_review.json" download>Independent scalar review</a> · <a href="data/housing_density_replay.json" download>Fresh replay</a> · <a href="data/housing_density_plan.json" download>Prior declaration</a> · <a href="data/settlement_sizes_source.csv" download>Attributed source table</a></p>
</details></section><!--housing-density-end-->'''
    html = page.read_text(); pattern = r'<!--housing-density-start-->[\s\S]*?<!--housing-density-end-->'
    if re.search(pattern, html):
        html = re.sub(pattern, lambda match: section, html)
    else:
        marker = '<!--settlement-sizes-start-->'
        if marker not in html:
            raise ValueError('Publish prior housing measurement evidence first')
        html = html.replace(marker, section + '\n' + marker, 1)
    page.write_text(html)
    registry = ROOT / 'calibration/earth_components_20261105/dataset_usage.json'
    usage = json.loads(registry.read_text())
    entry = dict(id='settlement_housing_diagnostic_20261112', status='exposed_mixed_period_density_development_scored',
        evidence='reports/SETTLEMENT_HOUSING_DIAGNOSTIC_20261112.md',
        note='50 prior housing observations;province-blocked density scores,coverage sensitivities,allphase/extent/sampling gates retained. NoAD150labels,prospective transfer,allocator fit or adoption.')
    usage['datasets'] = [r for r in usage['datasets'] if r['id'] != entry['id']] + [entry]
    for row in usage['datasets']:
        if row['id'] == 'settlement_size_evidence_20261112':
            row['note'] += ('' if 'downstream' in row['note'] else ' Same source now scored in downstream settlement_housing_diagnostic_20261112;preparation checkpoint remains historical.')
    write(registry, usage); shutil.copyfile(registry, data / 'dataset_usage.json')
    write(out / 'presentation.json', dict(status='published', page_sha256=sha(page), publisher_sha256=sha(Path(__file__))))
    print('Published reviewed housing density diagnostic; no map defaults changed.')


if __name__ == '__main__':
    main()
