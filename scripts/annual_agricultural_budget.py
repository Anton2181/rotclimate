"""Trace and check archived agricultural budgets; imports no model/solver."""
import argparse
import ast
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/annual_agricultural_budget_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/annual_agricultural_budget.json'
PARENT = ROOT / 'output/annual_assumption_impact_20261117'
SUPPLY = ROOT / 'output/urban_candidate_supply_20261116/results.json'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def close(a, b):
    assert math.isclose(a, b, rel_tol=2e-12, abs_tol=2e-6), (a, b)


def write(p, data):
    p.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def recipe():
    note = read(ROOT / 'research_notes/farm_labour_20261103.json')
    conversion = note['scenario']['hours_per_workday'] / note['scenario']['iugerum_hectares']
    listed = {c: math.fsum(tasks.values()) * conversion for c, tasks in note['workdays_per_iugerum'].items()}
    reap = {c: tasks['reap'] * conversion for c, tasks in note['workdays_per_iugerum'].items()}
    assert listed == {'wheat': 336., 'barley': 208.} and reap == {'wheat': 48., 'barley': 32.}
    tree = ast.parse((ROOT / 'harvest/field_support.py').read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'field_support')
    defaults = {arg.arg: ast.literal_eval(value) for arg, value in zip(function.args.kwonlyargs, function.args.kw_defaults) if value is not None}
    assert defaults == dict(worker_fraction=.4, hours_worker_year=600., harvest_days=30.,
                           hours_worker_day=8., ration_kcal_day=2500., year_days=365.)
    land = ast.parse((ROOT / 'scripts/land_people.py').read_text())
    constants = {}
    for n in land.body:
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name) and target.id in ['FARMED_SHARE', 'FALLOW', 'NEED_KCAL']:
                    constants[target.id] = ast.literal_eval(n.value)
    assert constants == dict(FARMED_SHARE=.6, FALLOW=.6, NEED_KCAL=1.1e6)
    return dict(field_support_defaults=defaults, listed_hours_per_cropped_hectare=listed,
        reaping_hours_per_cropped_hectare=reap, iugerum_hectares=note['scenario']['iugerum_hectares'],
        assumed_hours_per_workday=note['scenario']['hours_per_workday'], land_people_constants=constants,
        cereal_sown_share_of_arable=constants['FARMED_SHARE'] * constants['FALLOW'],
        annual_grain_ration_kcal=defaults['ration_kcal_day'] * defaults['year_days'],
        crop_selection='Least listed hours per net kcal among wheat/barley; not the broader population crop mix.',
        area_recipe='100 * land_fraction * cell_km**2 * arable * FARMED_SHARE * FALLOW hectares before work limits.',
        production_recipe='Selected cereal net kcal/ha * potential cropped hectares; seed/edible deductions already upstream.',
        retained_recipe='min(1,annual_hours/required_listed_hours,reaping_allowance/required_reaping_hours) per cell.',
        area_total='Not recovered from aggregate work totals; needs cell crop identities and retained area.',
        evidence='Columella task days prescribed; hour conversion, workforce, allowances and crop/land transfer are assumptions. FALLOW is a Han AD2 development calibration, not a Roman observation.')


