"""Month by month: what the weather does to travel.

Twelve months from the winter solstice (bin 0 is the solstice month, on
Earth roughly January). From monthly mean, maximum and minimum temperature
and precipitation (and latitude for the sunshine):

  snowpack   degree-day bucket: precipitation falls as snow below -1 C, as
             rain above +1 C (mixed between); melt 4 mm per C above 0 per
             day. Lasting snow when the pack holds over 10 mm (as the climate
             model's snow layer)
  soil       a 100 mm bucket filled by rain and melt, emptied by Hargreaves'
             PET (Hargreaves & Samani 1985) when not frozen; what overflows
             is runoff
  mud        the bucket nearly full (3/4 to full) and the ground not frozen
             (monthly mean above -2 C), or a month of snowmelt (rasputitsa)
  heat       marching shortened in the heat of the day: 1 + 0.4 x
             clip((Tmax - 33) / 7, 0, 1)
  floods     each river basin's monthly runoff against its mean: crossings
             off the roads take longer in the high-water months, and low water
             closes the upper rivers

Earth checks (snow months at Moscow, Kyiv, Beijing and Rome; mud at Kyiv;
the monsoon at Patna; Nile and Danube floods) are in
scripts/polity_earth_check.py. The coefficients are set from the literature
(calibration/polity_20261025/plan.json), not fitted.
"""
from __future__ import annotations

import numpy as np

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = 365.0 / 12
SNOW_LASTING_MM = 10.0
MELT_MM_C_DAY = 4.0
SOIL_MM = 100.0
FROZEN_C = -2.0
MUD_COEFFICIENT = 1.8          # Soule & Goldman (1972): swampy bog
MUD_ROAD = 1.1                 # the marked roads: built and drained
HEAT_GAIN = 0.4
CROSS_DAYS = 0.1               # a ford or a ferry over a navigable river, off the roads
FLOOD_GAIN = 4.0
LOW_WATER = 0.4


def extraterrestrial_mm(lat, month, tilt=23.44):
    """Daily top-of-atmosphere sunshine (mm of evaporation equivalent) in the
    middle of month bin `month` (0 = the month after the winter solstice)."""
    d = (month + 0.5) * DAYS
    decl = -np.radians(tilt) * np.cos(2 * np.pi * d / 365.0)
    phi = np.radians(np.asarray(lat, float))
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(decl), -1, 1))
    ra = 24 * 60 / np.pi * 0.0820 * (ws * np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.sin(ws))
    return 0.408 * np.maximum(ra, 0.0)


def hargreaves(T, Tmax, Tmin, lat, tilt=23.44):
    """Monthly PET (mm) for [12, ...] temperature fields."""
    pet = np.zeros_like(np.asarray(T, float))
    for m in range(12):
        pet[m] = 0.0023 * extraterrestrial_mm(lat, m, tilt) * (T[m] + 17.8) * np.sqrt(np.maximum(Tmax[m] - Tmin[m], 0))
    return np.maximum(pet, 0.0) * DAYS


def water_year(T, P, pet, spin=3):
    """Snowpack, melt, soil water and runoff for each month (mm), cycled
    `spin` years from a full bucket and no snow."""
    T = np.asarray(T, float); P = np.asarray(P, float)
    snow_frac = np.clip((1.0 - T) / 2.0, 0.0, 1.0)
    swe = np.zeros(T.shape[1:]); soil = np.full(T.shape[1:], SOIL_MM)
    out = {k: np.zeros(T.shape) for k in ("swe", "melt", "soil", "runoff")}
    for year in range(spin):
        for m in range(12):
            swe = swe + P[m] * snow_frac[m]
            melt = np.minimum(swe, MELT_MM_C_DAY * np.maximum(T[m], 0.0) * DAYS)
            swe = swe - melt
            frozen = T[m] < FROZEN_C
            water = soil + P[m] * (1 - snow_frac[m]) + melt - np.where(frozen, 0.0, pet[m])
            runoff = np.maximum(water - SOIL_MM, 0.0)
            soil = np.clip(water, 0.0, SOIL_MM)
            if year == spin - 1:
                out["swe"][m], out["melt"][m], out["soil"][m], out["runoff"][m] = swe, melt, soil, runoff
    return out


def fields(T, Tmax, Tmin, P, lat, tilt=23.44):
    """All monthly travel fields: lasting snow (0/1), mud (0-1), heat factor,
    runoff (mm), PET (mm), soil (mm), frozen (bool)."""
    T = np.asarray(T, float)
    pet = hargreaves(T, Tmax, Tmin, lat, tilt)
    w = water_year(T, P, pet)
    frozen = T < FROZEN_C
    mud = np.where(frozen, 0.0, np.clip((w["soil"] / SOIL_MM - 0.75) / 0.25, 0.0, 1.0))
    mud = np.maximum(mud, np.where(frozen, 0.0, np.clip(w["melt"] / 50.0, 0.0, 1.0)))
    heat = 1.0 + HEAT_GAIN * np.clip((np.asarray(Tmax, float) - 33.0) / 7.0, 0.0, 1.0)
    return dict(snow=(w["swe"] > SNOW_LASTING_MM).astype(float), mud=mud, heat=heat, runoff=w["runoff"],
                pet=pet, soil=w["soil"], swe=w["swe"], frozen=frozen)


def basin_flow(runoff, catchment, n_basins):
    """Monthly flow index of each basin: its catchment's mean runoff over the
    year's mean (1 = an average month). runoff [12, ...]; catchment: basin id
    per cell (0 = none). Returns [12, n_basins + 1] (row 0 unused, ones)."""
    q = np.ones((12, n_basins + 1))
    ids = catchment.ravel()
    ok = ids > 0
    for m in range(12):
        s = np.bincount(ids[ok], weights=runoff[m].ravel()[ok], minlength=n_basins + 1)
        n = np.bincount(ids[ok], minlength=n_basins + 1)
        q[m] = np.where(n > 0, s / np.maximum(n, 1), 0.0)
    mean = q.mean(0)
    return np.where(mean > 1e-6, q / np.maximum(mean, 1e-9), 1.0)


def flood_index(q):
    return np.clip((np.asarray(q) - 1.5) / 1.5, 0.0, 1.0)


def month_terrain(base_eta, f, m):
    """Soule-Goldman coefficient of open ground in month m: the biome and
    swamp coefficient, x 2.5 under lasting snow, x up to 1.8 in mud, x heat."""
    snow = 1.0 + 1.5 * f["snow"][m]
    mud = 1.0 + (MUD_COEFFICIENT - 1.0) * f["mud"][m]
    return base_eta * np.maximum(snow, mud) * f["heat"][m]
