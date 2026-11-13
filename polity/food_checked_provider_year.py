"""Choose one provider-year only when its OWN work and cereal food both pass."""
from dataclasses import dataclass

import numpy as np

from .provider_year_schedule import select_provider_years


@dataclass(frozen=True)
class FoodCheckedProviderYear:
    policy: np.ndarray
    selected_mandatory_complete: np.ndarray
    selected_food_no_shortage: np.ndarray
    qualified: np.ndarray
    baseline_task_counts: np.ndarray
    selected_task_counts: np.ndarray
    added_task_counts: np.ndarray
    joint_rejected_lost_tasks: np.ndarray
    qualified_tasks: tuple


def select_food_checked_provider_years(*,active,baseline_complete,joint_complete,baseline_food,joint_food,baseline_tasks,joint_tasks,funded_tasks):
    enabled=np.asarray(active);base=np.asarray(baseline_complete);joint=np.asarray(joint_complete);base_food=np.asarray(baseline_food);other_food=np.asarray(joint_food)
    if enabled.ndim!=1 or enabled.dtype.kind!='b':raise ValueError('Explicit active provider flags required')
    n=len(enabled)
    if any(v.shape!=(12,n) or v.dtype.kind!='b' for v in (base,joint)):raise ValueError('Twelve boolean work bins per provider required')
    if any(v.shape!=(n,) or v.dtype.kind!='b' for v in (base_food,other_food)):raise ValueError('One OWN-policy boolean food flag per provider required')
    selected=select_provider_years(active=enabled,baseline_complete=base & base_food[None,:],joint_complete=joint & other_food[None,:],
        baseline_tasks=baseline_tasks,joint_tasks=joint_tasks,funded_tasks=funded_tasks)
    use_joint=selected.policy==1
    physical=enabled & np.where(use_joint,joint.all(axis=0),base.all(axis=0))
    food=enabled & np.where(use_joint,other_food,base_food)
    qualified=physical & food
    np.testing.assert_array_equal(selected.mandatory_complete,qualified)
    return FoodCheckedProviderYear(selected.policy,physical,food,qualified,selected.baseline_task_counts,selected.selected_task_counts,
        selected.added_task_counts,selected.joint_rejected_lost_tasks,selected.qualified_tasks)