def main(out):
    assert not (out / 'results.json').exists(), 'Use a fresh --out'
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    q = read(PARENT / 'qualification.json')
    for n, h in {**q['sources_sha256'], **q['protected_sha256']}.items():
        assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items():
        assert sha(PARENT / n) == h, n
    screen = ROOT / 'output/karanis_density_feasibility_20261117/qualification.json'
    k = read(screen)
    for n, h in k['sources_sha256'].items():
        assert sha(ROOT / n) == h, n
    assert k['parent_qualification_sha256'] == sha(PARENT / 'qualification.json')
    source = read(SUPPLY); rows = []; fixed_potential = {}; identities = 0
    for model in ['candidate', 'control']:
        for climate in ['raw', 'corrected']:
            for name, s in sorted(source['variants'][model]['climates'][climate]['scenarios'].items()):
                d = source['diagnostics'][model][climate][name]; ledger = s['ledger_person_years']
                need = d['rural_need_person_years']; deficit = d['rural_food_shortfall_person_years']
                retained = need - deficit; surplus = d['source_surplus_person_years']
                potential = math.fsum([s['produced_person_years'], d['production_forgone_person_years']])
                transport = math.fsum([ledger['hinterland_transport'], ledger['between_town_transport']])
                checks = [(d['rural_workers'], .4 * s['rural_people']),
                    (d['annual_hours_available'], d['rural_workers'] * s['hours_worker_year']),
                    (d['reaping_hours_available'], d['rural_workers'] * min(s['hours_worker_year'], 240.)),
                    (s['produced_person_years'], math.fsum([retained, surplus])),
                    (d['marketed_person_years'], surplus * s['extraction']),
                    (d['marketed_person_years'], ledger['available']),
                    (ledger['available'], math.fsum([ledger['left_in_cells'], transport, ledger['eaten_from_hinterland'],
                        ledger['received_between_towns'], ledger['unused_excess']])),
                    (s['residents_fed'], math.fsum([ledger['eaten_from_hinterland'], ledger['received_between_towns']])),
                    (d['town_unfed_person_years'], s['residents'] - s['residents_fed'])]
                for a, b in checks:
                    close(a, b); identities += 1
                if climate in fixed_potential: close(potential, fixed_potential[climate])
                else: fixed_potential[climate] = potential
                assert 0 <= d['annual_hours_used'] <= d['annual_hours_available'] + 1e-5
                rows.append(dict(model=model, climate=climate, scenario=name, density=s['density'],
                    hours_per_worker=s['hours_worker_year'], rural_people=s['rural_people'], rural_workers=d['rural_workers'],
                    listed_hours_available=d['annual_hours_available'], listed_hours_used=d['annual_hours_used'],
                    allowance_hours_per_rural_person=d['annual_hours_available'] / s['rural_people'],
                    used_hours_per_rural_person=d['annual_hours_used'] / s['rural_people'],
                    unused_listed_hours=d['annual_hours_available'] - d['annual_hours_used'],
                    potential_grain_ration_years=potential, production_grain_ration_years=s['produced_person_years'],
                    forgone_under_work_limits_ration_years=d['production_forgone_person_years'],
                    retained_fraction_of_potential=s['produced_person_years'] / potential,
                    rural_need_ration_years=need, rural_retained_ration_years=retained, rural_shortfall_ration_years=deficit,
                    source_surplus_ration_years=surplus, marketed_fraction=s['extraction'],
                    marketed_ration_years=ledger['available'], unmarketed_surplus_ration_years=surplus - ledger['available'],
                    left_at_origins_ration_years=ledger['left_in_cells'],
                    transport_cost_ration_equivalents=transport,
                    town_consumed_ration_years=s['residents_fed'], unused_town_excess_ration_years=ledger['unused_excess'],
                    town_resident_request=s['residents'], town_shortfall_ration_years=d['town_unfed_person_years']))
    paths = [PLAN, Path(__file__), SUPPLY, PARENT / 'qualification.json', screen]
    paths += [ROOT / n for n in ['harvest/field_support.py', 'harvest/work_maps.py', 'scripts/land_people.py',
        'scripts/build_cereal_work_maps.py', 'scripts/prepare_settlement_feedback.py', 'scripts/build_wide_supply_release3.py',
        'research_notes/farm_labour_20261103.json']]
    # Historical annual receipts pin the field-support and supply implementations.
    for path in paths:
        key = str(path.relative_to(ROOT))
        if key in source['sources_sha256']: assert sha(path) == source['sources_sha256'][key], key
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'budget.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    write(out / 'recipe.json', recipe())
    write(out / 'results.json', dict(status='checked_archived_annual_agricultural_budget_not_complete_farm_economy',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths},
        files_sha256={n: sha(out / n) for n in ['budget.csv', 'recipe.json']},
        rows=len(rows), scalar_ledger_identities_checked=identities,
        scope='Archived aggregate scalar identities and current pinned recipe definitions; no new cell work/food/route calculation.',
        independent_model_revalidation=False, complete_crop_area_recovered=False,
        complete_household_draft_budget=False, model_solver_calls=0, main_atlas_changed=False, adopt=False))
    print(f'{len(rows)} annual budgets; {identities} scalar identities; no model runs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
