"""Reconstruct wind components and compare public surface reference; no runs."""
import json
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from circulation_components import bilinear_monthly, pressure_velocity
from local_benchmark_protocol import file_hash, write_json
from review_padding_sensitivity import validate_state

PLAN = ROOT / 'calibration/circulation_components_20261127/plan.json'
OUT = ROOT / 'output/circulation_components_20261127'


def monthly(value):
    n = len(value)
    weights = np.zeros((12, n))
    for m in range(12):
        for k in range(n):
            weights[m, k] = max(0., min((m+1)*365/12, (k+1)*365/n) - max(m*365/12, k*365/n)) / (365/12)
    return np.tensordot(weights, value.astype(float), axes=(1, 0))


def main():
    assert not (OUT / 'review.json').exists(), 'Preserve completed review'
    plan = json.loads(PLAN.read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    assert protocol['plan_sha256'] == file_hash(PLAN)
    assert result['protocol_sha256'] == file_hash(OUT / 'protocol.json')
    for section in ['model_sources_sha256', 'execution_sources_sha256', 'inputs_sha256']:
        for name, digest in plan[section].items():
            assert file_hash(ROOT / name) == digest, name
    assert [r['name'] for r in result['rows']] == [s['name'] for s in plan['cases']]
    assert len(result['rows']) == 4
    with np.load(ROOT / plan['surface_reference']) as z:
        reference = dict(z)
    statistics, plots, files = [], {}, {}
    for row, spec in zip(result['rows'], plan['cases'], strict=True):
        folder = OUT / spec['name']
        assert row == json.loads((folder / 'result.json').read_text())
        assert row['status'] == 'passed' and row['numerical_certificate']['all_checks_passed']
        assert row['physical_and_budget_fields_byte_exact']
        assert file_hash(folder / 'capture.npz') == row['capture_sha256']
        with np.load(folder / 'capture.npz') as z:
            s = dict(z)
        validate_state(s)
        with np.load(ROOT / spec['reference_fields']) as old:
            for key in ['T', 'P', 'E', 'W', 'u', 'v', 'days', 'rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P', 'step_gain', 'step_sinkd', 'step_W', 'step_P']:
                assert s[key].dtype == old[key].dtype and s[key].shape == old[key].shape
                assert s[key].tobytes() == old[key].tobytes()
        ii, jj, c = s['rows'], s['cols'], row['constants']
        np.testing.assert_array_equal(s['grid_geo_lat'], s['grid_lat'])
        pressure_u, pressure_v = pressure_velocity(s['diag__current_pressure'], s['grid_lat'],
            s['grid_bl_drag'], c['dx_m'], c['omega'], c['rho'])
        np.testing.assert_allclose(pressure_u[:, ii, jj], s['diag__pressure_u'], atol=2e-12, rtol=1e-13)
        np.testing.assert_allclose(pressure_v[:, ii, jj], s['diag__pressure_v'], atol=2e-12, rtol=1e-13)
        drag = s['grid_drag'][ii, jj]
        for axis in ['u', 'v']:
            reconstructed = (s['diag__zonal_' + axis] + s['diag__pressure_' + axis]) * drag
            np.testing.assert_allclose(reconstructed, s['step_' + axis], atol=2e-12, rtol=1e-13)
            np.testing.assert_array_equal(s['step_' + axis], s['step_moisture_' + axis])
            exported = monthly(s['step_' + axis].astype(np.float32))
            np.testing.assert_allclose(exported, s[axis], atol=1e-10, rtol=1e-12)
        cell = c['dx_m'] / 1000
        filtered = gaussian_filter(s['diag__previous_pressure'], sigma=(0, 500/cell, 500/cell), mode='nearest')
        fall = np.sign(s['grid_lat']) * np.gradient(filtered, axis=-2) * 10 / cell
        gate = np.clip(fall / c['monsoon_pressure_hpa'], 0, 1)
        lat, phi = s['grid_lat'], s['diag__phi_i_full']
        hs = -(c['hadley_edge'] - c['hadley_shift'] * s['diag__season']) * c['hadley_scale']
        crossing = (((lat > 0) & (lat < phi) & (lat > hs[:, None, None]) & (phi > 0))
                    | ((lat < 0) & (lat >= phi) & (lat < s['diag__phi_h_full']) & (phi < 0)))
        obs_u = bilinear_monthly(reference['u'], s['lat'], s['lon'])
        obs_v = bilinear_monthly(reference['v'], s['lat'], s['lon'])
        surface_pressure = bilinear_monthly(reference['slp_pa'], s['grid_geo_lat'], s['grid_lon'])
        zonal_anomaly = reference['slp_pa'] - reference['slp_pa'].mean(2, keepdims=True)
        anomaly_pressure = bilinear_monthly(zonal_anomaly, s['grid_geo_lat'], s['grid_lon'])
        observed_falls = []
        for value in [surface_pressure, anomaly_pressure]:
            smooth = gaussian_filter(value, sigma=(0, 500/cell, 500/cell), mode='nearest')
            observed_falls.append((np.sign(lat) * np.gradient(smooth, axis=-2) * 10 / cell)[:, ii, jj].mean(1))
        curves = dict(model_u=s['u'].mean(1), model_v=s['v'].mean(1), obs_u=obs_u.mean(1), obs_v=obs_v.mean(1),
            belt_u=monthly(s['diag__zonal_u']*drag).mean(1), belt_v=monthly(s['diag__zonal_v']*drag).mean(1),
            pressure_u=monthly(s['diag__pressure_u']*drag).mean(1), pressure_v=monthly(s['diag__pressure_v']*drag).mean(1),
            previous_model_fall=monthly(fall[:, ii, jj]).mean(1), observed_full_fall=observed_falls[0],
            observed_zonal_anomaly_fall=observed_falls[1],
            normalized_gate=monthly(gate[:, ii, jj]).mean(1), crossing_fraction=monthly(crossing[:, ii, jj].astype(float)).mean(1),
            effective_gate=monthly((gate*crossing)[:, ii, jj]).mean(1))
        plots[spec['name']] = curves
        stats = dict(name=spec['name'], region=spec['region'], pad_km=spec['pad_km'],
            vector_rmse_m_s=float(np.sqrt(np.mean((s['u']-obs_u)**2 + (s['v']-obs_v)**2))),
            july={k:float(v[6]) for k, v in curves.items()},
            monthly={k:v.tolist() for k, v in curves.items()},
            whole_domain_crossing_fraction=float(crossing.mean()),
            whole_domain_effective_gate=float((gate*crossing).mean()),
            heat_and_moisture_winds_identical_at_scored_samples=True)
        statistics.append(stats)
        for name in ['attempt.json', 'result.json', 'capture.npz']:
            path = folder / name
            files[str(path.relative_to(OUT))] = file_hash(path)
    figure(plan, plots)
    write_json(OUT / 'review.json', dict(status='reviewed_exact_wind_components_not_climate_qualification',
        protocol_sha256=file_hash(OUT / 'protocol.json'), result_sha256=file_hash(OUT / 'results.json'),
        statistics=statistics, files_sha256=files, figure_sha256=file_hash(OUT / 'wind_components.png'),
        interpretation='Observed 1991-2020 surface sigma0.995 climatology is a diagnostic comparator, not 850hPa wind or a model forcing. Model pressure is a thermal anomaly; full observed SLP and its global-zonal anomaly are distinct diagnostics. No gate copied from observations.',
        parameters_changed=False, climate_adopted=False, atlas_changed=False))
    print('Reconstructed all four wind decompositions; exact physical controls; no observed forcing.')


def figure(plan, plots):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 4, figsize=(17, 10))
    for col, spec in enumerate(plan['cases']):
        c = plots[spec['name']]
        for row, axis in enumerate(['u', 'v']):
            ax = axes[row, col]
            for key, label, color, style in [('model_', 'Model total', '#222222', '-'), ('obs_', 'NCEP surface', '#777777', '--'),
                    ('belt_', 'Belt/turning contribution', '#377d8d', '-'), ('pressure_', 'Pressure contribution', '#b47552', '-')]:
                ax.plot(range(1,13), c[key+axis], label=label, color=color, linestyle=style)
            ax.axhline(0, color='#aaaaaa', linewidth=.6)
            ax.set(ylabel=('Eastward' if axis=='u' else 'Northward')+' wind (m/s)')
        axes[0,col].set_title(spec['title'])
        ax = axes[2,col]
        ax.plot(range(1,13), c['normalized_gate'], color='#377d8d', label='Pressure gate fraction')
        ax.plot(range(1,13), c['crossing_fraction'], color='#777777', linestyle='--', label='Crossing eligible fraction')
        ax.plot(range(1,13), c['effective_gate'], color='#b47552', label='Stepwise gate x crossing')
        ax.set(ylim=(-.05,1.05), ylabel='Scored-sample fractions', xlabel='Model month')
        for row in range(3):
            axes[row,col].set_xticks([1,4,7,10,12])
            axes[row,col].grid(alpha=.15)
    axes[0,0].legend(fontsize=7)
    axes[2,0].legend(fontsize=7)
    fig.suptitle('Unchanged r58 physical replays: wind contributions and pressure-turning gate')
    fig.text(.5,.025,'Surface reference is diagnostic only (NCEP/NCAR 1991-2020, 2.5 degrees). Components reconstruct actual model samples.\n'
        'Gate uses the previous-step model thermal-pressure anomaly; this is not a full-pressure comparison, causal intervention or new climate.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.06,right=.99,top=.92,bottom=.11,wspace=.36,hspace=.30)
    fig.savefig(OUT / 'wind_components.png',dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
