"""The land-and-people rules on Earth, as a check of their absolute numbers.

Runs scripts/land_people.py's analysis unchanged on WorldClim 2.1 monthly
climate (5 arc-min, 1970-2000) from the Atlantic to the Pacific, with the
map's irrigation rule applied to Natural Earth's river centrelines (major
rivers as the navigable class, the rest as streams) and the map's arable
shares applied to local relief in place of the drawn terrain tiers. The
farming capacity it gives is then summed over regions whose population
around 1-200 AD is known (census or scholarly estimate), for comparison.

Inputs, downloaded separately (data/cache is not committed):
  data/cache/worldclim/wc2.1_5m_{tavg,tmax,tmin,prec,elev}.zip
  data/cache/naturalearth_dl/ne_10m_rivers_lake_centerlines.geojson

    python -I scripts/land_people_earth.py --out output/land_people/earth
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Poly
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from land_people import ARABLE_BY_TIER, analyse  # noqa: E402

WC = ROOT / "data" / "cache" / "worldclim"
RIVERS = ROOT / "data" / "cache" / "naturalearth_dl" / "ne_10m_rivers_lake_centerlines.geojson"
WINDOW = dict(lat=(0.0, 56.0), lon=(-12.0, 125.0))
RES = 12                      # cells per degree (5 arc-min)
SUB = 5                       # river raster: 1 arc-min
KM_DEG = 111.32
NAVIGABLE_RANK = 4            # Natural Earth scalerank: 0-4 the large rivers
TILT, WS_DAY = 23.44, 355.0
# relief over 3x3 cells (~25 km) standing in for the drawn tiers:
# plains, rolling uplands, hills, mountains
RELIEF_TIERS = (150.0, 400.0, 1000.0)

# Regions with a known population around 1-200 AD: an outline (lon, lat)
# close to the historical unit, and either its people (millions, low and
# high) or its density over the unit's whole area (people per km², low and
# high), which is applied to the outline's land. See reports/land_people.md.
REGIONS = {
    "Egypt": dict(
        poly=[(29.4, 31.6), (32.6, 31.6), (32.6, 29.5), (33.2, 24.0), (32.4, 24.0), (30.4, 29.0), (29.4, 30.6)],
        people=(4.5, 5.0), source="1st-2nd c., with Alexandria: Bagnall & Frier 1994, Rathbone 1990, Frier 2000"),
    "North China Plain (Han Yan, Yu, Ji, Qing, Xu)": dict(
        poly=[(113.0, 32.3), (113.0, 35.0), (114.0, 36.3), (114.2, 38.9), (116.5, 38.9), (117.7, 38.0),
              (118.8, 37.6), (120.6, 37.8), (122.7, 37.4), (120.3, 36.0), (119.2, 34.8), (120.8, 32.5),
              (119.5, 32.0), (117.0, 32.3)],
        density=(80.7, 80.7), fitted=True,
        source="AD 2 census (Hanshu 28): 29.4 M on 365,000 km²; areas Zheng & Wu 2026"),
    "Wei valley (Han Sanfu, with Chang'an)": dict(
        poly=[(106.5, 33.9), (106.5, 35.4), (110.4, 35.4), (110.4, 33.9)],
        density=(44.0, 44.0), source="AD 2 census: 2.44 M on 55,400 km²"),
    "Sichuan basin (Han Shu, Guanghan, Ba)": dict(
        poly=[(103.2, 28.6), (103.2, 32.4), (108.4, 32.4), (108.4, 28.6)],
        density=(10.7, 10.7), source="AD 2 census: 2.62 M on 245,000 km²"),
    "Hunan and Jiangxi (Han Changsha, Yuzhang)": dict(
        poly=[(110.8, 29.5), (113.8, 29.6), (116.0, 30.0), (118.3, 29.3), (117.3, 27.0), (116.4, 24.6),
              (114.0, 24.8), (112.0, 25.5), (110.8, 26.5)],
        density=(2.4, 2.4), source="AD 2 census: 0.59 M on 246,000 km²"),
    "Roman Italy (mainland)": dict(
        poly=[(6.7, 45.9), (13.8, 46.6), (13.9, 45.6), (12.3, 44.2), (18.6, 40.2), (16.0, 37.9), (12.4, 41.0),
              (10.0, 43.9), (7.5, 43.7)],
        density=(24.0, 45.0), source="AD 14-165, low count (Beloch 1886, Frier 2000) to high (Lo Cascio 1994, Harper 2017)"),
    "Roman Gaul": dict(
        poly=[(-4.8, 48.5), (2.4, 51.2), (6.0, 51.9), (8.3, 49.0), (7.6, 47.5), (6.9, 45.9), (7.6, 43.8),
              (3.1, 42.4), (-1.8, 43.4)],
        density=(8.0, 18.0), source="AD 14-165: Beloch 1886, Frier 2000, Harper 2017"),
    "Iberia": dict(
        poly=[(-9.6, 43.9), (3.4, 42.6), (0.0, 38.6), (-2.0, 36.6), (-6.0, 35.8), (-9.6, 37.0)],
        density=(8.5, 15.0), source="AD 14-165: Frier 2000, Harper 2017"),
    "Asia Minor": dict(
        poly=[(26.0, 40.5), (29.0, 41.4), (36.0, 42.1), (41.6, 41.5), (41.6, 37.0), (36.0, 36.0), (27.0, 36.6)],
        density=(15.0, 24.0), source="AD 14-165: Frier 2000, Harper 2017, Beloch 1886"),
    "Roman Syria": dict(
        poly=[(34.9, 32.6), (35.7, 34.6), (35.8, 36.0), (36.2, 36.9), (38.2, 36.9), (39.2, 35.8), (38.4, 34.0),
              (37.0, 32.4)],
        density=(39.0, 55.0), source="AD 14-165: Frier 2000, Harper 2017, Beloch 1886"),
    "Mesopotamian alluvium": dict(
        poly=[(43.2, 34.3), (44.8, 34.3), (46.6, 33.0), (48.2, 31.2), (48.2, 29.9), (46.0, 30.4), (44.0, 31.6),
              (43.2, 33.1)],
        people=(0.7, 2.0), source="Parthian to Sasanian peak: Adams 1965, 1981 (settled area, 100-200 per ha)"),
}


def wc(var, month=None):
    member = f"wc2.1_5m_{var}.tif" if month is None else f"wc2.1_5m_{var}_{month:02d}.tif"
    im = Image.open(io.BytesIO(zipfile.ZipFile(WC / f"wc2.1_5m_{var}.zip").read(member)))
    a = np.array(im, dtype=np.float32)
    a[a < -1e30] = np.nan
    return a


def window_slices():
    r0 = int(round((90 - WINDOW["lat"][1]) * RES))
    r1 = int(round((90 - WINDOW["lat"][0]) * RES))
    c0 = int(round((WINDOW["lon"][0] + 180) * RES))
    c1 = int(round((WINDOW["lon"][1] + 180) * RES))
    return slice(r0, r1), slice(c0, c1)


def river_masks(shape):
    """Navigable and stream masks at 1 arc-min over the window."""
    h, w = shape[0] * SUB, shape[1] * SUB
    nav = Image.new("L", (w, h))
    stream = Image.new("L", (w, h))
    dn, ds = ImageDraw.Draw(nav), ImageDraw.Draw(stream)
    lat1, lon0 = WINDOW["lat"][1], WINDOW["lon"][0]
    gj = json.loads(RIVERS.read_text(encoding="utf-8"))
    for f in gj["features"]:
        g, pr = f.get("geometry") or {}, f.get("properties") or {}
        if pr.get("featurecla") not in ("River", "Lake Centerline"):
            continue
        lines = [g["coordinates"]] if g.get("type") == "LineString" else g.get("coordinates", [])
        draw = dn if float(pr.get("scalerank", 99)) <= NAVIGABLE_RANK else ds
        for line in lines:
            pts = [((x - lon0) * RES * SUB, (lat1 - y) * RES * SUB) for x, y, *_ in line]
            if len(pts) > 1:
                draw.line(pts, fill=255, width=1)
    return np.array(nav) > 0, np.array(stream) > 0


def irrigation(shape):
    """The map's rule, exp(-d/6 km) from navigable rivers and
    0.6 exp(-d/2.5 km) from streams, averaged to 5 arc-min cells; distances
    in latitude bands so a degree of longitude has its local length."""
    nav, stream = river_masks(shape)
    H = nav.shape[0]
    irr = np.zeros(nav.shape, np.float32)
    band, pad = 4 * RES * SUB, RES * SUB // 2
    for b0 in range(0, H, band):
        lo, hi = max(b0 - pad, 0), min(b0 + band + pad, H)
        lat = WINDOW["lat"][1] - (b0 + band / 2) / (RES * SUB)
        samp = (KM_DEG / (RES * SUB), KM_DEG * np.cos(np.radians(lat)) / (RES * SUB))
        d_nav = ndi.distance_transform_edt(~nav[lo:hi], sampling=samp)
        d_st = ndi.distance_transform_edt(~stream[lo:hi], sampling=samp)
        part = np.maximum(np.exp(-d_nav / 6.0), 0.6 * np.exp(-d_st / 2.5))
        irr[b0:min(b0 + band, H)] = part[b0 - lo:b0 - lo + min(band, H - b0)]
    return irr.reshape(shape[0], SUB, shape[1], SUB).mean((1, 3))


def arable_share(elev):
    e = np.nan_to_num(elev, nan=0.0)
    relief = ndi.maximum_filter(e, 3) - ndi.minimum_filter(e, 3)
    tier = 1 + np.searchsorted(RELIEF_TIERS, relief)
    return np.vectorize(ARABLE_BY_TIER.get)(tier).astype(np.float32), relief


def compute(out, margins=None):
    t0 = time.time()
    rs, cs = window_slices()
    elev = wc("elev")[rs, cs]
    T = np.stack([wc("tavg", m)[rs, cs] for m in range(1, 13)])
    P = np.stack([wc("prec", m)[rs, cs] for m in range(1, 13)])
    D = np.stack([wc("tmax", m)[rs, cs] - wc("tmin", m)[rs, cs] for m in range(1, 13)])
    land = np.isfinite(elev) & np.isfinite(T).all(0) & np.isfinite(P).all(0) & np.isfinite(D).all(0)
    shape = elev.shape
    lat = WINDOW["lat"][1] - (np.arange(shape[0]) + 0.5) / RES
    lon = WINDOW["lon"][0] + (np.arange(shape[1]) + 0.5) / RES
    LAT = np.broadcast_to(lat[:, None], shape)
    print(f"climate {shape} read ({time.time() - t0:.0f}s)", flush=True)
    irr = irrigation(shape)
    arable, relief = arable_share(elev)
    print(f"rivers and relief ({time.time() - t0:.0f}s)", flush=True)
    res, names = analyse(T[:, land], P[:, land], LAT[land], TILT, WS_DAY, irr[land], arable[land], D[:, land],
                         margins=margins)
    print(f"analysis ({time.time() - t0:.0f}s)", flush=True)
    full = {}
    for k, v in res.items():
        g = np.full(shape, -1 if k == "main_crop" else np.nan, np.float32)
        g[land] = v
        full[k] = g
    np.savez_compressed(out / "earth.npz", **full, land=land, irr=irr, arable=arable, relief=relief,
                        lat=lat, lon=lon, crops=np.array(names))
    return full, land, irr, arable, lat, lon


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reuse", action="store_true", help="reuse earth.npz")
    ap.add_argument("--margins", help="T0,T1,A0,A1: apply harvest.models.margin_reliability to the crop capacity")
    ap.add_argument("--crop-margins", help="T0,T1,A0,A1 (or T0,T1 for cold only): margins inside the crop model, the dry one on the rain-fed share only")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.reuse and (out / "earth.npz").exists():
        full = dict(np.load(out / "earth.npz"))
        land, irr, arable, lat, lon = full["land"], full["irr"], full["arable"], full["lat"], full["lon"]
        shape = land.shape
        LAT = np.broadcast_to(lat[:, None], shape)
    else:
        cm = [float(x) for x in a.crop_margins.split(",")] if a.crop_margins else None
        margins = ((cm[0], cm[1]), (cm[2], cm[3]) if len(cm) == 4 else None) if cm else None
        full, land, irr, arable, lat, lon = compute(out, margins)
        shape = land.shape
        LAT = np.broadcast_to(lat[:, None], shape)
    cell_km2 = (KM_DEG / RES) ** 2 * np.cos(np.radians(LAT))
    cap = np.nan_to_num(full["capacity"]) * cell_km2
    if a.margins:
        from harvest.models import margin_reliability
        m = [float(x) for x in a.margins.split(",")]
        ai = np.nan_to_num(full["P_ann"]) / np.maximum(np.nan_to_num(full["PET_ann"]), 1.0)
        cap = cap * margin_reliability(np.nan_to_num(full["T_ann"]), ai, full["irr"], (m[0], m[1]), (m[2], m[3]))
    rows = {}
    LON = np.broadcast_to(lon[None, :], shape)
    pts = np.stack([LON.ravel(), LAT.ravel()], 1)
    for name, r in REGIONS.items():
        inside = Poly(r["poly"]).contains_points(pts).reshape(shape) & land
        km2 = float(cell_km2[inside].sum())
        people = float(cap[inside].sum())
        lo, hi = r["people"] if "people" in r else (d * km2 / 1e6 for d in r["density"])
        rows[name] = dict(area_km2=round(km2), capacity_m=round(people / 1e6, 2),
                          capacity_per_km2=round(people / km2, 1),
                          historical_m=[round(lo, 2), round(hi, 2)], historical_per_km2=[round(lo * 1e6 / km2, 1), round(hi * 1e6 / km2, 1)],
                          ratio=[round(lo * 1e6 / people, 2), round(hi * 1e6 / people, 2)],
                          irrigated_share=round(float((irr * arable * cell_km2)[inside].sum()
                                                      / max((arable * cell_km2)[inside].sum(), 1)), 3),
                          source=r["source"], fitted=r.get("fitted", False))
    (out / "regions.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(json.dumps(rows, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
