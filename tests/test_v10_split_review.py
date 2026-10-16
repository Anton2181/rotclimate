"""Independent tamper/closure checks for saved split-column evidence."""
from copy import deepcopy
import numpy as np
import pytest
from scripts import review_v10_split_column as review
from tests.test_v10_split_column import five_fixture


def closed_record():
    case, profile, setting, geometry, air, circulation = five_fixture()
    m = review.run.model
    initial = m.initial_state(case.domain, profile, setting, geometry, air)
    water = float((initial.water.sum(0)+initial.soil).mean());energy = float(initial.energy.sum(0).mean())
    totals = dict(ocean_evaporation_mm=0., land_evaporation_mm=0., rain_mm=0., ocean_rain_mm=0.,
        runoff_mm=0., boundary_export_mm=0., roundoff_correction_mm=0., surface_latent_input_j_m2=0.,
        temperature_relaxation_j_m2=0., energy_boundary_export_j_m2=0., roundoff_energy_j_m2=0.,
        prescribed_flow_work_j_m2=0., boundary_import_gross_mm=2., boundary_export_gross_mm=2.)
    info = dict(initial_water=water, initial_energy=energy, totals=totals,
        budget=dict(totals, annual_water_error_mm=0., annual_energy_error_j_m2=0.),
        diagnostics={'layer_rain_scored_land_mm': np.zeros((12, 5)).tolist()})
    record = (deepcopy(initial), np.zeros((12,)+case.domain.land.shape), None, None, info)
    return record, initial, case


def test_reconstructs_closed_annual_fields_without_integrating():
    record, initial, case = closed_record()
    assert set(review.verify_annual(record, initial, case).values()) == {0.}


def test_rejects_changed_fifth_water_layer_even_with_claimed_zero_residual():
    record, initial, case = closed_record();record[0].water[4] += .1
    with pytest.raises(ValueError, match='balance'):
        review.verify_annual(record, initial, case)


def test_rejects_hidden_energy_source():
    record, initial, case = closed_record();record[0].energy[4] += 100.
    with pytest.raises(ValueError, match='balance'):
        review.verify_annual(record, initial, case)


def test_rejects_changed_gross_import_even_when_net_export_unchanged():
    record, initial, case = closed_record();record[-1]['budget']['boundary_import_gross_mm'] += 1.
    with pytest.raises(ValueError, match='balance'):
        review.verify_annual(record, initial, case)


def test_rejects_unaccounted_layer_rain_and_broken_cycle_start():
    record, initial, case = closed_record()
    record[-1]['diagnostics']['layer_rain_scored_land_mm'][0][4] = 1.
    with pytest.raises(ValueError, match='Layer rainfall'):
        review.verify_annual(record, initial, case)
    record[-1]['initial_water'] += 1.
    with pytest.raises(ValueError, match='preceding physical state'):
        review.verify_annual(record, initial, case)


def test_supply_fraction_includes_ocean_rain_land_recycling_and_storage():
    b = dict(boundary_import_gross_mm=100., ocean_evaporation_mm=80., land_evaporation_mm=20.,
        boundary_export_gross_mm=160., rain_mm=30.)
    row = review.supply_balance(b)
    assert row['rain_to_supply'] == .15
    assert row['export_to_supply'] == .8  # Remaining .05 is atmospheric storage.
    assert row['total_atmospheric_supply_mm'] == 200.


def test_error_reduction_can_be_overwet_correction_while_dry_cell_worsens():
    observed = np.full((12, 1, 2), 10.)
    old = np.tile([30., 5.], (12, 1, 1));new = np.tile([15., 0.], (12, 1, 1))
    row = review.error_changes(old, new, observed, np.ones((1, 2), bool))
    assert row['total_mae_improvement_mm'] == 5.
    assert row['baseline_annual_overwet_cells_contribution_mm'] == 7.5
    assert row['baseline_annual_underwet_cells_contribution_mm'] == -2.5
    assert row['fraction_cells_with_lower_monthly_error'] == .5
