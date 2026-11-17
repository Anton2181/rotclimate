"""Six predeclared fixed-infrastructure Earth food counterfactuals and exact controls."""
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
import argparse
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from harvest.food_stocks import FoodYear
from polity.earth_storage_loss import fixed_storage_food, commercial_capacity
from urban_earth_monthly import inspect, sha, read, write, total, SHARES, KCAL

OUT = ROOT/'output/urban_storage_loss_20261117'
BASE = ROOT/'output/urban_earth_monthly_20261116'
ANNUAL = ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared'
PLAN = ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_storage_loss_factorial.json'
NUMERICS = ROOT/'calibration/urban_diagnosis_20261117/storage_loss_numerics.json'
COMBOS = [('loss05_days90', .05, 90), ('loss00_days365', 0., 365), ('loss00_days90', 0., 90)]
INPUTS = ['source_indices', 'people', 'withdrawn', 'rural', 'request', 'produced_components', 'boundary', 'owner', 'retention']


def flatten(case):
    result = {}
    for key, value in case.items():
        if isinstance(value, FoodYear):
            result.update({key+'__'+field: array for field, array in asdict(value).items() if array is not None})
        else:
            result[key] = value
    assert len(result) == 70
    return result


def gate():
    for path in (PLAN, NUMERICS):
        assert subprocess.check_output(['git', 'show', 'HEAD:'+str(path.relative_to(ROOT))], cwd=ROOT) == path.read_bytes()
    sources = {}; protected = {}
    for directory in (BASE, ROOT/'output/urban_calendar_sensitivity_20261116', ROOT/'output/urban_evidence_buffers_20261116'):
        q = read(directory/'qualification.json'); assert q['status'].startswith('passed_')
        for key, prefix in [('sources_sha256', ROOT), ('files_sha256', directory), ('protected_sha256', ROOT)]:
            for name, digest in q[key].items():
                assert sha(prefix/name) == digest, name
        sources[str((directory/'qualification.json').relative_to(ROOT))] = sha(directory/'qualification.json')
        protected.update(q['protected_sha256'])
    for path in [PLAN, NUMERICS, Path(__file__), ROOT/'polity/earth_storage_loss.py', ROOT/'tests/test_earth_storage_loss.py',
                 ROOT/'scripts/urban_earth_monthly.py', ROOT/'polity/earth_fixed_food.py', ROOT/'polity/seasonal_settlement_network.py',
                 ROOT/'harvest/food_stocks.py', ROOT/'harvest/field_support.py', ROOT/'polity/wide_supply.py']:
        sources[str(path.relative_to(ROOT))] = sha(path)
    return sources, protected


def routes(a):
    between = np.maximum(1-a['between'].astype(float)/270, 0)
    for quarter in range(4): np.fill_diagonal(between[quarter], 0)
    return between


def main(reading):
    sources, protected = gate()
    baseline_path = BASE/'cases'/reading/'fields.npz'
    a_path = ANNUAL/f'low_{reading}.npz'
    parent = read(BASE/'cases'/reading/'results.json')
    assert sha(baseline_path) == parent['fields_sha256']
    for name, digest in parent['sources_sha256'].items(): assert sha(ROOT/name) == digest, name
    for path in [baseline_path, a_path]: sources[str(path.relative_to(ROOT))] = sha(path)
    baseline = dict(np.load(baseline_path)); a = dict(np.load(a_path))
    reference = baseline['marketed'].sum(0)
    args = [baseline[key] for key in ('produced_components', 'boundary', 'rural', 'request', 'owner', 'retention')] + [routes(a)]
    common = dict(marketed_share=SHARES[reading], reference_market=reference)
    control_path = OUT/'controls'/f'{reading}.json'; control_path.parent.mkdir(parents=True, exist_ok=True)
    assert not control_path.exists(), 'Preserve completed controls; use an isolated OUT'
    control = flatten(fixed_storage_food(*args, **common, commercial_days=365, loss=.05))
    for key, value in control.items(): np.testing.assert_array_equal(value, baseline[key], err_msg=key)
    write(control_path, dict(status='all70_original_food_arrays_exact', reading=reading,
          arrays_exact=len(control), sources_sha256=sources, protected_sha256=protected))
    print(reading, 'all70 original food arrays EXACT', flush=True)
    for label, loss, days in COMBOS:
        folder = OUT/'cases'/f'{reading}_{label}'; folder.mkdir(parents=True, exist_ok=True)
        assert not (folder/'results.json').exists(), 'Preserve completed cases; use an isolated OUT'
        try:
            c = fixed_storage_food(*args, **common, commercial_days=days, loss=loss)
            audit = inspect(c, baseline['rural'], baseline['request'], SimpleNamespace(produced_total=baseline['harvest'].sum(0)))
            fields = {key: baseline[key] for key in INPUTS}
            fields.update(flatten(c)); fields['reference_market'] = reference
            fields['commercial_capacity'] = commercial_capacity(reference, days)
            np.savez_compressed(folder/'fields.npz', **fields)
            old_protected = baseline['rural_food__unmet'] <= 1e-8*np.maximum(1, baseline['rural_food__needed'])
            new_protected = c['rural_food'].unmet <= 1e-8*np.maximum(1, c['rural_food'].needed)
            new_zero = (~old_protected) & new_protected & (reference == 0)
            result = dict(status='six_case_factorial_pending_independent_review', reading=reading, label=label,
                loss_fraction_year=loss, commercial_days=days, marketed_share=SHARES[reading],
                reference_capacity='original baseline marketed energy, fixed across loss levels',
                sources_sha256=sources, protected_sha256=protected, fields_sha256=sha(folder/'fields.npz'),
                audit=audit, newly_protected_zero_capacity_origins=int(new_zero.sum()),
                newly_protected_zero_capacity_marketed_person_years=total(c['marketed'][:, new_zero])/KCAL,
                newly_protected_zero_capacity_departures_person_years=total(c['departures'][:, new_zero])/KCAL,
                zero_reference_origins=int((reference == 0).sum()),
                zero_reference_newly_marketed_origins=int(((reference == 0)&(c['marketed'].sum(0)>0)).sum()),
                source_count=len(reference), city_count=len(baseline['request']), shipment_rows=len(c['shipments']),
                demographic_iteration=False, actual_population_changed=False, new_fit=False, new_validation_claim=False, adopt=False)
            write(folder/'results.json', result)
            print(reading, label, 'meals', audit['town_meal_fraction'], 'rural unmet', audit['rural_unmet_person_years'], flush=True)
        except BaseException as error:
            write(folder/'failure.json', dict(status='preserved_case_failure', error=f'{type(error).__name__}: {error}', producer_sha256=sha(Path(__file__))))
            raise
    for name, digest in protected.items(): assert sha(ROOT/name) == digest, name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('reading', choices=['central', 'low'])
    main(parser.parse_args().reading)
