"""User-run bounded reference-weather audit; no climate simulation/calibration.

Default prints a plan. --fetch --run obtains small official six-hourly subsets.
--run uses only a complete verified cache. Same-command download resume.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_weather_audit as weather
from scripts import review_v10_pressure_thermo as pressure
from rotclimate_v10.earth import atomic_json, sha256


def source_id():
    digest = hashlib.sha256(pressure.run.source_id().encode())
    for path in (Path(__file__), Path(weather.__file__), Path(pressure.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare():
    manifest, state, inputs, _, _, _, _ = pressure.load_verified(ROOT/'output/v10_pressure_thermo')
    expected = {'schema': 1, 'code_sha256': source_id(),
        'pressure_manifest_sha256': sha256(ROOT/'output/v10_pressure_thermo/manifest.json'),
        'pressure_state_sha256': sha256(ROOT/'output/v10_pressure_thermo/state.json'),
        'request_plan': weather.request_plan(), 'pressure_levels_hpa': weather.LEVELS.tolist(),
        'windows': [list(window) for window in weather.WINDOWS],
        'sampling': 'Native 2.5-degree marine centers selected from the declared model upwind box and 100–700 km ocean mask; area-weighted pointwise temporal contrasts. Complete synchronized six-hourly samples only.',
        'statistics': '925–300 hPa mean(q*v), product of separate temporal means and their covariance difference; top-decile eastward-transport humidity/temperature composite. Specific humidity, not model dry mixing ratio.',
        'limits': 'Two years and Jan/Jul windows are mechanism evidence, not a long-term climate estimate, regional boundary budget, cyclone identification or independent rain validation.',
        'cache_cap_bytes': weather.CACHE_CAP, 'request_spacing_seconds': 3.,
        'invocation_cap_minutes': 30., 'climate_integrations': 0, 'atlas_publication': False,
        'acknowledgment': 'NCEP/NCAR Reanalysis 1 data provided by NOAA PSL, Boulder, Colorado, USA, https://psl.noaa.gov .'}
    return expected, {region: values[0] for region, values in inputs.items()}


def markdown(data):
    lines = ['# Six-hourly reference weather audit', '', f"Status: {data['status']}.", '']
    if data.get('message'):
        lines += [data['message'], '']
    if data.get('windows'):
        lines += ['| Marine box / window | Joint eastward flux | Product of means | Temporal covariance | Top-decile share of positive eastward flux |',
            '|---|---:|---:|---:|---:|']
        for name, row in data['windows'].items():
            flux = row['transport']['eastward'];share = row['positive_eastward_transport_share_in_top_decile']
            lines.append(f"| {name} | {flux['full_mean_kg_m_s']:.2f} | {flux['product_of_means_kg_m_s']:.2f} | {flux['temporal_covariance_kg_m_s']:+.2f} | {format(share, '.1%') if share is not None else 'no positive flux'} |")
    lines += ['', 'Fluxes are kg m⁻¹ s⁻¹ over 925–300 hPa, not rainfall or a closed regional '
        'boundary budget. Covariance is computed in time at each native point before '
        'spatial averaging. Neighboring pixels and successive weather samples are '
        'correlated; no independent-sample confidence interval is claimed.', '',
        'Top eastward transport is a descriptive composite, not identified cyclones. '
        'Only two years and January/July are sampled. Reanalysis is model-informed '
        'and coarse, with pressure-level/native terrain limitations. The lowest '
        '1000 hPa level is excluded to reduce below-surface contamination; the '
        '925–300 hPa column excludes lower and upper water transport. Liquid-reference '
        'relative humidity is diagnostic, not mixed-phase cloud physics.', '',
        'Current synthetic model vortices do not carry event-linked boundary '
        'temperature/humidity anomalies. This does not mean the model’s internally '
        'transported moisture has zero covariance. Use these measurements to decide '
        'whether a coupled weather-forcing mechanism earns its next prototype, '
        'not to fit precipitation or infer rainfall from vapor flux alone.', '',
        'Data provided by [NOAA PSL](https://psl.noaa.gov/thredds/catalog/Datasets/ncep.reanalysis/pressure/catalog.html). '
        'No seasonal climate integration, calibration or atlas change.']
    return '\n'.join(lines)+'\n'


def plot(data, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
    for region, ax in zip(('california', 'iberia'), axes):
        rows = [data['windows'][f'{region}_{year}_{month:02d}'] for year, month in weather.WINDOWS]
        labels = [f'{year} '+('Jan' if month == 1 else 'Jul') for year, month in weather.WINDOWS]
        full = [row['transport']['eastward']['full_mean_kg_m_s'] for row in rows]
        mean = [row['transport']['eastward']['product_of_means_kg_m_s'] for row in rows]
        x = np.arange(len(rows))
        ax.bar(x-.18, mean, .36, label='Product of separate means', color='#879a9f')
        ax.bar(x+.18, full, .36, label='Mean of paired weather transport', color='#2583a0')
        ax.set_xticks(x, labels);ax.axhline(0, color='#3f555d', lw=.7)
        ax.set(title=region.title()+' upwind marine box', ylabel='925–300 hPa eastward flux\nkg m⁻¹ s⁻¹')
        ax.grid(axis='y', alpha=.2)
    axes[0].legend(frameon=False)
    fig.suptitle('Does averaging weather lose moisture transport?', fontsize=15)
    fig.savefig(out/'weather_covariance.png', dpi=170)
    plt.close(fig)


def run(out, cache, fetch=False):
    expected, cases = prepare()
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != expected:
        raise ValueError('Weather audit protocol changed; preserve results and choose a new --out.')
    if not manifest.exists():
        atomic_json(manifest, expected)
    data = {'status': 'running', 'windows': {}, 'climate_integrations': 0, 'atlas_updated': False}
    deadline = time.monotonic()+30*60
    try:
        records, downloads = weather.acquire(cache, fetch=fetch, should_stop=lambda: time.monotonic() >= deadline)
        if source_id() != expected['code_sha256']:
            raise ValueError('Weather audit source changed during download.')
        locations = {}
        for year, month in weather.WINDOWS:
            for region, case in cases.items():
                fields = weather.merged_fields(records, year, month, region)
                selected, weights, points = weather.offshore_points(case, fields['air'])
                if region in locations and locations[region] != points.tolist():
                    raise ValueError('Native marine sampling changed between windows.')
                locations[region] = points.tolist()
                data['windows'][f'{region}_{year}_{month:02d}'] = weather.diagnose(fields, selected, weights)
        data.update(status='complete', native_marine_coordinates=locations, reference_downloads=downloads)
        plot(data, out)
    except weather.ServerPaused as error:
        data.update(status='fetch_paused', message=str(error))
    except KeyboardInterrupt:
        data.update(status='interrupted', message='Completed validated cache entries preserved; resume with the same command.')
    except (ValueError, RuntimeError, OSError) as error:
        data.update(status='needs_diagnosis', message=str(error))
    atomic_json(out/'result.json', data)
    (out/'summary.md').write_text(markdown(data))
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--cache', type=Path, default=ROOT/'data/v10_weather')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_weather_audit')
    args = parser.parse_args(argv)
    print('Four Jan/Jul 1990/2000 reference windows in two marine boxes; 48 small regional subsets plus 8 metadata files.', flush=True)
    print('Six-hourly temperature, specific humidity and winds; 96 MB cap, sequential spaced downloads, 30-minute cap and cache resume.', flush=True)
    print('No climate simulation, calibration or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Fetch and analyse: .venv/bin/python -u scripts/audit_v10_weather.py --fetch --run')
        return 0
    data = run(args.out, args.cache, args.fetch)
    print('Status: '+data['status'], flush=True)
    if data.get('message'):
        print(data['message'], flush=True)
    return 0 if data['status'] in ('complete', 'fetch_paused', 'interrupted') else 1


if __name__ == '__main__':
    raise SystemExit(main())
