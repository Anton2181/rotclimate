"""Where the water goes: runoff, drainage, river discharge and floodplains.

* runoff = precipitation - evaporation (evaporation capped by both the rain
  and a temperature-based potential evaporation)
* drainage = priority-flood over the terrain (Barnes et al. 2014): every land
  cell drains to the sea along a path that never climbs, depressions fill
* discharge = runoff accumulated down that tree (m3/s)
* floodplains = low land within ~12 km of a big river: rivers crossing low
  flat land make wetlands even where local rain is modest - the way the
  Tigris-Euphrates marshes or the Sudd are fed.
"""
from __future__ import annotations

import heapq

import numpy as np

try:
    import numba

    @numba.njit(cache=True)
    def _accumulate(order, recv, src):
        acc = src.copy()
        for k in range(order.size - 1, -1, -1):
            c = order[k]
            r = recv[c]
            if r >= 0:
                acc[r] += acc[c]
        return acc
except ImportError:  # pragma: no cover
    def _accumulate(order, recv, src):
        acc = src.copy()
        for c in order[::-1]:
            if recv[c] >= 0:
                acc[recv[c]] += acc[c]
        return acc

FLOODPLAIN_KM2 = 400.0
_NBRS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
_CACHE: dict = {}


def drainage(elev: np.ndarray, land: np.ndarray):
    """Receiver of every cell (-1 = outlet) and an outlet-first visiting order."""
    key = (id(elev), elev.shape, int(land.sum()))
    if key in _CACHE:
        return _CACHE[key]
    ny, nx = elev.shape
    e = elev.ravel()
    lnd = land.ravel()
    recv = np.full(ny * nx, -1, np.int64)
    seen = ~lnd.copy()
    heap = []
    # outlets: sea / lake cells touching land
    for c in np.flatnonzero(~lnd):
        i, j = divmod(int(c), nx)
        for di, dj in _NBRS:
            ii, jj = i + di, j + dj
            if 0 <= ii < ny and 0 <= jj < nx and lnd[ii * nx + jj]:
                heap.append((0.0, int(c)))
                break
    heapq.heapify(heap)
    order = []
    while heap:
        h, c = heapq.heappop(heap)
        order.append(c)
        i, j = divmod(c, nx)
        for di, dj in _NBRS:
            ii, jj = i + di, j + dj
            if 0 <= ii < ny and 0 <= jj < nx:
                n = ii * nx + jj
                if not seen[n]:
                    seen[n] = True
                    recv[n] = c
                    heapq.heappush(heap, (max(float(e[n]), h + 1e-3), n))
    out = (recv, np.array(order, np.int64))
    if len(_CACHE) > 16:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def annual_runoff(result) -> np.ndarray:
    """Runoff [mm/yr] on the model grid (0 over water)."""
    T, P = result.T, result.P
    pet = np.clip(0.0023 * 17.8 * (T + 17.8) * 1.9, 0.1, None)        # mm/day, Hargreaves-like
    ro = (P - np.minimum(P, 0.75 * pet)).sum(0) * result.params.year_days / result.nt
    return np.where(result.grid.land, ro, 0.0)


def analyse(result) -> dict:
    g = result.grid
    ro = annual_runoff(result)
    recv, order = drainage(g.elev, g.land)
    acc = _accumulate(order, recv, ro.ravel().astype(np.float64)).reshape(ro.shape)  # mm/yr x cells
    cell_km2 = g.cell_km ** 2
    q = acc / 1000.0 * cell_km2 * 1e6 / (365.0 * 86400.0)                          # m3/s
    inflow = np.maximum(acc - ro, 0.0)
    flood_mm = inflow * cell_km2 / FLOODPLAIN_KM2                                   # mm/yr over a floodplain
    return dict(runoff=ro, discharge=q, flood_mm=flood_mm, recv=recv)


def floodplain(hyd: dict, elev: np.ndarray, cell_km: float, q0: float = 20.0) -> np.ndarray:
    """0..1: low land within ~12 km of a big river (discharge >~ 20 m3/s).

    Uses the discharge of the largest river within a fixed physical radius,
    so the field is the same at any grid size."""
    from scipy import ndimage as ndi

    size = 2 * int(12.0 / cell_km + 0.3) + 1          # 1 cell at 21-28 km, 3 at 7-14 km
    q_near = ndi.maximum_filter(hyd["discharge"], size=size) if size > 1 else hyd["discharge"]
    wet = 1 / (1 + np.exp(-(np.log10(q_near + 0.1) - np.log10(q0)) / 0.22))
    low = 1 / (1 + np.exp(-(400.0 - elev) / 110.0))
    return wet * low
