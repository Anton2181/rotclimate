"""Constructive extra point visits using only already-unused patrol hours.

The caller keeps all earlier completions and their providers immutable. This
routine serves only a supplied pending request set; it proves no global optimum.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class SpareVisits:
    added: np.ndarray
    provider_for_added: np.ndarray
    cost_for_added: np.ndarray
    used_hours: np.ndarray
    unused_hours: np.ndarray


def add_spare_visits(provider, target, person_hours, *, provider_actor, supported_staff,
                     active, spare_hours, pending, crew):
    actors = np.asarray(provider_actor); staff = np.asarray(supported_staff, float)
    enabled = np.asarray(active); budget = np.asarray(spare_hours, float); requests = np.asarray(pending)
    p, t, costs = np.asarray(provider), np.asarray(target), np.asarray(person_hours, float)
    if actors.ndim != 1 or actors.dtype.kind not in 'iu' or requests.ndim != 2 or requests.dtype.kind != 'b':
        raise ValueError('Explicit provider actors and pending actor/point tasks required')
    n = len(actors)
    if np.any((actors < -1) | (actors >= len(requests))) or any(a.shape != (n,) for a in (staff, enabled, budget)) or enabled.dtype.kind != 'b':
        raise ValueError('Aligned known actor or -1,staff,availability and spare hours required')
    if any(not np.isfinite(a).all() or np.any(a < 0) for a in (staff, budget)) or np.any((~enabled | (staff == 0)) & (budget > 0)):
        raise ValueError('Spare hours require finite supported active staff')
    if isinstance(crew, bool) or not isinstance(crew, (int, np.integer)) or not 1 <= crew <= 2 ** 53:
        raise ValueError('Positive exact integer crew required')
    if p.ndim != 1 or t.shape != p.shape or costs.shape != p.shape or p.dtype.kind not in 'iu' or t.dtype.kind not in 'iu':
        raise ValueError('Aligned integer provider/target paths required')
    if np.any((p < 0) | (p >= n)) or np.any((t < 0) | (t >= requests.shape[1])) or not np.isfinite(costs).all() or np.any(costs <= 0):
        raise ValueError('Valid providers,targets and positive finite route costs required')
    if len(p):
        order = np.lexsort((t, p))
        if np.any((p[order][1:] == p[order][:-1]) & (t[order][1:] == t[order][:-1])):
            raise ValueError('Duplicate provider/target route')
    with np.errstate(over='ignore', under='ignore'): required = costs * crew
    if not np.isfinite(required).all() or np.any(required <= 0): raise ValueError('Crew work exceeds numerical range')
    candidates = {}
    for source, point, cost in zip(p.tolist(), t.tolist(), required.tolist()):
        actor = int(actors[source])
        if actor >= 0 and enabled[source] and staff[source] >= crew and requests[actor, point]:
            candidates.setdefault((actor, point), []).append((cost, source))
    ordered = sorted((min(options)[0], actor, point) for (actor, point), options in candidates.items())
    added = np.zeros_like(requests); chosen = np.full(requests.shape, -1, 'i8'); selected_cost = np.zeros(requests.shape); used = np.zeros(n)
    for _, actor, point in ordered:
        for cost, source in sorted(candidates[actor, point]):
            if used[source] + cost <= budget[source]:
                added[actor, point] = True; chosen[actor, point] = source; selected_cost[actor, point] = cost
                used[source] += cost
                break
    if np.any(added & ~requests) or np.any(used > budget): raise RuntimeError('Spare visits reused tasks or provider hours')
    return SpareVisits(added, chosen, selected_cost, used, budget - used)
