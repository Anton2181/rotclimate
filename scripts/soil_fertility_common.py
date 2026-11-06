"""Shared drivers for the soil-fertility development fit and the Exhaustion Land
evaluation (calibration/soil_fertility_20261106/plan.json).

Evapotranspiration for RothC and drainage is Hargreaves scaled monthly to RothC's Rothamsted
open-pan table (calibration/soil_fertility_20261106/amendment_evaporation.json); A0 is unchanged.
Weather: Rothamsted's observed monthly record (harvest.earth_yields.load_weather,
1878 on). Before 1878, temperature and evapotranspiration are the 1878-1907
monthly means; rain is observed from 1853 (the same rain workbook), and the
1853-1882 monthly means before that. Invalid months (missing data) take the
monthly mean of the missing variable. A0 (the climate potential) is computed
only from valid observed weather; other years use the crop's 1878-1907 mean A0.
"""
from __future__ import annotations

import math
import sys
from calendar import monthrange
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import openpyxl  # noqa: E402

from harvest.earth_yields import load_weather  # noqa: E402
from harvest.soil_fertility import Params, Pools, Season, equilibrium, simulate  # noqa: E402
from harvest.soil_water_dual import dual_soil_water, kcb_curve  # noqa: E402

CACHE = ROOT / "data/cache/era_low_input_20261105"
AMEND = ROOT / "calibration/soil_fertility_20261106/amendment_evaporation.json"
LAT = 51.81
FYM_C_PER_T = 3.0 / 35.0                  # t C per t FYM (RothC Hoosfield: 35 t FYM = 3.0 t C)
FYM_N_PER_T = 225.0 / 35.0                # kg N per t FYM (plan); Woburn's files give their own N
PRIOR_PLANT = [(0.2125, 40.0)] * 7 + [(0.0, 40.0)] * 4 + [(0.2125, 40.0)]   # 1.70 t C/yr, Jan-Jul + Dec
SOILS = dict(rothamsted=dict(clay=23.4, FC=0.335, WP=0.205, REW=9.5, ZE=0.10, ZR=1.5, P=0.55),
             woburn=dict(clay=10.0, FC=0.23, WP=0.11, REW=8.0, ZE=0.10, ZR=1.5, P=0.55))


# amendment_evaporation.json: Hargreaves x (0.75 open pan / Hargreaves), RothC's Rothamsted table
import json as _json  # noqa: E402
PAN = {int(k): float(v) for k, v in _json.loads(AMEND.read_text())["factors"].items()}


def water_mm(site):
    s = SOILS[site]
    return 1000.0 * s["FC"] * s["ZR"]


def _rain_before_1878():
    wb = openpyxl.load_workbook(CACHE / "roth_rain_0.xlsx", read_only=True, data_only=True)
    out = {}
    for row in wb["DATA"].iter_rows(min_row=5, values_only=True):
        y = row[0]
        if isinstance(y, (int, float)) and 1853 <= y < 1878:
            for m in range(12):
                v = row[1 + m]
                if v is not None:
                    out[int(y), m + 1] = float(v)
    wb.close()
    return out


@lru_cache(maxsize=None)
def monthly(first_year=1843, last_year=1939):
    """Ordered monthly forcing (year, month, T, rain, et) and the observed weather dict."""
    obs = load_weather(CACHE, last_year, LAT)
    early_rain = _rain_before_1878()
    clim = {}
    for m in range(1, 13):
        rows = [obs[(y, m)] for y in range(1878, 1908) if obs[(y, m)]["valid"]]
        rain = [early_rain[(y, m)] for y in range(1853, 1878) if (y, m) in early_rain]
        rain += [obs[(y, m)]["P"] for y in range(1878, 1883) if math.isfinite(obs[(y, m)]["P"])]
        clim[m] = dict(T=float(np.mean([r["T"] for r in rows])), et=float(np.mean([r["PET"] for r in rows])),
                       rain=float(np.mean(rain)))
    out = []
    for y in range(first_year, last_year + 1):
        for m in range(1, 13):
            r = obs.get((y, m))
            if r is not None:
                T = r["T"] if math.isfinite(r["T"]) else clim[m]["T"]
                rain = r["P"] if math.isfinite(r["P"]) else clim[m]["rain"]
                et = r["PET"] if math.isfinite(r["PET"]) else clim[m]["et"]
            else:
                T, et = clim[m]["T"], clim[m]["et"]
                rain = early_rain.get((y, m), clim[m]["rain"])
            out.append(dict(year=y, month=m, T=float(T), rain=float(max(rain, 0.0)), et=float(max(et, 0.0)) * PAN[m]))
    clim = {m: dict(v, et=v["et"] * PAN[m]) for m, v in clim.items()}
    return tuple(tuple(sorted(d.items())) for d in out), obs, clim


def forcing_rows(first_year, last_year):
    rows, obs, clim = monthly()
    rs = [dict(r) for r in rows]
    return [r for r in rs if first_year <= r["year"] <= last_year], obs, clim


# --- crop calendars for the drainage ledger ---------------------------------------------

