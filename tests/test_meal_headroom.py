from dataclasses import asdict

import numpy as np
import pytest

from harvest.meal_headroom import civilian_meal_headroom, passes


def run(**changes):
    args=dict(times=[0.],supplies=[100.],staff_residents=2.,civilian_residents=8.,capacity=100.,kcal_day=1.,year_days=10.,loss_fraction_year=0.)
    args.update(changes);return civilian_meal_headroom(**args)


def test_full_demand_and_zero_civilian_endpoints():
    r=run();assert r.staff_feasible and r.full_demand_passes and r.passing_alpha==1 and r.failing_alpha is None
    assert r.passing_inventory.needed==100 and r.passing_inventory.initial_stock==0
    r=run(civilian_residents=0.);assert r.passing_alpha==1 and r.full_demand.needed==20


def test_fixed_staff_and_storage_with_intermediate_tight_bound():
    r=run(supplies=[60.]);assert r.staff_feasible and not r.full_demand_passes
    assert r.passing_alpha==pytest.approx(.5,abs=2e-8) and r.failing_alpha-r.passing_alpha<=2**-48
    assert r.staff_only.needed==20 and r.full_demand.needed==100
    assert passes(r.passing_inventory) and not passes(r.failing_inventory)
    assert r.passing_inventory.needed==pytest.approx(60.,abs=1e-5)


def test_staff_only_failure_is_explicit_without_fictitious_residents():
    r=run(supplies=[10.]);assert not r.staff_feasible and r.passing_alpha is None and r.passing_inventory is None
    assert r.failing_alpha==0 and r.failing_inventory==r.staff_only and r.staff_only.unmet>0


def test_original_physical_capacity_is_not_rescaled_with_meals():
    # 100 units cannot be held in a 10-unit store; reducing demand does not
    # silently reduce that already fixed physical store further.
    r=run(capacity=10.,staff_residents=0.,supplies=[100.])
    assert r.passing_alpha==pytest.approx(.125,abs=2e-8)
    assert r.passing_inventory.peak_stock==10 and r.passing_inventory.overflow==90


def test_determinism_nonmutation_and_no_external_initial_reserve():
    times=np.array([5.]);cargo=np.array([60.]);old=cargo.copy()
    r=run(times=times,supplies=cargo);repeat=run(times=times,supplies=cargo)
    assert asdict(r)==asdict(repeat);np.testing.assert_array_equal(cargo,old)
    assert r.passing_inventory.initial_stock==pytest.approx(30.,abs=1e-5)
    assert abs(r.passing_inventory.periodic_residual)<1e-10


def test_invalid_residents_or_meal_units_rejected():
    for changes in [dict(staff_residents=-1.),dict(civilian_residents=float('nan')),dict(capacity=-1.),dict(kcal_day=0.)]:
        with pytest.raises(ValueError):run(**changes)
