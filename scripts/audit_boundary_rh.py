"""Cached native comparison of fixed marine RH shapes; zero climate runs.

Observed 925 hPa temperature anchors the already archived environmental6K/km
profile. Actual humidity is withheld from construction and used only to score
fixed uniform/partial/full pressure tapers. This is not a humidity reset or
the original 1967 radiative-convective model.
"""
from pathlib import Path
import argparse
import importlib.metadata
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_benchmark_protocol import file_hash, freeze, identity, write_json
from audit_pnw_vertical import partial_integrals, summarize_arrays
from rotclimate.column_thermodynamics import integrate_saturation_profile, specific_saturation
from earth_calendar import MONTH_DAYS

LEVELS = [925, 850, 700, 600, 500, 400, 300]
PROFILES = {'uniform': 0., 'half_taper': .5, 'mw_taper': 1.}
POLICY = dict(water_error_floor_mm=1., shape_error_floor=.02,
              regional_free_ratio=1.05, regional_weight=.25,
              reference_objective_max=.99)


def relative_humidity(pressure_pa, *, surface_pressure_pa=101325., surface_rh=.77, taper=1.):
    """Tropospheric pressure taper; the original stratospheric floor is absent.

    Full taper is RHs*(p/ps-.02)/.98 clipped at zero; half taper interpolates
    relative humidity, never already integrated humidity ratios.
    """
    p = np.asarray(pressure_pa, float)
    if (not np.isfinite(p).all() or (p <= 0).any() or not np.isfinite(surface_pressure_pa)
            or surface_pressure_pa <= 0 or (p > surface_pressure_pa).any()
            or not np.isfinite(surface_rh) or not 0 < surface_rh <= 1
            or not np.isfinite(taper) or not 0 <= taper <= 1):
        raise ValueError('Need finite pressure within column, RH in(0,1], taper in[0,1]')
    shape = np.maximum((p / surface_pressure_pa - .02) / .98, 0.)
    return surface_rh * ((1 - taper) + taper * shape)


def derive(qsat, observed, area, days, taper):
    p = np.asarray(LEVELS)[None, :, None] * 100.
    qsat = np.asarray(qsat, float)
    if (qsat.ndim != 3 or qsat.shape[:2] != (12, 7) or not np.isfinite(qsat).all()
            or (qsat <= 0).any()):
        raise ValueError('Need finite positive monthly saturation on seven native levels')
    q = qsat * relative_humidity(p, taper=taper)
    if (q < 0).any() or (q > qsat).any():
        raise ValueError('Humidity outside saturation bound')
    actual = partial_integrals(observed, LEVELS)
    model = partial_integrals(q, LEVELS)
    if not np.allclose(model['total_mm'], model['lower_mm'] + model['upper_mm'], rtol=0, atol=1e-12):
        raise ValueError('Partial-water sum does not close')
    raw = dict(specific_humidity_kg_kg=q, **{'model_' + k: v for k, v in model.items()},
               water_absolute_error_mm=np.abs(model['total_mm'] - actual['total_mm']),
               shape_absolute_error=np.abs(model['upper_lower_mean_q_ratio'] - actual['upper_lower_mean_q_ratio']),
               lower_water_absolute_error_mm=np.abs(model['lower_mm'] - actual['lower_mm']),
               upper_water_absolute_error_mm=np.abs(model['upper_mm'] - actual['upper_mm']))
    summary = summarize_arrays(raw, area, days)
    annual = summary['seasons']['annual']
    return dict(summary, water_mae_mm=annual['water_absolute_error_mm'],
                shape_mae=annual['shape_absolute_error'], physical_checks_passed=True), raw


