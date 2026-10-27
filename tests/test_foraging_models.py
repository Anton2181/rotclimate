"""Independent energy/resource cases for the published-equation human kernel."""
from dataclasses import replace
import math
import numpy as np
import pytest

from foraging.models import (ForagingParams, demographic_rates,
    dry_matter_g_m2_to_kg_km2, energy_to_fat_change, fat_components, simulate_foraging)


def fixed_effort(**updates):
    return replace(ForagingParams(),min_hours=.5,max_hours=.5,initial_hours=.5,
                   hours_step=0.,maximum_birth_rate=0.,background_mortality_year=0.,
                   reproduction_mj_birth=0.,population_floor_people_km2=0.,
                   plant_decay_day=0.,**updates)


def test_units_and_asymmetric_fat_conversion_have_analytic_values():
    np.testing.assert_array_equal(dry_matter_g_m2_to_kg_km2([0.,1.,1000.]),[0.,1000.,1e6])
    np.testing.assert_allclose(energy_to_fat_change([-39.3,0.,54.6]),[-1.,0.,1.])
    fat,debt=fat_components([-2.,0.,3.])
    np.testing.assert_array_equal(fat,[0.,0.,3.])
    np.testing.assert_allclose(debt,[78.6,0.,0.])


def test_no_food_pays_known_energy_cost_without_creating_a_negative_physical_stock():
    p=fixed_effort()
    result=simulate_foraging(np.zeros((1,1)),np.zeros((1,1)),params=p,
                            initial_density=1.,years=1,min_years=1)
    expected=7.5-(8.37+1.25*.5)/39.3
    np.testing.assert_allclose(result['effective_fat_kg'],expected)
    np.testing.assert_allclose(result['annual_expenditure_mj_person'],8.995)
    np.testing.assert_array_equal(result['annual_intake_mj_person'],0.)
    assert result['maximum_energy_residual_mj_person'].max() < 1e-12
    assert not result['converged'].any()  # Exhausting max years is not convergence.


def test_equal_food_pools_have_closed_form_total_intake_independent_of_time_split():
    # At P=1 and B_V=B_A=c*50=10,000 kgDM/km², both efficiencies are1/2.
    # Thus half an hour over either pool yields exactly10kgDM/person total.
    p=fixed_effort()
    r=simulate_foraging(np.full((1,1),10000.),np.full((1,1),10000.),
                       params=p,initial_density=1.,years=1,min_years=1)
    np.testing.assert_allclose(r['annual_intake_mj_person'],98.)
    np.testing.assert_allclose(r['annual_plant_harvest_kg_dm_km2']+
                               r['annual_meat_harvest_kg_dm_km2'],10.)
    np.testing.assert_allclose(r['plant_stock_kg_dm_km2']+
                               r['meat_stock_kg_dm_km2'],19990.)
    np.testing.assert_allclose(r['effective_fat_kg'],7.5+(98.-8.995)/54.6)


def test_harvest_and_fat_ceiling_leave_unconsumed_food_in_the_resource_pool():
    p=fixed_effort()
    r=simulate_foraging(np.full((1,1),1e8),np.full((1,1),1e8),params=p,
                       initial_density=1.,initial_fat_kg=15.,years=1,min_years=1)
    np.testing.assert_allclose(r['annual_intake_mj_person'],8.995)
    np.testing.assert_allclose(r['fat_kg'],15.)
    harvested=(r['annual_plant_harvest_kg_dm_km2']+r['annual_meat_harvest_kg_dm_km2'])
    np.testing.assert_allclose(harvested,8.995/9.8)
    assert r['maximum_relative_resource_residual'].max() < 1e-14
    assert r['maximum_relative_energy_residual'].max() < 1e-14


def test_annual_prey_reset_records_unused_mass_and_does_not_accumulate_it():
    p=fixed_effort()
    r=simulate_foraging(np.full((1,1),1e8),np.full((1,1),1e8),params=p,
                       initial_density=1.,initial_fat_kg=15.,years=2,min_years=2)
    assert r['annual_unused_prey_kg_dm_km2'][0] > 9e7
    assert r['meat_stock_kg_dm_km2'][0] < 1e8
    assert r['maximum_relative_resource_residual'].max() < 1e-14


