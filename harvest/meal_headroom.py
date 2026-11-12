"""Conditional civilian meals under fixed staff, cargo and physical storage.

This is not resident replanning: source production and worker jobs stay frozen.
"""
from dataclasses import dataclass
from math import isfinite

from harvest.event_food_stocks import EventFoodYear, periodic_event_food_year


@dataclass(frozen=True)
class MealHeadroom:
    staff_feasible: bool
    full_demand_passes: bool
    passing_alpha: float | None
    failing_alpha: float | None
    staff_only: EventFoodYear
    full_demand: EventFoodYear
    passing_inventory: EventFoodYear | None
    failing_inventory: EventFoodYear | None


def passes(inventory):
    return inventory.unmet <= 1e-8 * max(1., inventory.needed)


def civilian_meal_headroom(times, supplies, *, staff_residents, civilian_residents, capacity,
                           kcal_day=2500., year_days=365., loss_fraction_year=.05):
    if not all(isfinite(v) and v >= 0 for v in (staff_residents, civilian_residents, capacity)) or not isfinite(kcal_day) or kcal_day <= 0:
        raise ValueError('Residents, capacity and meal energy must be finite and nonnegative')
    times, supplies = tuple(times), tuple(supplies)
    def trial(alpha):
        return periodic_event_food_year(times, supplies, demand_rate=kcal_day*(staff_residents+alpha*civilian_residents),
            capacity=capacity, year_days=year_days, loss_fraction_year=loss_fraction_year)
    staff, full = trial(0.), trial(1.)
    if not passes(staff):
        if passes(full): raise ArithmeticError('Meal feasibility must be monotone')
        return MealHeadroom(False, False, None, 0., staff, full, None, staff)
    if passes(full): return MealHeadroom(True, True, 1., None, staff, full, full, None)
    low, high = 0., 1.; passing, failing = staff, full
    for _ in range(48):
        middle = low + .5*(high-low); inventory = trial(middle)
        if passes(inventory): low, passing = middle, inventory
        else: high, failing = middle, inventory
    if not passes(passing) or passes(failing) or high-low > 2**-48:
        raise ArithmeticError('Conditional meal bracket failed')
    return MealHeadroom(True, False, low, high, staff, full, passing, failing)
