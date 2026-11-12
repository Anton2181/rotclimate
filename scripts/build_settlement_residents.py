"""Finite resident-budget sensitivity on existing atlas destination food cases.

Catchment people are an explicitly assumed population envelope. Arrivals retain
the OLD rural-food claim, so these are demographic/destination-food diagnostics,
not a fully recomputed rural/urban food equilibrium or a production release.
"""
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity.settlement_residents import allocate_residents, audit_origin_food
from polity.settlement_support import allocate_settlement

OUT = ROOT / 'output/settlement_residents_20261112'
MODELS = {mode: ROOT / 'atlases/earth_fit/data' / ('corrected' if mode == 'corrected' else '') / 'settled_reach.json.gz'
          for mode in ('raw', 'corrected')}


def manufactured():
    records = []
    for name, source_people, retention, expected in [('balanced', 100., 1., True),
        ('transport_loss', 105., .8, True), ('rural_meal_shortage', 90., 1., False)]:
        allocation = allocate_residents(np.full((12, 1), 20 * 30.), [100.], np.array([0]), [100.], [True],
            transfer_fraction=.2, institutional_request=10., minimum_community=5., kcal_day=1.,
            year_days=360., store_days=360., loss_fraction_year=0.)
        departures = np.full((12, 1), 20 * 30. / retention)
        try:
            audit = audit_origin_food(allocation, np.full((12, 1), source_people * 30.), departures,
                origin_capacity_kcal=[100000.], retention=retention, delay_bins=0, loss_fraction_year=0.)
            record = {k: v for k, v in audit.items() if k != 'origin_food_year'}
            passed = True
        except ValueError as error:
            record = dict(status='rejected', reason=str(error)); passed = False
        if passed != expected:
            raise ValueError('Manufactured food gate differs from its declared expectation: ' + name)
        records.append(dict(name=name, manufactured_not_earth_evidence=True, expected_supported=expected, **record))
    return records


def run(out=OUT):
    out.mkdir(parents=True, exist_ok=True); sources = {str(p.relative_to(ROOT)): sha(p) for p in MODELS.values()}
    fields, rows, controls, inputs = {}, [], [], {}
    for climate, path in MODELS.items():
        model = json.loads(gzip.decompress(path.read_bytes())); spec = model['specification']; sites = model['sites']
        ids = [int(i) for s in sites for i in s['market_ids']]
        if len(ids) != len(set(ids)):
            raise ValueError('One market catchment appears at multiple destinations')
        population = np.array([s['served_people'] for s in sites], float)
        request = np.array([s['civilian_request_people'] for s in sites], float)
        affiliated = np.array([s['actor_index'] >= 0 for s in sites]); owners = np.arange(len(sites))
        fields[climate + '__origin_population'] = population
        fields[climate + '__nodes'] = np.array([s['node'] for s in sites], int)
        inputs[climate] = dict(sites=len(sites), reference_catchment_people=float(population.sum()),
            unique_market_ids=len(ids), minimum_origin_people=float(population.min()),
            population_status='Existing model catchment people used as a conditional population envelope, not observed residents.')
        for case in model['cases']:
            if not case.get('food_constrained'):
                continue
            arrivals = np.array(case['monthly_arrivals_kcal'], float).T
            options = dict(institutional_request=case.get('institutional_request_people', spec['institutional_request_people']),
                minimum_community=spec['minimum_community_people'], kcal_day=spec['ration_kcal_person_day'],
                year_days=spec['year_days'], store_days=spec['destination_store_demand_days'],
                loss_fraction_year=spec['annual_stored_energy_loss_fraction'])
            old = allocate_settlement(arrivals, request, affiliated, **options)
            for field, original in [('civilian_people', 'civilian_people'), ('institutional_people', 'institutional_people')]:
                np.testing.assert_allclose(getattr(old, field), case[original], rtol=1e-10, atol=1e-6)
            controls.append(dict(climate=climate, case=case['id'], original_destination_allocation_replayed=True,
                maximum_civilian_difference=float(np.abs(old.civilian_people - case['civilian_people']).max()),
                maximum_staff_difference=float(np.abs(old.institutional_people - case['institutional_people']).max())))
            for share in (.05, .075, .1):
                allocation = allocate_residents(arrivals, population, owners, request, affiliated,
                    transfer_fraction=share, **options)
                plan = allocation.settlement; key = f'{climate}__{case["id"]}__share{share:g}'
                values = dict(civilian=plan.civilian_people, staff=plan.institutional_people,
                    total=plan.total_people, rural=allocation.rural_people,
                    origin_transfer=allocation.transferred_people, population_budget=allocation.destination_budget,
                    food_ceiling=plan.food_ceiling_people, food_consumed=plan.food_year.consumed,
                    food_unmet=plan.food_year.unmet, food_spoiled=plan.food_year.spoiled,
                    food_unused=plan.food_year.overflow, active=plan.institutional_active)
                for suffix, value in values.items():
                    fields[key + '__' + suffix] = value
                rows.append(dict(climate=climate, case=case['id'], transfer_fraction=share, field_key=key,
                    reference_catchment_people=float(population.sum()), rural_people=float(allocation.rural_people.sum()),
                    civilian_people=float(plan.civilian_people.sum()), staff_people=float(plan.institutional_people.sum()),
                    town_people=float(plan.total_people.sum()), old_town_people=float(old.total_people.sum()),
                    old_staff_people=float(old.institutional_people.sum()), active_sources=int(plan.institutional_active.sum()),
                    old_active_sources=int(old.institutional_active.sum()), viable_communities=int(plan.community_viable.sum()),
                    population_balance_error=float(population.sum() - allocation.rural_people.sum() - plan.total_people.sum()),
                    maximum_population_excess=float(np.maximum(plan.total_people - allocation.destination_budget, 0).max()),
                    destination_food_unmet_kcal=float(plan.food_year.unmet.sum()),
                    destination_food_residual_kcal=float(np.abs(plan.food_year.ledger_residual).max()),
                    rural_food_and_production_recomputed=False, control_reach_recomputed=False))
        print(climate, 'resident-budget sensitivities complete', flush=True)
    if len(rows) != 60 or len(controls) != 20:
        raise ValueError('Incomplete existing-food comparison')
    np.savez_compressed(out / 'fields.npz', **fields)
    producers = [Path(__file__), ROOT / 'polity/settlement_residents.py', ROOT / 'polity/settlement_support.py', ROOT / 'harvest/food_stocks.py']
    for path, digest in sources.items():
        if sha(ROOT / path) != digest:
            raise ValueError('Existing atlas food source changed')
    write(out / 'results.json', dict(status='conditional_resident_budget_implementation_diagnostic', adopt=False,
        earth_calibrated_resident_sizes=False, sources=sources,
        producers={str(p.relative_to(ROOT)): sha(p) for p in producers}, fields_sha256=sha(out / 'fields.npz'),
        inputs=inputs, baseline_controls=controls, rows=rows, manufactured_food_gates=manufactured(),
        scope='Finite reference catchment people cap civilians and staff together. Twenty existing destination-food cases; all original map values unchanged.',
        limits='Urban shares and catchment population envelopes are scenarios. Existing food arrivals still inherit the old rural claim. Rural food/field-work feedback must be recomputed and pass the new origin-food audit before adoption. No new occupation, staff roles, control or transfer qualification.'))
    print('Completed60resident sensitivities,20old-allocation controls and3manufactured food gates.', flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    run(parser.parse_args().out)
