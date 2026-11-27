"""Review seven predeclared golden-field regressions; no model/gate calls."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'output/no_sea_inflow_guard_20261127'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE / 'plan.json').read_text())
    folder = OUT / 'guarded'
    summary = json.loads((folder / 'summary.json').read_text())
    protocol = json.loads((folder / 'protocol.json').read_text())
    assert summary['complete'] and set(summary['regions']) == set(plan['regions'])
    for section in ['model_sources_sha256', 'inputs_sha256']:
        for name, expected in plan[section].items():
            assert digest(ROOT / name) == expected, name
    rows, files = [], {}
    for name in plan['regions']:
        ref = plan['reference'][name]
        baseline_path = ROOT / ref['case_json']
        assert digest(baseline_path) == ref['case_json_sha256']
        baseline = json.loads(baseline_path.read_text())
        current = summary['regions'][name]
        assert baseline['status'] == current['status'] == 'passed'
        assert baseline['numerics']['all_checks_passed'] and current['numerics']['all_checks_passed']
        assert baseline['case_identity'] == current['case_identity']
        old_fields, new_fields = ROOT / ref['cells'], folder / 'cells' / (name + '.npz')
        assert digest(old_fields) == ref['cells_sha256']
        assert digest(new_fields) == current['cells_sha256']
        old_protocol_path = baseline_path.parent.parent / 'protocol.json'
        assert digest(old_protocol_path) == ref['protocol_sha256']
        old_protocol = json.loads(old_protocol_path.read_text())
        assert old_protocol['params'] == protocol['params']
        assert old_protocol['region_specs'][name] == protocol['region_specs'][name]
        with np.load(old_fields) as a, np.load(new_fields) as b:
            for key in ['To', 'Po', 'lat', 'lon', 'i', 'j', 'elev', 'elev_max']:
                np.testing.assert_array_equal(a[key], b[key])
            identical = all(a[k].shape == b[k].shape and a[k].dtype == b[k].dtype
                            and a[k].tobytes() == b[k].tobytes() for k in ['Ts', 'Ps'])
            if name in plan['mixed_controls']:
                assert identical, 'Mixed-grid arithmetic changed: ' + name
        row = dict(region=name, all_land=name in plan['all_land_cases'],
            scored_TP_byte_exact=identical,
            baseline_T_mae_C=baseline['temperature']['monthly_mae_C'],
            guarded_T_mae_C=current['temperature']['monthly_mae_C'],
            baseline_rain_loss=baseline['rain']['loss'], guarded_rain_loss=current['rain']['loss'],
            baseline_annual_rain_mm=baseline['rain']['sim_mean_annual_mm'],
            guarded_annual_rain_mm=current['rain']['sim_mean_annual_mm'])
        rows.append(row)
        for path in [new_fields, folder / 'cases' / (name + '.json'), old_fields, baseline_path]:
            files[str(path.relative_to(ROOT))] = digest(path)
    result = dict(status='passed_source_geometry_regression_not_new_climate_qualification',
        plan_sha256=digest(HERE / 'plan.json'), protocol_sha256=digest(folder / 'protocol.json'),
        summary_sha256=digest(folder / 'summary.json'), rows=rows, files_sha256=files,
        all_seven_original_numerical_certificates_passed=True,
        all_three_mixed_controls_byte_exact=True, new_regional_integrations=7,
        new_97_region_paired_reference=False, climate_adopted=False, atlas_changed=False,
        interpretation='Explicit changed-source golden-field comparison on the same case inputs; not a candidate-selection reference, global skill or a revival of closed W18c.')
    target = OUT / 'review.json'
    rendered = json.dumps(result, indent=2) + '\n'
    if target.exists():
        assert target.read_text() == rendered
    else:
        target.write_text(rendered)
    for row in rows:
        if row['all_land']:
            print(row)


if __name__ == '__main__':
    main()