def review_profiles(regions):
    result = {}
    base_shape = float(np.mean([v['profiles']['uniform']['shape_mae'] for v in regions.values()]))
    for name in PROFILES:
        scores = {}
        for region, row in regions.items():
            old, new = row['profiles']['uniform'], row['profiles'][name]
            water = 1 + (new['water_mae_mm'] - old['water_mae_mm']) / max(old['water_mae_mm'], POLICY['water_error_floor_mm'])
            shape = 1 + (new['shape_mae'] - old['shape_mae']) / max(old['shape_mae'], POLICY['shape_error_floor'])
            scores[region] = dict(water_error_normalized=water, shape_error_normalized=shape, combined=.5 * (water + shape))
        values = np.asarray([v['combined'] for v in scores.values()])
        objective = float(values.mean() + POLICY['regional_weight'] * np.mean(np.maximum(values - POLICY['regional_free_ratio'], 0)**2))
        mean_shape = float(np.mean([v['profiles'][name]['shape_mae'] for v in regions.values()]))
        result[name] = dict(objective=objective, mean_combined=float(values.mean()), worst_region=float(values.max()),
                            mean_shape_mae=mean_shape, baseline_mean_shape_mae=base_shape, regional=scores,
                            supports_separately_declared_coupled_pilot=(name != 'uniform' and objective <= POLICY['reference_objective_max'] and mean_shape <= base_shape),
                            scope='Reference-process evidence only; not a coupled response or adoption')
    return result


