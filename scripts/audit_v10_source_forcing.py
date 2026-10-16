"""Cached monthly-wind projection and vertical-humidity quadrature audit.

Independent steady flow constructions and profile integrals only. No climate
integration, parameter fit, download or atlas mutation. --write saves diagnosis.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import review_v10_water_sources as review
from experiments import v10_forcing_audit as atmosphere
from rotclimate_v10.core import CENTERS, interpolate_months
from rotclimate_v10.earth import atomic_json, sha256
m = review.run.model.model


class CapturedProjection(m.ColumnProjection):
    def project(self, x, y):
        self.raw_x, self.raw_y = x.copy(), y.copy()
        return super().project(x, y)


def raw_projected_velocity(projector, flow):
    """Both velocities use face mass before cell interpolation."""
    raw = SimpleNamespace(x=projector.raw_x, y=projector.raw_y)
    helper = m.winds.mass_model.cell_velocity
    return helper(raw, projector), helper(flow, projector)


def pressure_integral(values, native_pressure_hpa, bottom_pa=92500., top_pa=30000.):
    """Integral q dp/g, linear q in p between native levels, no extrapolation.

    values: month, native level, points. Bounds may differ by point.
    """
    pressure = np.asarray(native_pressure_hpa, float)*100
    values = np.asarray(values, float)
    bottom = np.broadcast_to(bottom_pa, values.shape[-1:])
    top = np.broadcast_to(top_pa, values.shape[-1:])
    if values.ndim != 3 or values.shape[1] != len(pressure) or not np.isfinite(values).all() or not np.isfinite(pressure).all() or not np.isfinite(bottom).all() or not np.isfinite(top).all():
        raise ValueError('Invalid pressure integral inputs.')
    if (np.diff(pressure) >= 0).any() or (top > bottom).any() or (top < pressure.min()).any() or (bottom > pressure.max()).any():
        raise ValueError('Pressure integral cannot extrapolate or reverse its bounds.')
    result = np.zeros((values.shape[0], values.shape[-1]))
    for index in range(len(pressure)-1):
        high, low = pressure[index:index+2]
        hi, lo = np.minimum(bottom, high), np.maximum(top, low)
        length = np.maximum(hi-lo, 0.)
        qlo = values[:, index+1]+(lo-low)/(high-low)*(values[:, index]-values[:, index+1])
        qhi = values[:, index+1]+(hi-low)/(high-low)*(values[:, index]-values[:, index+1])
        result += .5*(qlo+qhi)*length/m.base.G
    return result


def clipped_layer_weights(interfaces_pa, bottom_pa=92500., top_pa=30000.):
    if not np.isfinite(interfaces_pa).all() or (np.diff(interfaces_pa, axis=0) >= 0).any() or top_pa > bottom_pa:
        raise ValueError('Invalid model layer bounds.')
    return np.maximum(np.minimum(interfaces_pa[:-1], bottom_pa)-
        np.maximum(interfaces_pa[1:], top_pa), 0.)/m.base.G


def wind_audit(case, profile, geometry, air, wind, settings, mode):
    d = case.domain;projector = CapturedProjection(d, geometry);rows = []
    masks = {'scored_land': case.score_mask, 'offshore': atmosphere.offshore_mask(case),
        'coastal_land': case.score_mask & (case.coast_distance_km < 150)}
    for month, t in enumerate(CENTERS):
        flow = m.flow_at(d, profile, settings, [], float(t), geometry, wind, projector, wind_mode=mode)
        (raw_u, raw_v), (u, v) = raw_projected_velocity(projector, flow)
        difference = np.hypot(u-raw_u, v-raw_v)
        row = {'month': month+1, 'projection': projector.last_info.copy(), 'areas': {}}
        for name, mask in masks.items():
            eligible = mask & (np.hypot(raw_u[0], raw_v[0]) >= .5)
            reversed_flow = (raw_u[0]*u[0]+raw_v[0]*v[0]) < 0
            row['areas'][name] = {'correction_p50_p95_max_m_s': np.percentile(difference[:, mask], [50, 95, 100]).tolist(),
                'raw_lower_mean_east_north_m_s': [float(raw_u[0, mask].mean()), float(raw_v[0, mask].mean())],
                'projected_lower_mean_east_north_m_s': [float(u[0, mask].mean()), float(v[0, mask].mean())],
                'lower_vector_reversal_share_above_half_m_s': float(reversed_flow[eligible].mean()) if eligible.any() else None}
        rows.append(row)
    return {'monthly': rows, 'maximum_barotropic_adjustment_m_s': max(r['projection']['barotropic_velocity_adjustment_max_m_s'] for r in rows),
        'mean_monthly_scored_lower_reversal_share': float(np.mean([r['areas']['scored_land']['lower_vector_reversal_share_above_half_m_s'] or 0 for r in rows])),
        'note': 'No-storm prescribed monthly means. Raw flow is only a velocity comparison, not a mass-closed integration control. Both velocities divide by actual face masses before interpolation. This does not measure real transient-front transport or isolate the effect of changing the projection in a seasonal run.'}


def humidity_audit(case, profile, geometry, air, settings, fields):
    mask = atmosphere.offshore_mask(case)
    if (geometry.surface_pressure[mask] < 92500.).any():
        raise ValueError('Marine model surface is below the diagnostic pressure window.')
    reference = fields[case.domain.name, 'shum']
    native = []
    for pressure in reference.pressure_hpa:
        r, _, _ = atmosphere.at_pressure(reference, case.longitude, case.domain.latitude, pressure)
        native.append(r[:, mask]/(1+r[:, mask]))
    native = np.stack(native, axis=1)
    local = []
    for pressure in geometry.pressure:
        r, _, _ = atmosphere.at_pressure(reference, case.longitude, case.domain.latitude, pressure/100)
        local.append(r[:, mask]/(1+r[:, mask]))
    local = np.stack(local, axis=1)
    operational = []
    for t in CENTERS:
        target, _ = m.coordinates.targets(case.domain, profile, settings, float(t), air)
        r = np.broadcast_to(interpolate_months(profile.mixing_ratio, float(t))[:, None, None]*settings.humidity_scale, target.shape)
        r = np.minimum(r, .95*m.base.saturation(target, geometry.pressure))
        operational.append(r[:, mask]/(1+r[:, mask]))
    operational = np.stack(operational)
    rows = {}
    split_center_hpa = .5*(m.coordinates.TRANSITION_PA+30000.)/100
    r, _, _ = atmosphere.at_pressure(reference, case.longitude, case.domain.latitude, split_center_hpa)
    split_q = r[:, mask]/(1+r[:, mask])
    upper_band_mass = (m.coordinates.TRANSITION_PA-30000.)/m.base.G
    for name, bottom in (('common_925_300_hpa', 92500.), ('upper_60795_300_hpa', m.coordinates.TRANSITION_PA)):
        weights = clipped_layer_weights(geometry.interfaces_pa[:, mask], bottom_pa=bottom)
        observed = pressure_integral(native, reference.pressure_hpa, bottom_pa=bottom)
        midpoint = (local*weights[None]).sum(1)
        prescribed = (operational*weights[None]).sum(1)
        # Quadrature-only candidate: split the original top cell at 300 hPa.
        # Replace only its known 607.95–300 hPa contribution. Nothing above
        # 300 hPa is extrapolated or used to construct a climate state here.
        proposed = midpoint-local[:, -1]*upper_band_mass+split_q*upper_band_mass
        rows[name] = {'native_reference_mm_by_month': observed.mean(1).tolist(),
            'local_midpoint_quadrature_mm_by_month': midpoint.mean(1).tolist(),
            'operational_boundary_profile_mm_by_month': prescribed.mean(1).tolist(),
            'midpoint_to_native_mean_ratio': float(midpoint.mean()/observed.mean()),
            'operational_to_native_mean_ratio': float(prescribed.mean()/observed.mean()),
            'split_at_300hpa_quadrature_only_mm_by_month': proposed.mean(1).tolist(),
            'split_at_300hpa_quadrature_only_to_native_mean_ratio': float(proposed.mean()/observed.mean())}
    return {'offshore_model_cells': int(mask.sum()), 'windows': rows,
        'note': 'Partial-column specific-humidity integral (q dp/g), not complete atmospheric water or vapor import. Native monthly r is converted back to specific q. Model boundary r is converted similarly for an apples-to-apples profile comparison; this is not the model dry-mass water ledger. Local midpoint test separates quadrature from the operational uniform/capped offshore profile. Native values are nearest horizontally sampled; duplicated model cells are not independent observations. No vapor above 300 or below 925 hPa is extrapolated. Monthly fields and annual model surface pressure cannot exclude every instantaneous native below-ground issue.'}


def analyse():
    protocol, inputs, settings, _, _ = review.run.prepare()
    if json.loads((ROOT/'output/v10_water_sources/manifest.json').read_text()) != protocol:
        raise ValueError('Cached forcing audit inputs differ from the completed source experiment.')
    texts, downloads = atmosphere.acquire(ROOT/'data/v10_atmosphere', fetch=False)
    fields = atmosphere.fields_from_cache(texts)
    output = {'source_protocol_sha256': sha256(ROOT/'output/v10_water_sources/manifest.json'),
        'source_code_sha256': protocol['code_sha256'], 'reference_downloads': downloads,
        'audit_script_sha256': sha256(Path(__file__)), 'wind': {}, 'humidity': {},
        'new_climate_integrations': 0, 'new_downloads': 0, 'atlas_updated': False}
    for region, (case, profile, geometry, air, wind) in inputs.items():
        for mode, config in settings.items():
            output['wind'][region+'_'+mode] = wind_audit(case, profile, geometry, air, wind, config, mode)
        output['humidity'][region] = humidity_audit(case, profile, geometry, air, settings['spatial'], fields)
    return output


def markdown(data):
    lines = ['# Cached forcing audit after the source-water batch', '',
        'No climate integration or download. No-storm monthly flow constructions and partial-column profile integrals.', '',
        '| Region / wind mode | Maximum projection velocity correction | Mean monthly land low-level direction reversal |',
        '|---|---:|---:|']
    for key, row in data['wind'].items():
        lines.append(f"| {key} | {row['maximum_barotropic_adjustment_m_s']:.3f} m/s | {row['mean_monthly_scored_lower_reversal_share']:.2%} |")
    lines += ['', 'Corrections use consistent face velocities. Raw unprojected flow is not a valid '
        'closed-mass seasonal control. Small corrections alone cannot validate the '
        'circulation, but a huge projection-induced mean-flow reversal is not seen here.', '',
        '| Region / partial pressure window | Local midpoint / native water | Operational boundary / native water | Split-top quadrature / native water |',
        '|---|---:|---:|---:|']
    for region, row in data['humidity'].items():
        for window, values in row['windows'].items():
            lines.append(f"| {region} / {window} | {values['midpoint_to_native_mean_ratio']:.3f} | {values['operational_to_native_mean_ratio']:.3f} | {values['split_at_300hpa_quadrature_only_to_native_mean_ratio']:.3f} |")
    lines += ['', 'These are partial-column q dp/g comparisons, not complete atmospheric '
        'water, vapor import or rainfall. The local midpoint comparison isolates '
        'vertical quadrature; the operational boundary adds offshore averaging and '
        'saturation capping. Both use observed monthly means; no subdaily covariance '
        'is measured. No extrapolation beyond the native humidity pressure coverage.', '',
        'The proposed quadrature splits the original upper cell at 300 hPa and '
        'samples its lower portion at 453.975 hPa. This is a profile-only calculation, '
        'not a new five-layer climate or its rainfall prediction. Temperature, winds, '
        'microphysics and the unobserved humidity above 300 hPa still need an explicit '
        'consistent treatment before a five-layer simulation is prepared.', '',
        'Diagnose the pressure windows separately. A missing upper-partial moisture '
        'store does not by itself identify the cause of regional rain failure, '
        'and increasing upper humidity without consistent temperature/vertical '
        'resolution could simply trigger spurious saturation.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_water_sources_review')
    args = parser.parse_args(argv);data = analyse()
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'forcing_audit.json', data)
        (args.out/'forcing_audit.md').write_text(markdown(data))
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
