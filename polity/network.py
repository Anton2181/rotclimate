"""One month's travel network, the same for the map and for the Earth checks.

A world is a dict of grids (rows running south): elev, land, biome, swamp,
density (people / km2), cell_km, lat, tilt; monthly [12, ...] T, Tmax, Tmin,
P (mm), u, v (mean wind east / north, m/s), wind (mean speed), sigma (the
swing of the wind about its mean); river (navigable river cells), road,
ferry, tracks. See polity/control.py (walking, riding, ranks), polity/
transport.py (boats) and polity/seasons.py (the weather).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import control as C
from . import seasons as S
from . import transport as X

# fitted in scripts/polity_earth_check.py (calibration/polity_20261025): the
# storminess (m/s) at which the sea turns uncertain and closed, on the scale of
# SIGMA_TABLE: the thresholds that give the table's row at 37.5 N Vegetius'
# season (11 of 12 months; March comes out closed, not uncertain). On Earth the
# Mediterranean's own storminess gives 3.70 and 5.25 (also 11 of 12).
SEA_UNCERTAIN_SIGMA = 5.84
SEA_CLOSED_SIGMA = 7.74
# the swing of the surface wind about its monthly mean over the open ocean
# (NCEP/NCAR 1981-2010: sqrt(mean speed^2 - |mean vector|^2)), median by 5-degree
# latitude band (rows, 15-50 N) and month from the winter solstice (columns);
# the map's model winds are means, so this stands in for its storms
SIGMA_LAT = [17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5]
SIGMA_TABLE = [
    [2.59, 2.68, 2.54, 2.15, 2.09, 1.95, 1.89, 2.46, 3.12, 2.84, 2.69, 2.58],
    [4.29, 4.43, 3.94, 3.37, 2.93, 2.44, 2.08, 2.39, 3.09, 3.33, 3.60, 3.86],
    [6.12, 6.15, 5.97, 5.26, 4.62, 3.37, 2.69, 2.83, 3.82, 4.66, 5.30, 6.11],
    [7.48, 7.36, 7.55, 6.68, 5.98, 4.89, 4.08, 4.21, 5.12, 6.14, 6.99, 7.60],
    [8.03, 8.23, 8.27, 7.45, 6.77, 5.64, 4.71, 4.96, 6.05, 7.46, 8.15, 8.28],
    [8.58, 8.68, 8.79, 7.99, 7.33, 6.24, 5.38, 5.63, 6.94, 7.98, 8.59, 8.69],
    [9.30, 9.31, 9.29, 8.53, 7.83, 6.90, 5.85, 6.20, 7.55, 8.38, 9.00, 9.43],
]


def storminess(lat, month):
    table = np.asarray(SIGMA_TABLE)
    return np.interp(np.asarray(lat, float), SIGMA_LAT, table[:, month])


def statics(world):
    land = np.asarray(world["land"], bool)
    st = dict(land=land)
    st["water"] = ~land
    st["coast_km"] = ndi.distance_transform_edt(st["water"]) * world["cell_km"]
    st["eta"] = C.terrain_coefficient(world["biome"], world.get("swamp", np.zeros(land.shape, bool)), None)
    st["paths"] = C.path_factor(np.where(land, world["density"], 0.0))
    # rotclimate.biomes: temperate and tropical rainforest, boreal and temperate seasonal forest
    st["forest_or_swamp"] = np.isin(np.asarray(world["biome"]), [3, 4, 7, 9]) | world.get("swamp", False)
    river = np.asarray(world.get("river", np.zeros(land.shape, bool)), bool) & land
    st["basin"], st["n_basins"], st["steps"] = X.river_network(river, land, st["water"], world["elev"])
    st["catchment"] = X.catchments(st["basin"], land, world["cell_km"])
    st["river_cells"] = np.flatnonzero(st["basin"].ravel() > 0)
    return st


def climate(world, st):
    cl = S.fields(world["T"], world["Tmax"], world["Tmin"], world["P"], world["lat"], world.get("tilt", 23.44))
    cl["flow"] = S.basin_flow(cl["runoff"], st["catchment"], st["n_basins"])
    cl["steadiness"] = np.clip(np.hypot(world["u"], world["v"]) / np.maximum(world["wind"], 1e-6), 0, 1)
    cl["sea"] = np.stack([C.sea_season(world["sigma"][m], world["wind"][m], SEA_UNCERTAIN_SIGMA, SEA_CLOSED_SIGMA)
                          for m in range(12)])
    return cl


def cause(cl, st, m):
    """What slows travel most in month m: 0 nothing much, 1 snow, 2 mud,
    3 heat, 4 floods (cells near a river in flood)."""
    snow = 1.5 * cl["snow"][m]; mud = (S.MUD_COEFFICIENT - 1) * cl["mud"][m]; heat = cl["heat"][m] - 1
    flood = S.flood_index(cl["flow"][m][st["catchment"]]) * (st["catchment"] > 0) * 0.5
    stack = np.stack([np.full(snow.shape, 0.15), snow, mud, heat, flood])
    return np.argmax(stack, 0)


def month_network(world, st, cl, m, ports=(), river_places=(), boats=True, horse=False, sea=True):
    """The Network (polity.control) of month m. ports: (row, col) of the
    places where a traveller can take ship; river_places: where one can take a
    river boat. horse: riders instead of walkers (no boats, no roads)."""
    land, cell_km = st["land"], world["cell_km"]
    if horse:
        snow = 1.0 + (C.HORSE_SNOW_COEFFICIENT - 1.0) * cl["snow"][m]
        mud = 1.0 + (S.MUD_COEFFICIENT - 1.0) * cl["mud"][m]
        eta = st["eta"] * np.maximum(snow, mud) * cl["heat"][m]
        return C.Network(land.size, [C.horse_edges(world["elev"], land, eta, cell_km, st["forest_or_swamp"])])
    eta = S.month_terrain(st["eta"], cl, m)
    mud = cl["mud"][m]
    flood = S.flood_index(cl["flow"][m][st["basin"]])
    cross = np.where(st["basin"] > 0, S.CROSS_DAYS * (1.0 + S.FLOOD_GAIN * flood), 0.0)
    edges = [C.foot_edges(world["elev"], land, world["road"], eta, cell_km, st["paths"], world.get("ferry"),
                          world.get("tracks"), road_factor=1.0 + (S.MUD_ROAD - 1.0) * mud,
                          track_factor=1.0 + (S.MUD_COEFFICIENT - 1.0) * mud, cross=cross)]
    extra = 0
    if boats and sea:
        edges.append(X.sea_edges(st["water"], world["u"][m], world["v"][m], world["wind"][m], cl["steadiness"][m],
                                 cl["sea"][m], cell_km, st["coast_km"]))
        if len(ports):
            edges.append(X.harbour_edges(land, st["water"], list(ports), cell_km))
    if boats and len(st["river_cells"]):
        rr, rc, rd, cells = X.river_edges(st["basin"], st["steps"], cl["flow"][m], cell_km, land.size)
        edges.append((rr, rc, rd))
        edges.append(X.river_harbour_edges(cells, land.size, list(river_places), land.shape))
        extra = len(cells)
    return C.Network(land.size, edges, extra)
