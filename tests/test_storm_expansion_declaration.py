import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_development_pool_adds_spent_sets_without_leaking_reserved_holdout():
    plan = json.loads((ROOT / 'calibration/storm_expansion_20261103/plan.json').read_text())
    old = set(plan['historical49'])
    spent_d = set(json.loads((ROOT / 'calibration/sealed_20261101d/regions.json').read_text()))
    spent_e = set(json.loads((ROOT / 'calibration/sealed_20261102e/regions.json').read_text()))
    unopened = set(json.loads((ROOT / plan['holdout']).read_text()))
    assert len(old) == 49 and len(set(plan['regions'])) == 61
    assert set(plan['regions']) == old | spent_d | spent_e
    assert not unopened & set(plan['regions'])


def test_fixed_storm_families_preserve_planet_and_declared_strength_bases():
    plan = json.loads((ROOT / 'calibration/storm_expansion_20261103/plan.json').read_text())
    read = lambda p: json.loads((ROOT / p).read_text())
    raw = read(plan['raw_reference']); ref = read(plan['reference'])
    assert {k for k in raw if raw[k] != ref[k]} <= {'moisture_relaxation', 'picard_iters'}
    for name, path in plan['candidates'].items():
        p = read(path)
        base = raw if name == 'storm_r43' else read('calibration/local_accuracy_20261023/r42_params.json')
        assert {k for k in base if base[k] != p[k]} <= {'moisture_relaxation', 'picard_iters', 'eddy_moisture_scheme'}
        assert p['eddy_moisture_scheme'] == 'conservative'
        assert p['wind_source'] == p['sst_source'] == 'model'
