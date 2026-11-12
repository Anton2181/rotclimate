"""Choose one coherent provider-year calendar while retaining baseline tasks.

This constructs a feasible lower bound from already checked schedules. The
twelve-bin mandatory-work flag is a necessary delivery gate,not food validation.
"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np


@dataclass
class ProviderYearSelection:
    policy: np.ndarray
    mandatory_complete: np.ndarray
    baseline_task_counts: np.ndarray
    selected_task_counts: np.ndarray
    added_task_counts: np.ndarray
    joint_rejected_lost_tasks: np.ndarray
    qualified_tasks: tuple


def _tasks(values, providers):
    if len(values) != providers: raise ValueError('One task collection per provider required')
    result = []
    for tasks in values:
        normalized = set()
        for task in tasks:
            if not isinstance(task, (tuple, list)) or len(task) != 3:
                raise ValueError('Task identity requires month,actor,target')
            if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Integral) for v in task):
                raise ValueError('Exact integer task identities required')
            month, actor, target = map(int, task)
            if not 0 <= month < 12 or actor < 0 or target < 0: raise ValueError('Valid month and known actor/target required')
            identity = month, actor, target
            if identity in normalized: raise ValueError('Duplicate provider task identity')
            normalized.add(identity)
        result.append(frozenset(normalized))
    return result


def select_provider_years(*, active, baseline_complete, joint_complete, baseline_tasks, joint_tasks, funded_tasks):
    enabled = np.asarray(active); base_bins, joint_bins = np.asarray(baseline_complete), np.asarray(joint_complete)
    if enabled.ndim != 1 or enabled.dtype.kind != 'b': raise ValueError('Explicit active supported-provider flags required')
    n = len(enabled)
    if any(v.shape != (12, n) or v.dtype.kind != 'b' for v in (base_bins, joint_bins)):
        raise ValueError('Twelve mandatory-work completion bins per provider required')
    base, joint, funded = (_tasks(v, n) for v in (baseline_tasks, joint_tasks, funded_tasks))
    if any(not a.issubset(f) or not b.issubset(f) for a, b, f in zip(base, joint, funded)):
        raise ValueError('Calendar task outside the original funded plan')
    base_ok = enabled & base_bins.all(axis=0); joint_ok = enabled & joint_bins.all(axis=0)
    policy = np.zeros(n, 'i1'); complete = np.zeros(n, bool); old_counts = np.zeros(n, 'i8'); counts = np.zeros(n, 'i8'); rejected = np.zeros(n, bool); selected = []
    for site in range(n):
        old = base[site] if base_ok[site] else frozenset()
        if base_ok[site]:
            rejected[site] = bool(joint_ok[site] and not base[site].issubset(joint[site]))
            if joint_ok[site] and base[site].issubset(joint[site]) and len(joint[site]) > len(base[site]): policy[site] = 1
        elif joint_ok[site]: policy[site] = 1
        complete[site] = joint_ok[site] if policy[site] else base_ok[site]
        chosen = (joint[site] if policy[site] else base[site]) if complete[site] else frozenset()
        if not old.issubset(chosen) or not chosen.issubset(funded[site]): raise RuntimeError('Provider-year selection lost baseline tasks or invented work')
        old_counts[site] = len(old); counts[site] = len(chosen); selected.append(chosen)
    return ProviderYearSelection(policy, complete, old_counts, counts, counts - old_counts, rejected, tuple(selected))
