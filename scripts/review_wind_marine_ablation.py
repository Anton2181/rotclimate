"""Review twelve fixed wind-by-marine-relaxation diagnostics from saved arrays only."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT)]
from local_benchmark_protocol import file_hash, write_json
from padding_budget_capture import exact, equation_check, COMPONENTS
from review_padding_sensitivity import validate_state, summarize_state
from circulation_reference import projection_jacobian, geographic_wind
from circulation_components import bilinear_monthly

PLAN = ROOT / 'calibration/wind_marine_ablation_20261127/plan.json'
OUT = ROOT / 'output/wind_marine_ablation_20261127'


def main():
    assert not (OUT / 'review.json').exists(), 'Preserve completed review'
    plan = json.loads(PLAN.read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    preparation = json.loads((OUT / 'preparation.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    assert protocol['plan_sha256'] == preparation['plan_sha256'] == file_hash(PLAN)
    assert protocol['preparation_sha256'] == file_hash(OUT / 'preparation.json')
    assert result['protocol_sha256'] == file_hash(OUT / 'protocol.json')
    for section in ['inputs_sha256', 'execution_sources_sha256', 'model_sources_sha256']:
        for name, digest in plan[section].items():
            assert file_hash(ROOT / name) == digest, name
    for name, digest in plan['private_files_sha256'].items():
        f = OUT / 'model' / name
        assert not f.is_symlink() and f.stat().st_nlink == 1 and file_hash(f) == digest
    assert [r['name'] for r in result['rows']] == [s['name'] for s in plan['cases']]
    assert len(result['rows']) == plan['maximum_diagnostic_integrations'] == 12
    specs = json.loads((ROOT / plan['region_specs']).read_text())
    with np.load(ROOT / plan['surface_reference']) as z:
        surface = dict(z)
    statistics, states, files, params = [], {}, {}, {}
    for row, spec in zip(result['rows'], plan['cases'], strict=True):
        folder = OUT / spec['name']
        assert row == json.loads((folder / 'result.json').read_text())
        assert row['status'] == 'passed' and row['numerical_certificate']['all_checks_passed']
        assert row['residual_tolerance'] == .01
        assert file_hash(folder / 'capture.npz') == row['capture_sha256']
        attempt = json.loads((folder / 'attempt.json').read_text())
        assert attempt['spec'] == spec and attempt['protocol_sha256'] == file_hash(OUT / 'protocol.json')
        params[spec['region'], spec['arm'], spec['inflow']] = attempt['params']
        with np.load(folder / 'capture.npz') as z:
            state = dict(z)
        validate_state(state)
        with np.load(ROOT / spec['reference_capture']) as z:
            old = dict(z)
        for key in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P', 'days']:
            exact(state[key], old[key])
        if spec['inflow'] == 'legacy':
            assert row['baseline_byte_exact']
            for key in state:
                exact(state[key], old[key])
        else:
            assert attempt['params']['inflow_gain'] == 0.
            assert np.count_nonzero(state['budget__marine_exchange']) == 0
        if spec['arm'] == 'observed':
            assert row['actual_observed_wind_verified']
            f = OUT / ('forcing_' + spec['region'] + '.npz')
            assert file_hash(f) == preparation['forcing_sha256'][f.name]
            files[f.name] = file_hash(f)
            with np.load(f) as z:
                forcing = dict(z)
            center = specs[spec['region']]
            assert center['lat0'] > 0 and not attempt['params']['retrograde'] and attempt['params']['north_bearing'] == 0
            geometry = projection_jacobian(forcing['latitude'], forcing['longitude'], center['lat0'], center['lon0'])
            exact(np.stack(geometry), forcing['jacobian'])
            east, north = [bilinear_monthly(surface[k], forcing['latitude'], forcing['longitude']) for k in ['u', 'v']]
            exact(east, forcing['east'])
            exact(north, forcing['north'])
            restored = geographic_wind(forcing['wind'][:, 0], forcing['wind'][:, 1], geometry)
            np.testing.assert_allclose(restored, [east, north], rtol=1e-13, atol=2e-12)
            ii, jj = state['rows'], state['cols']
            exact(forcing['latitude'][ii, jj], state['lat'])
            exact(forcing['longitude'][ii, jj], state['lon'])
            # Independently use the production monthly-center calendar rather than
            # the producer's helper to validate actual heat and moisture samples.
            expected = []
            for day in state['days']:
                position = (day / attempt['params']['year_days'] * 12. - .5) % 12.
                first = int(np.floor(position))
                fraction = position - first
                expected.append(((1-fraction) * forcing['wind'][first] + fraction * forcing['wind'][(first+1) % 12])[:, ii, jj])
            expected = np.stack(expected)
            for axis, key in enumerate(['u', 'v']):
                exact(state['step_' + key], expected[:, axis])
                exact(state['step_moisture_' + key], expected[:, axis])
        budget = {k:state['budget__' + k] for k in COMPONENTS + ['residual']}
        scaled = equation_check(budget, state['step_P'].astype(np.float32).astype(float), .01)
        np.testing.assert_allclose(scaled, row['max_scaled_exported_residual'], atol=0, rtol=0)
        for name, expected in [('convergence_import', state['step_gain'] * state['step_W']),
                               ('column_drying', -state['step_sinkd'] * state['step_W'])]:
            assert np.all(np.abs(budget[name] - expected) <= 2*np.finfo(np.float32).eps*np.maximum(np.abs(expected), 1.))
        metrics = summarize_state(state)
        statistics.append(dict(region=spec['region'], arm=spec['arm'], inflow=spec['inflow'], **metrics,
            annual_sources_mm={k:float(v.astype(float).mean() * 365) for k, v in budget.items()},
            max_scaled_exported_residual=scaled))
        states[spec['region'], spec['arm'], spec['inflow']] = state
        for name in ['attempt.json', 'result.json', 'capture.npz']:
            f = folder / name
            files[str(f.relative_to(OUT))] = file_hash(f)
    comparisons, interactions = [], []
    for region in plan['regions']:
        lookup = {(r['arm'],r['inflow']):r for r in statistics if r['region'] == region}
        for inflow in ['legacy', 'disabled']:
            differences = {k:[params[region, 'model', inflow][k], params[region, 'observed', inflow][k]]
                           for k in params[region, 'model', inflow]
                           if params[region, 'model', inflow][k] != params[region, 'observed', inflow][k]}
            assert differences == dict(wind_source=['model', 'observed'])
        for arm in ['model', 'observed']:
            before, after = [lookup[arm, inflow] for inflow in ['legacy', 'disabled']]
            differences = {k:[params[region, arm, 'legacy'][k], params[region, arm, 'disabled'][k]]
                           for k in params[region, arm, 'legacy']
                           if params[region, arm, 'legacy'][k] != params[region, arm, 'disabled'][k]}
            assert set(differences) == {'inflow_gain'} and differences['inflow_gain'][1] == 0.
            comparisons.append(dict(region=region, arm=arm,
                temperature_mae_change_C=after['temperature_mae_C']-before['temperature_mae_C'],
                rain_loss_ratio=after['rain_loss']/before['rain_loss'],
                annual_rain_change_mm=after['annual_rain_mm']-before['annual_rain_mm'],
                annual_source_changes_mm={k:after['annual_sources_mm'][k]-v for k,v in before['annual_sources_mm'].items()}))
        wind_response = {inflow:lookup['observed',inflow]['annual_rain_mm']-lookup['model',inflow]['annual_rain_mm']
                         for inflow in ['legacy','disabled']}
        interactions.append(dict(region=region, wind_response_annual_rain_mm=wind_response,
            ablation_change_in_wind_response_mm=wind_response['disabled']-wind_response['legacy']))
    figure(plan, states)
    write_json(OUT / 'review.json', dict(status='reviewed_fixed_wind_marine_factorial_ablation_not_global_qualification',
        protocol_sha256=file_hash(OUT / 'protocol.json'), results_sha256=file_hash(OUT / 'results.json'),
        statistics=statistics, comparisons=comparisons, interactions=interactions, files_sha256=files,
        figure_sha256=file_hash(OUT / 'wind_response.png'),
        interpretation=plan['interpretation'], climate_adopted=False, atlas_changed=False))
    print('Reviewed six exact controls, six source ablations, prescribed wind and all local equations.')


def figure(plan, states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for col, (region, title) in enumerate(zip(plan['regions'], ['Somalia', 'Sahara', 'North India'], strict=True)):
        for field, row, unit in [('P', 0, 'Rain (mm/model month)'), ('T', 1, 'Temperature (C)')]:
            ax = axes[row, col]
            for arm, color in [('model', '#377d8d'), ('observed', '#b47552')]:
                for inflow, style in [('legacy', '-'), ('disabled', ':')]:
                    label = arm + ' wind / ' + ('marine on' if inflow == 'legacy' else 'marine off')
                    ax.plot(np.arange(1, 13), states[region, arm, inflow][field].mean(1),
                            label=label, color=color, linestyle=style)
            ax.plot(np.arange(1, 13), states[region, 'model', 'legacy']['obs_' + field].mean(1),
                    '--', label='Fixed observations', color='#777777')
            ax.set(ylabel=unit, xticks=[1, 4, 7, 10, 12], xlabel='Model month')
            ax.grid(alpha=.15)
        axes[0, col].set_title(title)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle('Wind × marine-relaxation ablation: coupled responses at identical scored cells')
    fig.text(.5, .035, 'NCEP surface sigma0.995 (1991–2020, 2.5 degree). Both heat and moisture winds replaced. Marine-off sets inflow_gain=0; all other settings fixed.\n'
             'Three exposed regions, no tuning or adoption. Coupled differences are not isolated source shares or a fictional-world solution.', ha='center', fontsize=8)
    fig.subplots_adjust(left=.07, right=.98, top=.89, bottom=.14, hspace=.35, wspace=.32)
    fig.savefig(OUT / 'wind_response.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
