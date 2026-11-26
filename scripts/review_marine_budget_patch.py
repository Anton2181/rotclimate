"""Review saved private comparisons and regression results without reruns."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json

OUT = ROOT / 'output/marine_budget_export_patch_20261126'
PLAN = ROOT / 'calibration/marine_budget_export_patch_20261126/plan.json'
PHYSICAL = ['T', 'Tsl', 'P', 'W', 'u', 'v', 'E']


def main():
    assert not (OUT / 'review.json').exists()
    plan = json.loads(PLAN.read_text())
    prep = json.loads((OUT / 'preparation.json').read_text())
    protocol = json.loads((OUT / 'validation_protocol.json').read_text())
    assert prep['plan_sha256'] == protocol['plan_sha256'] == file_hash(PLAN)
    assert protocol['preparation_sha256'] == file_hash(OUT / 'preparation.json')
    assert protocol['validator_sha256'] == file_hash(ROOT / 'scripts/validate_marine_budget_patch.py')
    for name, digest in prep['sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
        assert file_hash(OUT / 'baseline' / name) == digest, name
    for name, digest in prep['patched_sources_sha256'].items():
        assert file_hash(OUT / 'patched' / name) == digest, name
    assert prep['patch_sha256'] == file_hash(PLAN.parent / 'marine_budget.patch')
    results = []
    files = {}
    scalar_comparisons = 0
    for name in ['concentration', 'flux', 'reservoir']:
        loaded = {}
        receipts = {}
        for version, label in [('baseline', name + '_diagnosed'), ('patched', name + '_diagnosed'),
                               ('patched', name + '_ordinary')]:
            folder = OUT / ('validation_' + version) / label
            record = json.loads((folder / 'result.json').read_text())
            assert record['status'] == 'passed'
            assert record['fields_sha256'] == file_hash(folder / 'fields.npz')
            key = version + ('_diagnosed' if label.endswith('_diagnosed') else '_ordinary')
            with np.load(folder / 'fields.npz') as packet:
                loaded[key] = dict(packet)
            receipts[key] = record
            for path in [folder / n for n in ['attempt.json', 'result.json', 'fields.npz']]:
                files[str(path.relative_to(OUT))] = file_hash(path)
        base, new, ordinary = [loaded[key] for key in ['baseline_diagnosed', 'patched_diagnosed', 'patched_ordinary']]
        for key in PHYSICAL + (['layer_water'] if name == 'reservoir' else []):
            for other in [new, ordinary]:
                np.testing.assert_array_equal(base[key], other[key])
                assert base[key].dtype == other[key].dtype and base[key].tobytes() == other[key].tobytes()
                scalar_comparisons += base[key].size
        for key in base:
            if key.startswith('budget__') and key not in ['budget__residual', 'budget__absolute_residual']:
                np.testing.assert_array_equal(base[key], new[key])
        marine = new['budget__marine_exchange'].astype(float)
        old_residual = base['budget__residual'].astype(float)
        new_residual = new['budget__residual'].astype(float)
        # Independent relation: same physical terms, precisely one missing source added.
        bound = 8 * np.finfo(np.float32).eps * (np.abs(old_residual) + np.abs(marine) + 1.)
        assert np.all(np.abs(new_residual - old_residual - marine) <= bound)
        np.testing.assert_array_equal(new['budget__absolute_residual'], np.abs(new['budget__residual']))
        if name == 'reservoir':
            assert not marine.any()
            np.testing.assert_array_equal(old_residual, new_residual)
        assert receipts['patched_diagnosed']['numerics']['all_checks_passed']
        assert receipts['patched_ordinary']['numerics']['all_checks_passed']
        results.append(dict(name=name, all_physical_arrays_exact=True,
            original_all_checks_passed=receipts['baseline_diagnosed']['numerics']['all_checks_passed'],
            patched_all_checks_passed=True, marine_min_mm_day=float(marine.min()), marine_max_mm_day=float(marine.max()),
            original_export_max_abs_residual_mm_day=float(np.abs(old_residual).max()),
            patched_export_max_abs_residual_mm_day=float(np.abs(new_residual).max()),
            original_flux_scaled_residual=receipts['baseline_diagnosed']['numerics'].get('vapor_flux_budget', {}).get('max_scaled_equation_residual'),
            patched_flux_scaled_residual=receipts['patched_diagnosed']['numerics'].get('vapor_flux_budget', {}).get('max_scaled_equation_residual')))
    suites = ET.parse(OUT / 'unit_tests.xml').getroot()
    children = [suites] if suites.tag == 'testsuite' else list(suites.iter('testsuite'))
    totals = {key:sum(int(s.attrib.get(key, 0)) for s in children) for key in ['tests', 'errors', 'failures', 'skipped']}
    assert totals['tests'] > 0 and totals['errors'] == totals['failures'] == totals['skipped'] == 0
    for n in ['preparation.json', 'validation_protocol.json', 'validation_baseline.json', 'validation_patched.json', 'unit_tests.xml', 'unit_tests.log']:
        files[n] = file_hash(OUT / n)
    write_json(OUT / 'review.json', dict(status='passed_unapplied_private_patch_review',
        plan_sha256=file_hash(PLAN), patch_sha256=file_hash(PLAN.parent / 'marine_budget.patch'),
        reviewer_sha256=file_hash(Path(__file__)), files_sha256=files, cases=results,
        paired_toy_integrations=9, physical_scalar_comparisons=scalar_comparisons, unit_test_totals=totals,
        main_patch_applied=False, main_physical_source_unchanged=True, original_failures_preserved=True,
        earth_region_integrations=0, climate_adopted=False, atlas_changed=False))
    print(json.dumps(dict(cases=results, physical_scalar_comparisons=scalar_comparisons, tests=totals), indent=1))


if __name__ == '__main__':
    main()