def plot(regions, path):
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), constrained_layout=True)
    for column, (region, row) in enumerate(regions.items()):
        for ax, suffix, unit in zip(axes[:, column], ['total_mm', 'upper_lower_mean_q_ratio'],
                                    ['Partial water 925–300 hPa (mm)', 'Upper/lower mean specific humidity']):
            ax.plot(range(12), row['observed']['monthly'][suffix], 'o-', color='black', ms=3, label='Observed')
            for color, (name, taper) in zip(['#4477aa', '#ee7733', '#228833'], PROFILES.items()):
                ax.plot(range(12), row['profiles'][name]['monthly']['model_' + suffix], color=color, label=f'{name} · taper {taper:g}')
            ax.set(title=region.replace('_', ' ').title() + f' · {row["native_ocean_cells"]} native ocean cells',
                   ylabel=unit, xticks=range(12), xticklabels=list('JFMAMJJASOND'), ylim=(0, None))
            ax.grid(alpha=.15)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle('Marine RH shape · fixed surface RH 0.77, unchanged environmental 6 K/km', fontsize=15)
    fig.supxlabel('Same observed 925 hPa temperature anchor and native area/Gregorian weights; humidity withheld from construction.\n'
                  'Pressure taper changes column water; total water is not renormalized. Tropospheric process comparison, not the full 1967 model.\n'
                  'Tiny reused model-assisted samples, no downloads or Earth integrations; no humidity forcing or climate adoption.', fontsize=9)
    fig.savefig(path, dpi=145); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve(); plan_path = args.plan.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Preserve existing audit; use a fresh output')
    out.mkdir(parents=True, exist_ok=True)
    phase = 'freeze'
    try:
        p = json.loads(plan_path.read_text())
        if (p['profiles'] != PROFILES or p['policy'] != POLICY or p['pressure_hpa'] != LEVELS
                or p['regions'] != ['pacific_nw', 'iberia', 'california'] or p['surface_rh'] != .77
                or p['surface_pressure_pa'] != 101325. or p['climate_integrations'] != 0):
            raise ValueError('Changed predeclared process comparison')
        parent = ROOT / p['parent_directory']
        protocol = json.loads((parent / 'protocol.json').read_text()); prior = json.loads((parent / 'review.json').read_text())
        archive = parent / 'native_profiles.npz'
        if (prior['status'] != 'passed' or not prior['complete'] or prior['identity'] != identity(protocol)
                or file_hash(archive) != p['parent_arrays_sha256'] or file_hash(archive) != prior['arrays_sha256']
                or file_hash(parent / 'protocol.json') != prior['protocol_sha256']
                or file_hash(parent / 'protocol.json') != p['parent_protocol_sha256']
                or file_hash(parent / 'review.json') != p['parent_review_sha256']):
            raise ValueError('Changed parent process archive')
        sources = dict(protocol['sources'])
        for name, sha in sources.items():
            if file_hash(ROOT / name) != sha:
                raise ValueError('Changed parent source: ' + name)
        for path in [plan_path, Path(__file__), archive, parent / 'review.json', parent / 'protocol.json', ROOT / p['paper_cache']]:
            sources[str(path.relative_to(ROOT))] = file_hash(path)
        if sources[p['paper_cache']] != p['paper_sha256']:
            raise ValueError('Changed primary-paper cache')
        for module in tuple(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename:
                local = Path(filename).resolve()
                if local.is_relative_to(ROOT) and '.venv' not in local.relative_to(ROOT).parts and local.suffix == '.py':
                    sources[str(local.relative_to(ROOT))] = file_hash(local)
        token = freeze(out / 'protocol.json', dict(plan=p, sources=sources, packages={n: importlib.metadata.version(n) for n in ['numpy', 'scipy', 'matplotlib']}))
        phase = 'derive-fixed-profiles'
        regions, raw = {}, {}
        with np.load(archive, allow_pickle=False) as z:
            for region, count in zip(p['regions'], [4, 20, 3]):
                get = lambda key: z[region + '_' + key]
                area, days = get('native_area_km2'), get('month_days')
                pressure = get('pressure_hpa')
                if len(area) != count or not np.array_equal(days, MONTH_DAYS) or not np.array_equal(pressure, LEVELS):
                    raise ValueError('Changed native geometry or calendar')
                observed, qsat = get('observed_specific_humidity_kg_kg'), get('environmental_6_specific_saturation_kg_kg')
                anchor = get('observed_temperature_c')[:, 0]
                ps = np.full(anchor.shape, 92500.)
                edges = np.broadcast_to(np.asarray(LEVELS)[:, None, None] * 100., (7,) + anchor.shape)
                _, temperatures = integrate_saturation_profile(anchor, ps, edges, profile='lapse', lapse_k_km=6., steps=64)
                reproduced = specific_saturation(np.moveaxis(temperatures, 0, 1), pressure[None, :, None] * 100.)
                np.testing.assert_allclose(reproduced, qsat, rtol=1e-12, atol=1e-14)
                actual = partial_integrals(observed, pressure)
                regions[region] = dict(native_ocean_cells=count, area_km2=float(area.sum()),
                                       observed=summarize_arrays(actual, area, days), profiles={})
                for name, taper in PROFILES.items():
                    summary, arrays = derive(qsat, observed, area, days, taper)
                    regions[region]['profiles'][name] = summary
                    raw.update({region + '_' + name + '_' + k: v for k, v in arrays.items()})
                raw.update({region + '_' + k: get(k).copy() for k in ['native_area_km2', 'month_days', 'native_latitude', 'native_longitude', 'native_flat_indices', 'pressure_hpa', 'observed_specific_humidity_kg_kg']})
        scores = review_profiles(regions)
        np.savez_compressed(out / 'native_profiles.npz', **raw)
        plot(regions, out / 'marine_rh_profiles.png')
        for name, sha in sources.items():
            if file_hash(ROOT / name) != sha:
                raise ValueError('Frozen input/source changed: ' + name)
        write_json(out / 'review.json', dict(status='passed', complete=True, identity=token, regions=regions, reviews=scores,
                   arrays_sha256=file_hash(out / 'native_profiles.npz'), image_sha256=file_hash(out / 'marine_rh_profiles.png'),
                   protocol_sha256=file_hash(out / 'protocol.json'), climate_integrations=0, physics_or_atlas_adoption=False,
                   scope='All three fixed RH shapes retained; no fitted RH, reference forcing or coupled climate response'))
        print(json.dumps(scores, indent=2))
    except BaseException as e:
        write_json(out / 'failure.json', dict(phase=phase, error=repr(e), climate_integrations=0, physics_or_atlas_adoption=False))
        raise


if __name__ == '__main__':
    main()
