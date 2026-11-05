"""Add the historical crop result to the normal atlas evidence page."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import shutil
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from scripts.check_earth_yields import check
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    origin = ROOT / 'output/low_input_yields_20261105'; data = ROOT / 'atlases/earth_evidence/data/yields'
    data.mkdir(parents=True, exist_ok=True)
    replay = check(origin)
    if json.loads((origin / 'replay.json').read_text())['status'] != 'passed': raise ValueError('Missing successful source replay')
    result = json.loads((origin / 'evaluation.json').read_text()); chosen = json.loads((origin / 'selection.json').read_text())
    cases = json.loads(gzip.decompress((origin / 'cases.json.gz').read_bytes()))['cases']
    for name in ['evaluation.json', 'selection.json', 'preparation.json', 'replay.json', 'cases.json.gz']:
        shutil.copyfile(origin / name, data / name)
    for name in ['plan.json', 'amendment.json', 'sources.json']:
        shutil.copyfile(ROOT / 'calibration/low_input_yields_20261105' / name, data / name)
    fields = ['case_id', 'year', 'split', 'stratum', 'area_ha', 'observed_t_ha', 'baseline_t_ha', 'fitted_t_ha', 'temperature_missing_days', 'rain_missing_days']
    with (data / 'observations.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for c in cases:
            writer.writerow({k: chosen['scale'] * c['baseline_t_ha'] if k == 'fitted_t_ha' else c[k] for k in fields})
    primary = [c for c in cases if c['stratum'] == 'unmanured_plot3']
    test = [c for c in primary if c['split'] == 'evaluation']
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.2), layout='constrained')
    fig.patch.set_facecolor('#f1f3ef'); actual = '#263e48'; baseline = '#ad7c54'; fitted = '#367a71'
    ax = axes[0, 0]
    for split, label in [('training', 'Observed harvest'), ('evaluation', 'Observed harvest')]:
        rows = [c for c in primary if c['split'] == split]
        ax.plot([c['year'] for c in rows], [c['observed_t_ha'] for c in rows], 'o-', color=actual, lw=1, ms=3, label=label if split == 'training' else None)
    ax.plot([c['year'] for c in primary], [c['baseline_t_ha'] for c in primary], color=baseline, lw=1.2, label='Current response')
    ax.plot([c['year'] for c in primary], [chosen['scale'] * c['baseline_t_ha'] for c in primary], color=fitted, lw=1.2, label='Training-fitted scale')
    ax.axvline(1900.5, color='#899596', ls='--', lw=1); ax.set(title='Unfertilized plot 3 · training left / test right', ylabel='Harvested grain · t/ha', xlabel='Harvest year'); ax.legend(fontsize=8, ncol=2)
    ax = axes[0, 1]; observed = [c['observed_t_ha'] for c in test]; prediction = [chosen['scale'] * c['baseline_t_ha'] for c in test]
    points = ax.scatter(observed, prediction, c=[c['year'] for c in test], cmap='viridis', s=30)
    fig.colorbar(points, ax=ax, label='Harvest year', shrink=.8)
    ax.plot([0, 1.6], [0, 1.6], ls='--', color='#899596', lw=1)
    ax.set(title=f'Test years · r = {result["candidate"]["Pearson_r"]:.2f}', xlabel='Observed · t/ha', ylabel='Fitted-scale prediction · t/ha', xlim=(0, 1.6), ylim=(0, 1.6))
    ax = axes[1, 0]; cal = result['calendar']
    ax.barh(['Representable', 'Length rejected', 'Temperature rejected'], [cal['representable'], cal['failures'].get('length', 0), cal['failures'].get('temperature', 0)], color=[fitted, baseline, actual])
    ax.set(xlim=(0, 25), xlabel='Recorded seasons / 25 · failure categories overlap', title='Do existing rules represent observed winter wheat?')
    for i, value in enumerate([cal['representable'], cal['failures'].get('length', 0), cal['failures'].get('temperature', 0)]): ax.text(value + .3, i, str(value), va='center')
    ax = axes[1, 1]; names = ['unmanured_plot3', 'fym_only', 'mineral_only']; labels = ['No inputs · plot3', '35t FYM/ha/year', 'Mineral treatments']
    means = [result['evaluation_strata'][s]['baseline']['observed_mean'] for s in names]
    ax.bar(labels, means, color=[actual, fitted, baseline]); ax.axhline(result['baseline']['predicted_mean'], color=baseline, ls='--', label='Current response, no nutrient process')
    ax.set(title='Management strata kept separate · test means', ylabel='Harvested grain · t/ha'); ax.tick_params(axis='x', labelsize=8); ax.legend(fontsize=8)
    for ax in axes.flat: ax.grid(axis='y', alpha=.15)
    fig.suptitle('Historical wheat benchmark · mean-level fit fails annual-skill checks', fontsize=14)
    fig.supxlabel('Rothamsted/e-RA · CC BY4.0 · 20 training years, 25 test years at ONE English site.\nObserved monthly weather; crop potential is not actual sowing management. No AD200 defaults adopted.', fontsize=9)
    fig.savefig(data / 'historical_wheat.png', dpi=145); plt.close(fig)
    shutil.copyfile(data / 'historical_wheat.png', origin / 'historical_wheat.png')
    b, c = result['baseline'], result['candidate']
    section = f'''<!-- historical-yield-start -->
<section aria-labelledby="yield-h"><h2 id="yield-h">Historical wheat: the average is easier than the seasons</h2><div class="panel">
<p><strong id="yield-verdict">Failed annual-skill checks. No production change.</strong> Broadbalk's unfertilized plot3 supplies actual harvested wheat yields, matched to observed Rothamsted weather. Twenty years (1879–1900) fit one yield multiplier; 25 later years (1901–1925) test it. This is temporal transfer at one continuously cropped English site, not a global or AD200 validation.</p>
<div class="table"><table id="yield-benchmark"><thead><tr><th>Test: unfertilized wheat</th><th>Current response</th><th>Training-fitted scale</th></tr></thead><tbody>
<tr><td>Mean absolute log10 error</td><td>{b['MAE_log10']:.3f}</td><td>{c['MAE_log10']:.3f}</td></tr>
<tr><td>RMSE · harvested t/ha</td><td>{b['RMSE_t_ha']:.3f}</td><td>{c['RMSE_t_ha']:.3f}</td></tr>
<tr><td>Pearson correlation</td><td>{b['Pearson_r']:.2f}</td><td>{c['Pearson_r']:.2f}</td></tr>
<tr><td>RMSE skill vs constant training mean</td><td>{b['RMSE_skill_vs_training_mean']:.1%}</td><td>{c['RMSE_skill_vs_training_mean']:.1%}</td></tr></tbody></table></div>
<p>The selected multiplier is {chosen['scale']:.3f}. Log error improves {(1-c['MAE_log10']/b['MAE_log10']):.1%}, but predictions vary in the wrong direction and remain worse than the training-period mean. Multiplying yields cannot repair that response. A complete-temperature-record check (23 test years, no refit) reaches the same conclusion.</p>
<img src="data/yields/historical_wheat.png" alt="Historical wheat timeline, negative test correlation, incompatible winter seasons and separate management strata" loading="lazy">
<p><strong>Winter seasons expose a structural limit:</strong> only {cal['representable']} of {cal['records']} observed sowing-to-harvest seasons fit the current wheat length/temperature rules. {cal['failures']['length']} exceed the allowed season length; {cal['failures']['temperature']} fail the temperature window (overlapping groups). This monthly audit does not establish which missing process caused the yield errors.</p>
<p><strong>Management matters:</strong> the test averages are {means[0]:.2f}t/ha without inputs and {means[1]:.2f}t/ha with 35t/ha/year of manure. Intensive organic manure is not generic ancient low-input farming. Nutrient depletion, weeds, cultivar changes and weather hazards are not yet identified by this experiment.</p>
<p class="note">The initial complete-weather rule left too few training years. A disclosed amendment, frozen before numerical yield scoring, accepts published monthly means missing at most one daily temperature reading and retains the complete-record check. An impossible 1883 sowing date is excluded without silently repairing the source. Rain gaps are flagged; trace-only bounds are conditional. Woburn wheat/barley yields remain unscored until matching local weather is obtained.</p>
<p><a href="../../reports/HISTORICAL_WHEAT_20261105.md">Methods and next physics test</a> · <a href="data/yields/observations.csv" download>Yield observations CSV</a> · <a href="data/yields/cases.json.gz" download>Replay packet</a> · <a href="data/yields/evaluation.json" download>Complete scores</a> · <a href="data/yields/plan.json" download>Protocol</a> · <a href="data/yields/amendment.json" download>Pre-scoring amendment</a> · <a href="data/yields/selection.json" download>Frozen selection</a> · <a href="data/yields/sources.json" download>Sources and licence</a> · <a href="data/yields/replay.json" download>Replay audit</a></p>
<p class="note">Source: <a href="https://doi.org/10.23637/rbk1-1796346264-1">Rothamsted Research (2021), Broadbalk annual yields1852–1925</a>; <a href="https://doi.org/10.23637/rmsMAAirTemp1878-2024-01">Perryman &amp; Scott (2025), temperatures</a>; <a href="https://doi.org/10.23637/rmsTMArain1853-2024-01">Perryman &amp; Scott (2025), rain</a>. Electronic Rothamsted Archive, Rothamsted Research; CC BY4.0. Our processing and interpretation are not endorsed by the source authors.</p>
</div></section><!-- historical-yield-end -->'''
    page = ROOT / 'atlases/earth_evidence/index.html'; html = page.read_text()
    if '<!-- historical-yield-start -->' in html:
        a = html.index('<!-- historical-yield-start -->'); b = html.index('<!-- historical-yield-end -->') + len('<!-- historical-yield-end -->')
        html = html[:a] + section + html[b:]
    else:
        html = html.replace('</header>', '</header>\n' + section, 1)
    page.write_text(html)
    (origin / 'presentation.json').write_text(json.dumps(dict(status='published',page='atlases/earth_evidence/index.html',
        publisher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), public_packet_checked=True), indent=2) + '\n')
    print('Published historical wheat evidence; failed candidate retained as evidence, no production overrides')


if __name__ == '__main__': main()
