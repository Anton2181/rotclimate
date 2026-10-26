"""Publish the controlled moisture-source audit as a portable atlas companion."""
from pathlib import Path
from dataclasses import asdict
import html
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from local_benchmark_protocol import file_hash, write_json
from rotclimate.config import Params

AUDIT = ROOT/'output/moisture_sources_20261026'
DEST = ROOT/'atlases/climate_accuracy'
NAMES = ['north_india', 'iran_plateau', 'iberia']
LABELS = ['North India', 'Iran plateau', 'Iberia']


def verified_rows():
    review = json.loads((AUDIT/'review.json').read_text())
    protocol = json.loads((AUDIT/'protocol.json').read_text())
    if not review['complete'] or review['physics_or_atlas_adoption']:
        raise ValueError('Need the completed diagnostic, without climate adoption')
    for name, expected in protocol['source_hashes'].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError('Audit inputs changed: '+name)
    rows = {row['region']: row for row in review['records']}
    if set(rows) != set(NAMES):
        raise ValueError('Unexpected audit regions')
    for name, row in rows.items():
        if (row['identity'] != review['identity'] or row['status'] != 'passed'
                or not row['exact_climate_control'] or not row['numerics']['all_checks_passed']
                or file_hash(AUDIT/f'{name}.npz') != row['arrays_sha256']):
            raise ValueError('Incomplete or changed audit: '+name)
    return rows


def plots(rows, data):
    fig, axes = plt.subplots(2, 3, figsize=(12.8, 7.4), constrained_layout=True,
                             gridspec_kw=dict(height_ratios=[1, 1.25]))
    fields = ['evaporation', 'convergence_import', 'advection', 'diffusion', 'storm_exchange', 'column_drying']
    labels = ['Evaporation', 'Convergence import', 'Mean-wind transport', 'Diffusion', 'Storm exchange', 'Column drying']
    for column, (name, label) in enumerate(zip(NAMES, LABELS)):
        monthly = rows[name]['summaries']['all_land']['monthly']
        ax = axes[0, column]
        ax.plot(monthly['observed'], color='#222222', label='Observed', marker='.', lw=2)
        ax.plot(monthly['simulated'], color='#2a7098', label='r39 model', marker='.', lw=2)
        ax.set(title=label, xticks=np.arange(12), xticklabels=list('JFMAMJJASOND'), ylabel='Rain (mm / model month)')
        ax.grid(axis='y', alpha=.15)
        if column == 0:
            ax.legend(frameon=False, fontsize=9)
        ax = axes[1, column]
        values = np.array([monthly[key][6] for key in fields])
        ax.barh(np.arange(6), values, color=np.where(values >= 0, '#418c9e', '#be7046'))
        ax.axvline(0, color='#333333', lw=.7)
        for i, value in enumerate(values):
            ax.annotate(f'{value:+.1f}', (value, i), xytext=(3 if value >= 0 else -3, 0),
                        textcoords='offset points', ha='left' if value >= 0 else 'right', va='center', fontsize=9)
        ax.set(yticks=np.arange(6), yticklabels=labels if column == 0 else ['']*6,
               xlabel='July source (mm / model month)')
        ax.set_title(f'July: sum {values.sum():.1f} · observed {monthly["observed"][6]:.1f}', fontsize=11)
        ax.invert_yaxis()
        ax.margins(x=.2)
        ax.grid(axis='x', alpha=.12)
    fig.suptitle('Where does the rain water come from?', fontsize=17)
    fig.supxlabel('Unchanged r39; 56 km, reused regions, exact archived climate controls. Local nonconservative equation terms;\n'
                  'convergence import is parameterized. Column drying includes prescribed remote-monsoon drying. Model month = 365/12 days.', fontsize=9)
    fig.savefig(data/'rainfall_sources.png', dpi=150)
    plt.close(fig)

    with np.load(AUDIT/'north_india.npz') as arrays:
        valid = arrays['valid']
        elevation = arrays['elev']
        fields = {key: arrays[key][6].copy() for key in
                  ['observed', 'simulated', 'convergence_import', 'evaporation', 'storm_exchange', 'column_drying']}
    rain_max = max(300., float(np.percentile(fields['observed'][valid], 98)),
                   float(np.percentile(fields['simulated'][valid], 98)))
    source_max = max(100., *(float(np.percentile(np.abs(fields[key][valid]), 98))
                            for key in ['convergence_import', 'evaporation', 'storm_exchange', 'column_drying']))
    fig, axes = plt.subplots(2, 3, figsize=(12.8, 6.8), constrained_layout=True)
    titles = ['Observed July rain', 'r39 July rain', 'Convergence import',
              'Surface evaporation', 'Storm exchange', 'Column drying']
    for ax, (key, values), title in zip(axes.flat, fields.items(), titles):
        is_rain = key in ['observed', 'simulated']
        image = ax.imshow(np.where(valid, values, np.nan), interpolation='nearest',
                          cmap='YlGnBu' if is_rain else 'BrBG',
                          vmin=0 if is_rain else -source_max, vmax=rain_max if is_rain else source_max)
        ax.set_facecolor('#e5eaeb')
        if (elevation[valid] < 1000).any() and (elevation[valid] >= 1000).any():
            ax.contour(np.where(valid, elevation, np.nan), levels=[1000], colors='#6d6d6d', linewidths=.5)
        ax.set_title(title, fontsize=12)
        ax.set_axis_off()
        fig.colorbar(image, ax=ax, shrink=.7, label='mm / model month', extend='max' if is_rain else 'both')
    fig.suptitle('North India: missing monsoon moisture at the same locations', fontsize=16)
    fig.supxlabel('56 km cells; July, unchanged r39; grey contour = 1000 m. Rain maps share a scale; source maps share a signed scale.\n'
                  'Shared 98th-percentile absolute source range / 98th-percentile rain range clipped for readability. Reused regional test, not a global budget.', fontsize=9)
    fig.savefig(data/'north_india_july.png', dpi=150)
    plt.close(fig)


