"""Review six prescribed surface-wind diagnostics from saved arrays only."""
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

PLAN = ROOT / 'calibration/surface_wind_diagnostic_20261127/plan.json'
OUT = ROOT / 'output/surface_wind_diagnostic_20261127'


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
    assert len(result['rows']) == plan['maximum_diagnostic_integrations'] == 6
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
        params[spec['region'], spec['arm']] = attempt['params']
        with np.load(folder / 'capture.npz') as z:
            state = dict(z)
        validate_state(state)
        with np.load(ROOT / spec['reference_capture']) as z:
            old = dict(z)
        for key in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P', 'days']:
            exact(state[key], old[key])
        if spec['arm'] == 'model':
            assert row['baseline_byte_exact']
            for key in ['T', 'P', 'E', 'W', 'u', 'v', 'days', 'step_gain', 'step_sinkd', 'step_W', 'step_P',
                        'step_u', 'step_v', 'step_moisture_u', 'step_moisture_v', *['budget__' + k for k in COMPONENTS + ['residual', 'absolute_residual', 'monsoon_drying']]]:
                exact(state[key], old[key])
        else:
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
        statistics.append(dict(region=spec['region'], arm=spec['arm'], **metrics,
            annual_sources_mm={k:float(v.astype(float).mean() * 365) for k, v in budget.items()},
            max_scaled_exported_residual=scaled))
        states[spec['region'], spec['arm']] = state
        for name in ['attempt.json', 'result.json', 'capture.npz']:
            f = folder / name
            files[str(f.relative_to(OUT))] = file_hash(f)
    comparisons = []
    for region in plan['regions']:
        before, after = [next(s for s in statistics if s['region'] == region and s['arm'] == arm) for arm in ['model', 'observed']]
        differences = {k:[params[region, 'model'][k], params[region, 'observed'][k]]
                       for k in params[region, 'model'] if params[region, 'model'][k] != params[region, 'observed'][k]}
        assert differences == dict(wind_source=['model', 'observed'])
        comparisons.append(dict(region=region,
            temperature_mae_change_C=after['temperature_mae_C'] - before['temperature_mae_C'],
            rain_loss_ratio=after['rain_loss'] / before['rain_loss'],
            annual_rain_change_mm=after['annual_rain_mm'] - before['annual_rain_mm'],
            annual_source_changes_mm={k:after['annual_sources_mm'][k] - v for k, v in before['annual_sources_mm'].items()}))
    figure(plan, states)
    write_json(OUT / 'review.json', dict(status='reviewed_fixed_observed_surface_wind_diagnostics_not_global_qualification',
        protocol_sha256=file_hash(OUT / 'protocol.json'), results_sha256=file_hash(OUT / 'results.json'),
        statistics=statistics, comparisons=comparisons, files_sha256=files,
        figure_sha256=file_hash(OUT / 'wind_response.png'),
        interpretation=plan['interpretation'], climate_adopted=False, atlas_changed=False))
    print('Reviewed three exact controls, three verified wind interventions and all coupled local accounts.')


def figure(plan, states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for col, (region, title) in enumerate(zip(plan['regions'], ['Somalia', 'Sahara', 'North India'], strict=True)):
        for field, row, unit in [('P', 0, 'Rain (mm/model month)'), ('T', 1, 'Temperature (C)')]:
            ax = axes[row, col]
            for arm, label, color in [('model', 'Modeled wind', '#377d8d'), ('observed', 'Prescribed surface wind', '#b47552')]:
                ax.plot(np.arange(1, 13), states[region, arm][field].mean(1), label=label, color=color)
            ax.plot(np.arange(1, 13), states[region, 'model']['obs_' + field].mean(1), '--', label='Fixed observations', color='#777777')
            ax.set(ylabel=unit, xticks=[1, 4, 7, 10, 12], xlabel='Model month')
            ax.grid(alpha=.15)
        axes[0, col].set_title(title)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Prescribed surface-wind diagnostic: coupled responses at identical scored cells')
    fig.text(.5, .035, 'NCEP surface sigma0.995 (1991–2020, 2.5 degree). Both heat and moisture winds replaced; SST and coefficients unchanged.\n'
             'Three exposed regions, no tuning or adoption. Coupled differences are not isolated source shares or a fictional-world solution.', ha='center', fontsize=8)
    fig.subplots_adjust(left=.07, right=.98, top=.89, bottom=.14, hspace=.35, wspace=.32)
    fig.savefig(OUT / 'wind_response.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
