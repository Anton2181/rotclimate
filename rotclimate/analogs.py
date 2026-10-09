"""Real-world climate analogues ("this place feels like Tbilisi").

Both the simulated place and every reference city are reduced to 12 bins of
equal length that start at the *winter solstice*.  That puts northern and
southern hemisphere cities (and the world's own 10-month calendar) on one
seasonal clock.  Similarity combines

* the RMS difference of the 12 monthly mean temperatures (°C), and
* the RMS difference of sqrt(monthly precipitation), so 10 vs 40 mm counts
  about as much as 100 vs 160 mm.

The reference set is data/real_cities_wmo.csv (official WMO normals, built by
scripts/fetch_wmo_normals.py when network access allows) if present,
otherwise data/real_cities_approx.csv (≈130 cities, approximate values).
"""
from __future__ import annotations

import csv
from functools import lru_cache

import numpy as np

from .config import DATA
from .koppen import CODES, classify

YEAR = 365.0
NH_SOLSTICE = 354.5      # Dec 21, 0-based day of year
SH_SOLSTICE = 171.5      # Jun 21


def reference_source() -> str:
    return "WMO normals" if (DATA / "real_cities_wmo.csv").exists() else "approximate built-in normals"


@lru_cache(maxsize=1)
def load_reference():
    path = DATA / "real_cities_wmo.csv"
    if not path.exists():
        path = DATA / "real_cities_approx.csv"
    rows = []
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    for r in csv.DictReader(lines):
        T = np.array([float(r[f"T{i}"]) for i in range(1, 13)])
        P = np.array([float(r[f"P{i}"]) for i in range(1, 13)])
        lat = float(r["lat"])
        T12, P12 = _align_calendar_months(T, P, lat)
        rows.append(dict(name=r["name"], country=r["country"], lat=lat, lon=float(r["lon"]),
                         elev=float(r.get("elev") or 0), T=T, P=P, T12=T12, P12=P12))
    # Koppen of each reference (on calendar months; classification is
    # insensitive to the phase shift because summer is chosen by solstice)
    Tm = np.stack([r["T"] for r in rows], axis=1)
    Pm = np.stack([r["P"] for r in rows], axis=1)
    nh = np.array([r["lat"] >= 0 for r in rows])
    codes = []
    for hemi in (True, False):
        sel = nh == hemi
        if sel.any():
            summer = np.array([m in (3, 4, 5, 6, 7, 8) for m in range(12)])
            if not hemi:
                summer = ~summer
            k = classify(Tm[:, sel], Pm[:, sel], summer)
            codes.append((sel, k))
    kk = np.zeros(len(rows), int)
    for sel, k in codes:
        kk[sel] = k
    for r, c in zip(rows, kk):
        r["koppen"] = CODES[c] if c >= 0 else "?"
    return rows


def _align_calendar_months(T, P, lat):
    """Gregorian monthly normals -> 12 bins starting at the winter solstice."""
    centers = (np.arange(12) + 0.5) * YEAR / 12          # month centres, day of year
    ws = NH_SOLSTICE if lat >= 0 else SH_SOLSTICE
    phase = (centers - ws) % YEAR                          # days since winter solstice
    order = np.argsort(phase)
    ph = np.concatenate([phase[order] - YEAR, phase[order], phase[order] + YEAR])
    Tt = np.tile(T[order], 3)
    Pt = np.tile(P[order], 3)
    bins = (np.arange(12) + 0.5) * YEAR / 12
    return np.interp(bins, ph, Tt), np.interp(bins, ph, Pt)


def model_bins(T_series, P_series, days, winter_solstice_day, year_days=365):
    """Model steps [nt, ...] (T in C, P in mm/day) -> 12 solstice-aligned bins.

    Returns T12 [12, ...] (mean) and P12 [12, ...] (mm per bin)."""
    nt = len(days)
    phase = (np.asarray(days) - winter_solstice_day) % year_days
    b = np.minimum((phase / (year_days / 12)).astype(int), 11)
    shp = T_series.shape[1:]
    T12 = np.zeros((12,) + shp)
    P12 = np.zeros((12,) + shp)
    for i in range(12):
        sel = b == i
        if not sel.any():           # very coarse time steps: borrow the nearest
            sel = np.array([np.argmin(np.abs(((phase - (i + 0.5) * year_days / 12)
                                               + year_days / 2) % year_days - year_days / 2))])
            sel = np.isin(np.arange(nt), sel)
        T12[i] = T_series[sel].mean(0)
        P12[i] = P_series[sel].mean(0) * year_days / 12
    return T12, P12


def distance(T12a, P12a, T12b, P12b, wT=2.5, wP=2.0):
    dT = np.sqrt(np.mean((T12a - T12b) ** 2, axis=0))
    dP = np.sqrt(np.mean((np.sqrt(np.maximum(P12a, 0)) - np.sqrt(np.maximum(P12b, 0))) ** 2, axis=0))
    return dT / wT + dP / wP, dT, dP


def top_analogs(T12, P12, k=4):
    """Best k reference cities for one place (T12, P12 arrays of length 12)."""
    ref = load_reference()
    RT = np.stack([r["T12"] for r in ref], axis=1)      # [12, n]
    RP = np.stack([r["P12"] for r in ref], axis=1)
    d, dT, dP = distance(T12[:, None], P12[:, None], RT, RP)
    idx = np.argsort(d)[:k]
    return [dict(name=ref[i]["name"], country=ref[i]["country"], koppen=ref[i]["koppen"],
                 score=float(d[i]), dT=float(dT[i]), dP=float(dP[i]),
                 similarity=float(100 * np.exp(-d[i] / 2.0))) for i in idx]


def reference_payload():
    """Compact reference table for the atlas page."""
    return [dict(n=r["name"], c=r["country"], k=r["koppen"],
                 T=[round(float(v), 1) for v in r["T12"]],
                 P=[round(float(v)) for v in r["P12"]]) for r in load_reference()]
