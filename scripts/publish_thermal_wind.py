"""Publish the fixed thermal-wind pilot, preserving any failed run as failed."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, LogNorm
from local_benchmark_protocol import file_hash, write_json


def main():
    out = ROOT/'output/thermal_wind_20261026'
    review = json.loads((out/'review.json').read_text())
    protocol = json.loads((out/'protocol.json').read_text())
    plan = protocol['plan']
    if not review['complete'] or review['development_finalists']:
        raise ValueError('This publisher requires the completed non-qualifying pilot')
    for name, expected in protocol['sources'].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError('Frozen pilot source changed: '+name)
    records = {}
    for name in plan['profiles']:
        records[name] = {}
        for region in plan['regions']:
            path = out/name/f'{region}.json'
            row = json.loads(path.read_text())
            if row['identity'] != review['identity']:
                raise ValueError('Changed pilot identity')
            if row['status'] == 'passed':
                if not row['numerics']['all_checks_passed'] or file_hash(path.with_suffix('.npz')) != row['arrays_sha256']:
                    raise ValueError('Unverified successful record')
            elif row['status'] != 'failed':
                raise ValueError('Unknown pilot status')
            if name == 'reference' and (row['status'] != 'passed' or not row['legacy_exact']):
                raise ValueError('Need every exact climate control')
            records[name][region] = row
    names = list(plan['profiles'])
    regions = plan['regions']
    labels = ['r39', 'r39 damped', 'Conservative flux', 'Flux + thermal 1 km', 'Flux + thermal 2 km', 'Flux + thermal 3 km']
    ticks = ['r39', 'Damped', 'Flux', '+1 km', '+2 km', '+3 km']
    colors = ['#285c80', '#888888', '#269987', '#d2923c', '#a74d66', '#7968a9']
    rain = [[None if records[n][r]['status'] != 'passed' else
             records[n][r]['rain']['sim_mean_annual_mm']/records[n][r]['rain']['obs_mean_annual_mm'] for n in names] for r in regions]
    rain_loss = [[None if records[n][r]['status'] != 'passed' else
             records[n][r]['rain']['loss']/records['reference'][r]['rain']['loss'] for n in names] for r in regions]
    wind = [[None if records[n][r]['status'] != 'passed' else
             records[n][r]['circulation']['scores']['q925_300'][plan['circulation_groups'][r]]['vector_rmse_ms']/
             records['reference'][r]['circulation']['scores']['q925_300'][plan['circulation_groups'][r]]['vector_rmse_ms']
             for n in names] for r in plan['circulation_regions']]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    rain_values = np.array([[np.nan if v is None else v for v in row] for row in rain_loss])
    wind_values = np.array([[np.nan if v is None else v for v in row] for row in wind])
    for ax, values, ys, title, logarithm in [
        (axes[0], rain_values, [n.replace('_', ' ').title() for n in regions], 'Local rain loss / r39 · lower is better', True),
        (axes[1], wind_values, ['North India lowland', 'Iberia ocean', 'East Australia lowland'],
         'Partial-column vector RMSE / r39 · lower is better', False)]:
        drawn = np.log10(values) if logarithm else values-1
        norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1) if logarithm else TwoSlopeNorm(
            vmin=min(-.1, float(np.nanmin(drawn))-.05), vcenter=0, vmax=max(.1, float(np.nanmax(drawn))+.05))
        im = ax.imshow(drawn, cmap='RdBu_r', norm=norm, aspect='auto')
        for i, j in np.ndindex(values.shape):
            text = 'FAILED' if not np.isfinite(values[i, j]) else f'{values[i, j]:.2f}'
            ax.text(j, i, text, ha='center', va='center', fontsize=8,
                bbox=dict(facecolor='white', alpha=.8, edgecolor='none', pad=1))
        ax.set(xticks=np.arange(6), xticklabels=ticks, yticks=np.arange(len(ys)), yticklabels=ys, title=title)
        fig.colorbar(im, ax=ax, shrink=.7, label='Log10 local rain-loss ratio' if logarithm else 'RMSE ratio −1')
    fig.suptitle('Thermal-wind experiment: rainfall and outside circulation constraints', fontsize=15)
    fig.supxlabel('Fixed1/2/3km effective heights; modeled temperature gradients, no observed-wind forcing.\n'
        'Seven reused Earth regions; native2.5° circulation footprints. All safeguards remain in force; no profile is adopted.', fontsize=9)
    data = ROOT/'atlases/climate_accuracy/data'
    tradeoff = data/'thermal_wind_tradeoff.png'
    fig.savefig(tradeoff, dpi=145); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.3), constrained_layout=True)
    for name, label, color in zip(names, labels, colors):
        row = records[name]['north_india']
        if row['status'] != 'passed':
            continue
        axes[0].plot(row['monthly_rain']['simulated'], color=color, label=label, lw=1.8,
            ls='--' if name == 'reference_damped' else '-')
        score = row['circulation']['scores']['q925_300']['land']
        axes[1].plot(np.array(score['monthly_model'])[:, 0], color=color, lw=1.8)
    axes[0].plot(records['reference']['north_india']['monthly_rain']['observed'], color='#222', lw=2.4, label='WorldClim rain')
    reference = records['reference']['north_india']['circulation']['scores']['q925_300']['land']
    axes[1].plot(np.array(reference['monthly_reference'])[:, 0], color='#222', lw=2.4, label='NCEP q-weighted 925–300 hPa')
    axes[0].set(title='North India · rain', ylabel='mm / equal model month')
    axes[1].set(title='North India · eastward partial-column flow', ylabel='Eastward monthly mean (m/s)')
    for ax in axes:
        ax.set(xticks=np.arange(12), xticklabels=list('JFMAMJJASOND')); ax.grid(alpha=.15)
        ax.legend(frameon=False, fontsize=8)
    axes[1].axhline(0, color='#777', lw=.7)
    fig.suptitle('Does vertical shear fix the circulation and the monsoon together?', fontsize=15)
    fig.supxlabel('Rain keeps the legacy equal-month benchmark; wind uses actual calendar overlap and fixed native lowland footprints.\n'
        'These are paired development diagnostics, not a global score update or a validation of full atmospheric moisture flux.', fontsize=9)
    seasons = data/'thermal_wind_seasons.png'
    fig.savefig(seasons, dpi=145); plt.close(fig)
    # The closer regional total must not conceal where rain actually falls.
    from rotclimate import earth
    earth.REGIONS.update(json.loads((ROOT/'calibration/local_accuracy_20261023/regions_dev12.json').read_text()))
    case = earth.region_case('north_india', plan['cell_km'])
    sl = case.grid.map_slice()
    lon, lat = case.lon[sl], case.grid.lat[sl]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    panels = [('reference', 'observed', 'WorldClim observed'), ('reference', 'simulated', 'Adopted r39'),
              ('flux_damped', 'simulated', 'Conservative flux'), ('thermal3', 'simulated', 'Flux + thermal 3 km')]
    for ax, (name, field, title) in zip(axes.ravel(), panels):
        row = records[name]['north_india']
        if row['status'] != 'passed':
            ax.text(.5, .5, 'FAILED · no accepted map', transform=ax.transAxes, ha='center'); continue
        with np.load(out/name/'north_india.npz') as z:
            values = np.where(z['valid'], np.maximum(z[field].sum(0), .001), np.nan)
            mean = float(z[field][:, z['valid']].sum(0).mean())
            im = ax.pcolormesh(lon, lat, values, shading='nearest', cmap='YlGnBu', norm=LogNorm(vmin=50, vmax=4000))
        ax.contour(lon, lat, case.grid.elev[sl], levels=[1500, 3000], colors='#444', linewidths=.45, alpha=.6)
        ax.set(title=f'{title} · regional mean {mean:.0f} mm/year', xlabel='Longitude (°E)', ylabel='Latitude (°N)')
        ax.set_aspect(1/np.cos(np.radians(lat.mean())))
    fig.colorbar(im, ax=axes, shrink=.75, extend='both', label='Annual rain (mm/year) · same logarithmic scale')
    fig.suptitle('A nearly correct regional total can still put rain in the wrong places', fontsize=15)
    fig.supxlabel('Same scored 56 km land cells and observed fields. Thin contours: 1500/3000 m model terrain.\n'
        'Thermal 3 km matches North India’s annual mean closely, but worsens local monthly MAE. No candidate is adopted.', fontsize=9)
    spatial = data/'thermal_wind_india_maps.png'
    fig.savefig(spatial, dpi=145); plt.close(fig)
    attempted = sum(len(v) for v in records.values())
    passed = sum(row['status'] == 'passed' for group in records.values() for row in group.values())
    drift = {}
    for region in regions:
        with np.load(out/'reference'/f'{region}.npz') as a, np.load(out/'reference_damped'/f'{region}.npz') as b:
            drift[region] = float(np.max(np.abs((a['simulated']-b['simulated'])[:, a['valid']])))
    summary = dict(complete=True, decision='No candidate qualified; retain adopted profiles', attempted_runs=attempted,
        passed_runs=passed, failed_runs=attempted-passed, screen=review['screen'], profiles=names, regions=regions,
        annual_rain_ratio=rain, local_rain_loss_ratio=rain_loss, circulation_rmse_ratio=wind, circulation_regions=plan['circulation_regions'],
        numerical_drift_max_rain_mm=drift, scope=plan['publication'], physical_definition=plan['physical_definition'],
        north_india={name: None if records[name]['north_india']['status'] != 'passed' else
            dict(annual_rain_mm=records[name]['north_india']['rain']['sim_mean_annual_mm'],
                 rain_metrics=records[name]['north_india']['rain'],
                 monthly_rain=records[name]['north_india']['monthly_rain'],
                 circulation=records[name]['north_india']['circulation']) for name in names},
        failures=[dict(profile=n, region=r, error=row['error']) for n, group in records.items() for r, row in group.items() if row['status'] != 'passed'],
        provenance=dict(protocol_sha256=file_hash(out/'protocol.json'), review_sha256=file_hash(out/'review.json'),
            publisher_sha256=file_hash(Path(__file__))), images_sha256={p.name: file_hash(p) for p in [tradeoff, seasons, spatial]})
    write_json(data/'thermal_wind.json', summary)
    page = ROOT/'atlases/climate_accuracy/index.html'
    content = page.read_text()
    start, end = '<!--thermal-wind-start-->', '<!--thermal-wind-end-->'
    section = f'''<!--thermal-wind-start--><section aria-labelledby="thermal-h"><h2 id="thermal-h">Thermal-wind shear: an effective layer remains insufficient</h2>
<p>The outside wind comparison motivated a new physical experiment. Horizontal modeled temperature gradients generate hydrostatic/geostrophic shear up to fixed effective heights of1,2 and3km. Earth’s orbit, radiation, rotation and geography stay fixed. No observed wind enters the model. The mechanism is opt-in, with the legacy default unchanged.</p>
<p>The fixed six-profile pilot attempts{attempted} integrations;{passed} pass strict numerics and{attempted-passed} fail. Seven original climate controls and three native wind controls reproduce exactly. Separate damped controls keep numerical sensitivity distinct from physical changes. <strong>No physical candidate qualifies.</strong> The selection still requires rainfall, temperature, regional, ocean and outside-wind safeguards; no full31 or fine stage runs.</p>
<figure><a href="data/thermal_wind_tradeoff.png"><img src="data/thermal_wind_tradeoff.png" width="1885" height="870" loading="lazy" alt="Seven-region local rainfall-loss ratios and three-region native wind-error ratios for the thermal-wind pilot"></a><figcaption>Wind errors compare a fixed humidity-weighted925–300hPa reference; this partial column excludes transient moisture covariance. Rain loss preserves local annual and monthly errors; a closer regional annual total can still have worse local monthly rain. White FAILED cells, if present, remain failed rather than entering partial means.</figcaption></figure>
<figure><a href="data/thermal_wind_seasons.png"><img src="data/thermal_wind_seasons.png" width="1885" height="769" loading="lazy" alt="North India monthly rainfall and eastward moisture-wind response to three thermal-wind heights"></a><figcaption>Changed transport direction alone is insufficient evidence of a better climate. The approximation still has one effective moist layer, fixed synoptic smoothing and an equatorial taper; it does not resolve vertical return flow or an atmospheric momentum/energy budget.</figcaption></figure>
<figure><a href="data/thermal_wind_india_maps.png"><img src="data/thermal_wind_india_maps.png" width="1740" height="1160" loading="lazy" alt="Observed and three modeled annual rainfall maps on identical North India cells, exposing spatial errors behind a nearly correct regional total"></a><figcaption>At3km, the regional annual total reaches754mm versus761mm observed, while local monthly MAE rises from50.0mm for r39 to59.3mm. The map shows why a correct average does not establish accurate local climate.</figcaption></figure>
<p><a href="data/thermal_wind.json" download>Download thermal-wind results and safeguards</a> · <a href="../../reports/THERMAL_WIND_20261026.md">Thermal-wind method and results</a></p></section><!--thermal-wind-end-->'''
    if start in content:
        before, rest = content.split(start, 1); _, after = rest.split(end, 1)
        content = before+section+after
    else:
        content = content.replace('</main>', section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json', dict(status='published_nonqualifying_pilot', page_sha256=file_hash(page),
        metadata_sha256=file_hash(data/'thermal_wind.json'), images_sha256=summary['images_sha256'], physics_or_atlas_adoption=False))


if __name__ == '__main__':
    main()
