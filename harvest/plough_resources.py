"""One-origin plough-package completion with explicit, simultaneous resources.

No Roman rate, operator fraction, animal supply or calendar is defaulted. These
are supplied partial-task scenarios, not complete crop or food-production plans.
"""
from dataclasses import dataclass
from numbers import Integral
from typing import ClassVar

import numpy as np

from harvest.labour import FarmOperation, plan_farm


@dataclass
class PloughCompletion:
    origin_id: str | int
    completed_hectares: float
    completed_hectares_by_period: np.ndarray
    resource_hours_used: np.ndarray
    unused_resource_hours: np.ndarray

    resource_names: ClassVar[tuple[str, ...]] = (
        'total_human', 'qualified_operator_subset', 'draft_team')
    scope: ClassVar[str] = 'plough_package_only'
    complete_crop_activity: ClassVar[bool] = False


def _scalar(value, label, *, positive):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f'{label} must be an explicit numeric quantity')
    array = np.asarray(value, float)
    if array.ndim != 0 or not np.isfinite(array):
        raise ValueError(f'Finite scalar {label} required')
    number = float(array)
    if number < 0 or (positive and number == 0):
        raise ValueError(f'{label} must be {"positive" if positive else "nonnegative"}')
    return number


def plan_plough_package(*, origin_id, maximum_package_hectares,
                        human_hours_per_hectare, operator_hours_per_hectare,
                        draft_team_hours_per_hectare, allowed, available_hours):
    """Complete supplied plough-package hectares at one physical origin.

    available_hours is time x (total human, operator subset, draft team), in
    already supplied NET hours after other duties. Operators claim the same
    human hours; the two human columns must not be added together. Each period
    requires human, qualified operator and team service simultaneously. One
    team-hour is an explicitly supplied team service, not one animal or head.

    All rates, availability and the window are mandatory. The package may bundle
    passes/ridging/sowing only as the caller defines; there is no implied pass
    sequence, full annual occupation, animal feed, crop completion or grain yield.
    Divisible area and resources follow the existing linear scheduler.
    """
    if isinstance(origin_id, (bool, np.bool_)) or not isinstance(origin_id, (str, Integral)):
        raise ValueError('One explicit string or integer physical origin ID required')
    if isinstance(origin_id, str) and not origin_id.strip():
        raise ValueError('Nonempty physical origin ID required')
    hectares = _scalar(maximum_package_hectares, 'maximum package hectares', positive=False)
    human = _scalar(human_hours_per_hectare, 'human hours/hectare', positive=True)
    operator = _scalar(operator_hours_per_hectare, 'operator hours/hectare', positive=True)
    team = _scalar(draft_team_hours_per_hectare, 'draft-team hours/hectare', positive=True)
    if operator > human:
        raise ValueError('Operator work must be a subset of total human work')
    availability = np.asarray(available_hours, float)
    if availability.ndim != 2 or availability.shape[1:] != (3,) or not len(availability):
        raise ValueError('Explicit time x three-resource availability required')
    if not np.isfinite(availability).all() or np.any(availability < 0):
        raise ValueError('Finite nonnegative net resource hours required')
    if np.any(availability[:, 1] > availability[:, 0]):
        raise ValueError('Available operator hours cannot exceed the same total human hours')
    mask = np.asarray(allowed)
    if mask.dtype.kind != 'b' or mask.shape != (len(availability),) or not mask.any():
        raise ValueError('Explicit nonempty boolean plough-package window required')
    operation = FarmOperation('supplied_plough_package', 0, mask, [human, operator, team])
    # The supplied objective is one completed PACKAGE hectare, never food.
    plan = plan_farm([1.], [operation], land_hectares=hectares, available_hours=availability)
    return PloughCompletion(origin_id, float(plan.hectares[0]),
        plan.completed_hectares[:, 0].copy(), plan.resource_hours_used.copy(),
        availability - plan.resource_hours_used)
