"""Experimental fixed-count locations; this module does not infer population or authority.

The count is supplied independently of suitability/history. Weighted sampling
without replacement provides a point-process alternative to the atlas's greedy
catchment tiling. A distance exclusion can prevent duplicate neighbouring centres;
it is an experimental parameter, not an Earth-qualified service radius.
"""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

import numpy as np
from scipy import ndimage as ndi

from polity import settle


@dataclass(frozen=True)
class Placement:
    towns: tuple[tuple[int, int], ...]
    requested: int
    eligible_cells: int

    @property
    def shortfall(self):
        return self.requested - len(self.towns)


def site_fields(density, land, water_km, road, elev, cell_km, *, allowed=None,
                aridity=None, marked=()):
    """Reuse the current environmental eligibility and marked-town catchments.

    A history prior may change scores later, but cannot change this eligibility
    mask or the legacy count budget. Neither real evaluation sites nor political
    ownership are used as attraction points here.
    """
    land = np.asarray(land, bool)
    if not np.isfinite(cell_km) or cell_km <= 0:
        raise ValueError("cell_km must be positive and finite")
    coast = ndi.distance_transform_edt(land) * cell_km
    score, smooth = settle.site_score(density, land, water_km, coast, road, elev, cell_km)
    eligible = land & (smooth >= settle.MIN_DENSITY)
    if allowed is not None:
        eligible &= np.asarray(allowed, bool)
    if aridity is not None:
        near = np.minimum(np.nan_to_num(np.asarray(water_km, float), nan=1e9), coast)
        eligible &= (np.asarray(aridity) >= settle.DRY_ARIDITY) | (near <= settle.DRY_WATER_KM)
    catchment = (settle.SEAT_PEOPLE / settle.SEAT_REF_DENSITY
                 * (settle.SEAT_REF_DENSITY / np.maximum(smooth, 1e-9)) ** settle.SEAT_BETA)
    radius_km = np.minimum(np.sqrt(catchment / np.pi), settle.MAX_RADIUS_KM)
    h, w = land.shape
    for y, x in marked:
        if not (0 <= y < h and 0 <= x < w):
            raise ValueError("marked anchor lies outside the grid")
        rad = settle.SPACING * radius_km[y, x] / cell_km
        r = int(np.ceil(rad))
        y0, y1 = max(0, y-r), min(h, y+r+1)
        x0, x1 = max(0, x-r), min(w, x+r+1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        eligible[y0:y1, x0:x1] &= (yy-y)**2 + (xx-x)**2 > rad**2
    return score, eligible


def fixed_count_sites(score, eligible, count, cell_km, *, min_spacing_km=0.0,
                      seed=1, history=None, stochastic=True):
    """Place up to ``count`` centres, reporting infeasible requests explicitly.

    ``history`` is an optional externally supplied nonnegative relative weight;
    it neither changes people nor sets the count. Zero weight removes a candidate
    and can therefore cause a reported shortfall. Positive rescaling of weights
    leaves the draw unchanged. With stochastic=False this is a greedy ablation.
    No exclusion or eligibility constraint is relaxed to fill a count.
    """
    if isinstance(count, bool) or not isinstance(count, Integral) or count < 0:
        raise ValueError("count must be a nonnegative integer")
    if not np.isfinite(cell_km) or cell_km <= 0:
        raise ValueError("cell_km must be positive and finite")
    if not np.isfinite(min_spacing_km) or min_spacing_km < 0:
        raise ValueError("min_spacing_km must be nonnegative and finite")
    score, eligible = np.asarray(score, float), np.asarray(eligible, bool)
    if score.ndim != 2 or eligible.shape != score.shape:
        raise ValueError("score and eligibility must be matching 2D grids")
    if np.any(~np.isfinite(score[eligible])) or np.any(score[eligible] < 0):
        raise ValueError("eligible scores must be finite and nonnegative")
    log_weight = np.full(score.shape, -np.inf)
    positive = eligible & (score > 0)
    log_weight[positive] = np.log(score[positive])
    if history is not None:
        prior = np.asarray(history, float)
        if prior.shape != score.shape or np.any(~np.isfinite(prior[eligible])) or np.any(prior[eligible] < 0):
            raise ValueError("history must match the grid and be finite and nonnegative on eligible cells")
        positive &= prior > 0
        log_weight[~positive] = -np.inf
        log_weight[positive] += np.log(prior[positive])
    candidates = np.flatnonzero(positive)
    available = len(candidates)
    if not count or not available:
        return Placement((), int(count), available)
    rank = log_weight.ravel()[candidates].copy()
    if stochastic:
        # Gumbel top-k gives weighted draws without replacement before exclusion.
        rank += np.random.default_rng(seed).gumbel(size=available)
    order = np.argsort(-rank, kind="stable")
    blocked = np.zeros(score.shape, bool)
    h, w = score.shape
    rad = min_spacing_km / cell_km
    r = int(np.ceil(rad))
    towns = []
    for idx in candidates[order]:
        y, x = divmod(int(idx), w)
        if blocked[y, x]:
            continue
        towns.append((y, x))
        if len(towns) == count:
            break
        y0, y1 = max(0, y-r), min(h, y+r+1)
        x0, x1 = max(0, x-r), min(w, x+r+1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        blocked[y0:y1, x0:x1] |= (yy-y)**2 + (xx-x)**2 <= rad**2
    return Placement(tuple(towns), int(count), available)


def prior_tiling_sites(density, land, water_km, road, elev, cell_km, *, prior=None, allowed=None,
                       aridity=None, marked=(), seat_people=None, seed=1):
    """Production catchment tiling with an optional occupation prior (family B).

    The prior multiplies the site score and the density that sets catchment
    radius. Eligibility always comes from the unmodified density. With
    prior=None and default seat_people this is settle.place_towns exactly.
    """
    land = np.asarray(land, bool)
    seat_people = settle.SEAT_PEOPLE if seat_people is None else seat_people
    coast_km = ndi.distance_transform_edt(land) * cell_km
    score, d = settle.site_score(density, land, water_km, coast_km, road, elev, cell_km)
    rng = np.random.default_rng(seed)
    quirk = ndi.gaussian_filter(rng.standard_normal(land.shape), 1.5)
    score = score * np.exp(0.25 * quirk / max(quirk.std(), 1e-9))
    ok = land & (d >= settle.MIN_DENSITY)
    if allowed is not None:
        ok &= np.asarray(allowed, bool)
    if aridity is not None:
        near = np.minimum(np.nan_to_num(np.asarray(water_km, float), nan=1e9), coast_km)
        ok &= ~(np.asarray(aridity, float) < settle.DRY_ARIDITY) | (near <= settle.DRY_WATER_KM)
    d_eff = d
    if prior is not None:
        p = np.asarray(prior, float)
        if p.shape != land.shape or np.any(~np.isfinite(p[ok])) or np.any(p[ok] <= 0):
            raise ValueError('Finite positive prior required on eligible cells')
        p = np.where(ok, p, 1.0); score = score * p; d_eff = d * p
    catchment = seat_people / settle.SEAT_REF_DENSITY * (settle.SEAT_REF_DENSITY / np.maximum(d_eff, 1e-9)) ** settle.SEAT_BETA
    radius = np.minimum(np.sqrt(catchment / np.pi), settle.MAX_RADIUS_KM) / cell_km * settle.SPACING
    blocked = np.zeros(land.shape, bool); h, w = land.shape

    def block(y, x, rad):
        r = int(np.ceil(rad)); y0, y1, x0, x1 = max(0, y - r), min(h, y + r + 1), max(0, x - r), min(w, x + r + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        blocked[y0:y1, x0:x1] |= (yy - y) ** 2 + (xx - x) ** 2 <= rad * rad
    for y, x in marked:
        block(int(y), int(x), radius[int(y), int(x)])
    towns = []; cy, cx = np.nonzero(ok)
    for k in np.argsort(-score[ok]):
        y, x = int(cy[k]), int(cx[k])
        if blocked[y, x]:
            continue
        towns.append((y, x)); block(y, x, radius[y, x])
    return towns


def match_count(place, target, *, lo=2000.0, hi=2.0e6, steps=40):
    """Bisection on seat_people so the greedy tiling yields about ``target`` centres."""
    best = None
    for _ in range(steps):
        mid = float(np.sqrt(lo * hi)); towns = place(mid)
        if best is None or abs(len(towns) - target) < abs(len(best[1]) - target):
            best = (mid, towns)
        if len(towns) == target:
            break
        if len(towns) > target:
            lo = mid
        else:
            hi = mid
    return best
