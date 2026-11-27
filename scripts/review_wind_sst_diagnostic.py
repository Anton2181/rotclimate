"""Review twelve fixed wind-by-prescribed-SST diagnostics from saved arrays only."""
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

PLAN = ROOT / 'calibration/wind_sst_diagnostic_20261127/plan.json'
OUT = ROOT / 'output/wind_sst_diagnostic_20261127'


def sample_woa(latitude, longitude):
    from scipy import ndimage as ndi
    with np.load(OUT/'woa_surface_reference.npz') as z:
        ocean = z['sst'].astype(float)
    sampled = []
    for month in ocean:
        missing = ~np.isfinite(month)
        nearest = ndi.distance_transform_edt(missing, return_distances=False, return_indices=True)
        filled = month[tuple(nearest)]
        wrapped = np.concatenate([filled, filled[:, :1]], axis=1)
        sampled.append(ndi.map_coordinates(wrapped, [latitude+89.5, (longitude+179.5)%360.], order=1, mode='nearest'))
    return np.stack(sampled)


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
    assert preparation['woa_reference_sha256'] == file_hash(OUT/'woa_reference.json')
    from prepare_woa18 import check as check_woa, raw_sources
    receipt = check_woa(OUT/'woa_surface_reference.npz', raw_sources(ROOT/'data/cache/woa18'))
    assert receipt == json.loads((OUT/'woa_reference.json').read_text())
    statistics, states, files, params = [], {}, {}, {}
    for row, spec in zip(result['rows'], plan['cases'], strict=True):
        folder = OUT / spec['name']
        assert row == json.loads((folder / 'result.json').read_text())
        assert row['status'] == 'passed' and row['numerical_certificate']['all_checks_passed']
        assert row['residual_tolerance'] == .01
        assert file_hash(folder / 'capture.npz') == row['capture_sha256']
        attempt = json.loads((folder / 'attempt.json').read_text())
        assert attempt['spec'] == spec and attempt['protocol_sha256'] == file_hash(OUT / 'protocol.json')
        params[spec['region'], spec['arm'], spec['sst']] = attempt['params']
        parent = ROOT / Path(spec['reference_capture']).parent / 'attempt.json'
        parent_params = json.loads(parent.read_text())['params']
        wanted_params = dict(parent_params, sst_source=spec['sst'])
        assert attempt['params'] == wanted_params

        with np.load(folder / 'capture.npz') as z:
            state = dict(z)
        validate_state(state)
        with np.load(ROOT / spec['reference_capture']) as z:
            old = dict(z)
        for key in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P', 'days']:
            exact(state[key], old[key])
        if spec['sst'] == 'model':
            assert row['baseline_byte_exact']
            for key in old:
                exact(state[key], old[key])
        else:
            assert attempt['params']['sst_source'] == 'observed'
            assert row['actual_heat_and_moisture_SST_verified']
        # The saved source is a full padded-grid monthly input. Validate it
        # against the verified WOA cache independently of producer case setup.
        f = OUT / ('forcing_' + spec['region'] + '.npz')
        assert file_hash(f) == preparation['forcing_sha256'][f.name]
        with np.load(f) as z:
            sea_input = dict(z)
        wanted = sample_woa(sea_input['latitude'], sea_input['longitude'])
        exact(sea_input['sst'], wanted)
        sr, sc = state['sea_rows'], state['sea_cols']
        cached = OUT/'model/data/cache/earth'/f"{spec['region']}_56km_1100pad.npz"
        with np.load(cached) as z:
            sea_grid = ~(z['land_frac'] >= .5)
        wanted_rows, wanted_cols = np.where(sea_grid)
        exact(sr, wanted_rows)
        exact(sc, wanted_cols)
        assert (sea_input['sst'][:, sr, sc] > -1.).all()
        if spec['sst'] == 'observed':
            expected_sst = []
            for day in state['days']:
                position = (day / attempt['params']['year_days'] * 12. - .5) % 12.
                first = int(np.floor(position)); fraction = position - first
                expected_sst.append((1-fraction)*wanted[first]+fraction*wanted[(first+1)%12])
            expected_sst = np.stack(expected_sst)
            for key in ['step_sea_SST', 'step_sea_Teq', 'step_sea_heat_SST']:
                exact(state[key], expected_sst[:, sr, sc])
            exact(state['step_SST'], expected_sst[:, state['rows'], state['cols']])
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
        annual, observed = state['P'].sum(0), state['obs_P'].astype(float).sum(0)
        metrics['annual_per_cell_log_rmse'] = float(np.sqrt(np.mean(np.log((annual+50)/(observed+50))**2)))
        metrics['normalized_cell_month_error'] = float(12*np.abs(state['P']-state['obs_P']).mean()/(observed.mean()+120))
        worst = np.argsort(np.abs(annual-observed))[::-1][:4]
        metrics['largest_annual_errors'] = [dict(latitude=float(state['lat'][i]),longitude=float(state['lon'][i]),annual_rain_mm=float(annual[i]),observed_mm=float(observed[i])) for i in worst]

        statistics.append(dict(region=spec['region'], arm=spec['arm'], sst=spec['sst'], **metrics,
            annual_sources_mm={k:float(v.astype(float).mean() * 365) for k, v in budget.items()},
            max_scaled_exported_residual=scaled))
        states[spec['region'], spec['arm'], spec['sst']] = state
        for name in ['attempt.json', 'result.json', 'capture.npz']:
            f = folder / name
            files[str(f.relative_to(OUT))] = file_hash(f)
    comparisons, interactions = [], []
    for region in plan['regions']:
        lookup = {(r['arm'],r['sst']):r for r in statistics if r['region'] == region}
        for sst in ['model', 'observed']:
            differences = {k:[params[region, 'model', sst][k], params[region, 'observed', sst][k]]
                           for k in params[region, 'model', sst]
                           if params[region, 'model', sst][k] != params[region, 'observed', sst][k]}
            assert differences == dict(wind_source=['model', 'observed'])
        for arm in ['model', 'observed']:
            before, after = [lookup[arm, sst] for sst in ['model', 'observed']]
            differences = {k:[params[region, arm, 'model'][k], params[region, arm, 'observed'][k]]
                           for k in params[region, arm, 'model']
                           if params[region, arm, 'model'][k] != params[region, arm, 'observed'][k]}
            assert differences == dict(sst_source=['model', 'observed'])
            comparisons.append(dict(region=region, arm=arm,
                temperature_mae_change_C=after['temperature_mae_C']-before['temperature_mae_C'],
                rain_loss_ratio=after['rain_loss']/before['rain_loss'],
                annual_rain_change_mm=after['annual_rain_mm']-before['annual_rain_mm'],
                annual_source_changes_mm={k:after['annual_sources_mm'][k]-v for k,v in before['annual_sources_mm'].items()}))
        wind_response = {sst:lookup['observed',sst]['annual_rain_mm']-lookup['model',sst]['annual_rain_mm']
                         for sst in ['model','observed']}
        interactions.append(dict(region=region, wind_response_annual_rain_mm=wind_response,
            SST_change_in_wind_response_mm=wind_response['observed']-wind_response['model']))
    figure(plan, states)
    write_json(OUT / 'review.json', dict(status='reviewed_fixed_wind_sst_factorial_diagnostic_not_global_qualification',
        protocol_sha256=file_hash(OUT / 'protocol.json'), results_sha256=file_hash(OUT / 'results.json'),
        statistics=statistics, comparisons=comparisons, interactions=interactions, files_sha256=files,
        figure_sha256=file_hash(OUT / 'wind_response.png'),
        interpretation=plan['interpretation'], climate_adopted=False, atlas_changed=False))
    print('Reviewed six exact controls, six prescribed-SST interventions, actual heat/moisture targets and equations.')


