"""Measure saved regional Gaussian support and boundary-extension sensitivity."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, freeze, write_json

PLAN = ROOT / 'calibration/convergence_boundary_audit_20261126/plan.json'
OUT = ROOT / 'output/convergence_boundary_audit_20261126'
PARENT = ROOT / 'output/somalia_mechanism_20261126'
MODES = ['reflect', 'nearest', 'constant']


def main():
    assert not (OUT / 'results.json').exists(), 'Preserve completed boundary audit'
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    plan = json.loads(PLAN.read_text())
    parameter_path = ROOT / 'calibration/local_accuracy_20261023/r58_params.json'
    p = json.loads(parameter_path.read_text())
    for name, expected in dict(monsoon_heating=0., moisture_pressure_drag_ratio=1.,
        moisture_thermal_height_km=0., moisture_mass_balance=False, moisture_wind_factor=1.,
        water_land_friction=0., moisture_reservoirs=False).items():
        assert p[name] == expected, name
    qualification_path = ROOT / 'output/convergence_import_audit_20261126/qualification.json'
    qualification = json.loads(qualification_path.read_text())
    for name, digest in qualification['sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in qualification['files_sha256'].items():
        assert file_hash(qualification_path.parent / name) == digest, name
    paths = [PLAN, Path(__file__), parameter_path, qualification_path, ROOT / 'rotclimate/model.py',
             ROOT / 'scripts/local_benchmark_protocol.py']
    paths += [PARENT / c['region'] / c['variant'] / 'fields.npz' for c in plan['cases']]
    sources = {str(path.relative_to(ROOT)):file_hash(path) for path in paths}
    OUT.mkdir(parents=True, exist_ok=True)
    sigma = p['flux_scale_km'] / 56.
    freeze(OUT / 'preparation.json', dict(plan=plan, sources_sha256=sources, sigma_cells=sigma,
                                        truncate=4., scipy_version=__import__('scipy').__version__))
    rows, summaries = [], []
    for case in plan['cases']:
        region, variant = case['region'], case['variant']
        with np.load(PARENT / region / variant / 'fields.npz') as packet:
            f = dict(packet)
        mask = f['mask']
        ii, jj = np.nonzero(mask)
        mass = ndi.gaussian_filter(np.ones(mask.shape), sigma, mode='constant', cval=0.)
        exterior = 1 - mass[mask]
        filtered = {mode:[] for mode in MODES}
        for m in range(12):
            # Monthly proxy: no temperature gate, multiplication by W or gain reconstruction.
            divergence = (np.gradient(f['u'][m].astype(float), axis=1)
                          - np.gradient(f['v'][m].astype(float), axis=0)) / 56000.
            smooth = {mode:ndi.gaussian_filter(divergence, sigma, mode=mode, cval=0.) for mode in MODES}
            for mode in MODES:
                filtered[mode].append(smooth[mode][mask])
            for r, c in zip(ii, jj):
                row = dict(region=region, variant=variant, month=m + 1, row=int(r), col=int(c),
                           nominal_in_domain_kernel_mass=float(mass[r, c]),
                           nominal_exterior_kernel_mass=float(1 - mass[r, c]),
                           monthly_raw_divergence_per_s=float(divergence[r, c]))
                for mode in MODES:
                    value = float(smooth[mode][r, c])
                    row[mode + '_smoothed_divergence_per_s'] = value
                    row[mode + '_positive_convergence_proxy_per_day'] = float(np.clip(-value, 0., 1e-5) * 86400)
                rows.append(row)
        reference = np.array(filtered['reflect'])
        summaries.append(dict(region=region, variant=variant, scored_cells=len(ii),
            grid_shape=list(mask.shape), cell_month_rows=len(ii) * 12,
            nominal_exterior_kernel_mass=dict(min=float(exterior.min()), mean=float(exterior.mean()), max=float(exterior.max())),
            extensions={mode:dict(mean_signed_divergence_per_s=float(np.mean(values)),
                mean_positive_convergence_proxy_per_day=float(np.clip(-np.array(values), 0., 1e-5).mean() * 86400),
                sign_disagreement_cell_months=int(np.count_nonzero(np.sign(values) != np.sign(reference))),
                mean_absolute_difference_from_reflect_per_s=float(np.mean(np.abs(np.array(values) - reference))))
                for mode, values in filtered.items()}))
    with (OUT / 'cell_months.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for name, digest in sources.items():
        assert file_hash(ROOT / name) == digest, name
    write_json(OUT / 'results.json', dict(status='completed_saved_field_boundary_stress_audit', sources_sha256=sources,
        files_sha256={'cell_months.csv':file_hash(OUT / 'cell_months.csv')}, summaries=summaries,
        sigma_cells=sigma, radius_cells=int(4 * sigma + .5), cell_km=56., truncate=4.,
        climate_integrations=0, climate_adopted=False,
        interpretation='Exterior kernel weight and monthly frozen-field extension sensitivity only. Neither outside-domain winds, actual instantaneous gain nor rainfall bias are established; no boundary mode is selected.'))
    print(json.dumps(summaries, indent=1))


if __name__ == '__main__':
    main()
