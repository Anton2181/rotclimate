"""Earth mode: run the production model on real geography and score it
against observed climate.

The fantasy calibration infers unknowns (latitude, tilt, spin, surroundings)
together with physics constants. On Earth every geographic unknown is known,
so the same physics can be tested directly: build the model grid from
WorldClim 2.1 terrain for a region, run it with Earth's tilt, spin and
calendar, and compare its monthly temperature and rain with WorldClim's
1970-2000 normals on the same cells.

Grid: azimuthal equidistant projection about the region centre (distances
exact, local north within a few degrees of grid-up near the centre), square
cells of `cell_km`, the scored rectangle plus `pad_km` of real surroundings on
every side. Each cell averages the WorldClim 5-arc-minute pixels inside it,
weighted by pixel area; a cell is land where at least half of it is.

The scored region's "painted zones" are what the zone rules say for the
observed climate (with the Koppen label gate), so every fantasy score
(coverage, precision, F1, strict agreement) has an Earth counterpart.

    python -I scripts/earth_benchmark.py --region california --params <file>
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import DATA, Params
from .geography import Grid
from .koppen import CODES, classify, climate_indices, summer_months

R_EARTH_KM = 6371.0
WORLDCLIM = DATA / "cache" / "worldclim"
CACHE = DATA / "cache" / "earth"
WINTER = np.array([0, 1, 2, 9, 10, 11])          # Oct-Mar, as in the V10 Earth tests

# scored rectangles (km, in the local projection) chosen to match the V10
# Earth domains, plus the regions standing in for the other painted zones
REGIONS = {
    "california": dict(lat0=37.0, lon0=-118.8, width_km=900, height_km=1270,
                       note="Mediterranean coast, Central Valley, Sierra Nevada, Mojave/Sonoran desert"),
    "iberia": dict(lat0=37.1, lon0=-3.45, width_km=2400, height_km=1690,
                   note="Iberia, the western Mediterranean and north-west Africa"),
    # analogues of the other painted zones, at the map's latitudes
    "southeast_us": dict(lat0=31.0, lon0=-89.0, width_km=2000, height_km=1300,
                         note="Gulf coast swamps, Florida, humid subtropical south, Appalachians, Texas plains"),
    "levant": dict(lat0=36.0, lon0=36.5, width_km=1900, height_km=1300,
                   note="Aegean/Levant Mediterranean coasts, Anatolian steppe, Syrian desert, Zagros"),
    "central_asia": dict(lat0=42.0, lon0=66.0, width_km=2000, height_km=1300,
                         note="Turan steppe and deserts, Tian Shan / Pamir foothills"),
    "east_china": dict(lat0=29.0, lon0=113.0, width_km=1800, height_km=1300,
                       note="monsoon humid subtropics: Yangtze, south China hills, Sichuan basin"),
    # southern-hemisphere Mediterranean climates (held out; run mirrored, see region_case)
    "chile": dict(lat0=-34.0, lon0=-71.0, width_km=700, height_km=1500,
                  note="central Chile: Mediterranean coast, Andes, Atacama edge"),
    "cape": dict(lat0=-33.4, lon0=20.6, width_km=780, height_km=560,
                 note="Western Cape Mediterranean, Karoo, southern coast"),
    "sw_australia": dict(lat0=-32.0, lon0=118.5, width_km=1200, height_km=1000,
                         note="south-west Australia: Mediterranean coast to the interior deserts"),
}


# well-known places for climographs (lat, lon); the model cell containing each
STATIONS = {
    "california": {"San Francisco": (37.77, -122.42), "Sacramento": (38.58, -121.49), "Fresno": (36.74, -119.79),
                   "Los Angeles": (34.05, -118.24), "San Diego": (32.72, -117.16), "Reno": (39.53, -119.81),
                   "Las Vegas": (36.17, -115.14)},
    "iberia": {"Lisbon": (38.72, -9.14), "Porto": (41.15, -8.61), "Madrid": (40.42, -3.70), "Seville": (37.39, -5.98),
               "Valencia": (39.47, -0.38), "Barcelona": (41.39, 2.17), "Algiers": (36.75, 3.06),
               "Marrakech": (31.63, -7.99)},
    "southeast_us": {"Houston": (29.76, -95.37), "New Orleans": (29.95, -90.07), "Memphis": (35.15, -90.05),
                     "Atlanta": (33.75, -84.39), "Tampa": (27.95, -82.46), "Miami": (25.76, -80.19)},
    "levant": {"Athens": (37.98, 23.73), "Istanbul": (41.01, 28.98), "Ankara": (39.93, 32.86), "Beirut": (33.89, 35.50),
               "Damascus": (33.51, 36.28), "Jerusalem": (31.77, 35.21)},
    "central_asia": {"Ashgabat": (37.95, 58.38), "Bukhara": (39.77, 64.42), "Samarkand": (39.65, 66.96),
                     "Tashkent": (41.30, 69.24), "Dushanbe": (38.56, 68.77), "Aralsk": (46.80, 61.67)},
    "east_china": {"Shanghai": (31.23, 121.47), "Nanjing": (32.06, 118.80), "Wuhan": (30.59, 114.31),
                   "Changsha": (28.23, 112.94), "Chongqing": (29.56, 106.55), "Guangzhou": (23.13, 113.26)},
    "chile": {"La Serena": (-29.90, -71.25), "Valparaiso": (-33.05, -71.62), "Santiago": (-33.45, -70.67),
              "Concepcion": (-36.83, -73.05)},
    "cape": {"Cape Town": (-33.92, 18.42), "Worcester": (-33.65, 19.45), "George": (-33.96, 22.46),
             "Beaufort West": (-32.35, 22.58)},
    "sw_australia": {"Geraldton": (-28.78, 114.61), "Perth": (-31.95, 115.86), "Albany": (-35.02, 117.88),
                     "Kalgoorlie": (-30.75, 121.47)},
}


@dataclass
class EarthCase:
    name: str
    grid: Grid
    lon: np.ndarray            # deg, per cell
    obs_T: np.ndarray          # [12, ny, nx] observed monthly mean temperature (C), NaN over sea
    obs_P: np.ndarray          # [12, ny, nx] observed monthly rain (mm), NaN over sea
    coast_km: np.ndarray       # distance from the sea (km)


# ---------------------------------------------------------------- projection
def forward(lat, lon, lat0, lon0):
    """(lat, lon) deg -> (x, y) km, azimuthal equidistant about (lat0, lon0)."""
    p, l = np.radians(lat), np.radians(lon - lon0)
    p0 = np.radians(lat0)
    cosc = np.clip(np.sin(p0) * np.sin(p) + np.cos(p0) * np.cos(p) * np.cos(l), -1, 1)
    c = np.arccos(cosc)
    k = np.where(c > 1e-12, c / np.maximum(np.sin(c), 1e-12), 1.0)
    x = R_EARTH_KM * k * np.cos(p) * np.sin(l)
    y = R_EARTH_KM * k * (np.cos(p0) * np.sin(p) - np.sin(p0) * np.cos(p) * np.cos(l))
    return x, y


def inverse(x, y, lat0, lon0):
    """(x, y) km -> (lat, lon) deg."""
    p0 = np.radians(lat0)
    rho = np.hypot(x, y)
    c = rho / R_EARTH_KM
    with np.errstate(invalid="ignore", divide="ignore"):
        lat = np.arcsin(np.clip(np.cos(c) * np.sin(p0) + np.where(rho > 0, y * np.sin(c) * np.cos(p0) / rho, 0),
                                -1, 1))
        lon = lon0 + np.degrees(np.arctan2(x * np.sin(c), rho * np.cos(p0) * np.cos(c) - y * np.sin(p0) * np.sin(c)))
    return np.degrees(lat), lon


# ---------------------------------------------------------------- WorldClim
def _wc(var, month=None):
    member = f"wc2.1_5m_{var}.tif" if month is None else f"wc2.1_5m_{var}_{month:02d}.tif"
    from PIL import Image

    im = Image.open(io.BytesIO(zipfile.ZipFile(WORLDCLIM / f"wc2.1_5m_{var}.zip").read(member)))
    a = np.array(im, dtype=np.float32)
    nd = im.tag_v2.get(42113)
    if nd is not None:
        a[a == np.float32(float(str(nd).strip("\x00 ")))] = np.nan
    a[a < -1e30] = np.nan
    return a


def region_case(name: str, cell_km: float = 28.0, pad_km: float = 1100.0) -> EarthCase:
    spec = REGIONS[name]
    lat0, lon0 = spec["lat0"], spec["lon0"]
    half_w, half_h = spec["width_km"] / 2 + pad_km, spec["height_km"] / 2 + pad_km
    nx = int(np.ceil(2 * half_w / cell_km))
    ny = int(np.ceil(2 * half_h / cell_km))
    key = f"{name}_{cell_km:g}km_{pad_km:g}pad.npz"
    CACHE.mkdir(parents=True, exist_ok=True)
    if (CACHE / key).exists():
        z = np.load(CACHE / key)
        fields = {k: z[k] for k in z.files}
    else:
        fields = _aggregate(lat0, lon0, nx, ny, cell_km, half_w, half_h)
        np.savez_compressed(CACHE / key, **fields)
    xs = -half_w + (np.arange(nx) + 0.5) * cell_km
    ys = half_h - (np.arange(ny) + 0.5) * cell_km
    X, Y = np.meshgrid(xs, ys)
    lat, lon = inverse(X, Y, lat0, lon0)
    if lat0 < 0:
        # The model is written for a northern-hemisphere map. The mirror image
        # (north <-> south) of a southern region is the same physics in the
        # north: the Coriolis turning and the reflection both flip handedness,
        # winds still blow west to east in the westerlies. Seasons move by half
        # a year: observed July is the mirrored January.
        fields = {k: (np.roll(v[:, ::-1], 6, axis=0) if v.ndim == 3 else v[::-1]) for k, v in fields.items()}
        lat, lon, Y = -lat[::-1], lon[::-1], -Y[::-1]
    land = fields["land_frac"] >= 0.5
    inmap = (np.abs(X) <= spec["width_km"] / 2) & (np.abs(Y) <= spec["height_km"] / 2)
    pad = int(round(pad_km / cell_km))
    from scipy import ndimage as ndi

    coast = ndi.distance_transform_edt(land) * cell_km
    obs_T = np.where(land[None], fields["T"], np.nan)
    obs_P = np.where(land[None], fields["P"], np.nan)
    elev = np.where(land, np.nan_to_num(fields["elev"], nan=0.0), 0.0)
    elev_max = np.where(land, np.nan_to_num(fields["elev_max"], nan=0.0), 0.0)
    g = Grid(params=None, f=1, pad=pad, ny=ny, nx=nx, cell_km=cell_km, land=land,
             land_frac=fields["land_frac"], elev=np.maximum(elev, np.where(land, 1.0, 0.0)),
             elev_max=np.maximum(elev_max, elev), lat=lat, inmap=inmap,
             target=np.zeros((ny, nx), np.int8), rivers=np.zeros((ny, nx)), lake=np.zeros((ny, nx), bool))
    g.target = observed_zones(obs_T, obs_P, g)
    return EarthCase(name=name, grid=g, lon=lon, obs_T=obs_T, obs_P=obs_P, coast_km=coast)


def _aggregate(lat0, lon0, nx, ny, cell_km, half_w, half_h):
    """Area-weighted means of WorldClim pixels in each projected cell."""
    elev = _wc("elev")
    H, W = elev.shape
    plat = 90 - (np.arange(H) + 0.5) / 12
    plon = -180 + (np.arange(W) + 0.5) / 12
    # a lat/lon window safely containing the projected rectangle
    span = np.degrees(np.hypot(half_w, half_h) / R_EARTH_KM) + 1
    rows = np.flatnonzero(np.abs(plat - lat0) <= span)
    dlon = span / max(np.cos(np.radians(min(abs(lat0) + span, 89))), 0.05)
    cols = np.flatnonzero(np.abs(((plon - lon0 + 180) % 360) - 180) <= dlon)
    LAT, LON = np.meshgrid(plat[rows], plon[cols], indexing="ij")
    x, y = forward(LAT, LON, lat0, lon0)
    i = np.floor((half_h - y) / cell_km).astype(int)
    j = np.floor((x + half_w) / cell_km).astype(int)
    ok = (i >= 0) & (i < ny) & (j >= 0) & (j < nx)
    flat = np.where(ok, i * nx + j, -1).ravel()
    w = np.cos(np.radians(LAT)).ravel()
    sub = (rows[:, None], cols[None, :])
    e = elev[sub].ravel()
    isl = np.isfinite(e)
    n = ny * nx
    sel = flat >= 0

    def binsum(vals, mask):
        m = sel & mask
        return np.bincount(flat[m], weights=vals[m], minlength=n)

    wall = binsum(w, np.ones_like(isl))
    wland = binsum(w, isl)
    out = dict(land_frac=(wland / np.maximum(wall, 1e-12)).reshape(ny, nx))
    with np.errstate(invalid="ignore", divide="ignore"):
        out["elev"] = (binsum(w * np.nan_to_num(e), isl) / wland).reshape(ny, nx)
        emax = np.full(n, -np.inf)
        np.maximum.at(emax, flat[sel & isl], e[sel & isl])
        out["elev_max"] = np.where(np.isfinite(emax), emax, np.nan).reshape(ny, nx)
        T = np.full((12, ny, nx), np.nan, np.float32)
        P = np.full((12, ny, nx), np.nan, np.float32)
        for m in range(12):
            for var, arr in (("tavg", T), ("prec", P)):
                v = _wc(var, m + 1)[sub].ravel()
                good = np.isfinite(v)
                arr[m] = (binsum(w * np.nan_to_num(v), good) / binsum(w, good)).reshape(ny, nx)
    out["T"], out["P"] = T, P
    return out


# ---------------------------------------------------------------- zones and params
def observed_zones(T, P, g) -> np.ndarray:
    """The painted-zone label the zone rules give the observed climate."""
    from .score import best_zone, memberships, terrain_slope

    summer = summer_months(365, 12, 172.0)
    land = g.land & np.isfinite(T).all(0)
    Tf, Pf = np.nan_to_num(T, nan=0.0), np.nan_to_num(P, nan=0.0)
    ix = climate_indices(Tf, Pf, summer)
    mem = memberships(ix, slope=terrain_slope(g))
    z = best_zone(mem, koppen=classify(Tf, Pf, summer))
    return np.where(land, z, 0).astype(np.int8)


def earth_params(base: Params, case: EarthCase) -> Params:
    """Earth's own geometry and calendar (day 0 = 1 January) with the
    physics constants of `base`."""
    lat0 = REGIONS[case.name]["lat0"]
    return base.replace(tilt=23.44, retrograde=False, north_bearing=0.0, eccentricity=0.0167,
                        # mirrored southern regions: perihelion falls in their (mirrored) summer
                        perihelion_after_solstice=13.0 if lat0 >= 0 else 13.0 + 365.25 / 2,
                        year_days=365, winter_solstice_day=354.5, lat_center=abs(lat0))


# ---------------------------------------------------------------- scoring
def compare(result, case: EarthCase) -> dict:
    """Skill against WorldClim on the scored land cells."""
    from .koppen import monthly_stats
    from .score import best_zone, memberships, objective, precision_f1, terrain_slope

    g = case.grid
    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    Ts, Ps, summer = st["Tm"], st["Pm"], st["summer"]
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0)
    To, Po = np.nan_to_num(case.obs_T), np.nan_to_num(case.obs_P)
    ks = classify(Ts, Ps, summer)
    ko = classify(To, Po, summer)
    kr = classify(To, Ps, summer)                   # observed temperature, simulated rain (V10's convention)
    names = np.array(CODES)

    def kstats(k):
        a, b = names[ko[m]], names[k[m]]
        med = np.char.startswith(a, "Cs")
        return dict(exact=float((a == b).mean()), main_group=float(np.mean([x[0] == y[0] for x, y in zip(a, b)])),
                    arid_share=float(np.char.startswith(b, "B").mean()),
                    cs_to_arid=float(np.char.startswith(b[med], "B").mean()) if med.any() else None,
                    cs_retained=float(np.char.startswith(b[med], "Cs").mean()) if med.any() else None)

    ann_s, ann_o = Ps.sum(0), Po.sum(0)
    coast = m & (case.coast_km < 150)
    ix = climate_indices(Ts, Ps, summer)
    mem = memberships(ix, slope=terrain_slope(g))
    cov = {}
    from .geography import TARGET_CLASSES
    for cid, key, _, _ in TARGET_CLASSES:
        sel = m & (g.target == cid)
        cov[key] = float(mem[key][sel].mean()) if sel.any() else float("nan")
    present = {k: v for k, v in cov.items() if np.isfinite(v)}
    prec, f1 = precision_f1(mem, g.target, m, cov, elev=g.elev)
    pred = best_zone(mem, koppen=ks)
    painted = m & (g.target > 0)
    recall = {key: float((pred[m & (g.target == cid)] == cid).mean())
              for cid, key, _, _ in TARGET_CLASSES if (m & (g.target == cid)).any()}
    f1p = {k: f1[k] for k in present}
    obj = objective(dict(f1=f1p, per_class=present,
                         realism=dict(map_median=float(np.median(ann_s[m])), map_p95=float(np.percentile(ann_s[m], 95)))),
                    "f1")
    return dict(
        region=case.name, scored_land_cells=int(m.sum()), cell_km=g.cell_km,
        climate_distance=climate_distance(result, case),
        temperature=dict(bias_C=float((Ts - To)[:, m].mean()), rmse_C=float(np.sqrt(((Ts - To)[:, m] ** 2).mean())),
                         monthly_bias_C=[float(x) for x in (Ts - To)[:, m].mean(1)],
                         coldest_bias_C=float((Ts.min(0) - To.min(0))[m].mean()),
                         warmest_bias_C=float((Ts.max(0) - To.max(0))[m].mean())),
        rain=dict(sim_mean_annual_mm=float(ann_s[m].mean()), obs_mean_annual_mm=float(ann_o[m].mean()),
                  sim_monthly_mm=[float(x) for x in Ps[:, m].mean(1)], obs_monthly_mm=[float(x) for x in Po[:, m].mean(1)],
                  monthly_mae_mm=float(np.abs(Ps - Po)[:, m].mean()),
                  annual_log_rmse=float(np.sqrt((np.log((ann_s[m] + 50) / (ann_o[m] + 50)) ** 2).mean())),
                  annual_rank_corr=_spearman(ann_s[m], ann_o[m]),
                  coast_winter_sim_mm=float(Ps[WINTER].sum(0)[coast].mean()) if coast.any() else None,
                  coast_winter_obs_mm=float(Po[WINTER].sum(0)[coast].mean()) if coast.any() else None,
                  winter_share_mae=float(np.abs(Ps[WINTER].sum(0) / np.maximum(ann_s, 1)
                                                - Po[WINTER].sum(0) / np.maximum(ann_o, 1))[m & (ann_o >= 50)].mean())),
        koppen_full_model=kstats(ks), koppen_observed_T_sim_rain=kstats(kr),
        zones=dict(objective_f1=obj, strict_agreement=float((pred[painted] == g.target[painted]).mean()),
                   coverage=present, f1=f1p, recall=recall))


def station_cell(case: EarthCase, lat, lon):
    """(row, col) of the land cell holding (lat, lon), or the nearest land cell
    (a coastal city can fall in a cell that is mostly sea)."""
    spec = REGIONS[case.name]
    x, y = forward(lat, lon, spec["lat0"], spec["lon0"])
    g = case.grid
    if spec["lat0"] < 0:
        y = -y                                   # mirrored region
    half_w, half_h = g.nx * g.cell_km / 2, g.ny * g.cell_km / 2
    i, j = int((half_h - y) // g.cell_km), int((x + half_w) // g.cell_km)
    if not g.land[i, j]:
        ii, jj = np.nonzero(g.land)
        k = np.argmin((ii - i) ** 2 + (jj - j) ** 2)
        i, j = int(ii[k]), int(jj[k])
    return i, j


def station_table(result, case: EarthCase) -> dict:
    """Monthly simulated and observed temperature (C) and rain (mm) at the
    region's STATIONS, with both Koppen classes (calendar months; for a
    mirrored southern region month 0 is July)."""
    from .koppen import monthly_stats

    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    out = {}
    for name, (la, lo) in STATIONS.get(case.name, {}).items():
        i, j = station_cell(case, la, lo)
        Ts, Ps = st["Tm"][:, i, j], st["Pm"][:, i, j]
        To, Po = case.obs_T[:, i, j], case.obs_P[:, i, j]
        if not np.isfinite(To).all():
            continue
        k = lambda T, P: CODES[int(classify(T[:, None], P[:, None], st["summer"])[0])]
        out[name] = dict(cell=(i, j), elev_m=float(case.grid.elev[i, j]), sim_T=Ts.tolist(), obs_T=To.tolist(),
                         sim_P=Ps.tolist(), obs_P=Po.tolist(), sim_koppen=k(Ts, Ps), obs_koppen=k(To, Po))
    return out


def climate_distance(result, case: EarthCase) -> float:
    """Mean over scored land cells of the atlas's climate distance to the
    observed climate: RMS monthly temperature error / 2.5 C + RMS monthly
    sqrt-rain error / 2 (0 = identical; 1 ~ 2.5 C or 100 vs 144 mm off)."""
    from .koppen import monthly_stats

    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    g = case.grid
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0)
    dT = np.sqrt(((st["Tm"] - np.nan_to_num(case.obs_T)) ** 2)[:, m].mean(0))
    dP = np.sqrt(((np.sqrt(np.maximum(st["Pm"], 0)) - np.sqrt(np.nan_to_num(case.obs_P))) ** 2)[:, m].mean(0))
    return float((dT / 2.5 + dP / 2.0).mean())


def _spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def run_case(base: Params, case: EarthCase, steps=25):
    from .model import ClimateModel

    p = earth_params(base, case).replace(steps_per_year=steps)
    return ClimateModel(p, grid=case.grid).run()


def summary_line(r: dict) -> str:
    t, rn, k, kr, z = r["temperature"], r["rain"], r["koppen_full_model"], r["koppen_observed_T_sim_rain"], r["zones"]
    pct = lambda x: "  - " if x is None else f"{x:4.0%}"
    mm = lambda x: "  - " if x is None else f"{x:4.0f}"
    return (f"{r['region']:12s} d {r['climate_distance']:.2f} | T bias {t['bias_C']:+5.1f} C (rmse {t['rmse_C']:4.1f}) | "
            f"rain {rn['sim_mean_annual_mm']:5.0f}/{rn['obs_mean_annual_mm']:5.0f} mm, coast winter "
            f"{mm(rn['coast_winter_sim_mm'])}/{mm(rn['coast_winter_obs_mm'])} | Koppen exact {pct(k['exact'])} "
            f"(obs-T {pct(kr['exact'])}), Cs->arid {pct(k['cs_to_arid'])}, Cs kept {pct(k['cs_retained'])} "
            f"| zones {pct(z['strict_agreement'])}")


def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1))
