"""Check prepared domain footprints and the live integration interlock."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json

OUT = ROOT / 'output/padding_sensitivity_20261126'
PLAN = ROOT / 'calibration/padding_sensitivity_20261126/plan.json'


def main():
    assert not (OUT / 'preparation_review.json').exists()
    plan = json.loads(PLAN.read_text())
    prepared = json.loads((OUT / 'preparation.json').read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    assert prepared['status'] == 'prepared_no_climate_integrations' and prepared['climate_integrations'] == 0
    assert prepared['plan_sha256'] == protocol['plan_sha256'] == file_hash(PLAN)
    assert prepared['protocol_sha256'] == file_hash(OUT / 'protocol.json')
    assert protocol['runner_sha256'] == file_hash(ROOT / 'scripts/padding_sensitivity.py')
    assert len(prepared['cases']) == plan['maximum_integrations'] == 9
    sources = {**plan['model_sources_sha256'], **plan['cache_seed_sha256'], **protocol['helper_sources_sha256']}
    for name, digest in sources.items():
        private = OUT / 'model' / name
        assert not private.is_symlink() and private.is_file()
        assert file_hash(private) == digest, name
        assert file_hash(ROOT / name) == digest, name
        assert private.stat().st_ino != (ROOT / name).stat().st_ino or private.stat().st_dev != (ROOT / name).stat().st_dev
    for name, digest in plan['inputs_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    files = {name:file_hash(OUT / name) for name in ['preparation.json', 'protocol.json']}
    counts = {}
    exact_values = 0
    for region in plan['regions']:
        base = None
        for pad, offset in zip(plan['pads_km'], plan['pad_cell_offsets'], strict=True):
            folder = OUT / region / f'pad_{pad:g}'
            receipt = json.loads((folder / 'prepared.json').read_text())
            assert receipt in prepared['cases']
            assert receipt['footprint_sha256'] == file_hash(folder / 'footprint.npz')
            with np.load(folder / 'footprint.npz') as packet:
                data = dict(packet)
            assert len(data['rows']) == receipt['scored_cells']
            if base is None:
                base = data
                counts[region] = len(data['rows'])
            for key, values in data.items():
                if key in ['rows', 'cols']:
                    np.testing.assert_array_equal(values, base[key] + offset)
                elif key in ['lat', 'lon']:
                    np.testing.assert_allclose(values, base[key], rtol=0, atol=1e-10)
                else:
                    np.testing.assert_array_equal(values, base[key])
                    exact_values += values.size
            for name in ['prepared.json', 'footprint.npz']:
                path = folder / name
                files[str(path.relative_to(OUT))] = file_hash(path)
        if region == 'north_india':
            path = ROOT / 'output/ppe_20261126/ref58/r58_dev31/cells/north_india.npz'
            with np.load(path) as reference:
                np.testing.assert_array_equal(base['obs_T'], reference['To'])
                np.testing.assert_array_equal(base['obs_P'], reference['Po'])
                np.testing.assert_array_equal(base['rows'], reference['i'])
                np.testing.assert_array_equal(base['cols'], reference['j'])
        else:
            path = ROOT / 'output/somalia_mechanism_20261126' / region / 'control/fields.npz'
            with np.load(path) as reference:
                np.testing.assert_array_equal(base['obs_T'], reference['obs_T'][:, reference['mask']])
                np.testing.assert_array_equal(base['obs_P'], reference['obs_P'][:, reference['mask']])
    assert not list(OUT.rglob('attempt.json'))
    # Exercise the real CLI, not a mock predicate: it must stop before integration.
    attempt = subprocess.run([sys.executable, '-I', str(ROOT / 'scripts/padding_sensitivity.py'), '--run'],
                             text=True, capture_output=True, cwd=ROOT)
    assert attempt.returncode != 0 and 'W18c still active or nonterminal' in attempt.stderr
    assert not list(OUT.rglob('attempt.json'))
    write_json(OUT / 'preparation_review.json', dict(status='passed_preparation_only_no_climate_results',
        plan_sha256=file_hash(PLAN), protocol_sha256=file_hash(OUT / 'protocol.json'),
        reviewer_sha256=file_hash(Path(__file__)), files_sha256=files,
        historical_context_sha256={name:file_hash(ROOT / name) for name in
            ['calibration/map_edge_20261124/README.md', 'calibration/edge_moisture_20261124/findings.md']},
        private_regular_files_checked=len(sources), exact_scored_static_values_checked=exact_values,
        scored_cells=counts, all_nine_footprints_checked=True, active_W18c_live_CLI_interlock_test_passed=True,
        no_integration_attempts=True, climate_integrations=0, climate_adopted=False))
    print(json.dumps(dict(private_files=len(sources), exact_static_values=exact_values, scored_cells=counts,
                         no_climate_integrations=True, live_interlock_passed=True)))


if __name__ == '__main__':
    main()
