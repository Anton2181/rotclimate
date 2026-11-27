"""Review a fixed padding study after execution; never start integrations."""
import argparse
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json

PLAN = ROOT / 'calibration/padding_sensitivity_20261126/plan.json'
OUT = ROOT / 'output/padding_sensitivity_20261126'
MONTHLY = dict(T='C', P='mm/model month', E='mm/model month', W='mm', u='m/s', v='m/s')


def validate_state(state):
    n = len(state['rows'])
    if not n or state['cols'].shape != (n,):
        raise ValueError('Nonempty fixed scored cells required')
    for name in [*MONTHLY, 'obs_T', 'obs_P']:
        value = state[name]
        if value.shape != (12, n) or not np.isfinite(value).all():
            raise ValueError('Invalid monthly field: ' + name)
    for name in ['P', 'obs_P']:
        if (state[name] < 0).any():
            raise ValueError('Negative rainfall: ' + name)
    for name in ['lat', 'lon']:
        if state[name].shape != (n,) or not np.isfinite(state[name]).all():
            raise ValueError('Invalid scored coordinates')
    nt = len(state['days'])
    if not nt or not np.isfinite(state['days']).all():
        raise ValueError('Missing trace calendar')
    np.testing.assert_allclose(state['days'], (np.arange(nt) + .5) * 365 / nt, rtol=0, atol=1e-10)
    for name in ['step_gain', 'step_sinkd', 'step_W', 'step_P']:
        value = state[name]
        if value.shape != (nt, n) or not np.isfinite(value).all() or (value < 0).any():
            raise ValueError('Invalid instantaneous field: ' + name)
    # Raw result fields are stored at float32 before model-month averaging.
    # Reconstruct independently from actual saved trace values, retaining that rounding.
    for source, target, amount in [('step_P', 'P', True), ('step_W', 'W', False)]:
        reconstructed = np.zeros((12, n))
        for m in range(12):
            for k in range(nt):
                overlap = max(0., min((m + 1) * 365 / 12, (k + 1) * 365 / nt)
                              - max(m * 365 / 12, k * 365 / nt))
                reconstructed[m] += state[source][k].astype(np.float32).astype(float) * overlap
        if not amount:
            reconstructed /= 365 / 12
        bound = 4 * np.finfo(np.float32).eps * np.maximum(np.abs(reconstructed), 1.)
        if not np.all(np.abs(state[target] - reconstructed) <= bound):
            raise ValueError('Monthly fields do not match the instantaneous trace: ' + target)


def summarize_state(state):
    validate_state(state)
    simulated = state['P'].astype(float)
    observed = state['obs_P'].astype(float)
    sim_annual, obs_annual = simulated.sum(0), observed.sum(0)
    log_rmse = float(np.sqrt(np.mean(np.log((sim_annual + 50) / (obs_annual + 50)) ** 2)))
    monthly_mae = float(np.abs(simulated - observed).mean())
    return dict(temperature_mae_C=float(np.abs(state['T'] - state['obs_T']).mean()),
        rain_loss=.5 * (log_rmse + 12 * monthly_mae / (float(obs_annual.mean()) + 120)),
        annual_rain_mm=float(sim_annual.mean()), observed_annual_rain_mm=float(obs_annual.mean()),
        annual_import_mm=float((state['step_gain'] * state['step_W']).mean() * 365),
        annual_drying_mm=-float((state['step_sinkd'] * state['step_W']).mean() * 365))


def compare_states(base, other, offset):
    validate_state(base)
    validate_state(other)
    for name in ['rows', 'cols']:
        np.testing.assert_array_equal(other[name], base[name] + offset, err_msg='Scored cells moved')
    for name in ['obs_T', 'obs_P', 'days']:
        np.testing.assert_array_equal(other[name], base[name], err_msg='Observation/calendar changed')
    for name in ['lat', 'lon']:
        np.testing.assert_allclose(other[name], base[name], atol=1e-10, rtol=0, err_msg='Coordinates moved')
    comparisons = {}
    for name, unit in MONTHLY.items():
        delta = other[name].astype(float) - base[name].astype(float)
        annual = delta.sum(0) if name in ['P', 'E'] else delta.mean(0)
        comparisons[name] = dict(monthly_unit=unit, annual_unit='mm/year' if name in ['P', 'E'] else unit,
            mean_signed_monthly_change=float(delta.mean()), mean_absolute_monthly_change=float(np.abs(delta).mean()),
            rms_monthly_change=float(np.sqrt(np.mean(delta ** 2))), max_absolute_monthly_change=float(np.abs(delta).max()),
            mean_signed_annual_change=float(annual.mean()), rms_annual_change=float(np.sqrt(np.mean(annual ** 2))),
            max_absolute_annual_change=float(np.abs(annual).max()))
    before, after = summarize_state(base), summarize_state(other)
    return dict(fields=comparisons, annual_import_change_mm=after['annual_import_mm'] - before['annual_import_mm'],
                annual_drying_change_mm=after['annual_drying_mm'] - before['annual_drying_mm'])


