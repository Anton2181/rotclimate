"""Independently reconstruct pressure-taper native diagnostics and decisions."""
from pathlib import Path
import argparse
import json
import math
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
from local_benchmark_protocol import file_hash, identity, write_json


def integrals(q, pressure):
    # Independent composite trapezoids, with the 700hPa split counted once.
    segments = [.5 * (q[:, k] + q[:, k + 1]) * (pressure[k] - pressure[k + 1]) / 9.80665 for k in range(6)]
    lower = np.sum(segments[:2], axis=0); upper = np.sum(segments[2:], axis=0)
    return dict(total_mm=lower + upper, lower_mm=lower, upper_mm=upper,
                lower_mean_q=lower * 9.80665 / 22500., upper_mean_q=upper * 9.80665 / 40000.,
                upper_lower_mean_q_ratio=(upper / 40000.) / (lower / 22500.))


def check_summary(summary, arrays, area, days):
    for key, value in arrays.items():
        np.testing.assert_allclose(summary['native'][key], value, rtol=1e-12, atol=1e-12)
        monthly = np.sum(value * area, axis=-1) / math.fsum(area)
        np.testing.assert_allclose(summary['monthly'][key], monthly, rtol=1e-12, atol=1e-12)
        for season, indices in [('annual', np.arange(12)), ('DJF', np.array([11, 0, 1])), ('JJA', np.array([5, 6, 7]))]:
            weighted = np.einsum('m...c,m,c->...', value[indices], days[indices], area)
            expected = weighted / (math.fsum(days[indices]) * math.fsum(area))
            np.testing.assert_allclose(summary['seasons'][season][key], expected, rtol=1e-12, atol=1e-12)