def figure(plan, states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for col, (region, title) in enumerate(zip(plan['regions'], ['Somalia', 'Sahara', 'North India'], strict=True)):
        for field, row, unit in [('P', 0, 'Rain (mm/model month)'), ('T', 1, 'Temperature (C)')]:
            ax = axes[row, col]
            for arm, color in [('model', '#377d8d'), ('observed', '#b47552')]:
                for sst, style in [('model', '-'), ('observed', ':')]:
                    label = arm + ' wind / ' + ('modeled SST' if sst == 'model' else 'observed SST')
                    ax.plot(np.arange(1, 13), states[region, arm, sst][field].mean(1),
                            label=label, color=color, linestyle=style)
            ax.plot(np.arange(1, 13), states[region, 'model', 'model']['obs_' + field].mean(1),
                    '--', label='Fixed observations', color='#777777')
            ax.set(ylabel=unit, xticks=[1, 4, 7, 10, 12], xlabel='Model month')
            ax.grid(alpha=.15)
        axes[0, col].set_title(title)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle('Wind × prescribed SST: coupled responses at identical scored cells')
    fig.text(.5, .035, 'NCEP surface wind (1991–2020, 2.5 degree) and WOA18 all-decade SST (1 degree). Heat and moisture SST verified; no modeled anomaly addback.\n'
             'Three exposed regions, no tuning or adoption. Coupled differences are not isolated source shares or a fictional-world solution.', ha='center', fontsize=8)
    fig.subplots_adjust(left=.07, right=.98, top=.89, bottom=.14, hspace=.35, wspace=.32)
    fig.savefig(OUT / 'wind_response.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