def make_comparisons(regions, pads, states, cell_km):
    comparisons, unavailable = [], []
    for region in regions:
        for first, second in itertools.combinations(pads, 2):
            pair = dict(region=region, from_pad_km=first, to_pad_km=second)
            if (region, first) not in states or (region, second) not in states:
                unavailable.append(pair)
                continue
            shift = (second - first) / cell_km
            if not float(shift).is_integer():
                raise ValueError('Comparison requires integer-cell padding increments')
            comparisons.append(dict(**pair, **compare_states(states[region, first], states[region, second], int(shift))))
    return comparisons, unavailable


def assert_control(region, state, archive_root=ROOT):
    if region == 'north_india':
        path = archive_root / 'output/ppe_20261126/ref58/r58_dev31/cells/north_india.npz'
        with np.load(path) as packet:
            for name, archived in [('T', 'Ts'), ('P', 'Ps')]:
                np.testing.assert_array_equal(state[name].astype(np.float32), packet[archived].astype(np.float32))
    else:
        path = archive_root / 'output/somalia_mechanism_20261126' / region / 'control/fields.npz'
        with np.load(path) as packet:
            for name in MONTHLY:
                np.testing.assert_array_equal(state[name].astype(np.float32), packet[name][:, packet['mask']].astype(np.float32))


