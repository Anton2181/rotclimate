"""Review completed fine arrays independently; never run a model or gate."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FOLDERS = [ROOT / 'output/ppe_20261126/ref58/r58_fine28',
           ROOT / 'output/ppe_20261127/W18c/runs/w1_005/candidate_fine28']


def array_scores(state):
    # benchmark_local saves all four fields at float32 after scoring float64.
    # One stored ULP bounds each original value; propagate those bounds through
    # absolute error, log RMSE and normalized monthly MAE, not a fitted tolerance.
    error = {k:np.abs(np.spacing(state[k])).astype(float) for k in ['Ts', 'To', 'Ps', 'Po']}
    T = float(np.abs(state['Ts'].astype(float) - state['To'].astype(float)).mean())
    T_bound = float((error['Ts'] + error['To']).mean())
    rain, obs = state['Ps'].astype(float), state['Po'].astype(float)
    annual, observed = rain.sum(0), obs.sum(0)
    da, db = error['Ps'].sum(0), error['Po'].sum(0)
    assert np.all(annual + 50 > da) and np.all(observed + 50 > db)
    log_error = da / (annual + 50 - da) + db / (observed + 50 - db)
    monthly = np.abs(rain - obs).mean()
    monthly_bound = (error['Ps'] + error['Po']).mean()
    denominator, denominator_bound = observed.mean() + 120, db.mean()
    normalized_bound = 12 * (monthly_bound / (denominator - denominator_bound)
        + monthly * denominator_bound / (denominator * (denominator - denominator_bound)))
    P = float(.5 * (np.sqrt(np.mean(np.log((annual + 50) / (observed + 50)) ** 2)) + 12 * monthly / denominator))
    P_bound = float(.5 * (np.sqrt(np.mean(log_error ** 2)) + normalized_bound))
    rounding = 64 * np.finfo(float).eps * np.maximum(np.abs([T, P]), 1.)
    return np.array([T, P]), np.array([T_bound, P_bound]) + rounding


def main():
    summaries = [json.loads((f / 'summary.json').read_text()) for f in FOLDERS]
    names = ['california', 'western_europe', 'japan', 'new_zealand']
    rows, files = [], {}
    for name in names:
        fields, scores, bounds, reported = [], [], [], []
        for folder, summary in zip(FOLDERS, summaries, strict=True):
            record = summary['regions'][name]
            assert record['status'] == 'passed' and record['numerics']['all_checks_passed']
            path = folder / 'cells' / (name + '.npz')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == record['cells_sha256']
            files[str(path.relative_to(ROOT))] = digest
            with np.load(path) as z:
                state = dict(z)
            fields.append(state)
            score, bound = array_scores(state)
            original = np.array([record['temperature']['monthly_mae_C'], record['rain']['loss']])
            assert np.all(np.abs(score - original) <= bound), 'Score exceeds archive quantization bound'
            scores.append(score.tolist())
            bounds.append(bound.tolist())
            reported.append(original.tolist())
        for key in ['To', 'Po', 'i', 'j', 'lat', 'lon', 'elev', 'elev_max']:
            np.testing.assert_array_equal(fields[0][key], fields[1][key])
        rows.append(dict(region=name, reference=scores[0], candidate=scores[1],
            archive_rounding_bounds=bounds, reported=reported))
    reference = np.mean([r['reference'] for r in rows], axis=0)
    candidate = np.mean([r['candidate'] for r in rows], axis=0)
    ratios = candidate / reference
    combined = float(ratios.mean())
    errors = np.mean([r['archive_rounding_bounds'] for r in rows], axis=0)
    bound = errors[1] / (reference - errors[0]) + candidate * errors[0] / (reference * (reference - errors[0]))
    gate = json.loads((HERE / 'gate_fine.json').read_text())
    reported_means = np.mean([r['reported'] for r in rows], axis=0)
    reported_ratios = reported_means[1] / reported_means[0]
    np.testing.assert_allclose([reported_ratios.mean(), * (reported_ratios - 1)],
        [gate['S28']['S'], gate['S28']['T'], gate['S28']['P']], rtol=1e-12, atol=1e-12)
    assert abs(combined - gate['S28']['S']) <= bound.mean()
    assert not gate['passes'] and combined - bound.mean() > 1.01
    for folder in FOLDERS:
        for name in ['summary.json', 'protocol.json']:
            f = folder / name
            files[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    result = dict(status='reviewed_permanent_W18c_fine_gate_failure', regions=rows,
        independent_S28=combined, independent_T_fractional_change=float(ratios[0] - 1),
        independent_rain_loss_fractional_change=float(ratios[1] - 1),
        aggregate_archive_rounding_bound=float(bound.mean()), original_gate_S28=gate['S28']['S'],
        archive_precision='Explicit propagated one-ULP float32 bounds; original gate/threshold unchanged.',
        original_threshold=1.01, all_eight_numerical_certificates_passed=True,
        matched_fine_observations_and_geometry=True, files_sha256=files,
        integrations=0, gate_reruns=0, alternate_finalist_selected=False, adopted=False)
    rendered = json.dumps(result, indent=2) + '\n'
    target = HERE / 'fine_array_review.json'
    if target.exists():
        assert target.read_text() == rendered
    else:
        target.write_text(rendered)
    print('Fine array review:', combined, 'FAIL, original threshold 1.01; no integrations/gate reruns.')


if __name__ == '__main__':
    main()