def verify(out):
    protocol = json.loads((out / 'protocol.json').read_text()); p = protocol['plan']
    review = json.loads((out / 'review.json').read_text())
    if (review.get('complete') is not True or review.get('status') != 'passed'
            or review['identity'] != identity(protocol) or review['climate_integrations'] != 0
            or review['physics_or_atlas_adoption'] is not False
            or file_hash(out / 'protocol.json') != review['protocol_sha256']
            or file_hash(out / 'native_profiles.npz') != review['arrays_sha256']
            or file_hash(out / 'marine_rh_profiles.png') != review['image_sha256']):
        raise ValueError('Changed completed process audit')
    for name, sha in protocol['sources'].items():
        if file_hash(ROOT / name) != sha:
            raise ValueError('Changed frozen source/input: ' + name)
    parent = ROOT / p['parent_directory']
    if any(file_hash(parent / filename) != p[key] for filename, key in [
            ('native_profiles.npz', 'parent_arrays_sha256'), ('review.json', 'parent_review_sha256'),
            ('protocol.json', 'parent_protocol_sha256')]):
        raise ValueError('Changed parent native archive')
    errors = {n: {} for n in ['uniform', 'half_taper', 'mw_taper']}
    if p['profiles'] != dict(uniform=0., half_taper=.5, mw_taper=1.):
        raise ValueError('Changed fixed RH shapes')
    with np.load(parent / 'native_profiles.npz', allow_pickle=False) as old, np.load(out / 'native_profiles.npz', allow_pickle=False) as new:
        for region, count in zip(['pacific_nw', 'iberia', 'california'], [4, 20, 3]):
            get = lambda key: old[region + '_' + key]
            area, days = get('native_area_km2'), get('month_days')
            pressure = get('pressure_hpa') * 100.
            observed = get('observed_specific_humidity_kg_kg'); saturation = get('environmental_6_specific_saturation_kg_kg')
            if (len(area) != count or (area <= 0).any() or not np.isfinite(area).all()
                    or not np.array_equal(days, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
                    or not np.array_equal(pressure, [92500, 85000, 70000, 60000, 50000, 40000, 30000])):
                raise ValueError('Changed geometry or calendar')
            for key in ['native_area_km2', 'month_days', 'native_latitude', 'native_longitude', 'native_flat_indices', 'pressure_hpa', 'observed_specific_humidity_kg_kg']:
                np.testing.assert_array_equal(new[region + '_' + key], get(key))
            actual = integrals(observed, pressure)
            row = review['regions'][region]
            if row['native_ocean_cells'] != count or row['area_km2'] != float(area.sum()):
                raise ValueError('Changed footprint certificate')
            check_summary(row['observed'], actual, area, days)
            for name, taper in p['profiles'].items():
                rh = np.array([.77 * (1 - taper + taper * max((float(v) / 101325. - .02) / .98, 0.)) for v in pressure])
                q = saturation * rh[None, :, None]
                if not np.isfinite(q).all() or (q < 0).any() or (q > saturation).any():
                    raise ValueError('Humidity physical bounds failed')
                model = integrals(q, pressure)
                fields = dict(specific_humidity_kg_kg=q, **{'model_' + k: v for k, v in model.items()},
                              water_absolute_error_mm=np.abs(model['total_mm'] - actual['total_mm']),
                              shape_absolute_error=np.abs(model['upper_lower_mean_q_ratio'] - actual['upper_lower_mean_q_ratio']),
                              lower_water_absolute_error_mm=np.abs(model['lower_mm'] - actual['lower_mm']),
                              upper_water_absolute_error_mm=np.abs(model['upper_mm'] - actual['upper_mm']))
                for key, value in fields.items():
                    np.testing.assert_allclose(new[region + '_' + name + '_' + key], value, rtol=1e-12, atol=1e-12)
                check_summary(row['profiles'][name], fields, area, days)
                weight = days[:, None] * area[None, :]
                error = lambda value: float(np.sum(value * weight) / math.fsum(weight.ravel()))
                errors[name][region] = (error(fields['water_absolute_error_mm']), error(fields['shape_absolute_error']))
                np.testing.assert_allclose([row['profiles'][name]['water_mae_mm'], row['profiles'][name]['shape_mae']], errors[name][region], rtol=1e-12, atol=1e-12)
    reproduced = {}
    baseline_shape = math.fsum(v[1] for v in errors['uniform'].values()) / 3
    for name in p['profiles']:
        scores = []
        for region in p['regions']:
            water, shape = errors[name][region]; oldwater, oldshape = errors['uniform'][region]
            normalized = [1 + (water - oldwater) / max(oldwater, 1.), 1 + (shape - oldshape) / max(oldshape, .02)]
            combined = math.fsum(normalized) / 2
            saved = review['reviews'][name]['regional'][region]
            np.testing.assert_allclose([saved['water_error_normalized'], saved['shape_error_normalized'], saved['combined']], [*normalized, combined], rtol=1e-12, atol=1e-12)
            scores.append(combined)
        mean = math.fsum(scores) / 3
        objective = mean + .25 * math.fsum(max(v - 1.05, 0)**2 for v in scores) / 3
        shape = math.fsum(v[1] for v in errors[name].values()) / 3
        supports = name != 'uniform' and objective <= .99 and shape <= baseline_shape
        saved = review['reviews'][name]
        np.testing.assert_allclose([saved['objective'], saved['mean_combined'], saved['worst_region'], saved['mean_shape_mae'], saved['baseline_mean_shape_mae']],
                                   [objective, mean, max(scores), shape, baseline_shape], rtol=1e-12, atol=1e-12)
        if saved['supports_separately_declared_coupled_pilot'] != supports:
            raise ValueError('Changed process advancement decision')
        reproduced[name] = dict(objective=objective, supports_coupled_pilot=supports)
    declaration = [n for n in protocol['sources'] if n.endswith('/plan.json') and json.loads((ROOT / n).read_text()) == p]
    if len(declaration) != 1:
        raise ValueError('Need unique frozen declaration')
    commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', declaration[0]], cwd=ROOT, text=True).strip()
    if not commit:
        raise ValueError('Declaration was not committed')
    return dict(status='passed', identity=identity(protocol), scientific_source_epoch=commit[:7], declaration_commit=commit,
                frozen_sources_verified=len(protocol['sources']), native_ocean_cells=27, native_regions=3,
                all_native_arrays_monthly_seasonal_summaries_and_decisions_recomputed=True, independent_scores=reproduced,
                climate_integrations=0, physics_or_atlas_adoption=False, review_sha256=file_hash(out / 'review.json'),
                protocol_sha256=file_hash(out / 'protocol.json'), verifier_sha256=file_hash(Path(__file__)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve(); result = verify(out)
    write_json(out / 'scientific_verification.json', result)
    print(json.dumps(result, indent=2))
