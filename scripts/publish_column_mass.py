"""Publish mass-consistent column diagnostics and all fixed pilot outcomes."""
from pathlib import Path
import html
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, LogNorm
from circulation_reference import acquire, vector_scores
from earth_calendar import MONTH_DAYS
from local_benchmark_protocol import file_hash, write_json
from rotclimate import earth


def dry_pressure_mean(field):
    """Actual shared925–300hPa levels; not an extrapolated full atmosphere."""
    pressure = np.array([925, 850, 700, 600, 500, 400, 300])
    indices = [list(field.pressure_hpa).index(p) for p in pressure]
    return np.trapezoid(field.values[:, indices[::-1]], x=pressure[::-1]*100, axis=1)/62500


def main():
    out = ROOT/'output/column_mass_20261026'
    review = json.loads((out/'review.json').read_text())
    protocol = json.loads((out/'protocol.json').read_text()); plan = protocol['plan']
    if not review['complete'] or review['physics_or_atlas_adoption']:
        raise ValueError('Need completed pilot with no adoption by this publisher')
    for name, expected in protocol['sources'].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError('Changed scientific source epoch: '+name)
    records = {}
    for name in plan['profiles']:
        records[name] = {}
        for region in plan['regions']:
            path = out/name/f'{region}.json'; row = json.loads(path.read_text())
            if row['identity'] != review['identity']:
                raise ValueError('Changed pilot identity')
            if row['status'] == 'passed':
                if not row['numerics']['all_checks_passed'] or file_hash(path.with_suffix('.npz')) != row['arrays_sha256']:
                    raise ValueError('Unverified physical record')
            elif row['status'] != 'failed':
                raise ValueError('Unknown solve status')
            if name == 'reference' and (row['status'] != 'passed' or not row['legacy_exact']):
                raise ValueError('Missing exact adopted control')
            if name in plan['profile_control_archives'] and (row['status'] != 'passed' or not row['physical_control_exact']):
                raise ValueError('Missing exact historical physical control')
            records[name][region] = row
    names = list(plan['profiles']); regions = plan['regions']
    labels = ['r39', 'Damped', 'Flux', 'Thermal\ncontrol', 'Balanced\nflux', 'Balanced\n+1 km', 'Balanced\n+2 km']
    table_labels = dict(zip(names, ['Adopted r39', 'r39 numerical control', 'Conservative flux',
        'Thermal control, 1 km', 'Mass-balanced flux', 'Balanced +1 km', 'Balanced +2 km']))
    losses = [[None if records[n][r]['status'] != 'passed' else
        records[n][r]['rain']['loss']/records['reference'][r]['rain']['loss'] for n in names] for r in regions]
    winds = [[None if records[n][r]['status'] != 'passed' else
        records[n][r]['circulation']['scores']['q925_300'][plan['circulation_groups'][r]]['vector_rmse_ms']/
        records['reference'][r]['circulation']['scores']['q925_300'][plan['circulation_groups'][r]]['vector_rmse_ms']
        for n in names] for r in plan['circulation_regions']]
    data = ROOT/'atlases/climate_accuracy/data'
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    for ax, values, row_labels, title in [(axes[0], losses, [n.replace('_', ' ').title() for n in regions],
            'Local rain loss / r39 · lower is better'),
            (axes[1], winds, ['North India lowland', 'Iberia ocean', 'East Australia lowland'],
             'Partial-column wind RMSE / r39 · lower is better')]:
        values = np.array([[np.nan if x is None else x for x in row] for row in values])
        plotted = np.log10(values)
        bound = max(.2, float(np.nanmax(np.abs(plotted))))
        image = ax.imshow(plotted, cmap='RdBu_r', norm=TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound), aspect='auto')
        for i, j in np.ndindex(values.shape):
            ax.text(j, i, 'FAILED' if not np.isfinite(values[i, j]) else f'{values[i, j]:.2f}',
                ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=.8, edgecolor='none', pad=1))
        ax.set(xticks=np.arange(len(names)), xticklabels=labels, yticks=np.arange(len(row_labels)),
               yticklabels=row_labels, title=title)
        ax.tick_params(axis='x', labelsize=8)
        fig.colorbar(image, ax=ax, shrink=.7, label='Log10 error ratio')
    fig.suptitle('Does stationary column mass balance improve the climate?', fontsize=16)
    fig.supxlabel('Same Earth planet and geography; seven reused development regions. Gray/white cells near1 are little changed.\n'
        'The column constraint is kinematic, not a momentum solution or a validation of humidity-weighted winds.', fontsize=9)
    tradeoff = data/'column_mass_tradeoff.png'; fig.savefig(tradeoff, dpi=145); plt.close(fig)

    # Exploratory reference-only check of the closure's strongest assumption.
    # It changes no pilot score, threshold, candidate or validation sampling.
    fields, _ = acquire(ROOT, json.loads((ROOT/plan['circulation_reference_plan']).read_text()))
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), constrained_layout=True)
    reference_gap = {}
    months = np.array(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    for index, region in enumerate(plan['circulation_regions']):
        row = records['reference'][region]; group = plan['circulation_groups'][region]
        order = np.array(row['circulation']['original_month'])
        dry = np.stack([dry_pressure_mean(fields[region, variable]) for variable in ['uwnd', 'vwnd']], axis=1)
        dry = dry[order].reshape(12, 2, -1)
        with np.load(out/'reference'/f'{region}.npz') as z:
            mask = z['circulation_mask_'+group]; area = z['circulation_area'][mask]
            moist = z['circulation_reference_q925_300'][:, :, mask]
        score = vector_scores(dry[:, :, mask], moist, area, MONTH_DAYS[order])
        reference_gap[region] = score
        for component, ax in enumerate(axes[index]):
            ax.plot(np.array(score['monthly_reference'])[:, component], color='#252e35', lw=2.3, label='Reanalysis humidity-weighted')
            ax.plot(np.array(score['monthly_model'])[:, component], color='#c4863d', lw=2, label='Reanalysis pressure-mass-weighted')
            for name, color, label in [('reference', '#7f898e', 'Adopted r39'), ('balanced_thermal1', '#3187a1', 'Balanced +1 km')]:
                candidate = records[name][region]
                if candidate['status'] == 'passed':
                    means = candidate['circulation']['scores']['q925_300'][group]['monthly_model']
                    ax.plot(np.array(means)[:, component], color=color, lw=1.5, ls='--', label=label)
            ax.set(xticks=np.arange(12), xticklabels=months[order],
                ylabel=('Eastward' if component == 0 else 'Northward')+' (m/s)',
                title=region.replace('_',' ').title()+' · '+group)
            ax.axhline(0, color='#777', lw=.6); ax.grid(alpha=.15)
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc='outside lower center', ncol=2, frameon=False, fontsize=9)
    fig.suptitle('Dry-air and humidity-weighted winds are different targets\n'
        'Reference-only exploratory check · shared 925–300 hPa partial column · monthly means', fontsize=14)
    reference_plot = data/'column_mass_reference.png'; fig.savefig(reference_plot, dpi=145); plt.close(fig)

    earth.REGIONS.update(json.loads((ROOT/'calibration/local_accuracy_20261023/regions_dev12.json').read_text()))
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), constrained_layout=True)
    for index, region in enumerate(['north_india', 'pacific_nw']):
        case = earth.region_case(region, plan['cell_km']); sl = case.grid.map_slice()
        lon, lat = case.lon[sl], case.grid.lat[sl]
        for ax, (profile, key, label) in zip(axes[index], [('reference', 'observed', 'WorldClim'),
            ('flux_damped', 'simulated', 'Conservative flux'), ('balanced_thermal1', 'simulated', 'Balanced +1 km')]):
            if records[profile][region]['status'] != 'passed':
                ax.text(.5,.5,'FAILED · no accepted map',ha='center',transform=ax.transAxes);continue
            with np.load(out/profile/f'{region}.npz') as z:
                value = np.where(z['valid'], np.maximum(z[key].sum(0), .001), np.nan)
                mean = float(z[key][:, z['valid']].sum(0).mean())
            image = ax.pcolormesh(lon, lat, value, shading='nearest', cmap='YlGnBu', norm=LogNorm(vmin=50,vmax=4000))
            ax.contour(lon,lat,case.grid.elev[sl],levels=[1500,3000],colors='#444',linewidths=.4,alpha=.5)
            ax.set(title=f'{region.replace("_"," ").title()} · {label}\n{mean:.0f} mm/year',xlabel='Longitude (°E)',ylabel='Latitude (°N)')
            ax.set_aspect(1/np.cos(np.radians(lat.mean())))
    fig.colorbar(image, ax=axes, shrink=.7, extend='both', label='Annual rainfall (mm/year) · same logarithmic scale')
    fig.suptitle('Rainfall placement: monsoon interior and wet mountain coast', fontsize=16)
    fig.supxlabel('Identical scored 56 km cells. Thin terrain contours:1500/3000m. These fixed examples do not replace local monthly scores.\n'
        'Every trial and numerical failure is retained in the downloaded results.', fontsize=9)
    maps = data/'column_mass_rain_maps.png'; fig.savefig(maps,dpi=145);plt.close(fig)

    attempted = sum(len(v) for v in records.values())
    passed = sum(row['status']=='passed' for group in records.values() for row in group.values())
    compact = {n: {r: {key: row.get(key) for key in ['status','error','rain','temperature','sst','column_speed','monthly_rain','circulation']}
        for r,row in group.items()} for n,group in records.items()}
    mass = {n: {r: None if 'column_mass_balance' not in row.get('numerics',{}) else
        {key:value for key,value in row['numerics']['column_mass_balance'].items() if key!='steps'} for r,row in group.items()} for n,group in records.items()}
    qualifiers = review['development_finalists']
    decision = 'No candidate passed the fixed screening safeguards' if not qualifiers else 'Screening qualifiers require subsequent full Earth/world gates'
    summary = dict(complete=True,decision=decision,physics_or_atlas_adoption=False,attempted_runs=attempted,passed_runs=passed,
        failed_runs=attempted-passed,profiles=names,regions=regions,screen=review['screen'],qualifiers=qualifiers,
        records=compact,mass_certificates=mass,local_rain_loss_ratio=losses,circulation_rmse_ratio=winds,
        exploratory_partial_column_reference_gap=reference_gap,
        reference_check_scope='Reference-only, same retained native footprints; mass-weighted925–300hPa is not full-column wind. No new scoring/selection or q\'u\' covariance.',
        physical_definition=plan['physical_definition'],scope=plan['publication'],
        provenance=dict(protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),publisher_sha256=file_hash(Path(__file__))),
        images_sha256={p.name:file_hash(p) for p in [tradeoff,reference_plot,maps]})
    write_json(data/'column_mass.json',summary)
    table = []
    for name in names:
        row = records[name]['north_india']
        if row['status']=='passed':
            table.append(f'<tr><td>{html.escape(table_labels[name])}</td><td>{row["rain"]["sim_mean_annual_mm"]:.0f}</td>'
                f'<td>{row["rain"]["monthly_mae_mm"]:.2f}</td><td>{row["circulation"]["scores"]["q925_300"]["land"]["vector_rmse_ms"]:.2f}</td></tr>')
        else:table.append(f'<tr><td>{html.escape(table_labels[name])}</td><td colspan="3">FAILED</td></tr>')
    page = ROOT/'atlases/climate_accuracy/index.html'; content = page.read_text()
    start,end = '<!--column-mass-start-->','<!--column-mass-end-->'
    section = f'''<!--column-mass-start--><section aria-labelledby="column-mass-h"><h2 id="column-mass-h">Mass-consistent column flow</h2>
<p>A divergent surface-like wind can accumulate air when applied to a whole stationary column. This experiment makes the minimum mass-weighted velocity correction needed to cancel dry-column face-flux divergence. It keeps Earth’s planetary settings fixed and adds no observed-wind forcing. Surface heat, evaporation and terrain lift retain the surface wind.</p>
<p>The fixed pilot attempts {attempted} integrations: {passed} pass strict numerics and {attempted-passed} fail. Seven adopted climate controls and three native wind controls reproduce exactly. Another21 physical/numerical controls reproduce every archived array field. <strong>{decision}.</strong> No fit or atlas climate is adopted by this page.</p>
<figure><a href="data/column_mass_tradeoff.png"><img src="data/column_mass_tradeoff.png" width="2030" height="870" loading="lazy" alt="Local rainfall and outside wind error ratios for all seven fixed mass-consistency profiles"></a><figcaption>Lower ratios improve on r39; the full selection also protects temperature, individual regions, ocean climate and solver/budget validity. Numerical success and mass consistency are separate from climate accuracy.</figcaption></figure>
<div class="table"><table><caption>North India, identical scored cells</caption><thead><tr><th>Profile</th><th>Annual rain mm</th><th>Monthly rain MAE mm</th><th>Wind vector RMSE m/s</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<figure><a href="data/column_mass_reference.png"><img src="data/column_mass_reference.png" width="1740" height="1305" loading="lazy" alt="Reference partial-column pressure-mass and humidity-weighted winds differ across seasons and regions"></a><figcaption>This reference-only exploratory check exposes the closure’s strongest assumption: a mass-consistent dry-air wind need not carry moisture in the right direction. Both targets span only925–300hPa, use monthly means and omit transient moisture covariance. No new target or validation sample is used to select a candidate.</figcaption></figure>
<figure><a href="data/column_mass_rain_maps.png"><img src="data/column_mass_rain_maps.png" width="2030" height="1160" loading="lazy" alt="Observed, conservative-flux and fixed balanced-flow rainfall maps for North India and Pacific Northwest"></a><figcaption>These two fixed examples show rain placement in the monsoon interior and a wet mountain coast. All candidates and failures remain in the results; maps do not replace monthly cell errors.</figcaption></figure>
<p class="note">This is a stationary equivalent-barotropic kinematic closure with approximate hydrostatic column mass and adjustable open-border winds. It does not solve momentum, surface-pressure storage, vertical return circulation or the vertical humidity profile. Flat-grid geometry and reference-period limitations remain. The historical global/city climate scores are unchanged.</p>
<p><a href="data/column_mass.json" download>Download column mass, rainfall and wind diagnostics</a> · <a href="../../reports/COLUMN_MASS_20261026.md">Column mass method and results</a></p></section><!--column-mass-end-->'''
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_research_only',page_sha256=file_hash(page),
        metadata_sha256=file_hash(data/'column_mass.json'),images_sha256=summary['images_sha256'],physics_or_atlas_adoption=False))


if __name__=='__main__':main()
