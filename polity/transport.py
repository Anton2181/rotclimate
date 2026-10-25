"""Boats: sailing over open water and along the coasts, and river boats.

Sailing (Casson 1951, "Speed under sail of ancient ships", TAPA 82):
  speed      5 knots before a fair wind over open water (Casson: 4-6), x 0.7
             within 20 km of land (3-4 knots coasting and among islands),
             round the clock
  polar      the share of that speed by the angle between the course and the
             way the wind blows: 1 with the wind anywhere abaft the beam, 0.85
             at 100 degrees from downwind (a square rig points 80 degrees off
             the wind), beyond that the progress of tacking, 0.85 cos(angle -
             100); at dead upwind ~0.15, i.e. under one knot in a steady
             headwind (Casson: under 2 to 2.5 knots against the wind)
  variable   winds that swing (steadiness s = |mean wind| / mean speed) mix
             the polar with its average over all courses
  strength   x min(1, speed / 6 m/s), at least 0.25 (light airs)
  season     x 0.5 when the sea is uncertain and x 0.15 when it is closed
             (polity/control.py: storminess thresholds fitted to Vegetius)
A traveller boards at a port (a town on the shore, 0.5 day) and can land
anywhere on a coast (0.25 day).

River boats (the map's navigable rivers): downstream and upstream speeds of
ORBIS's civilian river transport, boarding at a town on the river (0.25 day)
and landing anywhere on the banks (0.25 day). Low water (a basin's monthly
runoff under 0.4 of its mean) closes upstream travel and halves the speed
downstream.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

KNOT_KM_H = 1.852
SAIL_FAIR_KNOTS = 5.0
COAST_KM = 20.0
COAST_FACTOR = 0.7
CLOSE_HAULED = 100.0           # degrees from downwind
CLOSE_HAULED_SHARE = 0.85
FULL_WIND = 6.0                # m/s
LIGHT_AIRS = 0.25
BOARD_DAYS = 0.5
LAND_DAYS = 0.25
RIVER_BOARD_DAYS = 0.25
RIVER_DOWN_KM_DAY = 70.0       # a ~1 m/s current and oars (~3.5 km/h) for 10 hours (ORBIS' file lacks it)
RIVER_UP_KM_DAY = 17.9         # ORBIS civilian river edges off the Nile, towed upstream (median of 41)
UNCERTAIN_FACTOR = 0.5
CLOSED_FACTOR = 0.15
NEIGHBOURS = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]


def polar(theta_deg):
    """Share of the fair-wind speed made good along a course theta degrees
    from downwind."""
    t = np.abs(np.asarray(theta_deg, float))
    reach = np.where(t <= 90.0, 1.0, 1.0 - (1.0 - CLOSE_HAULED_SHARE) * (t - 90.0) / (CLOSE_HAULED - 90.0))
    tack = CLOSE_HAULED_SHARE * np.cos(np.radians(t - CLOSE_HAULED))
    return np.where(t <= CLOSE_HAULED, reach, tack)


POLAR_MEAN = float(polar(np.linspace(0.0, 180.0, 1801)).mean())


def sail_km_day(cos_theta, steadiness, wind, coastal, season=1.0):
    theta = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))
    s = np.clip(steadiness, 0.0, 1.0)
    h = s * polar(theta) + (1.0 - s) * POLAR_MEAN
    g = np.clip(np.asarray(wind, float) / FULL_WIND, LIGHT_AIRS, 1.0)
    return SAIL_FAIR_KNOTS * KNOT_KM_H * 24.0 * h * g * np.where(coastal, COAST_FACTOR, 1.0) * season


def sea_edges(water, u, v, wind, steadiness, season, cell_km, coast_km=None):
    """Directed sailing edges between water cells for one month. u, v: the
    mean wind (east, north components, m/s) per cell; wind: mean scalar speed;
    season: the closure factor per cell (1, 0.5, 0.15). Grid rows run
    southward (north = -row). Returns (src, dst, days) flat-index arrays."""
    water = np.asarray(water, bool); h, w = water.shape
    if coast_km is None:
        coast_km = ndi.distance_transform_edt(water) * cell_km
    coastal = coast_km <= COAST_KM
    speed = np.hypot(u, v)
    ex = np.where(speed > 1e-6, u / np.maximum(speed, 1e-6), 0.0)
    ny = np.where(speed > 1e-6, v / np.maximum(speed, 1e-6), 0.0)
    nodes = np.arange(h * w).reshape(h, w)
    rows, cols, cost = [], [], []
    for dy, dx in NEIGHBOURS:
        y0, y1 = max(0, -dy), min(h, h - dy); x0, x1 = max(0, -dx), min(w, w - dx)
        src = np.s_[y0:y1, x0:x1]; dst = np.s_[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        ok = water[src] & water[dst]
        if dy and dx:
            ok &= water[y0:y1, x0 + dx:x1 + dx] & water[y0 + dy:y1 + dy, x0:x1]
        norm = np.hypot(dy, dx)
        cos_t = (dx * 0.5 * (ex[src] + ex[dst]) - dy * 0.5 * (ny[src] + ny[dst])) / norm
        # wind direction and its steadiness at the step's midpoint
        km_day = sail_km_day(cos_t, 0.5 * (steadiness[src] + steadiness[dst]), 0.5 * (wind[src] + wind[dst]),
                             coastal[src] & coastal[dst], np.minimum(season[src], season[dst]))
        days = cell_km * norm / np.maximum(km_day, 1e-6)
        rows.append(nodes[src][ok]); cols.append(nodes[dst][ok]); cost.append(days[ok])
    return np.concatenate(rows), np.concatenate(cols), np.concatenate(cost)


def harbour_edges(land, water, ports, cell_km, reach=2):
    """Boarding at ports (to every water cell within `reach` cells, BOARD_DAYS
    plus the walk) and landing on any coast (water to each land neighbour,
    LAND_DAYS)."""
    land = np.asarray(land, bool); water = np.asarray(water, bool); h, w = land.shape
    rows, cols, cost = [], [], []
    for (py, px) in ports:
        y0, y1, x0, x1 = max(0, py - reach), min(h, py + reach + 1), max(0, px - reach), min(w, px + reach + 1)
        yy, xx = np.nonzero(water[y0:y1, x0:x1])
        for y, x in zip(yy + y0, xx + x0):
            rows.append(py * w + px); cols.append(y * w + x)
            cost.append(BOARD_DAYS + np.hypot(y - py, x - px) * cell_km / 30.0)
    for dy, dx in NEIGHBOURS:
        y0, y1 = max(0, -dy), min(h, h - dy); x0, x1 = max(0, -dx), min(w, w - dx)
        src = np.s_[y0:y1, x0:x1]; dst = np.s_[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        ok = water[src] & land[dst]
        n = np.arange(h * w).reshape(h, w)
        rows.extend(n[src][ok].tolist()); cols.extend(n[dst][ok].tolist()); cost.extend([LAND_DAYS] * int(ok.sum()))
    return np.asarray(rows, np.int64), np.asarray(cols, np.int64), np.asarray(cost, float)


def ports_of(places, water, reach=2):
    """Settlements (row, col) within `reach` cells of water."""
    near = ndi.binary_dilation(np.asarray(water, bool), iterations=reach)
    return [(int(y), int(x)) for y, x in places if near[int(y), int(x)]]


def river_network(river, land, water, elev):
    """Basins and flow direction of the navigable river cells. Returns basin
    id per cell (0 = no river), the number of basins and the steps to the
    mouth along the river (downstream = fewer steps). A basin's mouth is its
    cells touching open water, else its lowest cell."""
    river = np.asarray(river, bool) & np.asarray(land, bool)
    basin, n = ndi.label(river, structure=np.ones((3, 3)))
    near_water = ndi.binary_dilation(np.asarray(water, bool), structure=np.ones((3, 3)))
    steps = np.full(river.shape, -1, np.int64)
    from collections import deque
    queue = deque()
    for b, sl in enumerate(ndi.find_objects(basin), 1):
        cells = basin[sl] == b
        mouth = cells & near_water[sl]
        if not mouth.any():
            e = np.where(cells, elev[sl], np.inf)
            mouth = e == e.min()
        for y, x in zip(*np.nonzero(mouth)):
            y, x = y + sl[0].start, x + sl[1].start
            steps[y, x] = 0; queue.append((y, x))
    h, w = river.shape
    while queue:
        y, x = queue.popleft()
        for dy, dx in NEIGHBOURS:
            q, c = y + dy, x + dx
            if 0 <= q < h and 0 <= c < w and river[q, c] and steps[q, c] < 0:
                steps[q, c] = steps[y, x] + 1; queue.append((q, c))
    return basin, n, steps


def catchments(basin, land, cell_km, max_km=150.0):
    """Each land cell's basin: that of its nearest river cell within max_km."""
    dist, (iy, ix) = ndi.distance_transform_edt(basin == 0, return_indices=True)
    c = basin[iy, ix]
    return np.where(np.asarray(land, bool) & (dist * cell_km <= max_km), c, 0)


