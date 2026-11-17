"""Fixed grain scenarios as conditional city-area features; never infer hours."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_hierarchy as SH
from cereal_activity_packet import read, write, sha, table, verify_parent
from polity import earth as E
from polity.settlement_sizes import hinterlands, draws, generate_area
from polity.urban_predictive_pilot import nested_fit
from harvest.work_maps import cereal_work
from harvest.field_support import field_support
from run_roman_benchmark import node_scores, score, masks

OUT = ROOT / 'output/conditional_grain_extent_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/conditional_grain_extent.json'
GRID = ROOT / 'output/urban_population_recipe_20261116/restored/grid/earth.npz'
WINDOW = ROOT / 'output/settlement_locations_20261110/rome_inputs.npz'
ROMAN = ROOT / 'output/roman_benchmark_20261117'
KCAL = 912500.
SEEDS = np.arange(1000, 1256)
MODELS = ['M0', 'H_reference', 'G_potential', 'G_h600', 'G_h300']


def verify_inputs():
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    verify_parent()
    for folder in [ROOT / 'output/reaping_contract_target_20261117', ROMAN]:
        q = read(folder / 'qualification.json')
        for n, h in {**q['sources_sha256'], **q.get('protected_sha256', {})}.items():
            assert sha(ROOT / n) == h, n
        for n, h in q['files_sha256'].items(): assert sha(folder / n) == h, n


def features():
    with np.load(WINDOW) as z: x = dict(z)
    with np.load(GRID) as z: g = dict(z)
    land = x['land']; cell = float(x['cell_km'])
    original = E.EARTH_NPZ
    try:
        E.EARTH_NPZ = GRID
        density, _, inside = E.earth_people(x['lat'], x['lon'])
    finally:
        E.EARTH_NPZ = original
    step = float(g['lat'][0] - g['lat'][1])
    r = (g['lat'][0] + step / 2 - x['lat']) / step - .5
    c = (x['lon'] - (g['lon'][0] - step / 2)) / step - .5
    rc = [np.clip(r, 0, len(g['lat']) - 1), np.clip(c, 0, len(g['lon']) - 1)]
    sample = lambda name: np.where(inside & land, map_coordinates(np.nan_to_num(g[name]).astype(float), rc, order=0), 0.)
    energy = np.stack([sample('kcal_wheat'), sample('kcal_barley')])
    arable = sample('arable'); people = np.where(land, density * cell ** 2, 0.)
    work = cereal_work(energy, np.array([336., 208.]), np.array([48., 32.]), food_target=1e6)
    chosen = np.where(work.crop == 1, energy[0], np.where(work.crop == 2, energy[1], 0.))
    hectares = land * cell ** 2 * 100 * arable * .6 * .6
    potential = chosen * hectares
    centres = np.column_stack(np.unravel_index(x['real'], land.shape))
    (origin, centre, weight), H = hinterlands(centres, land, people, cell)
    aggregate = lambda v: np.bincount(centre, weights=weight * v.ravel()[origin], minlength=len(centres))
    rows, _, _, _ = SH.cohort(); row_centre = np.array([r['cell'] for r in rows])
    with np.load(ROOT / 'output/urban_population_recipe_20261116/model.npz') as z:
        np.testing.assert_array_equal(H, z['floodplain_settlement_base__centre_H'])
        np.testing.assert_array_equal(H[row_centre], z['floodplain_settlement_base__row_H'])
    fields = dict(people=people, arable=arable, crop=work.crop, hectares=hectares, chosen_kcal_ha=chosen,
                  potential=potential, inside=inside, land=land, origin=origin, centre=centre, weight=weight,
                  row_centre=row_centre, H_reference=H[row_centre], centre_H=H, energy=energy)
    arrays = {'M0': np.ones(len(rows)), 'H_reference': np.log(H[row_centre])}
    summaries = []
    for label, hours in [('G_potential', None), ('G_h600', 600.), ('G_h300', 300.)]:
        retained = np.where(potential > 0, 1., 0.)
        if hours is not None:
            support = field_support(potential, np.nan_to_num(work.hours), np.nan_to_num(work.reaping),
                                    rural_need_kcal=people * KCAL, hours_worker_year=hours)
            retained = support.retained
        gross = potential * retained; G = aggregate(gross) / KCAL
        fields[label + '__retained'] = retained
        fields[label + '__centre_rations'] = G
        fields[label + '__row_rations'] = G[row_centre]
        arrays[label] = np.log1p(G[row_centre])
        summaries.append(dict(model=label, allocated_hours_worker_year=hours,
            gross_window_ration_years=float(gross.sum() / KCAL), assigned_ration_years=float(G.sum()),
            unassigned_ration_years=float((gross.sum() / KCAL) - G.sum()),
            positive_cereal_cells=int((potential > 0).sum()),
            limited_cereal_cells=int(((potential > 0) & (retained < 1 - 1e-10)).sum()),
            annual_potential_ha=float(hectares[potential > 0].sum()),
            retained_ha=float((hectares * retained).sum()),
            zero_grain_rows=int((G[row_centre] == 0).sum()),
            row_ration_min=float(G[row_centre].min()), row_ration_median=float(np.median(G[row_centre])),
            row_ration_max=float(G[row_centre].max())))
    fields.update({'x__' + k: v for k, v in arrays.items()})
    coverage = dict(land_cells=int(land.sum()), covered_land_cells=int((land & inside).sum()),
        covered_land_fraction=float(inside[land].mean()), window_shape=list(land.shape), cell_km=cell,
        centres=len(centres), rows=len(rows), unique_row_centres=len(set(row_centre.tolist())),
        wheat_cells=int((work.crop == 1).sum()), barley_cells=int((work.crop == 2).sum()),
        land_no_cereal_cells=int((land & (work.crop == 0)).sum()),
        reference_people=float(people.sum()), assigned_reference_people=float(H.sum()))
    return fields, arrays, summaries, coverage


def run(out):
    assert not (out / 'results.json').exists(), 'Preserve completed experiment; use --out'
    verify_inputs()
    fields, xs, feature_summaries, coverage = features()
    with np.load(ROMAN / 'design.npz') as z: d = dict(z)
    with np.load(ROMAN / 'ensemble.npz') as z: old = dict(z)
    prior = read(ROMAN / 'results.json'); bounds = prior['bounds_ha']
    province_names = read(ROMAN / 'preparation.json')['province_names']
    fold = d['fold']; y = np.log(d['area']); n = len(y)
    fits = []; ensembles = {}; means = {}
    for model in MODELS:
        X = np.ones((n, 1)) if model == 'M0' else np.column_stack([np.ones(n), xs[model]])
        ensemble = np.zeros((len(SEEDS), n)); mean = np.zeros(n)
        for outer in range(4):
            beta, sigma, inner = nested_fit(X, y, fold, np.ones(n, bool), outer)
            test = fold == outer; mean[test] = X[test] @ beta
            for j, seed in enumerate(SEEDS):
                ensemble[j, test] = generate_area(X @ beta, sigma, draws(n, int(seed)), *bounds)[test]
            fits.append(dict(model=model, outer=outer, coefficients=beta.tolist(), sigma=sigma, inner=inner,
                             training_n=int((~test).sum()), test_n=int(test.sum())))
        if model == 'M0': np.testing.assert_allclose(ensemble, old['baseline'], rtol=3e-15, atol=3e-12)
        ensembles[model] = ensemble; means[model] = mean
    # The original M0 uses scalar means, whose summation order differs from lstsq.
    # Keep its exact archived draws after proving numerical equivalence above.
    ensembles['M0'] = old['baseline'].copy()
    ensembles['hierarchy_reference'] = old['hierarchy'].copy()
    scores = []; folds = []; provinces = []; nodal = {}; sets = masks(d)
    for model, area in ensembles.items():
        ns = node_scores(area, d['area']); nodal[model] = ns
        for cohort, mask in sets.items():
            scores.append(dict(model=model, cohort=cohort, **score(area, d['area'], ns, mask)))
            for outer in range(4):
                folds.append(dict(model=model, cohort=cohort, outer=outer, **score(area, d['area'], ns, mask & (fold == outer))))
            for code, name in enumerate(province_names):
                use = mask & (d['province'] == code)
                provinces.append(dict(model=model, cohort=cohort, province=name, small_sample=bool(use.sum() < 5),
                                      **score(area, d['area'], ns, use)))
    comparisons = []
    for cohort in sets:
        for model in MODELS[1:]:
            result = next(r for r in scores if r['model'] == model and r['cohort'] == cohort)
            for baseline in ['M0', 'H_reference', 'G_potential']:
                base = next(r for r in scores if r['model'] == baseline and r['cohort'] == cohort)
                model_provinces = [r for r in provinces if r['model'] == model and r['cohort'] == cohort and r['n']]
                base_provinces = [r for r in provinces if r['model'] == baseline and r['cohort'] == cohort and r['n']]
                pairs = [(next(r for r in folds if r['model'] == k and r['cohort'] == cohort and r['outer'] == f)['log_area_crps'])
                         for f in range(4) for k in [model, baseline]]
                comparisons.append(dict(cohort=cohort, model=model, baseline=baseline,
                    crps_relative_improvement=1-result['log_area_crps']/base['log_area_crps'],
                    mae_relative_improvement=1-result['median_log_area_mae']/base['median_log_area_mae'],
                    model_equal_province_crps=float(np.mean([r['log_area_crps'] for r in model_provinces])),
                    baseline_equal_province_crps=float(np.mean([r['log_area_crps'] for r in base_provinces])),
                    nonempty_comparison_folds=sum(pairs[i] is not None for i in range(0, 8, 2)),
                    fold_crps_wins=sum(pairs[i] < pairs[i+1] for i in range(0, 8, 2) if pairs[i] is not None)))
    a, b = xs['G_h600'], xs['G_h300']; affine = np.polyfit(a, b, 1); residual = b - np.polyval(affine, a)
    identification = dict(log_feature_correlation=float(np.corrcoef(a, b)[0, 1]),
        affine_h300_on_h600_slope=float(affine[0]), affine_intercept=float(affine[1]),
        affine_residual_rms=float(np.sqrt(np.mean(residual**2))), affine_residual_max_abs=float(abs(residual).max()),
        out_of_fold_mean_log_prediction_difference_rms=float(np.sqrt(np.mean((means['G_h300']-means['G_h600'])**2))),
        actual_household_hours_identified=False, historical_resource_capacity_fit=False,
        explanation='Gross-output scale can be absorbed by fitted intercept; reference workforce and hours remain supplied scenarios.')
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'features.npz', **fields)
    np.savez_compressed(out / 'ensembles.npz', **ensembles, **{'mean__'+k:v for k,v in means.items()}, seeds=SEEDS)
    for name, records in [('feature_summaries', feature_summaries), ('scores', scores), ('folds', folds),
                          ('provinces', provinces), ('comparisons', comparisons)]: table(out / (name + '.csv'), records)
    write(out / 'identifiability.json', identification)
    paths = [PLAN, Path(__file__), GRID, WINDOW, ROMAN / 'qualification.json', ROMAN / 'results.json',
             ROMAN / 'preparation.json', ROMAN / 'design.npz', ROMAN / 'ensemble.npz',
             ROOT / 'output/reaping_contract_target_20261117/qualification.json',
             ROOT / 'output/urban_population_recipe_20261116/model.npz']
    paths += [ROOT / p for p in ['polity/earth.py', 'harvest/work_maps.py', 'harvest/field_support.py',
             'polity/settlement_sizes.py', 'polity/urban_predictive_pilot.py', 'scripts/settlement_hierarchy.py',
             'scripts/run_roman_benchmark.py', 'scripts/cereal_activity_packet.py', 'harvest/models.py']]
    files = ['features.npz', 'ensembles.npz', 'feature_summaries.csv', 'scores.csv', 'folds.csv',
             'provinces.csv', 'comparisons.csv', 'identifiability.json']
    write(out / 'results.json', dict(status='conditional_grain_extent_development_comparison',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        files_sha256={n:sha(out / n) for n in files}, coverage=coverage, fits=fits, scores=scores,
        feature_summaries=feature_summaries, identifiability=identification, bounds_ha=bounds,
        baseline_archived_draws_exact=True, H_replay_exact=True, original_rows=664,
        evaluation_seeds=SEEDS.tolist(), new_mean_fits=20, hierarchy_reference_refit=False,
        independent_new_validation=False, dated_extent_qualification=False,
        historical_agricultural_capacity_calibrated=False, new_hour_estimate=False,
        atlas_population_or_defaults_changed=False, crop_climate_route_solver_calls=0, adopt=False))
    for r in scores:
        if r['cohort'] in ['AD200_compatible', 'AD200_strict']: print(r)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT)
    run(p.parse_args().out)