def main():
    rows = verified_rows()
    data = DEST/'data'
    data.mkdir(parents=True, exist_ok=True)
    plots(rows, data)
    archive = ROOT/'output/constrained_blend_20261025'
    old_review = json.loads((archive/'review.json').read_text())
    if not old_review['eligible_for_adoption'] or old_review['selected'] != 'g0.9995_a1':
        raise ValueError('Unexpected adopted Earth calibration')
    historical = json.loads((archive/'development/g0.9995_a1/protocol.json').read_text())['params']
    if json.dumps(asdict(Params(**historical)), sort_keys=True) != json.dumps(
            asdict(Params.from_json(ROOT/'calibration/local_accuracy_20261023/r39_params.json')), sort_keys=True):
        raise ValueError('Historical accuracy and current physical profile differ')
    cities = json.loads((archive/'city_rain.json').read_text())
    city_reference = cities['output/constrained_blend_20261025/reference']['model']
    city_current = cities['output/constrained_blend_20261025/development/g0.9995_a1']['model']
    development = old_review['development']['g0.9995_a1']
    summary = dict(date='2026-10-26', physics_profile='r39', published_earth_atlas_profile='r38',
                   earth_development=development, cities=dict(r38=city_reference, r39=city_current),
                   moisture_audit={name: {key: rows[name][key] for key in ['rain', 'summaries', 'source_reconstruction_max_mm_month']}
                                   for name in NAMES},
                   scope='Modern observed Earth normals, conditional regional forcing, reused development regions. '
                         'Not measured accuracy of the fantasy map; not historical 200 AD weather or a population validation.',
                   sources_sha256={str(path.relative_to(ROOT)): file_hash(path) for path in
                                   [AUDIT/'review.json', AUDIT/'protocol.json', archive/'review.json', archive/'city_rain.json',
                                    archive/'development/g0.9995_a1/protocol.json', Path(__file__)]},
                   images_sha256={name: file_hash(data/name) for name in ['rainfall_sources.png', 'north_india_july.png']})
    write_json(data/'summary.json', summary)
    table = ''.join(f'<tr><th scope="row">{html.escape(label)}</th><td>{rows[name]["rain"]["sim_mean_annual_mm"]:.0f}</td>'
                    f'<td>{rows[name]["rain"]["obs_mean_annual_mm"]:.0f}</td></tr>' for name, label in zip(NAMES, LABELS))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Climate accuracy and joint fit · Rotclimate</title><style>
