"""Run the predeclared exposed, mixed-period housing observation diagnostic."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import unicodedata

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity.housing_diagnostic import MODELS, fit_predict, province_folds
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_housing_diagnostic_20261112/plan.json'
OUT = ROOT / 'output/settlement_housing_diagnostic_20261112'


def metrics(observed, predicted, provinces):
    error = np.asarray(predicted) - np.asarray(observed)
    groups = sorted(set(provinces))
    return dict(mean_absolute_log_error=float(np.abs(error).mean()),
        root_mean_square_log_error=float(np.sqrt(np.mean(error ** 2))),
        median_multiplicative_error=float(np.exp(np.median(np.abs(error)))),
        equal_province_mean_absolute_log_error=float(np.mean([
            np.abs(error[np.array(provinces) == g]).mean() for g in groups])))


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit diagnostic declaration before scoring')
    plan = json.loads(PLAN.read_text())
    source_paths = [ROOT / p for p in plan['sources'].values() if '/' in p]
    source_paths += [PLAN, Path(__file__), ROOT / 'polity/housing_diagnostic.py']
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    # Freeze both actual model packets and the preceding preparation/review.
    protected = [ROOT / 'atlases/earth_fit/data/atlas.json']
    protected += [ROOT / 'atlases/earth_fit/data' / mode / 'settled_reach.json.gz'
                  for mode in ('', 'corrected')]
    protected += [ROOT / 'output/settlement_size_evidence_20261112' / n
                  for n in ('results.json', 'review.json', 'replay.json')]
    original_hashes = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    with (ROOT / plan['sources']['table']).open() as f:
        raw = list(csv.DictReader(f))
    identities = [(unicodedata.normalize('NFKC', r['ancient_name']).strip().casefold(), r['province']) for r in raw]
    if len(raw) != 50 or len({r['city_key'] for r in raw}) != 50 or len(set(identities)) != 50:
        raise ValueError('Unexpected repeated housing identities; resolve groups before scoring')
    prepared = json.loads((ROOT / plan['sources']['prepared']).read_text())
    gates = {r['city_key']: r for r in prepared['rows']}
    rows = [dict(r, **{k: float(r[k]) for k in ('site_area_ha', 'sample_area_ha')},
                 AD150_blockers=gates[r['city_key']]['AD150_blockers'],
                 AD150_size_fit_eligible=gates[r['city_key']]['AD150_size_fit_eligible']) for r in raw]
    for r in rows:
        r['properties'] = int(r['properties'])
        r['sample_fraction'] = r['sample_area_ha'] / r['site_area_ha']
    cohorts = []
    for spec in plan['cohorts']:
        selected = [r for r in rows if r['sample_fraction'] >= spec['minimum_sample_fraction']]
        record = dict(spec, cities=len(selected), provinces=len({r['province'] for r in selected}),
                      city_keys=[r['city_key'] for r in selected])
        try:
            folds = province_folds(selected)
        except ValueError as error:
            cohorts.append(dict(record, status='unscored', reason=str(error)))
            continue
        observed = np.log([r['properties'] / r['sample_area_ha'] for r in selected])
        groups = [r['province'] for r in selected]
        models = []
        for model in MODELS:
            predicted = np.empty(len(selected)); fold_records = []; max_household_error = 0.
            for group, train, test in folds:
                training, held = [selected[i] for i in train], [selected[i] for i in test]
                coefficients, values = fit_predict(training, held, model)
                predicted[test] = values
                for household in (3, 5, 7):
                    _, shifted = fit_predict(training, held, model, household=household)
                    difference = np.abs((shifted - np.log(household)) - values)
                    max_household_error = max(max_household_error, float(difference.max()))
                fold_records.append(dict(province=group, training_keys=[r['city_key'] for r in training],
                    test_keys=[r['city_key'] for r in held], coefficients=coefficients.tolist(),
                    mean_absolute_log_error=float(np.abs(values - observed[test]).mean())))
            if max_household_error > 1e-12:
                raise ValueError('Household unit change altered held-out errors')
            all_coefficients, _ = fit_predict(selected, selected, model)
            predictions = []
            for r, actual, value in zip(selected, observed, predicted):
                density = float(np.exp(value))
                predictions.append(dict(city_key=r['city_key'], province=r['province'],
                    observed_log_property_density=float(actual), predicted_log_property_density=float(value),
                    log_error=float(value - actual), conditional_predicted_people_at5=density * r['site_area_ha'] * 5))
            models.append(dict(id=model, metrics=metrics(observed, predicted, groups), folds=fold_records,
                predictions=predictions, descriptive_all_city_coefficients=all_coefficients.tolist(),
                maximum_household_log_error_difference=max_household_error,
                fold_coefficient_min=np.min([r['coefficients'] for r in fold_records], axis=0).tolist(),
                fold_coefficient_max=np.max([r['coefficients'] for r in fold_records], axis=0).tolist()))
        baseline = models[0]
        for model in models:
            model['province_error_difference_vs_constant'] = [dict(province=f['province'],
                mean_absolute_log_error_difference=f['mean_absolute_log_error'] - b['mean_absolute_log_error'])
                for f, b in zip(model['folds'], baseline['folds'])]
        cohorts.append(dict(record, status='scored_exposed_development', models=models))
    for path, digest in {**source_hashes, **original_hashes}.items():
        if sha(ROOT / path) != digest:
            raise ValueError('Input changed: ' + path)
    out.mkdir(parents=True, exist_ok=True)
    write(out / 'results.json', dict(status='exposed_mixed_period_observation_diagnostic', adopt=False,
        AD150_size_fit_eligible=sum(r['AD150_size_fit_eligible'] for r in rows),
        catalogue_join_certified=False, prospective_transfer=False, source_rows=rows, cohorts=cohorts,
        sources_sha256=source_hashes, unchanged_sha256=original_hashes,
        limits='Conditional property-density errors on a selected mixed-period archive. Province blocking is coarse. Coverage shares a denominator with density. No census, phase/extent/sampling qualification, confidence interval, allocator fit or default change.'))
    for c in cohorts:
        print(c['id'], c['status'], 'cities', c['cities'], 'provinces', c['provinces'])
        for m in c.get('models', []):
            print(' ', m['id'], m['metrics'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
