"""Account for completed padding responses without integrations or tuning."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/padding_sensitivity_parallel_20261127'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    review = json.loads((OUT / 'review.json').read_text())
    assert review['all_nine_cases_passed']
    assert not review['preserved_failures'] and not review['unavailable_pairs']
    assert review['aggregate_score'] is None
    for name, expected in review['files_sha256'].items():
        assert digest(OUT / name) == expected, name
    assert digest(OUT / 'padding_changes.png') == review['figure_sha256']
    assert digest(OUT / 'results.json') == review['result_sha256']
    plan_path = ROOT / 'calibration/padding_sensitivity_parallel_20261127/plan.json'
    assert digest(plan_path) == review['plan_sha256']
    plan = json.loads(plan_path.read_text())
    records = []
    for stat in review['statistics']:
        folder = OUT / stat['region'] / f"pad_{stat['pad_km']:g}"
        with np.load(folder / 'fields.npz') as z:
            P = z['P'].astype(float)
            E = z['E'].astype(float)
            nt, nc = z['step_W'].shape
            import_step = z['step_gain'] * z['step_W']
            drying_step = -z['step_sinkd'] * z['step_W']
            source_monthly = np.zeros((2, 12, nc))
            for m in range(12):
                for k in range(nt):
                    overlap = max(0., min((m + 1) * 365 / 12, (k + 1) * 365 / nt)
                                  - max(m * 365 / 12, k * 365 / nt))
                    source_monthly[0, m] += import_step[k] * overlap
                    source_monthly[1, m] += drying_step[k] * overlap
            annual = dict(rain_mm=float(P.sum(0).mean()), surface_E_mm=float(E.sum(0).mean()),
                import_mm=float(import_step.mean() * 365), drying_mm=float(drying_step.mean() * 365))
            for key, field in [('rain_mm', 'annual_rain_mm'), ('import_mm', 'annual_import_mm'),
                               ('drying_mm', 'annual_drying_mm')]:
                assert math.isclose(annual[key], stat[field], rel_tol=1e-12, abs_tol=1e-10)
            np.testing.assert_allclose(source_monthly.sum(1).mean(1),
                [annual['import_mm'], annual['drying_mm']], rtol=1e-12, atol=1e-10)
            remainder = P - E - source_monthly.sum(0)
            annual['unpartitioned_remainder_mm'] = float(remainder.sum(0).mean())
            assert math.isclose(annual['rain_mm'], sum(annual[k] for k in
                ['surface_E_mm', 'import_mm', 'drying_mm', 'unpartitioned_remainder_mm']),
                rel_tol=1e-12, abs_tol=1e-10)
            records.append(dict(region=stat['region'], pad_km=stat['pad_km'], **annual))
    assert len(records) == len(plan['regions']) * len(plan['pads_km']) == 9
    differences = []
    for region in plan['regions']:
        base = next(r for r in records if r['region'] == region and r['pad_km'] == plan['pads_km'][0])
        for other in [r for r in records if r['region'] == region and r['pad_km'] != base['pad_km']]:
            delta = {k: other[k] - base[k] for k in base if k not in ['region', 'pad_km']}
            differences.append(dict(region=region, from_pad_km=base['pad_km'], to_pad_km=other['pad_km'], **delta))
    result = dict(status='descriptive_accounting_not_budget_closure_or_causal_attribution',
        review_sha256=digest(OUT / 'review.json'), producer_sha256=digest(Path(__file__)),
        annual_scored_cell_means=records, changes_from_control=differences,
        interpretation='Remainder is defined as P minus surface E, actual instantaneous import and drying. '
            'It includes unrecorded advection, diffusion, storm/marine exchange and equation residual; '
            'it is not measured boundary transport, a separated process or a closure certificate.',
        integrations=0, climate_adopted=False, atlas_changed=False)
    destination = OUT / 'completed_accounting.json'
    rendered = json.dumps(result, indent=2) + '\n'
    if destination.exists():
        assert destination.read_text() == rendered, 'Preserve completed analysis'
    else:
        destination.write_text(rendered)
    for row in differences:
        print(row)


if __name__ == '__main__':
    main()