def kcb_series(days, calendar):
    """calendar: harvest_year -> crop kind. Winter wheat sown 15 Oct, harvested 15 Aug;
    spring barley/oats 25 Mar - 15 Aug; potatoes 20 Apr - 25 Sep (Kcb end 0.65); red clover
    perennial: 0.80 Mar-Oct, 0.30 Nov-Feb; fallow and cowpea years bare (declared)."""
    idx = {d: i for i, d in enumerate(days)}
    n = len(days)
    k = np.zeros(n)
    ar = np.arange(n)
    for y, kind in calendar.items():
        if kind == "wheat":
            s, h = date(y - 1, 10, 15), date(y, 8, 15)
            if s in idx and h in idx:
                k = np.maximum(k, kcb_curve(ar, idx[s], idx[h]))
        elif kind in ("barley", "oats"):
            s, h = date(y, 3, 25), date(y, 8, 15)
            if s in idx and h in idx:
                k = np.maximum(k, kcb_curve(ar, idx[s], idx[h]))
        elif kind == "potato":
            s, h = date(y, 4, 20), date(y, 9, 25)
            if s in idx and h in idx:
                k = np.maximum(k, kcb_curve(ar, idx[s], idx[h], kcb_end=0.65))
        elif kind == "clover":
            for i, d in enumerate(days):
                if d.year == y:
                    k[i] = max(k[i], 0.80 if 3 <= d.month <= 10 else 0.30)
    return k


def monthly_drainage(site, first_year, last_year, calendar, every=3):
    rows, _, _ = forcing_rows(first_year, last_year)
    days, rain, et0 = [], [], []
    for r in rows:
        n = monthrange(r["year"], r["month"])[1]
        ev = [d for d in range(n) if d % every == every // 2]
        for d in range(n):
            days.append(date(r["year"], r["month"], d + 1)); et0.append(r["et"] / n)
            rain.append(r["rain"] / len(ev) if d in ev else 0.0)
    kcb = kcb_series(days, calendar)
    s = SOILS[site]
    taw = 1000 * (s["FC"] - s["WP"]) * s["ZR"]
    led = dual_soil_water(np.array(rain), np.array(et0), kcb, total_available=taw, depletion_fraction=s["P"],
                          total_evaporable=1000 * (s["FC"] - 0.5 * s["WP"]) * s["ZE"], readily_evaporable=s["REW"],
                          initial_depletion=0.0)
    out = {}
    for d, v in zip(days, led.drainage):
        out[(d.year, d.month)] = out.get((d.year, d.month), 0.0) + float(v)
    return out, led.ledger_residual


# --- climate potential A0 ------------------------------------------------------------------

@lru_cache(maxsize=None)
def a0(year, crop):
    """Existing production capacity (t/ha) for wheat or barley rules; None without valid weather."""
    from woburn_yields import capacity
    _, obs, _ = monthly()
    return capacity(year, obs, "wheat" if crop == "wheat" else "barley")


@lru_cache(maxsize=None)
def a0_mean(crop):
    vals = [a0(y, crop) for y in range(1879, 1908)]
    vals = [v for v in vals if v is not None]
    return float(np.mean(vals))


def potential(year, crop):
    v = a0(year, crop)
    return (v if v is not None else a0_mean(crop)), v is not None


# --- spin-up ---------------------------------------------------------------------------------

@lru_cache(maxsize=None)
def spin_parts(site):
    """Equilibria (linear in inputs): prior plant input alone, and 1 t C/ha/yr of FYM in February alone."""
    _, _, clim = monthly()
    months = [dict(T=clim[m]["T"], rain=clim[m]["rain"], et=clim[m]["et"], vegetated=PRIOR_PLANT[m - 1][0] > 0)
              for m in range(1, 13)]
    clay = SOILS[site]["clay"]
    plant = equilibrium(months, clay, plant=PRIOR_PLANT)
    fym = [(0.0, 0.0)] * 12
    fym[1] = (1.0, 1000.0 * FYM_N_PER_T / (1000.0 * FYM_C_PER_T))      # 1 t C at the FYM C:N
    unit = equilibrium(months, clay, plant=[(0.0, 40.0)] * 12, fym=fym)
    return plant, unit


def start_pools(site, prior_manure):
    p, u = spin_parts(site)
    f = prior_manure
    return Pools(dpm=p.dpm + f * u.dpm, rpm=p.rpm + f * u.rpm, bio=p.bio + f * u.bio, hum=p.hum + f * u.hum,
                 dpm_n=p.dpm_n + f * u.dpm_n, rpm_n=p.rpm_n + f * u.rpm_n, tsmd=0.0)


# --- seasons -----------------------------------------------------------------------------------

def months_between(a, b):
    """Inclusive list of (year, month) from a to b."""
    out = []
    y, m = a
    while (y, m) <= b:
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def season(kind, year):
    """Season objects with the plan's uptake and vegetated months."""
    if kind == "wheat":
        return Season("cereal", (year, 8), frozenset(months_between((year, 3), (year, 7))),
                      frozenset(months_between((year - 1, 10), (year, 7))), potential(year, "wheat")[0], f"wheat {year}")
    if kind in ("barley", "oats"):
        return Season("cereal", (year, 8), frozenset(months_between((year, 4), (year, 7))),
                      frozenset(months_between((year, 4), (year, 7))), potential(year, "barley")[0], f"{kind} {year}")
    if kind == "potato":
        return Season("potato", (year, 9), frozenset(months_between((year, 4), (year, 9))),
                      frozenset(months_between((year, 5), (year, 9))), None, f"potato {year}")
    if kind == "clover":
        return Season("clover", (year, 12), frozenset(), frozenset(months_between((year, 1), (year, 12))), None, f"clover {year}")
    return Season("fallow", (year, 12), frozenset(), frozenset(), None, f"{kind} {year}")


def run(site, first_year, last_year, calendar, events, params, drainage=None):
    rows, _, _ = forcing_rows(first_year, last_year)
    if drainage is None:
        drainage, _ = monthly_drainage(site, first_year, last_year, calendar)
    for r in rows:
        r["drainage"] = drainage[(r["year"], r["month"])]
    seasons = [season(k, y) for y, k in sorted(calendar.items())]
    return simulate(rows, seasons, params, SOILS[site]["clay"], water_mm(site),
                    start=start_pools(site, params.prior_manure), events=events)
