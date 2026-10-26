"""Publish verified circulation diagnostics without adopting a fitted climate."""
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
from local_benchmark_protocol import file_hash, write_json
from rotclimate import earth


def main():
    out = ROOT/'output/circulation_audit_20261026'
    review = json.loads((out/'review.json').read_text())
    protocol = json.loads((out/'protocol.json').read_text())
    if not review['complete'] or review['physics_or_atlas_adoption']:
        raise ValueError('Require completed diagnostic-only audit')
    for name, expected in protocol['sources'].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError('Audit source changed: '+name)
    for name, record in protocol['references'].items():
        if file_hash(ROOT/name) != record['sha256']:
            raise ValueError('Reference data changed: '+name)
    rows = {r['region']: r for r in review['records']}
    for name, row in rows.items():
        if (row['identity'] != review['identity'] or row['status'] != 'passed' or not row['legacy_exact']
                or not row['numerics']['all_checks_passed'] or file_hash(out/f'{name}.npz') != row['arrays_sha256']):
            raise ValueError('Changed or unverified circulation result')
    data = ROOT/'atlases/climate_accuracy/data'
    regions = [('north_india', 'land', 'North India · lowland'),
               ('east_australia', 'land', 'Eastern Australia · lowland'),
               ('iberia', 'ocean', 'Iberia · ocean'), ('california', 'ocean', 'California · ocean')]
    fig, axes = plt.subplots(4, 2, figsize=(12, 11), constrained_layout=True)
    colors = {'925': '#b78747', '850': '#699442', 'q925_300': '#287894'}
    months = np.array(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    for row_index, (name, kind, label) in enumerate(regions):
        row = rows[name]
        for component, ax in enumerate(axes[row_index]):
            for target, color in colors.items():
                score = row['scores']['moisture'][target][kind]
                ax.plot(np.arange(12), np.array(score['monthly_reference'])[:, component],
                    color=color, lw=1.7, label={'925': 'Reanalysis925 hPa', '850': 'Reanalysis850 hPa',
                                              'q925_300': 'Reanalysis q-weighted925–300 hPa'}[target])
            model = np.array(score['monthly_model'])[:, component]
            ax.plot(np.arange(12), model, color='#9e3f44', lw=2.5, label='Model moisture wind')
            ax.axhline(0, color='#555', lw=.65)
            ax.set(xticks=np.arange(12), xticklabels=months[row['original_month']],
                   ylabel=('Eastward' if component == 0 else 'Northward')+' (m/s)',
                   title=f'{label} · {score["native_cells"]} native cells')
            ax.grid(alpha=.15)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='outside lower center', ncol=2, frameon=False)
    fig.suptitle('A single wind layer misses observed vertical differences\n'
        'Area means of monthly vectors · NCEP/NCAR1981–2010 · native2.5° footprints', fontsize=14)
    seasonal = data/'circulation_seasons.png'
    fig.savefig(seasonal, dpi=140); plt.close(fig)

    earth.REGIONS.update(json.loads((ROOT/'calibration/local_accuracy_20261023/regions_dev12.json').read_text()))
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for index, name in enumerate(['north_india', 'east_australia']):
        row = rows[name]
        month = row['original_month'].index(0 if name == 'north_india' else 6)
        physical_month = 'January' if name == 'north_india' else 'July'
        case = earth.region_case(name, 56)
        lat = -case.grid.lat if row['mirrored'] else case.grid.lat
        with np.load(out/f'{name}.npz') as z:
            longitude, latitude = np.meshgrid(z['reference_longitude'], z['reference_latitude'])
            longitude = (longitude+180)%360-180
            mask = z['mask_land']
            for column, key, title in [(0, 'model_moisture', 'Model moisture wind'),
                                      (1, 'reference_q925_300', 'Reanalysis partial-column wind')]:
                ax = axes[index, column]
                ax.contour(case.lon, lat, case.grid.land.astype(float), levels=[.5], colors='#9aacae', linewidths=.8)
                wind = z[key][month]
                speed = np.hypot(wind[0], wind[1])
                # Convert physical vector directions to longitude/latitude plot axes.
                arrows = ax.quiver(longitude.ravel()[mask], latitude.ravel()[mask],
                    wind[0, mask]/np.cos(np.radians(latitude.ravel()[mask])), wind[1, mask], speed[mask],
                    angles='xy', scale_units='xy', scale=3, cmap='viridis', clim=(0, 10), width=.006)
                selected = case.grid.inmap
                ax.quiverkey(arrows, .80, .95, 5/np.cos(np.radians(lat[selected].mean())),
                    '5 m/s eastward', coordinates='axes', labelpos='S', fontproperties={'size': 8})
                ax.set(xlim=(case.lon[selected].min(), case.lon[selected].max()),
                    ylim=(lat[selected].min(), lat[selected].max()), title=f'{name.replace("_", " ").title()} · {physical_month}\n{title}',
                    xlabel='Longitude (°E)', ylabel='Latitude (°N)')
                ax.set_aspect(1/np.cos(np.radians(lat[selected].mean())))
                ax.grid(alpha=.15)
    fig.colorbar(arrows, ax=axes, shrink=.7, label='Magnitude of monthly mean vector (m/s)')
    fig.suptitle('Subtropical winter flow: direction differs, not only speed', fontsize=16)
    fig.supxlabel('Only retained lowland native cells are drawn; missing mountain/coastal footprints are deliberately unscored.\n'
        'Arrows show motion toward a direction, corrected for map latitude. Model is surface-like; reference spans925–300 hPa.', fontsize=9)
    maps = data/'circulation_winter_maps.png'
    fig.savefig(maps, dpi=140); plt.close(fig)
    summary = dict(complete=True, physics_changed=False, fitted=False,
        records={name: {key: row[key] for key in ['scores', 'coverage', 'original_month', 'mirrored']} for name, row in rows.items()},
        scope=protocol['plan']['decision'], reference=protocol['plan']['reference'],
        limitations=protocol['plan']['targets'],
        provenance=dict(protocol_sha256=file_hash(out/'protocol.json'), review_sha256=file_hash(out/'review.json'),
                        publisher_sha256=file_hash(Path(__file__))),
        images_sha256={p.name: file_hash(p) for p in [seasonal, maps]})
    write_json(data/'circulation.json', summary)
    page = ROOT/'atlases/climate_accuracy/index.html'
    content = page.read_text()
    start, end = '<!--circulation-start-->', '<!--circulation-end-->'
    section = '''<!--circulation-start--><section aria-labelledby="circulation-h"><h2 id="circulation-h">Checking the winds against reanalysis</h2>
<p>Four unchanged r39 integrations reproduce archived climate fields exactly and pass strict numerics. Their modeled wind vectors are compared with NCEP/NCAR1981–2010 pressure-level monthly means. This is an outside circulation diagnosis; it changes no climate fit or rainfall score.</p>
<p>Over North India’s11 retained lowland cells, the humidity-weighted925–300hPa vector RMSE is7.21m/s and direction cosine−0.54. Eastern Australia’s7 lowland cells give6.27m/s and−0.14. Iberia’s20 ocean cells show an overly strong mean-vector magnitude:7.77m/s modeled versus4.21m/s in that partial column. Different pressure targets give different answers; the model’s single surface-like layer cannot represent the full wind profile.</p>
<figure><a href="data/circulation_seasons.png"><img src="data/circulation_seasons.png" width="1680" height="1540" loading="lazy" alt="Four-region seasonal eastward and northward model vectors compared with925hPa,850hPa and humidity-weighted partial-column reanalysis vectors"></a><figcaption>Monthly mean vector components expose direction, season and height differences. Actual month overlap and full projection geometry are included. A speed-only comparison would miss reversed flow.</figcaption></figure>
<figure><a href="data/circulation_winter_maps.png"><img src="data/circulation_winter_maps.png" width="1680" height="1120" loading="lazy" alt="North India January and eastern Australia July model and reference wind arrows on the retained coarse lowland footprints"></a><figcaption>Conservative exclusions leave11/7 lowland cells in India/Australia and no California land sample; California has only3 retained ocean cells. Fine model cells are aggregated into native2.5° footprints rather than counted as independent references.</figcaption></figure>
<p class="note">Reanalysis is model-assisted, not direct point observations. The humidity-weighted partial column omits air below925hPa/above300hPa and transient q′u′ covariance. Terrain masking uses model geography; native below-ground flags are unavailable. The reference period differs from WorldClim1970–2000 rainfall. These reused regions do not establish global circulation or rainfall skill.</p>
<p><a href="data/circulation.json" download>Download circulation vectors and diagnostics</a> · <a href="../../reports/CIRCULATION_20261026.md">Circulation method and scope</a></p></section><!--circulation-end-->'''
    if start in content:
        before, rest = content.split(start, 1); _, after = rest.split(end, 1)
        content = before+section+after
    else:
        content = content.replace('</main>', section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json', dict(status='published_diagnostics_only', page_sha256=file_hash(page),
        metadata_sha256=file_hash(data/'circulation.json'), images_sha256=summary['images_sha256'], physics_or_atlas_adoption=False))


if __name__ == '__main__':
    main()
