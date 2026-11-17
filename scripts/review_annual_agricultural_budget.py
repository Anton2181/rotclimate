"""Independent scalar check of every budget column; no production-model replay."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/annual_agricultural_budget_20261117'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    assert not (OUT / 'qualification.json').exists()
    result = read(OUT / 'results.json')
    for n, h in result['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in result['files_sha256'].items(): assert sha(OUT / n) == h, n
    for n in ['results.json', *result['files_sha256']]:
        assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    parent = read(ROOT / 'output/annual_assumption_impact_20261117/qualification.json')
    for n, h in {**parent['sources_sha256'], **parent['protected_sha256']}.items(): assert sha(ROOT / n) == h, n
    for n, h in parent['files_sha256'].items(): assert sha(ROOT / 'output/annual_assumption_impact_20261117' / n) == h, n
    source = read(ROOT / 'output/urban_candidate_supply_20261116/results.json')
    checked = 0; seen = set()
    with (OUT / 'budget.csv').open() as f:
        for row in csv.DictReader(f):
            m, c, n = row['model'], row['climate'], row['scenario']
            assert (m, c, n) not in seen; seen.add((m, c, n))
            s = source['variants'][m]['climates'][c]['scenarios'][n]; d = source['diagnostics'][m][c][n]
            l = s['ledger_person_years']; rural = s['rural_people']; production = s['produced_person_years']
            # Reconstruct intermediate quantities using independent complementary identities.
            rural_retained = production - d['source_surplus_person_years']
            marketed = d['source_surplus_person_years'] * s['extraction']
            transport = marketed - l['left_in_cells'] - s['residents_fed'] - l['unused_excess']
            expected = dict(model=m, climate=c, scenario=n, density=s['density'],
                hours_per_worker=s['hours_worker_year'], rural_people=rural, rural_workers=rural * .4,
                listed_hours_available=rural * .4 * s['hours_worker_year'], listed_hours_used=d['annual_hours_used'],
                allowance_hours_per_rural_person=.4 * s['hours_worker_year'],
                used_hours_per_rural_person=d['annual_hours_used'] / rural,
                unused_listed_hours=rural * .4 * s['hours_worker_year'] - d['annual_hours_used'],
                potential_grain_ration_years=production + d['production_forgone_person_years'],
                production_grain_ration_years=production,
                forgone_under_work_limits_ration_years=d['production_forgone_person_years'],
                retained_fraction_of_potential=1 / (1 + d['production_forgone_person_years'] / production),
                rural_need_ration_years=rural, rural_retained_ration_years=rural_retained,
                rural_shortfall_ration_years=d['rural_food_shortfall_person_years'],
                source_surplus_ration_years=d['source_surplus_person_years'], marketed_fraction=s['extraction'],
                marketed_ration_years=marketed,
                unmarketed_surplus_ration_years=d['source_surplus_person_years'] * (1 - s['extraction']),
                left_at_origins_ration_years=l['left_in_cells'], transport_cost_ration_equivalents=transport,
                town_consumed_ration_years=l['eaten_from_hinterland'] + l['received_between_towns'],
                unused_town_excess_ration_years=l['unused_excess'], town_resident_request=s['residents'],
                town_shortfall_ration_years=s['residents'] - s['residents_fed'])
            assert set(row) == set(expected)
            for k, value in expected.items():
                if isinstance(value, str): assert row[k] == value
                else: assert math.isclose(float(row[k]), value, rel_tol=2e-12, abs_tol=1e-5), (m, c, n, k, row[k], value)
                checked += 1
    assert len(seen) == result['rows'] == 32 and result['scalar_ledger_identities_checked'] == 288
    assert seen == {(m, c, n) for m in ['candidate', 'control'] for c in ['raw', 'corrected']
                    for n in source['variants'][m]['climates'][c]['scenarios']}
    recipe = read(OUT / 'recipe.json')
    assert recipe['annual_grain_ration_kcal'] == 912500 and recipe['land_people_constants']['NEED_KCAL'] == 1100000
    assert recipe['cereal_sown_share_of_arable'] == .36
    sources = dict(result['sources_sha256'])
    next_plan = 'calibration/roman_benchmark_20261117/cereal_activity_packet.json'
    for n in ['scripts/review_annual_agricultural_budget.py', 'reports/ANNUAL_AGRICULTURAL_BUDGET_20261117.md', next_plan]:
        sources[n] = sha(ROOT / n)
    receipt = dict(status='passed_scalar_annual_agricultural_trace_not_complete_farm_economy',
        sources_sha256=sources, files_sha256={n: sha(OUT / n) for n in ['results.json', 'budget.csv', 'recipe.json']},
        rows_checked=32, exported_values_checked=checked, existing_ledger_identities_checked=288,
        fresh_exports_byte_exact=True, prior_science_and_atlas_identities_exact=True,
        complete_crop_area_recovered=False, complete_household_draft_budget=False,
        model_solver_calls=0, new_fit=False, main_atlas_changed=False, adopt=False, next_plan=next_plan)
    (OUT / 'qualification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'Passed {checked} scalar/string export checks; annual grain and work trace only')


if __name__ == '__main__':
    main()
