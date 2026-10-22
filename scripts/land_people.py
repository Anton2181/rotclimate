"""Land and people: what the simulated climate would grow and how many it
could feed, using published empirical relationships only.

From the monthly temperature and rain of a fit (the satellite renderer's
climate cache):

* reference evaporation, Hargreaves & Samani (1985), from the temperature,
  the day/night range (rotclimate.diurnal, learned from WorldClim; on Earth
  WorldClim's own) and the sunlight above the air from the world's latitude
  and tilt (FAO-56); Thornthwaite (1948) only as a fallback, since from
  temperature alone it badly underestimates dry, sunny winters;
* a 100 mm soil-water bucket and the FAO length of growing period (months
  warm enough, >= 5 C, and wet enough, rain plus soil water >= half the
  potential evaporation);
* growing degree days above 5 C;
* net primary productivity, the Miami model (Lieth 1975);
* staple crops of a Han / Parthian world around 200 AD (wheat, barley,
  foxtail millet, paddy rice, date palm): a GAEZ-style check of each crop's
  temperature window, heat sum and season water balance (FAO-33 yield
  response, Doorenbos & Kassam 1979), with irrigation near the drawn rivers
  (navigable rivers fully, streams in part); low-input yields of the period;
  a second crop in the months the first leaves free, at half weight;
* calories per hectare (the best crop or pair, after seed), in the spirit of
  the Caloric Suitability Index (Galor & Ozak 2016);
* a farming population capacity: calories x arable share (by terrain) x
  share cropped in a year (fallow; calibrated on the Han census of AD 2,
  see scripts/land_people_earth.py) / a person's yearly need;
* malaria suitability, MARA (Craig, Snow & le Sueur 1999): months with
  22-32 C and >= 80 mm rain (fuzzy edges), the best run of 5 such months.

    python -I scripts/land_people.py --params calibration/earth/free_e5p_ds16.json \
        --cache output/satellite/climate_cache.npz --out output/land_people
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

MAP_KM = 3680.0
DAYS = 365.0 / 12.0

# Staple crops around 200 AD. Window: monthly mean temperature the crop
# grows in; base and heat: degree days above `base` the season needs;
# months: season length; kc, ky: FAO-33 crop coefficient and yield response;
# grain: low-input harvest t/ha of the period (Roman / Han / Mesopotamian
# estimates: wheat and barley 0.6-1.2, millet ~0.9, paddy 1.5-2.5); edible:
# share left after hulling or milling; kcal per kg of that (USDA); seed:
# share of the harvest sown again (wheat ~140 kg/ha, barley ~120, millet
# ~15, transplanted rice ~50).
CROPS = {
    "wheat": dict(window=(3.0, 24.0), base=0.0, heat=1500.0, months=(4, 9), kc=0.8, ky=1.05,
                  grain=1.0, edible=0.90, kcal=3300.0, seed=0.14, need_warm=12.0),
    "barley": dict(window=(2.0, 25.0), base=0.0, heat=1200.0, months=(3, 8), kc=0.75, ky=0.9,
                   grain=1.0, edible=0.87, kcal=3540.0, seed=0.12, need_warm=10.0),
    "millet": dict(window=(14.0, 33.0), base=10.0, heat=1100.0, months=(3, 5), kc=0.7, ky=0.8,
                   grain=0.9, edible=0.78, kcal=3780.0, seed=0.02, need_warm=18.0),
    "rice": dict(window=(19.0, 35.0), base=10.0, heat=1700.0, months=(4, 6), kc=1.15, ky=1.2,
                 grain=1.8, edible=0.68, kcal=3600.0, seed=0.03, need_warm=22.0, flood_mm=300.0),
}
# date palm: fruit t/ha of an irrigated grove, kcal/kg; it needs a dry
# climate (the fruit spoils in rain) and water from rivers or wells
DATES = dict(grain=3.0, kcal=2800.0, dry_mm=(300.0, 500.0))
NEED_KCAL = 1.1e6                          # a person's year: 2,100 kcal/day, storage losses, draft animals
FARMED_SHARE = 0.6                         # of arable land: fields (the rest pasture, wood, villages, roads)
# of the fields, sown in a given year: between a two-field fallow (0.5) and
# annual cropping (1), set so that the same rules on Earth's climate put the
# Han North China Plain's AD 2 census population (29.4 M on 365,000 km²,
# about 81 per km²) at its capacity (scripts/land_people_earth.py)
FALLOW = 0.68
# arable share by drawn terrain tier (lowland .. mountain): the GAEZ slope
# classes (0-8 % fully, 8-16 % 0.6, 16-30 % 0.3, steeper 0.05) weighted by
# the slopes typical of each landform
ARABLE_BY_TIER = {1: 0.85, 2: 0.75, 3: 0.45, 4: 0.08}


def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def day_length(lat, tilt, ws_day, year_days=365.0):
    """Monthly mean day length (hours), shape (12,) + lat.shape."""
    out = []
    for m in range(12):
        d = (m + 0.5) * year_days / 12.0
        dec = -np.radians(tilt) * np.cos(2 * np.pi * (d - ws_day) / year_days)
        x = -np.tan(np.radians(lat)) * np.tan(dec)
        out.append(24.0 / np.pi * np.arccos(np.clip(x, -1.0, 1.0)))
    return np.array(out)


def thornthwaite(T, L):
    """Monthly potential evaporation (mm), Thornthwaite (1948)."""
    Tp = np.maximum(T, 0.0)
    I = np.sum((Tp / 5.0) ** 1.514, axis=0)
    a = 6.75e-7 * I ** 3 - 7.71e-5 * I ** 2 + 1.792e-2 * I + 0.49239
    with np.errstate(divide="ignore", invalid="ignore"):
        pet = 16.0 * (L / 12.0) * (DAYS / 30.0) * np.where(I > 0, (10.0 * Tp / np.maximum(I, 1e-9)) ** a, 0.0)
    hot = -415.85 + 32.24 * T - 0.43 * T ** 2                   # above 26.5 C
    pet = np.where(T > 26.5, hot * (L / 12.0) * (DAYS / 30.0), pet)
    return np.where(T > 0, pet, 0.0)


def sunlight_top(lat, tilt, ws_day, year_days=365.0):
    """Monthly extraterrestrial radiation (FAO-56 eq. 21) as mm/day of
    evaporation, shape (12,) + lat.shape."""
    phi = np.radians(lat)
    out = []
    for m in range(12):
        d = (m + 0.5) * year_days / 12.0
        dec = -np.radians(tilt) * np.cos(2 * np.pi * (d - ws_day) / year_days)
        ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1.0, 1.0))
        ra = 24 * 60 / np.pi * 0.0820 * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
        out.append(0.408 * np.maximum(ra, 0.0))
    return np.array(out)


def hargreaves(T, dtr, Ra):
    """Monthly reference evaporation (mm), Hargreaves & Samani (1985)."""
    return 0.0023 * np.maximum(T + 17.8, 0.0) * np.sqrt(np.maximum(dtr, 0.0)) * Ra * DAYS


def bucket(P, PET, cap=100.0):
    """Soil water at the start of each month (mm), from a two-year spin-up."""
    S = np.full(P.shape[1:], cap / 2)
    start = np.zeros_like(P)
    for _ in range(2):
        for m in range(12):
            start[m] = S
            S = np.clip(S + P[m] - np.minimum(PET[m], P[m] + S), 0.0, cap)
    return start


def crop_yield(T, P, PET, S0, irr, c):
    """Best season of one crop: (net kcal per ha, season mask (12,...))."""
    best = np.zeros(T.shape[1:])
    best_mask = np.zeros(T.shape, bool)
    lo, hi = c["window"]
    for L in range(c["months"][0], c["months"][1] + 1):
        for s in range(12):
            idx = [(s + k) % 12 for k in range(L)]
            Ts, Ps, Es = T[idx], P[idx], PET[idx]
            ok = np.all((Ts >= lo) & (Ts <= hi), axis=0) & (Ts.max(0) >= c["need_warm"])
            heat = np.sum(np.maximum(Ts - c["base"], 0.0), axis=0) * DAYS
            ok &= heat >= c["heat"]
            etc = c["kc"] * Es.sum(0) + c.get("flood_mm", 0.0)
            supply = 0.8 * Ps.sum(0) + S0[idx[0]]
            fw = np.clip(supply / np.maximum(etc, 1.0), 0.0, 1.0)
            # the FAO-33 line holds for deficits up to about half the need;
            # with under a third of it the crop fails
            yf = np.clip(1.0 - c["ky"] * (1.0 - fw), 0.0, 1.0) * smoothstep(fw, 0.3, 0.5)
            yf = irr + (1.0 - irr) * yf                      # the irrigated share is fully watered
            # beyond the heat the crop needs, a longer season adds little
            y = np.where(ok, yf, 0.0) * c["grain"] * 1000.0 * c["edible"] * c["kcal"] * (1 - c["seed"])
            better = y > best
            best = np.where(better, y, best)
            m = np.zeros(T.shape, bool)
            m[idx] = True
            best_mask = np.where(better[None], m, best_mask)
    return best, best_mask


def malaria(T, P):
    """MARA climatic suitability (0-1): the best run of five months."""
    ft = np.minimum(smoothstep(T, 18.0, 22.0), 1.0 - smoothstep(T, 32.0, 40.0))
    fp = smoothstep(P, 0.0, 80.0)
    f = np.minimum(ft, fp)
    best = np.zeros(T.shape[1:])
    for s in range(12):
        best = np.maximum(best, np.min([f[(s + k) % 12] for k in range(5)], axis=0))
    return best


def best_crop_mix(kcal, masks, can_double):
    """Choose the actual primary and secondary crops of the best calorie mix."""
    names = list(kcal)
    stack = np.array([kcal[n] for n in names])
    total = stack.max(0)
    primary = np.where(total > 0, stack.argmax(0), -1)
    secondary = np.full(total.shape, -1, dtype=int)
    for i, a in enumerate(names):
        if a == 'dates':
            continue
        for j, b in enumerate(names):
            if b == a or b == 'dates':
                continue
            allowed = ~np.any(masks[a] & masks[b], axis=0) & can_double
            candidate = kcal[a]+0.5*kcal[b]
            better = allowed & (kcal[b] > 0) & (candidate > total)
            total = np.where(better, candidate, total)
            primary = np.where(better, i, primary)
            secondary = np.where(better, j, secondary)
    return total, primary, secondary


def analyse(T, P, lat, tilt, ws_day, irr, arable, dtr=None):
    """Every product, from monthly T (C), P (mm) and day/night range (C),
    shape (12, ...)."""
    if dtr is not None:
        PET = hargreaves(T, dtr, sunlight_top(lat, tilt, ws_day))
    else:
        PET = thornthwaite(T, day_length(lat, tilt, ws_day))
    S0 = bucket(P, PET)
    Tann, Pann = T.mean(0), P.sum(0)
    grow = (T >= 5.0) & (P + S0 >= 0.5 * PET)
    out = dict(T_ann=Tann, P_ann=Pann, PET_ann=PET.sum(0), aridity=Pann / np.maximum(PET.sum(0), 1.0),
               lgp_days=grow.sum(0) * DAYS, gdd5=np.sum(np.maximum(T - 5.0, 0.0), 0) * DAYS,
               npp=np.minimum(3000.0 / (1.0 + np.exp(1.315 - 0.119 * Tann)), 3000.0 * (1.0 - np.exp(-0.000664 * Pann))))
    kcal, masks = {}, {}
    for name, c in CROPS.items():
        kcal[name], masks[name] = crop_yield(T, P, PET, S0, irr, c)
    # date palm: a hot, frost-free, dry-country crop, watered by rivers
    palm_ok = (T.min(0) >= 7.0) & (np.sum(T >= 24.0, 0) >= 5) & (T.max(0) >= 30.0)
    palm_water = irr * (1.0 - smoothstep(Pann, *DATES["dry_mm"]))
    kcal["dates"] = np.where(palm_ok, palm_water, 0.0) * DATES["grain"] * 1000.0 * DATES["kcal"]
    names = list(kcal)
    # a second crop in the months the first leaves free, at half weight, and
    # only where water allows it every year: irrigated land, or a growing
    # period of ten months or more
    can_double = (irr >= 0.5) | (out["lgp_days"] >= 300)
    total, first, second = best_crop_mix(kcal, masks, can_double)
    out["kcal_ha"] = total
    out["main_crop"] = first
    out["second_crop"] = second
    out["double_crop"] = second >= 0
    # a double-cropped field is sown every year, not left fallow
    sown = np.where(out["double_crop"], 1.0, FALLOW)
    out["capacity"] = out["kcal_ha"] * arable * FARMED_SHARE * sown * 100.0 / NEED_KCAL
    out["malaria"] = malaria(T, P)
    for n in names:
        out[f"kcal_{n}"] = kcal[n]
    return out, names


def map_fields(params_path, cache_path, div):
    """Monthly T and P, latitude, irrigation access and arable share on the
    drawing's grid divided by `div`."""
    from render_satellite import elevation, load, original_terrain
    from rotclimate.model import ClimateModel
    from vector_rivers import river_classes

    p = load(params_path)
    z = np.load(cache_path)
    Tm, Pm, gl, pad, f = z["Tm"], z["Pm"], z["land"], int(z["pad"]), int(z["f"])
    land, tier, lake, rivers = original_terrain()
    H, W = land.shape
    px_scale = W / 2000.0
    elev = elevation(tier, land, p.tier_tops, px_scale, a_rise=22.0)
    stream, navigable = river_classes(rivers)
    km_px = MAP_KM / W
    d_nav = ndi.distance_transform_edt(~navigable) * km_px
    d_stream = ndi.distance_transform_edt(~stream) * km_px
    irr = np.maximum(np.exp(-d_nav / 6.0), 0.6 * np.exp(-d_stream / 2.5))
    arable = np.zeros(land.shape, np.float32)
    for k, v in ARABLE_BY_TIER.items():
        arable[tier == k] = v
    # block-average to the analysis grid
    h, w = H // div, W // div
    blk = lambda a: a[:h * div, :w * div].reshape(h, div, w, div).mean((1, 3))
    landf, elev_b, irr_b, arable_b = blk(land.astype(np.float32)), blk(elev), blk(irr), blk(arable)
    lat_g = ClimateModel(p.replace(downsample=f)).lat
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy = ((yy + 0.5) * div) / px_scale / f - 0.5 + pad
    cx = ((xx + 0.5) * div) / px_scale / f - 0.5 + pad
    _, (fy, fx) = ndi.distance_transform_edt(~gl, return_indices=True)
    up = lambda a: ndi.map_coordinates(np.asarray(a, float)[fy, fx], [cy, cx], order=1, mode="nearest")
    T = np.array([up(Tm[m]) for m in range(12)]) - p.lapse_rate * elev_b[None] / 1000.0
    P = np.maximum(np.array([up(Pm[m]) for m in range(12)]) * 1.0, 0.0)
    lat = up(lat_g)
    # the day/night range, learned from WorldClim (rotclimate.diurnal)
    from rotclimate.diurnal import coast_distance_km, dtr
    landb = landf > 0.5
    dist = coast_distance_km(landb, km_px * div)
    D = np.full(T.shape, 10.0)
    D[:, landb] = dtr(T[:, landb], P[:, landb], elev_b[landb], dist[landb], lat[landb])
    return dict(T=T, P=P, D=D, lat=lat, land=landb, irr=irr_b, arable=arable_b, elev=elev_b,
                tilt=p.tilt, ws=p.winter_solstice_day, div=div, shape=(h, w), full=(H, W))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--div", type=int, default=4, help="analysis grid = drawing / div")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    F = map_fields(a.params, a.cache, a.div)
    print(f"fields {F['shape']} ready ({time.time() - t0:.0f}s)", flush=True)
    res, names = analyse(F["T"], F["P"], F["lat"], F["tilt"], F["ws"], F["irr"], F["arable"], F["D"])
    print(f"analysis done ({time.time() - t0:.0f}s)", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    land = F["land"]
    arrays = {k: np.where(land, v, np.nan).astype(np.float32) if v.dtype != bool else (v & land)
              for k, v in res.items()}
    arrays["main_crop"] = np.where(land, res["main_crop"], -2).astype(np.int8)
    np.savez_compressed(out / "land_people.npz", **arrays, land=land, irr=F["irr"].astype(np.float32),
                        arable=F["arable"].astype(np.float32), div=a.div)
    km2 = (MAP_KM / F["full"][1] * a.div) ** 2
    cap = np.nansum(arrays["capacity"]) * km2
    summary = dict(params=a.params, crops=names, grid=list(F["shape"]), cell_km2=km2,
                   capacity_people=float(cap), land_km2=float(land.sum() * km2),
                   mean_capacity_per_km2=float(cap / (land.sum() * km2)),
                   main_crop_share={n: float(np.mean(res["main_crop"][land] == i)) for i, n in enumerate(names)},
                   no_crop_share=float(np.mean(res["main_crop"][land] < 0)),
                   double_crop_share=float(np.mean(res["double_crop"][land])))
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