def main():
    global PLAN, OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=PLAN)
    args = parser.parse_args()
    PLAN = args.plan.resolve()
    plan = json.loads(PLAN.read_text())
    OUT = ROOT / plan['out']
    if not (OUT / 'results.json').exists():
        raise SystemExit('Padding study has not completed; no physical results to review.')
    assert not (OUT / 'review.json').exists(), 'Preserve completed study review'
    preparation = json.loads((OUT / 'preparation.json').read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    assert protocol['plan_sha256'] == preparation['plan_sha256'] == file_hash(PLAN)
    assert protocol['runner_sha256'] == file_hash(ROOT / 'scripts/padding_sensitivity.py')
    for name, digest in {**plan['model_sources_sha256'], **plan['cache_seed_sha256'], **protocol['helper_sources_sha256']}.items():
        assert file_hash(OUT / 'model' / name) == digest, name
    for name, digest in plan['inputs_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    keys = [(r['region'], r['pad_km']) for r in result['rows']]
    assert len(keys) == len(set(keys))
    expected = {(r, p) for r in plan['regions'] for p in plan['pads_km']}
    if result['status'] == 'closed_control_failed':
        assert set(keys) == {(r, plan['pads_km'][0]) for r in plan['regions']}
        assert any(r['status'] == 'failed' for r in result['rows'])
    else:
        assert result['status'] == 'completed_fixed_padding_diagnostic' and set(keys) == expected
        assert result['all_numerical_checks_passed'] == all(r['status'] == 'passed' for r in result['rows'])
    states, statistics, failures, files = {}, [], [], {}
    for row in result['rows']:
        region, pad = row['region'], row['pad_km']
        folder = OUT / region / f'pad_{pad:g}'
        saved = json.loads((folder / 'result.json').read_text())
        assert row == saved
        attempt = json.loads((folder / 'attempt.json').read_text())
        assert attempt['protocol_sha256'] == file_hash(OUT / 'protocol.json')
        prepared = next(r for r in preparation['cases'] if r['region'] == region and r['pad_km'] == pad)
        assert row['case_identity'] == prepared['case_identity']
        assert file_hash(folder / 'footprint.npz') == prepared['footprint_sha256']
        for name in ['result.json', 'attempt.json', 'footprint.npz']:
            path = folder / name
            files[str(path.relative_to(OUT))] = file_hash(path)
        if row['status'] == 'failed':
            failures.append(row)
            continue
        assert row['status'] == 'passed' and row['numerics']['all_checks_passed']
        assert row['fields_sha256'] == file_hash(folder / 'fields.npz')
        with np.load(folder / 'fields.npz') as packet:
            state = dict(packet)
        with np.load(folder / 'footprint.npz') as fixed:
            for name in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P']:
                np.testing.assert_array_equal(state[name], fixed[name])
        if pad == plan['pads_km'][0]:
            assert row['exact_control_reproduction']
            assert_control(region, state)
        summary = summarize_state(state)
        for key in ['temperature_mae_C', 'annual_import_mm', 'annual_drying_mm']:
            assert math.isclose(summary[key], row[key], rel_tol=1e-12, abs_tol=1e-10), key
        assert math.isclose(summary['rain_loss'], row['rain']['loss'], rel_tol=1e-12, abs_tol=1e-10)
        states[region, pad] = state
        statistics.append(dict(region=region, pad_km=pad, **summary))
        files[str((folder / 'fields.npz').relative_to(OUT))] = file_hash(folder / 'fields.npz')
    comparisons, unavailable = make_comparisons(plan['regions'], plan['pads_km'], states, plan['cell_km'])
    figure(plan, statistics)
    write_json(OUT / 'review.json', dict(status='reviewed_padding_diagnostic_not_climate_qualification',
        result_sha256=file_hash(OUT / 'results.json'), plan_sha256=file_hash(PLAN), reviewer_sha256=file_hash(Path(__file__)),
        files_sha256=files, statistics=statistics, pairwise_changes=comparisons, unavailable_pairs=unavailable,
        preserved_failures=failures, all_nine_cases_passed=len(states) == 9, aggregate_score=None,
        figure_sha256=file_hash(OUT / 'padding_changes.png'), climate_adopted=False, atlas_changed=False,
        interpretation='Same-footprint state changes and instantaneous source integrals, not isolated convergence causality or evidence that the largest padding is truth. No best padding selected.'))
    print(f'Reviewed {len(states)} passed cases, retained {len(failures)} failures; no aggregate or adoption.')


def figure(plan, statistics):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    by_key = {(r['region'], r['pad_km']):r for r in statistics}
    titles = ['Somalia', 'Sahara', 'North India']
    for col, (region, title) in enumerate(zip(plan['regions'], titles, strict=True)):
        pads = plan['pads_km']
        records = [by_key.get((region, pad)) for pad in pads]
        annual = [r['annual_rain_mm'] if r else np.nan for r in records]
        imported = [r['annual_import_mm'] if r else np.nan for r in records]
        drying = [r['annual_drying_mm'] if r else np.nan for r in records]
        axes[0, col].plot(pads, annual, 'o-', color='#377d8d', label='Modeled annual rain')
        valid = next((r for r in records if r), None)
        if valid:
            axes[0, col].axhline(valid['observed_annual_rain_mm'], color='#777777', linestyle='--', label='Unchanged observations')
        axes[0, col].set(title=title, ylabel='Rain (mm/year)')
        axes[1, col].plot(pads, imported, 'o-', color='#377d8d', label='Convergence import')
        axes[1, col].plot(pads, drying, 'o-', color='#b47552', label='Column drying')
        axes[1, col].axhline(0, color='#777777', linewidth=.7)
        axes[1, col].set(xlabel='Real padding (km)', ylabel='Selected signed sources (mm/year)')
        for row in range(2):
            axes[row, col].grid(alpha=.15)
            axes[row, col].set_xticks(pads)
        if not all(records):
            axes[0, col].text(.02, .94, 'Missing/failed cases remain gaps', transform=axes[0, col].transAxes, fontsize=8, va='top')
    axes[0, 0].legend(fontsize=8)
    axes[1, 0].legend(fontsize=8)
    fig.suptitle('Unchanged r58 physics across fixed, aligned padding sizes', fontsize=15)
    fig.text(.5, .035, 'Identical scored cells and observations; failed cases are not zero-filled or averaged into a score.\n'
             'Larger domains change several operators. These are diagnostic responses, not a selected padding, climate adoption or proof of isolated causality.',
             ha='center', fontsize=9)
    fig.subplots_adjust(left=.065, right=.985, top=.90, bottom=.15, wspace=.32, hspace=.28)
    fig.savefig(OUT / 'padding_changes.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