def river_edges(basin, steps, flow, cell_km, offset, down_km_day=None, up_km_day=None):
    """Directed edges between river-boat nodes (node = offset + index of the
    river cell in `cells`). flow: [n_basins + 1] this month's flow index."""
    down = RIVER_DOWN_KM_DAY if down_km_day is None else down_km_day
    up = RIVER_UP_KM_DAY if up_km_day is None else up_km_day
    h, w = basin.shape
    cells = np.flatnonzero(basin.ravel() > 0)
    boat = np.full(h * w, -1, np.int64); boat[cells] = offset + np.arange(len(cells))
    b = basin.ravel(); s = steps.ravel()
    rows, cols, cost = [], [], []
    for dy, dx in NEIGHBOURS:
        y, x = np.divmod(cells, w)
        q, c = y + dy, x + dx
        ok = (q >= 0) & (q < h) & (c >= 0) & (c < w)
        src, dst = cells[ok], q[ok] * w + c[ok]
        ok2 = b[dst] == b[src]
        src, dst = src[ok2], dst[ok2]
        km = cell_km * np.hypot(dy, dx)
        q_index = flow[b[src]]
        low = q_index < 0.4
        downstream = s[dst] < s[src]
        upstream = s[dst] > s[src]
        speed = np.where(downstream, down * np.where(low, 0.5, 1.0), up)
        keep = downstream | (upstream & ~low)
        rows.append(boat[src][keep]); cols.append(boat[dst][keep]); cost.append((km / speed)[keep])
    return np.concatenate(rows), np.concatenate(cols), np.concatenate(cost), cells


def river_harbour_edges(cells, offset, places, shape, reach=1):
    """Boarding a river boat at a settlement on (or beside) the river, and
    landing from any river cell onto its own bank."""
    h, w = shape
    boat = {int(c): offset + i for i, c in enumerate(cells)}
    rows, cols, cost = [], [], []
    for y, x in places:
        for dy in range(-reach, reach + 1):
            for dx in range(-reach, reach + 1):
                q, c = int(y) + dy, int(x) + dx
                if 0 <= q < h and 0 <= c < w and q * w + c in boat:
                    rows.append(int(y) * w + int(x)); cols.append(boat[q * w + c]); cost.append(RIVER_BOARD_DAYS)
    rows += list(boat.values()); cols += list(boat.keys()); cost += [LAND_DAYS] * len(boat)
    return np.asarray(rows, np.int64), np.asarray(cols, np.int64), np.asarray(cost, float)
