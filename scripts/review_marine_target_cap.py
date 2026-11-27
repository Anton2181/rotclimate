"""Review fixed cap pilot from actual fields; no model imports or refitting."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json
from review_padding_sensitivity import validate_state

PLAN = ROOT / 'calibration/marine_target_cap_20261127/plan.json'
OUT = ROOT / 'output/marine_target_cap_20261127'
TERMS = ['evaporation', 'marine_exchange', 'column_drying', 'convergence_import',
         'advection', 'diffusion', 'storm_exchange']


def main():
    assert not (OUT / 'review.json').exists(), 'Preserve completed review'
    plan = json.loads(PLAN.read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    assert protocol['plan_sha256'] == file_hash(PLAN)
    assert result['protocol_sha256'] == file_hash(OUT / 'protocol.json')
    for section in ['inputs_sha256', 'execution_sources_sha256', 'main_model_sources_sha256']:
        for name, digest in plan[section].items():
            assert file_hash(ROOT / name) == digest, name
    for name, digest in plan['private_files_sha256'].items():
        assert file_hash(OUT / 'model' / name) == digest, name
    assert [r['name'] for r in result['rows']] == [r['name'] for r in plan['cases']]
    assert len(result['rows']) == 6
    statistics, states, files = [], {}, {}
    for row, spec in zip(result['rows'], plan['cases'], strict=True):
        folder = OUT / row['name']
        assert row == json.loads((folder / 'result.json').read_text())
        assert row['status'] == 'passed' and row['numerical_certificate']['all_checks_passed']
        assert row['residual_tolerance'] == .01
        assert file_hash(folder / 'fields.npz') == row['fields_sha256']
        assert json.loads((folder / 'attempt.json').read_text()) == dict(spec=spec, protocol_sha256=file_hash(OUT / 'protocol.json'))
        with np.load(folder / 'fields.npz') as z:
            state = dict(z)
        validate_state(state)
        with np.load(ROOT / spec['reference_fields']) as old:
            for name in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P', 'days']:
                np.testing.assert_array_equal(state[name], old[name])
            if row['arm'] == 'legacy':
                assert row['legacy_control_exact']
                for name in ['T', 'P', 'E', 'W', 'u', 'v', 'step_gain', 'step_sinkd', 'step_W', 'step_P']:
                    assert state[name].dtype == old[name].dtype and state[name].shape == old[name].shape
                    assert state[name].tobytes() == old[name].tobytes()
        t = float(np.abs(state['T'] - state['obs_T']).mean())
        rain, obs = state['P'].astype(float), state['obs_P'].astype(float)
        annual, observed = rain.sum(0), obs.sum(0)
        p = float(.5 * (np.sqrt(np.mean(np.log((annual + 50) / (observed + 50)) ** 2))
                        + 12 * np.abs(rain - obs).mean() / (observed.mean() + 120)))
        np.testing.assert_allclose([t, p], [row['metrics']['temperature_mae_C'], row['metrics']['rain_loss']], rtol=1e-12, atol=1e-12)
        terms = [state['budget__' + k].astype(float) for k in TERMS]
        raw_rain = state['step_P'].astype(np.float32).astype(float)
        residual = state['budget__residual'].astype(float)
        rounding = 8 * np.finfo(np.float32).eps * (np.abs(raw_rain) + sum(np.abs(a) for a in terms))
        assert np.all(np.abs(sum(terms) - raw_rain - residual) <= rounding + 1e-12)
        scale = np.maximum(raw_rain + np.abs(sum(terms[:4])), .1)
        assert np.all(np.abs(residual) <= .01 * scale + rounding + 1e-12)
        stat = dict(region=row['region'], arm=row['arm'], temperature_mae_C=t, rain_loss=p,
            annual_rain_mm=float(annual.mean()), observed_annual_rain_mm=float(observed.mean()),
            annual_sources_mm={k:float(a.mean() * 365) for k, a in zip(TERMS, terms, strict=True)},
            mean_absolute_residual_mm_day=float(np.abs(residual).mean()),
            max_scaled_residual=float(np.max(np.abs(residual) / scale)))
        if row['arm'] == 'cap':
            target, legacy, source, rate = [state['target__' + k] for k in ['bounded', 'legacy', 'source', 'rate']]
            assert all(np.isfinite(a).all() and (a >= 0).all() for a in [target, legacy, source, rate])
            np.testing.assert_array_equal(target, np.minimum(legacy, source))
            expected = rate * (target - state['step_W'])
            assert np.all(np.abs(expected - state['budget__marine_exchange']) <=
                4 * np.finfo(np.float32).eps * np.maximum(np.abs(expected), 1.))
            active = rate > 0
            stat.update(target_binding_fraction=float((target < legacy).mean()),
                active_rate_sample_fraction=float(active.mean()),
                binding_fraction_when_rate_positive=float((target[active] < legacy[active]).mean()) if active.any() else None)
        statistics.append(stat)
        states[row['region'], row['arm']] = state
        for name in ['attempt.json', 'result.json', 'fields.npz']:
            f = folder / name
            files[str(f.relative_to(OUT))] = file_hash(f)
    comparisons = []
    for region in plan['regions']:
        before, after = [next(r for r in statistics if r['region'] == region and r['arm'] == a) for a in ['legacy', 'cap']]
        comparisons.append(dict(region=region, T_ratio=after['temperature_mae_C'] / before['temperature_mae_C'],
            rain_loss_ratio=after['rain_loss'] / before['rain_loss'], annual_rain_change_mm=after['annual_rain_mm'] - before['annual_rain_mm'],
            annual_source_changes_mm={k:after['annual_sources_mm'][k] - v for k, v in before['annual_sources_mm'].items()}))
    decision = (all(r['T_ratio'] <= 1.01 and r['rain_loss_ratio'] <= 1.01 for r in comparisons)
                and next(r for r in comparisons if r['region'] == 's_2n_43e')['rain_loss_ratio'] <= .99)
    figure(plan, states)
    write_json(OUT / 'review.json', dict(status='reviewed_fixed_boolean_cap_pilot_not_global_qualification',
        protocol_sha256=file_hash(OUT / 'protocol.json'), results_sha256=file_hash(OUT / 'results.json'),
        statistics=statistics, comparisons=comparisons, files_sha256=files,
        prospective_screen_eligible_for_further_exposed_evaluation=bool(decision),
        screen=plan['screen'], figure_sha256=file_hash(OUT / 'cap_response.png'),
        interpretation='Three exposed regional responses, not planetary skill, source tagging, causal isolation, a replacement for full validation or a deployable climate.',
        climate_adopted=False, atlas_changed=False))
    print('Six-case cap pilot reviewed; prospective local screen:', bool(decision))


def figure(plan, states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for col, (region, title) in enumerate(zip(plan['regions'], ['Somalia', 'Sahara', 'North India'], strict=True)):
        a, b = states[region, 'legacy'], states[region, 'cap']
        months = np.arange(1, 13)
        for field, row, unit in [('P', 0, 'Rain (mm/model month)'), ('T', 1, 'Temperature (C)')]:
            ax = axes[row, col]
            ax.plot(months, a[field].mean(1), label='Legacy target', color='#377d8d')
            ax.plot(months, b[field].mean(1), label='Source cap', color='#b47552')
            ax.plot(months, a['obs_' + field].mean(1), '--', label='Fixed observations', color='#777777')
            ax.set(ylabel=unit, xticks=[1, 4, 7, 10, 12], xlabel='Model month')
            ax.grid(alpha=.15)
        axes[0, col].set_title(title)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Fixed marine-equilibrium target cap: coupled responses at identical scored cells')
    fig.text(.5, .035, 'No fitted coefficients; same warm/onshore/distance laws. Realized rates can respond to coupled climate changes.\n'
             'Three exposed cases are a diagnostic pilot, not global validation or a selected climate. Numerical failures stop execution and are never retried automatically.', ha='center', fontsize=8)
    fig.subplots_adjust(left=.07, right=.98, top=.89, bottom=.14, hspace=.35, wspace=.32)
    fig.savefig(OUT / 'cap_response.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
