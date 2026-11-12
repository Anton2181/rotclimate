"""Whole point visits consume a supplied, already reserved provider-hour slice.

Targets are points, not territories. Conditional demand and route preparation
belong to the caller; no extra people, food, hours or transport are inferred.
"""
from dataclasses import dataclass
import numpy as np


def land_block_targets(land, area, *, cell_km, block_cells=3):
    mask = np.asarray(land); weights = np.asarray(area, float)
    if mask.dtype.kind != 'b' or mask.ndim != 2 or weights.shape != mask.shape:
        raise ValueError('Matching boolean land and area rasters required')
    if not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError('Finite nonnegative physical cell areas required')
    if not np.isfinite(cell_km) or cell_km <= 0:
        raise ValueError('Positive physical cell size required')
    if isinstance(block_cells, bool) or not isinstance(block_cells, int) or block_cells < 1:
        raise ValueError('Positive integer target-block edge required')
    h, w = mask.shape; columns = (w + block_cells - 1) // block_cells
    nodes = []; blocks = []; areas = []; counts = []
    for y in range(0, h, block_cells):
        for x in range(0, w, block_cells):
            y1, x1 = min(h, y + block_cells), min(w, x + block_cells)
            yy, xx = np.nonzero(mask[y:y1, x:x1])
            if not len(yy): continue
            yy = yy + y; xx = xx + x
            distance = (yy - (y + y1 - 1) / 2) ** 2 + (xx - (x + x1 - 1) / 2) ** 2
            j = int(np.argmin(distance))  # nonzero is row-major: deterministic grid-ID tie.
            nodes.append(int(yy[j] * w + xx[j])); blocks.append((y // block_cells) * columns + x // block_cells)
            areas.append(float(weights[yy, xx].sum())); counts.append(len(yy))
    return dict(nodes=np.asarray(nodes, np.int64), block_ids=np.asarray(blocks, np.int64),
                represented_area_km2=np.asarray(areas), land_cells=np.asarray(counts, np.int64),
                block_edge_km=float(cell_km * block_cells))


@dataclass
class VisitAllocation:
    provider_for_target: np.ndarray
    chosen_cost_hours: np.ndarray
    served: np.ndarray
    route_unreachable: np.ndarray
    provider_work_unavailable: np.ndarray
    capacity_unmet: np.ndarray
    used_hours: np.ndarray
    unused_hours: np.ndarray


def allocate_reserved_visits(provider, target, person_hours, *, provider_actor, supported_staff,
                             active, reserved_hours, demand, crew):
    """Choose one initially affordable provider, then ration whole visits once.

    Cheapest same-actor crew-hours choose the provider; provider index breaks
    ties. Providers serve assigned jobs in cost/target order without rerouting.
    All hours must have been reserved by the SAME upstream food/work consumer.
    """
    p, t = np.asarray(provider), np.asarray(target)
    costs = np.asarray(person_hours, float); actors = np.asarray(provider_actor)
    staff = np.asarray(supported_staff, float); enabled = np.asarray(active); budget = np.asarray(reserved_hours, float)
    requests = np.asarray(demand)
    if requests.ndim != 2 or requests.dtype.kind != 'b':
        raise ValueError('Explicit actor/target boolean request grid required')
    if actors.ndim != 1 or actors.dtype.kind not in 'iu' or np.any((actors < -1) | (actors >= len(requests))):
        raise ValueError('One known actor or -1 per provider required')
    n = len(actors)
    if any(a.shape != (n,) for a in (staff, enabled, budget)) or enabled.dtype.kind != 'b':
        raise ValueError('Aligned provider staff, availability and reserved hours required')
    if any(not np.isfinite(a).all() or np.any(a < 0) for a in (staff, budget)) or np.any((~enabled | (staff == 0)) & (budget > 0)):
        raise ValueError('Reserved hours require finite supported active staff')
    if isinstance(crew, bool) or not isinstance(crew, (int, np.integer)) or not 1 <= crew <= 2 ** 53:
        raise ValueError('Positive exact integer crew size required')
    if p.ndim != 1 or t.shape != p.shape or costs.shape != p.shape or p.dtype.kind not in 'iu' or t.dtype.kind not in 'iu':
        raise ValueError('Aligned integer provider/target pairs and person-hour costs required')
    if np.any((p < 0) | (p >= n)) or np.any((t < 0) | (t >= requests.shape[1])):
        raise ValueError('Invalid visit provider or target index')
    if not np.isfinite(costs).all() or np.any(costs <= 0):
        raise ValueError('Positive finite per-person trip/duty costs required')
    if len(p):
        order = np.lexsort((t, p)); same = (p[order][1:] == p[order][:-1]) & (t[order][1:] == t[order][:-1])
        if same.any(): raise ValueError('Repeated provider/target pair would duplicate a visit')
    with np.errstate(over='ignore', under='ignore'): required = costs * crew
    if not np.isfinite(required).all() or np.any(required <= 0):
        raise ValueError('Crew work exceeds numerical range')
    actor = actors[p]; known = actor >= 0
    included = known & enabled[p]
    included[known] &= requests[actor[known], t[known]]
    physical = np.zeros_like(requests); physical[actor[included], t[included]] = True
    affordable = included & (staff[p] >= crew) & (budget[p] >= required)
    indices = np.flatnonzero(affordable)
    order = indices[np.lexsort((p[indices], required[indices], t[indices], actor[indices]))]
    first = np.r_[True, (actor[order][1:] != actor[order][:-1]) | (t[order][1:] != t[order][:-1])] if len(order) else np.zeros(0, bool)
    selected = order[first]
    chosen = np.full(requests.shape, -1, np.int64); chosen_cost = np.zeros(requests.shape)
    chosen[actor[selected], t[selected]] = p[selected]; chosen_cost[actor[selected], t[selected]] = required[selected]
    served = np.zeros_like(requests); used = np.zeros(n)
    for source in np.unique(p[selected]):
        jobs = selected[p[selected] == source]
        jobs = jobs[np.lexsort((t[jobs], required[jobs]))]
        with np.errstate(over='ignore'): cumulative = np.cumsum(required[jobs])
        if not np.isfinite(cumulative).all(): raise ValueError('Assigned visit work exceeds numerical range')
        completed = jobs[cumulative <= budget[source]]
        served[actor[completed], t[completed]] = True
        # Same positive sequential sum as the capacity predicate.
        used[source] = cumulative[len(completed) - 1] if len(completed) else 0.
    no_route = requests & ~physical
    no_provider = requests & physical & (chosen < 0)
    exhausted = requests & (chosen >= 0) & ~served
    partition = served.astype(np.uint8) + no_route + no_provider + exhausted
    if not np.array_equal(partition, requests.astype(np.uint8)) or np.any(used > budget):
        raise RuntimeError('Actor/target visits or reserved provider hours were reused')
    return VisitAllocation(chosen, chosen_cost, served, no_route, no_provider, exhausted, used, budget - used)
