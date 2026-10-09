"""Real-world climate analogues ("this place feels like Tbilisi").

Both the simulated place and every reference city are reduced to 12 bins of
equal length that start at the *winter solstice*.  That puts northern and
southern hemisphere cities (and the world's own 10-month calendar) on one
seasonal clock.  Similarity combines

* the RMS difference of the 12 monthly mean temperatures (°C), and
* the RMS difference of sqrt(monthly precipitation), so 10 vs 40 mm counts
  about as much as 100 vs 160 mm.

    d = RMS(dT) / 2.5 C  +  RMS(d sqrt P) / 2.0        similarity = 100 exp(-d / 2)

so a place 2.5 C off in a typical month, or with rain off by 2 sqrt-mm
(e.g. 100 vs 144 mm), loses a factor e^-0.5 = 0.61 each.

The reference set is data/real_cities_worldclim.csv: every city of 50,000+
people and every national capital (GeoNames), with WorldClim 2.1 normals
corrected to the city's elevation (built by scripts/build_reference.py).
Official WMO station normals (data/real_cities_wmo.csv, from
scripts/fetch_wmo_normals.py) add the remote places no city covers: stations
more than 50 km from any listed city. Result lists skip a place within
100 km of a better match, so near-copies don't crowd them.
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


def _read_csv(path):
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def reference_source() -> str:
    ref = load_reference()
    n_city = sum(r["source"] == "worldclim" for r in ref)
    n_wmo = sum(r["source"] == "wmo" for r in ref)
    parts = []
    if n_city:
        parts.append(f"{n_city:,} cities with WorldClim 1970–2000 normals")
    if n_wmo:
        parts.append(f"{n_wmo:,} {'remote ' if n_city else ''}WMO weather stations")
    return " + ".join(parts) or "no reference data"


def _km(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(np.radians, (lat1, lon1, lat2, lon2))
    c = np.sin(la1) * np.sin(la2) + np.cos(la1) * np.cos(la2) * np.cos(lo1 - lo2)
    return 6371.0 * np.arccos(np.clip(c, -1.0, 1.0))


@lru_cache(maxsize=1)
def load_reference():
    """Cities with WorldClim normals, plus WMO stations far from any of them."""
    raw = []
    city = DATA / "real_cities_worldclim.csv"
    if city.exists():
        raw += [(r, "worldclim") for r in _read_csv(city)]
    wmo = DATA / "real_cities_wmo.csv"
    if wmo.exists():
        stations = _read_csv(wmo)
        if raw:
            clat = np.array([float(r["lat"]) for r, _ in raw])
            clon = np.array([float(r["lon"]) for r, _ in raw])
            stations = [w for w in stations
                        if _km(float(w["lat"]), float(w["lon"]), clat, clon).min() > 50.0]
        taken = {(r["name"], _short_country(r["country"])) for r, _ in raw}
        raw += [(w, "wmo") for w in stations if (w["name"], _short_country(w["country"])) not in taken]
    rows = []
    for r, src in raw:
        T = np.array([float(r[f"T{i}"]) for i in range(1, 13)])
        P = np.array([float(r[f"P{i}"]) for i in range(1, 13)])
        lat = float(r["lat"])
        T12, P12 = _align_calendar_months(T, P, lat)
        rows.append(dict(name=r["name"], country=_short_country(r["country"]), lat=lat,
                         lon=float(r["lon"]), source=src, period=r.get("period", ""),
                         population=int(r.get("population") or 0),
                         T=T, P=P, T12=T12, P12=P12))
    _attach_koppen(rows)
    return rows


_COUNTRY_SHORT = {
    "United States of America": "USA", "Russian Federation": "Russia",
    "Iran (Islamic Republic of)": "Iran", "United Kingdom of Great Britain and Northern Ireland": "UK",
    "Hong Kong, China": "Hong Kong", "Macao, China": "Macao", "Republic of Korea": "South Korea",
    "Democratic People's Republic of Korea": "North Korea", "Syrian Arab Republic": "Syria",
    "Viet Nam": "Vietnam", "Lao People's Democratic Republic": "Laos", "Türkiye": "Turkey",
    "Republic of Moldova": "Moldova", "United Republic of Tanzania": "Tanzania",
    "Bolivia (Plurinational State of)": "Bolivia", "Venezuela (Bolivarian Republic of)": "Venezuela",
    "Democratic Republic of the Congo": "DR Congo", "Brunei Darussalam": "Brunei",
}


def _short_country(c):
    return _COUNTRY_SHORT.get(c, c)


def _attach_koppen(rows):
    Tm = np.stack([r["T"] for r in rows], axis=1)
    Pm = np.stack([r["P"] for r in rows], axis=1)
    nh = np.array([r["lat"] >= 0 for r in rows])
    kk = np.zeros(len(rows), int)
    for hemi in (True, False):
        sel = nh == hemi
        if sel.any():
            summer = np.array([m in (3, 4, 5, 6, 7, 8) for m in range(12)])
            if not hemi:
                summer = ~summer
            kk[sel] = classify(Tm[:, sel], Pm[:, sel], summer)
    for r, c in zip(rows, kk):
        r["koppen"] = CODES[c] if c >= 0 else "?"


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


def diverse(order, lat, lon, k, min_km=100.0):
    """First k indices of `order` that are at least min_km from every earlier pick."""
    picks = []
    for i in order:
        if all(_km(lat[i], lon[i], lat[j], lon[j]) >= min_km for j in picks):
            picks.append(int(i))
            if len(picks) == k:
                break
    return picks


def top_analogs(T12, P12, k=4, min_km=100.0):
    """Best k reference places for one place (T12, P12 arrays of length 12),
    skipping any within min_km of a better match."""
    ref = load_reference()
    RT = np.stack([r["T12"] for r in ref], axis=1)      # [12, n]
    RP = np.stack([r["P12"] for r in ref], axis=1)
    d, dT, dP = distance(T12[:, None], P12[:, None], RT, RP)
    lat = np.array([r["lat"] for r in ref])
    lon = np.array([r["lon"] for r in ref])
    idx = diverse(np.argsort(d)[: 50 * k], lat, lon, k, min_km)
    rain = np.sqrt(np.mean((P12[:, None] - RP) ** 2, axis=0))
    return [dict(name=ref[i]["name"], country=ref[i]["country"], koppen=ref[i]["koppen"],
                 source=ref[i]["source"],
                 score=float(d[i]), dT=float(dT[i]), dP=float(dP[i]), rain_mm=float(rain[i]),
                 similarity=float(100 * np.exp(-d[i] / 2.0))) for i in idx]


def reference_payload():
    """Compact reference table for the atlas page."""
    # T in tenths of a degree, P in mm, lat/lon to 0.1 degree (for spacing out results)
    return [dict(n=r["name"], c=r["country"], k=r["koppen"], s=int(r["source"] == "wmo"),
                 y=round(r["lat"], 1), x=round(r["lon"], 1), p=int(round(r["population"] / 1000)),
                 T=[int(round(10 * float(v))) for v in r["T12"]],
                 P=[int(round(float(v))) for v in r["P12"]]) for r in load_reference()]