def test_starvation_floor_is_visible_and_not_reported_as_supported_population():
    r=simulate_foraging(np.zeros((365,2)),np.zeros((365,2)),
                       years=5,min_years=2)
    assert r['unsupported'].all() and r['floor_limited'].all()
    np.testing.assert_array_equal(r['density_people_km2'],0.)
    np.testing.assert_allclose(r['raw_density_people_km2'],.001)
    assert (r['fat_kg'] >= 0).all() and (r['energy_debt_mj'] > 0).all()
    assert not r['converged'].any()


def test_individual_cells_and_chunks_are_identical():
    plants=np.tile([10.,100.,1000.],(12,1))
    prey=np.zeros_like(plants);prey[0]=[1000.,10000.,100000.]
    together=simulate_foraging(plants,prey,years=3,min_years=2)
    for i in range(3):
        alone=simulate_foraging(plants[:,i:i+1],prey[:,i:i+1],years=3,min_years=2)
        for key in ('density_people_km2','foraging_hours_day','meat_fraction',
                    'scarcity_days_year','fat_kg','energy_debt_mj','years_simulated','converged'):
            np.testing.assert_array_equal(together[key][i:i+1],alone[key])


def test_birth_and_starvation_reference_points_and_invalid_forcing():
    birth,starve=demographic_rates([0.,7.5,15.])
    np.testing.assert_allclose(birth[1],.05)
    np.testing.assert_allclose(starve[0],.5)
    assert np.all(np.diff(birth)>0) and np.all(np.diff(starve)<0)
    with pytest.raises(ValueError):simulate_foraging(np.ones((12,2)),np.zeros((12,3)))
    with pytest.raises(ValueError):simulate_foraging(-np.ones((12,2)),np.zeros((12,2)))
    with pytest.raises(ValueError):simulate_foraging(np.ones((12,2)),np.zeros((12,2)),day_weights=np.arange(1,13))
    with pytest.raises(ValueError):replace(ForagingParams(),plant_decay_day=1.01).validate()


def test_display_averages_final_years_instead_of_arbitrary_terminal_phase():
    plant=np.full((10,1),100.)
    meat=np.zeros_like(plant);meat[0]=10000.
    annual=[]
    for years in range(1,5):
        annual.append(simulate_foraging(plant,meat,years=years,min_years=years,
                                       averaging_years=1)['terminal_density_people_km2'][0])
    averaged=simulate_foraging(plant,meat,years=4,min_years=4,averaging_years=3)
    np.testing.assert_allclose(averaged['mean_density_people_km2'],np.mean(annual[-3:]))
    np.testing.assert_allclose(averaged['density_std_people_km2'],np.std(annual[-3:]))
    assert averaged['averaging_years_used'][0] == 3
    assert not averaged['converged'][0]


def test_final_annual_resource_and_energy_accounts_include_reset_and_reproduction():
    plant=np.full((20,2),100.)
    meat=np.zeros_like(plant);meat[0]=[500.,1500.]
    r=simulate_foraging(plant,meat,years=3,min_years=3)
    plant_balance=(r['annual_start_plant_stock_kg_dm_km2']+
        r['annual_plant_supply_kg_dm_km2']-r['annual_plant_harvest_kg_dm_km2']-
        r['annual_plant_decay_kg_dm_km2']-r['plant_stock_kg_dm_km2'])
    meat_balance=(r['annual_start_meat_stock_kg_dm_km2']+
        r['annual_meat_supply_kg_dm_km2']-r['annual_meat_harvest_kg_dm_km2']-
        r['annual_meat_decay_kg_dm_km2']-r['annual_unused_prey_kg_dm_km2']-
        r['meat_stock_kg_dm_km2'])
    np.testing.assert_allclose(plant_balance,0.,atol=1e-10)
    np.testing.assert_allclose(meat_balance,0.,atol=1e-10)
    np.testing.assert_allclose(r['annual_intake_mj_person']-
        r['annual_expenditure_mj_person']-r['annual_reproduction_mj_person']-
        r['annual_fat_energy_change_mj_person'],0.,atol=1e-10)
