"""Refresh the current Earth overview for r59 (atlas world on r59w) while retaining labelled historical studies."""
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
PARTS = ['dev31', 'retired_a', 'retired_b', 'retired_c', 'tropical_t', 'sealed_r', 'sealed_S18', 'sealed_U18']


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from check_v22_release_inputs import verify_correction
    physics = ROOT/'calibration/local_accuracy_20261023/r59_params.json'
    world = ROOT/'calibration/local_accuracy_20261023/r59w_params.json'
    cal = ROOT/'calibration/earth_correction_r59_20261128'
    adopted = json.loads((ROOT/'calibration/local_accuracy_20261023/r59_adoption.json').read_text())
    assert adopted['adopted'] == 'r59'
    assert hashlib.sha256(physics.read_bytes()).hexdigest() == adopted['params_sha256']
    correction = {name: json.loads((cal/name/'protocol.json').read_text())['meta'] for name in ['temperature', 'rain_pattern']}
    hashes = {name: verify_correction(cal/name, world) for name in correction}
    source = ROOT/adopted['validation']; regions = {}; paths = []
    for part in PARTS:
        path = source/f'candidate_{part}'/'summary.json'; paths.append(path); summary = json.loads(path.read_text())
        assert summary['complete']
        for name, row in summary['regions'].items():
            assert name not in regions and row['status'] == 'passed' and row['numerics']['all_checks_passed']
            regions[name] = row
    n = len(regions)
    raw = dict(regions=n, monthly_temperature_mae_C=sum(r['temperature']['monthly_mae_C'] for r in regions.values())/n,
               rain_loss=sum(r['rain']['loss'] for r in regions.values())/n)
    cv31 = dict(regions=31, raw_temperature_mae_C=correction['temperature']['raw_monthly_mae_C'],
                corrected_temperature_mae_C=correction['temperature']['held_out_monthly_mae_C'],
                raw_rain_loss=correction['rain_pattern']['raw_loss'], corrected_rain_loss=correction['rain_pattern']['held_out_loss'])
    data = ROOT/'atlases/climate_accuracy/data'; data.mkdir(parents=True, exist_ok=True)
    edge = json.loads((ROOT/'calibration/map_world_r58_planet/edge_screen.json').read_text())
    result = dict(profile='r59', world_profile='r59w', date='2026-11-28', raw_development=raw, correction_cluster_cv31=cv31,
                  adoption=adopted, world_edge_forcing=edge, recovered_model_sha256=hashes,
                  source_files_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in [*paths, physics, world, ROOT/'output/earth_correction_r59_20261128/training_receipt.json']},
                  interpretation='r59 adoption evidence (policy v6 against r58: dev6, fine28, sealed AA) plus corrections retrained for r59w '
                                 '(the atlas physics) with the unchanged recipe. Raw and correction pools differ; never subtract them as a paired improvement.')
    (data/'current_earth_r59.json').write_text(json.dumps(result, indent=2)+'\n')
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), layout='constrained'); fig.patch.set_facecolor('#f1f3ef')
    previous = ROOT/'calibration/earth_correction_r51_20261122'
    for ax, name, raw_key, cv_key, metric in [(axes[0], 'temperature', 'raw_monthly_mae_C', 'held_out_monthly_mae_C', 'Monthly temperature MAE · °C'),
                                              (axes[1], 'rain_pattern', 'raw_loss', 'held_out_loss', 'Rain loss · lower is better')]:
        old = json.loads((previous/name/'protocol.json').read_text())['meta']; new = correction[name]; x = np.arange(2)
        ax.bar(x-.17, [old[raw_key], new[raw_key]], .34, label='Raw physics', color='#ad7c54')
        ax.bar(x+.17, [old[cv_key], new[cv_key]], .34, label='Cluster CV correction', color='#367a71')
        ax.set(xticks=x, xticklabels=['r51', 'r59w'], ylabel=metric)
        for i, v in enumerate([old[cv_key], new[cv_key]]): ax.text(i+.17, v, f'{v:.4f}', ha='center', va='bottom', fontsize=9)
        ax.set_ylim(0, max(old[raw_key], new[raw_key])*1.18); ax.grid(axis='y', alpha=.15); ax.legend(fontsize=8)
    fig.suptitle('Earth correction models retrained for r59w · the same 31-region study', fontsize=13)
    fig.supxlabel('Fixed recipe; leave whole clusters out; weights selected within that CV.\nDevelopment data, not a blind test. Corrected changes include refitting the correction.', fontsize=9)
    fig.savefig(data/'r59_corrections.png', dpi=145); plt.close(fig)
    g = adopted['gates']
    section = f'''<!--current-earth-overview-start--><h2>Current adopted raw Earth physics: r59</h2>
<p>On the {n}-region development and spent-check pool, monthly temperature MAE is <strong>{raw['monthly_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{raw['rain_loss']:.5f}</strong>. At adoption, combined error was {100*(1-g['dev6']['S97']):.1f}% below r58 over 97 regions (90 % interval {100*(1-g['dev6']['q95']):.1f}–{100*(1-g['dev6']['q05']):.1f}%), the paired 28 km check passed (S {g['fine28']['S28']:.4f}), and then-unseen set AA passed (combined error {100*(1-g['sealed_AA']['S']):.2f}% below r58). r59 lets the warm western-boundary currents fade toward the equator as on Earth: the sea off Somalia had run 4-6 °C too warm in July. These are regional checks, not a global accuracy percentage.</p>
<p>The atlas world has no observations at its edges, so it runs <strong>r59w</strong>: identical except that edges take the globe's land-mean column water at their latitude. On Earth that costs {100*(edge['zonal']['S97']-1):.1f}% of r58's skill (switching edge water off would cost {100*(edge['off']['S97']-1):.1f}%). The temperature and rainfall corrections were retrained for r59w with the unchanged recipe: <strong>{cv31['corrected_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{cv31['corrected_rain_loss']:.5f}</strong> on the 31-region study with whole clusters held out (raw {cv31['raw_temperature_mae_C']:.4f} °C / {cv31['raw_rain_loss']:.5f}).</p>
<figure><img src="data/r59_corrections.png" alt="Raw and cluster-cross-validated errors for r51 and r59w on the same 31 development regions"><figcaption>Corrections for r51 and r59w on the same development pool, whole clusters held out.</figcaption></figure>
<p>Known open problems: hot dry land 2–3 °C too cold, Somalia still too wet (no Somali jet), the West African rain season too long once the Gulf of Guinea is corrected, southern maritime coasts too cold, spring timing, and dry interiors (Kalahari, inland Australia).</p>
<p><a href="data/current_earth_r59.json" download>Current measurements and provenance</a> · <a href="../../reports/RELEASE_R59_20261128.md">r59 release report</a></p>
<h2>Historical r39 benchmark · 27 October 2026</h2><p class="note">The cards and audit immediately below retain their original r39 measurements and sample definitions. They are not current r59 city accuracy.</p><!--current-earth-overview-end-->'''
    page = ROOT/'atlases/climate_accuracy/index.html'; html = page.read_text()
    if '<!--current-earth-overview-start-->' not in html: raise ValueError('Missing current/historical overview boundary')
    html = re.sub(r'<!--current-earth-overview-start-->.*?<!--current-earth-overview-end-->', lambda m: section, html, count=1, flags=re.S)
    html = re.sub(r'Updated \d+ \w+ \d{4} · current results and historical benchmarks', 'Updated 28 November 2026 · current results and historical benchmarks', html, count=1)
    page.write_text(html)
    print('Published current r59 overview; historical experiments retained with their original labels')


if __name__ == '__main__': main()