:root{color-scheme:light dark;--paper:#eef1f1;--plate:#f8faf9;--ink:#1b262c;--soft:#4b5a62;--rule:#c9d2d4;--link:#805616}
@media(prefers-color-scheme:dark){:root{--paper:#12191d;--plate:#182126;--ink:#e3e9eb;--soft:#afbec5;--rule:#2c3a41;--link:#e0b462}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.6 system-ui,sans-serif}
main{max-width:1160px;margin:auto;padding:24px 16px 64px}a{color:var(--link);text-underline-offset:3px}
h1,h2{font-family:Georgia,serif;line-height:1.2}h1{font-size:clamp(2rem,5vw,3rem)}p{max-width:80ch}
.note{font-size:.9rem;color:var(--soft)}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.card,figure,.table{background:var(--plate);border:1px solid var(--rule);border-radius:6px;padding:16px}
.number{display:block;font:2rem Georgia,serif}.card small{display:block;color:var(--soft)}figure{margin:24px 0}
img{display:block;width:100%;height:auto;background:white}figcaption{padding-top:12px;font-size:.9rem;color:var(--soft)}
.table{overflow-x:auto;padding:0}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px 16px;border-bottom:1px solid var(--rule)}
tr:last-child td,tr:last-child th{border-bottom:0}@media(max-width:620px){.cards{grid-template-columns:1fr}body{font-size:16px}figure{padding:8px}}
</style><main><nav aria-label="Atlas navigation"><a href="../">All atlases</a> · <a href="../earth_fit/">Earth atlas</a> · <a href="data/summary.json" download>Download measurements</a></nav>
<p class="note">Updated 26 October 2026 · observed Earth climate normals</p>
<h1>Climate accuracy and the joint fit</h1>
<p>Temperature is closer than rainfall. The latest qualified Earth physics, <strong>r39</strong>, improves regional rainfall loss by 2.30%, but local errors remain substantial. The fantasy-world Earth atlas still uses the verified <strong>r38</strong> climate: later r39 world fits have not passed every release check.</p>
<div class="cards"><div class="card"><span class="number">1.79 °C</span>Monthly temperature MAE<small>31 development regions, equal regional weight</small></div>
<div class="card"><span class="number">32.84 mm</span>Monthly rainfall MAE<small>3,667 cities sampled from regional model cells</small></div>
<div class="card"><span class="number">46.47%</span>Annual rain totals within 25%<small>City comparison; slightly below r38's 46.66%</small></div></div>
<p class="note">MAE is mean absolute error. These are different summaries, not one overall accuracy percentage. The cities share reused regional runs; they are not an independent global station validation. The model is checked against modern WorldClim normals, not reconstructed weather for 200 AD.</p>
<h2>The rainfall problem is regional</h2><p>Iran improves, while North India remains far too dry. Extending numerical warm-up barely changes these errors. The audit below reproduces all three archived climates exactly and passes all per-step solver checks.</p>
<div class="table"><table><thead><tr><th>Region</th><th>r39 rain, mm/year</th><th>Observed, mm/year</th></tr></thead><tbody>TABLE</tbody></table></div>
<figure><a href="data/rainfall_sources.png"><img src="data/rainfall_sources.png" width="1920" height="1110" alt="Three regions: observed and simulated monthly rain above signed July moisture-source contributions"></a>
<figcaption>North India's July rain is 70 mm against 224 mm observed. Evaporation and parameterized convergence supply water, while net transport and drying remove it. The bars sum to simulated rain up to the small local equation residual. Positive and negative terms can vary within a region; they are not source-water tracers.</figcaption></figure>
<figure><a href="data/north_india_july.png"><img src="data/north_india_july.png" width="1920" height="1020" loading="lazy" alt="North India July maps comparing observed and simulated rainfall, convergence import, evaporation, storm exchange and drying"></a>
<figcaption>Matched 56 km cells show where rain and local equation sources occur. Source maps share a signed colour scale, with extremes clipped. These are concentration-advection equation diagnostics, not a closed global water budget.</figcaption></figure>
<h2>Can the joint fit stay physically realistic?</h2>
<p>We can preserve the shared physical laws and fit uncertain geography separately. The new input boundary locks Earth's solar flux, greenhouse reference, radius, tilt, rotation and calendar; fantasy-world changes cannot alter that Earth test. World profiles also cannot replace the verified physical or solver settings.</p>
<p>That removes a tooling weakness, but the transfer problem remains. In the nine-layout audit, r39's average world-fit gain was positive and seven of nine paired gains were positive, yet its declared bootstrap interval crossed zero. The release gate therefore rejected it. The existing fantasy planet also has retrograde rotation and a 33.5° tilt; it is Earth-sized, not modern Earth.</p>
<p>There is another physical limit: Earth regional tests prescribe remote-monsoon descent from observed global rainfall, while the fantasy model generates it from its own rain. In Iran, this prescribed term removes about 52 mm in July. The model's Indian rain source is too weak, so the Earth improvement does not by itself demonstrate that the generated feedback will transfer.</p>
<p>The next physical priority is monsoon moisture delivery and the consistency of remote forcing. A new experiment must retain distant monsoon sources and test shared physics against protected Earth regions, modelled ocean temperatures, matched resolutions and multiple world surroundings. More fantasy-map agreement cannot compensate for a failed Earth check.</p>
<p class="note">This audit selects no parameters and replaces no atlas climate, farming or population data. The r39 temperature/rain statistics apply to Earth runs; they are not measured accuracy estimates for either free fit or Whittaker fit. Settlement maps remain scenarios for low-input technology around 200 AD.</p>
<p><a href="../../reports/JOINT_INPUTS_20261026.md">Methods and parameter separation</a> · <a href="../../reports/CONSTRAINED_BLEND_R39_20261025.md">r39 calibration record</a> · <a href="../../reports/R39_WORLD_TRANSFER_20261026.md">Rejected world-transfer checks</a></p>
</main></html>'''.replace('TABLE', table)
    (DEST/'index.html').write_text(page)
    write_json(AUDIT/'publication.json', dict(status='published_diagnostic_only',
        summary_sha256=file_hash(data/'summary.json'), page_sha256=file_hash(DEST/'index.html'),
        images_sha256=summary['images_sha256'], exact_controls=3, physics_or_atlas_climate_adoption=False))


if __name__ == '__main__':
    main()
