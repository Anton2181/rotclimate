"""Review resident scenarios from scalar caps without using the new allocator."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from build_settlement_residents import OUT, MODELS
from harvest.food_stocks import periodic_food_year


def check(out=OUT):
    r = json.loads((out / 'results.json').read_text())
    for path, digest in {**r['sources'], **r['producers']}.items():
        assert sha(ROOT / path) == digest, path
    assert sha(out / 'fields.npz') == r['fields_sha256']
    fields = dict(np.load(out / 'fields.npz')); checked = 0; sites_checked = 0; max_balance = 0.
    assert len(r['rows']) == 60 and len(r['baseline_controls']) == 20
    for climate, path in MODELS.items():
        model = json.loads(gzip.decompress(path.read_bytes())); spec = model['specification']
        population = np.array([s['served_people'] for s in model['sites']])
        request = np.array([s['civilian_request_people'] for s in model['sites']])
        affiliated = np.array([s['actor_index'] >= 0 for s in model['sites']])
        market_ids = [i for s in model['sites'] for i in s['market_ids']]
        assert len(market_ids) == len(set(market_ids))
        np.testing.assert_array_equal(fields[climate + '__origin_population'], population)
        for row in [a for a in r['rows'] if a['climate'] == climate]:
            c = next(c for c in model['cases'] if c['id'] == row['case'])
            ceiling = np.array(c['food_ceiling_people']); cap = population * row['transfer_fraction']
            cohort = c.get('institutional_request_people', spec['institutional_request_people'])
            active = affiliated & (request >= spec['minimum_community_people']) & (
                np.minimum(ceiling, cap) >= cohort + spec['minimum_community_people'])
            staff = np.where(active, cohort, 0.)
            civil = np.minimum(request, np.maximum(np.minimum(ceiling, cap) - staff, 0.))
            total = civil + staff; rural = population - total
            key = row['field_key']; extract = lambda suffix: fields[key + '__' + suffix]
            for name, expected in [('civilian', civil), ('staff', staff), ('total', total), ('rural', rural),
                                   ('population_budget', cap), ('origin_transfer', total), ('food_ceiling', ceiling)]:
                np.testing.assert_allclose(extract(name), expected, rtol=1e-10, atol=1e-6)
            np.testing.assert_array_equal(extract('active'), active)
            assert np.all(total <= cap + 1e-7) and np.all(total <= ceiling + 1e-7)
            error = float(population.sum() - rural.sum() - total.sum()); max_balance = max(max_balance, abs(error))
            assert abs(error) < 1e-7 * max(1., population.sum())
            arrivals = np.array(c['monthly_arrivals_kcal']).T
            need = np.broadcast_to(total * spec['ration_kcal_person_day'] * spec['year_days'] / 12, arrivals.shape)
            food = periodic_food_year(arrivals, need, total * spec['ration_kcal_person_day'] * spec['destination_store_demand_days'],
                loss_fraction_year=spec['annual_stored_energy_loss_fraction'], step_days=spec['year_days'] / 12, record=True)
            for field, suffix in [('consumed', 'food_consumed'), ('unmet', 'food_unmet'), ('spoiled', 'food_spoiled'), ('overflow', 'food_unused')]:
                np.testing.assert_allclose(extract(suffix), getattr(food, field), rtol=1e-9, atol=1e-2)
            assert np.all(food.unmet <= 1e-6 * np.maximum(1., food.needed))
            sums = dict(reference_catchment_people=population.sum(), rural_people=rural.sum(),
                civilian_people=civil.sum(), staff_people=staff.sum(), town_people=total.sum(),
                old_town_people=np.sum(c['civilian_people']) + np.sum(c['institutional_people']),
                old_staff_people=np.sum(c['institutional_people']), active_sources=active.sum(),
                old_active_sources=np.sum(c['institutional_active']),
                viable_communities=np.sum(civil >= spec['minimum_community_people']),
                destination_food_unmet_kcal=food.unmet.sum())
            for name, expected in sums.items():
                np.testing.assert_allclose(row[name], expected, rtol=1e-10, atol=1e-3)
            assert not row['rural_food_and_production_recomputed'] and not row['control_reach_recomputed']
            checked += 1; sites_checked += len(population)
    gates = {g['name']: g for g in r['manufactured_food_gates']}
    assert gates['balanced']['source_food_feasible'] and gates['transport_loss']['source_food_feasible']
    assert gates['rural_meal_shortage']['status'] == 'rejected'
    for name in ('balanced', 'transport_loss'):
        g = gates[name]
        assert abs(g['rural_people'] + g['settlement_people'] - 100) < 1e-9
        balance = (g['origin_harvest_kcal'] - g['rural_meals_kcal'] - g['origin_spoilage_kcal']
            - g['origin_unused_kcal'] - g['transport_loss_kcal'] - g['destination_meals_kcal']
            - g['destination_spoilage_kcal'] - g['destination_unused_kcal'] - g['periodic_stock_change_kcal'])
        assert abs(balance - g['joint_residual_kcal']) < 1e-8 and abs(balance) < 1e-6
    assert not r['adopt'] and not r['earth_calibrated_resident_sizes']
    write(out / 'review.json', dict(status='passed', results_sha256=sha(out / 'results.json'),
        reviewer_sha256=sha(Path(__file__)), scenarios_checked=checked, site_scenarios_checked=sites_checked,
        maximum_population_balance_error=max_balance, scalar_population_caps_independent=True,
        destination_food_replayed=True, manufactured_food_balances_checked=2, manufactured_shortage_refused=True,
        actual_rural_food_feedback_qualified=False, production_atlas_unchanged=True))
    print('Reviewed60resident scenarios,', sites_checked, 'site/scenario caps and both manufactured grain balances.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    check(parser.parse_args().out)
