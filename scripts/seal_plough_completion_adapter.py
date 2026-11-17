"""Seal manufactured analytical controls; no Earth capacity/adoption claim."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import read, write, sha, verify_parent
OUT = ROOT / 'output/plough_completion_adapter_20261117'


def main():
    assert not (OUT / 'qualification.json').exists()
    verify_parent(); r = read(OUT / 'results.json'); tests = read(OUT / 'tests.json')
    assert r['status'] == 'passed_nine_analytical_plough_package_controls_not_crop_feasibility'
    for n, h in r['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in r['files_sha256'].items(): assert sha(OUT / n) == h, n
    for n in ['results.json', *r['files_sha256']]: assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    assert tests['exit_code'] == 0 and tests['passed'] == 62
    for n, h in tests['tested_sources_sha256'].items(): assert sha(ROOT / n) == h, n
    parent_path = ROOT / 'output/plough_resource_contract_20261117'; parent = read(parent_path / 'qualification.json')
    for n, h in parent['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in parent['files_sha256'].items(): assert sha(parent_path / n) == h, n
    assert not r['complete_crop_activity'] and not r['grain_or_population_output']
    sources = dict(r['sources_sha256'])
    next_plan = 'calibration/roman_benchmark_20261117/cereal_seed_area_link.json'
    for n in ['scripts/seal_plough_completion_adapter.py', 'reports/PLOUGH_COMPLETION_ADAPTER_20261117.md', next_plan]: sources[n] = sha(ROOT / n)
    write(OUT / 'qualification.json', dict(status='passed_supplied_plough_resource_adapter_not_full_farm_or_atlas_feasibility',
        sources_sha256=sources, files_sha256={n: sha(OUT / n) for n in ['results.json', 'controls.csv', 'controls.json', 'tests.json']},
        tests_passed=62, manufactured_analytical_controls=9, fresh_controls_byte_exact=True,
        existing_scheduler_reused=True, operator_subset_enforced=True, simultaneous_draft_enforced=True,
        numerical_Roman_defaults_adopted=0, atlas_model_calls=0, complete_crop_activity=False,
        grain_or_population_output=False, new_fit=False, main_atlas_changed=False, adopt=False, next_plan=next_plan))
    print('Sealed tested plough-only adapter; no Earth resources or food outputs adopted')


if __name__ == '__main__': main()
