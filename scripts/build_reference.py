"""Build the real-world reference set for climate analogues.

Cities: GeoNames cities15000 (population >= 50,000, plus every national
capital), with suburbs folded into a larger city within 15 km.
Climate: WorldClim 2.1 monthly normals (1970-2000, 5 arc-minutes, ~9 km),
sampled at each city and corrected to the city's own elevation
(6.5 C per km between the WorldClim cell and the city), plus the monthly
day/night range (mean daily maximum minus minimum).

Also cross-checks the result against the official WMO station normals
(data/real_cities_wmo.csv) for cities with a station within 10 km.

Inputs are read from data/cache/ (downloaded separately, see the README):
  geonames/cities15000.zip, geonames/admin1CodesASCII.txt, geonames/countryInfo.txt
  worldclim/wc2.1_5m_{tavg,tmin,tmax,prec,elev}.zip
Output: data/real_cities_worldclim.csv

Run with:  python -I scripts/build_reference.py <repo root>
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "real_cities_worldclim.csv"
MIN_POP = 50_000
SUBURB_KM = 15.0
LAPSE = 6.5            # C per km

COUNTRY_SHORT = {
    "United States": "USA", "United Kingdom": "UK", "Russia": "Russia",
    "Democratic Republic of the Congo": "DR Congo", "Republic of the Congo": "Congo",
    "Central African Republic": "CAR", "Bosnia and Herzegovina": "Bosnia",
    "United Arab Emirates": "UAE", "Dominican Republic": "Dominican Rep.",
    "Papua New Guinea": "PNG", "South Korea": "South Korea", "North Korea": "North Korea",
}


def read_cities():
    z = zipfile.ZipFile(CACHE / "geonames" / "cities15000.zip")
    rows = [ln.split("\t") for ln in z.read("cities15000.txt").decode("utf-8").splitlines()]
    countries = {}
    for ln in (CACHE / "geonames" / "countryInfo.txt").read_text(encoding="utf-8").splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("\t")
            countries[f[0]] = COUNTRY_SHORT.get(f[4], f[4])
    admin1 = {}
    for ln in (CACHE / "geonames" / "admin1CodesASCII.txt").read_text(encoding="utf-8").splitlines():
        f = ln.split("\t")
        if len(f) >= 2:
            admin1[f[0]] = f[1]
    out = []
    for r in rows:
        pop = int(r[14] or 0)
        if pop < MIN_POP and r[7] != "PPLC":
            continue
        dem = int(r[16]) if r[16] not in ("", "-9999") else None
        elev = int(r[15]) if r[15] not in ("", "-9999") else dem
        out.append(dict(name=r[1], lat=float(r[4]), lon=float(r[5]), cc=r[8],
                        country=countries.get(r[8], r[8]), region=admin1.get(f"{r[8]}.{r[10]}", ""),
                        pop=pop, capital=r[7] == "PPLC", elev=elev))
    return out


def fold_suburbs(cities):
    """Keep a city only if no larger kept city lies within SUBURB_KM."""
    cities = sorted(cities, key=lambda c: (not c["capital"], -c["pop"]))
    lat = np.radians([c["lat"] for c in cities])
    lon = np.radians([c["lon"] for c in cities])
    keep = []
    klat, klon = np.empty(0), np.empty(0)
    for i, c in enumerate(cities):
        if keep:
            cc = (np.sin(lat[i]) * np.sin(klat) + np.cos(lat[i]) * np.cos(klat) * np.cos(lon[i] - klon))
            if (6371.0 * np.arccos(np.clip(cc, -1, 1))).min() < SUBURB_KM:
                continue
        keep.append(c)
        klat, klon = np.append(klat, lat[i]), np.append(klon, lon[i])
    return keep


def read_grid(zname, member):
    z = zipfile.ZipFile(CACHE / "worldclim" / zname)
    im = Image.open(io.BytesIO(z.read(member)))
    a = np.array(im, dtype=np.float32)
    nodata = im.tag_v2.get(42113)                 # GDAL_NODATA tag (differs per variable)
    if nodata is not None:
        a[a == np.float32(float(str(nodata).strip("\x00 ")))] = np.nan
    a[a < -1e30] = np.nan
    return a


def sample(grid, lat, lon, radius=4):
    """Bilinear interpolation using valid (land) cells only; coastal and
    island cities whose cell is sea fall back to the nearest land cells."""
    ny, nx = grid.shape
    y = (90.0 - lat) * 12.0 - 0.5
    x = (lon + 180.0) * 12.0 - 0.5
    out = np.full(lat.shape, np.nan)
    for i in range(lat.size):
        y0, x0 = int(np.floor(y[i])), int(np.floor(x[i]))
        best = None
        for r in range(0, radius + 1):
            ys = np.arange(y0 - r, y0 + 2 + r)
            xs = np.arange(x0 - r, x0 + 2 + r) % nx
            ys = ys[(ys >= 0) & (ys < ny)]
            win = grid[np.ix_(ys, xs)]
            ok = np.isfinite(win)
            if ok.any():
                yy, xx = np.meshgrid(ys, np.arange(x0 - r, x0 + 2 + r), indexing="ij")
                d = np.hypot(yy - y[i], xx - x[i])
                w = np.where(ok, np.maximum(1e-3, 1.0 - d / (r + 1.5)) ** 2, 0.0)
                if w.sum() > 0:
                    best = float((np.nan_to_num(win) * w).sum() / w.sum())
                    break
        if best is not None:
            out[i] = best
    return out


def label_cities(cities):
    """'Name, Country', or 'Name, Region, Country' when the name repeats."""
    from collections import Counter
    n = Counter((c["name"], c["country"]) for c in cities)
    for c in cities:
        c["label"] = c["name"] if n[(c["name"], c["country"])] == 1 or not c["region"] else f"{c['name']}, {c['region']}"


def cross_check(rows):
    path = ROOT / "data" / "real_cities_wmo.csv"
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        wmo = list(csv.DictReader(ln for ln in f if not ln.startswith("#")))
    clat = np.radians([r["lat"] for r in rows])
    clon = np.radians([r["lon"] for r in rows])
    dT, rP, dD = [], [], []
    for w in wmo:
        la, lo = np.radians(float(w["lat"])), np.radians(float(w["lon"]))
        cc = np.sin(la) * np.sin(clat) + np.cos(la) * np.cos(clat) * np.cos(lo - clon)
        d = 6371.0 * np.arccos(np.clip(cc, -1, 1))
        i = int(np.argmin(d))
        if d[i] > 10:
            continue
        Tw = np.array([float(w[f"T{m}"]) for m in range(1, 13)])
        Pw = np.array([float(w[f"P{m}"]) for m in range(1, 13)])
        dT.append(np.sqrt(np.mean((Tw - rows[i]["T"]) ** 2)))
        rP.append((rows[i]["P"].sum() + 1) / (Pw.sum() + 1))
        if w.get("D1"):
            Dw = np.array([float(w[f"D{m}"]) for m in range(1, 13)])
            dD.append(np.mean(rows[i]["D"]) - np.mean(Dw))
    dT, rP, dD = np.array(dT), np.array(rP), np.array(dD)
    print(f"cross-check with {dT.size} WMO stations within 10 km of a city:")
    print(f"  monthly temperature RMS difference: median {np.median(dT):.2f} C, 90% below {np.percentile(dT, 90):.2f} C")
    print(f"  annual rainfall ratio WorldClim/WMO: median {np.median(rP):.2f}, 80% within "
          f"{np.percentile(rP, 10):.2f}-{np.percentile(rP, 90):.2f}")
    if dD.size:
        print(f"  mean day/night range, WorldClim minus WMO ({dD.size} stations): median {np.median(dD):+.2f} C, "
              f"80% within {np.percentile(dD, 10):+.1f} to {np.percentile(dD, 90):+.1f} C")


def main():
    cities = read_cities()
    print(f"{len(cities)} cities with >= {MIN_POP:,} people or a national capital")
    cities = fold_suburbs(cities)
    print(f"{len(cities)} after folding suburbs within {SUBURB_KM:.0f} km into a larger city")
    lat = np.array([c["lat"] for c in cities])
    lon = np.array([c["lon"] for c in cities])
    elev_cell = sample(read_grid("wc2.1_5m_elev.zip", "wc2.1_5m_elev.tif"), lat, lon)
    T = np.stack([sample(read_grid("wc2.1_5m_tavg.zip", f"wc2.1_5m_tavg_{m:02d}.tif"), lat, lon) for m in range(1, 13)])
    P = np.stack([sample(read_grid("wc2.1_5m_prec.zip", f"wc2.1_5m_prec_{m:02d}.tif"), lat, lon) for m in range(1, 13)])
    D = np.stack([sample(read_grid("wc2.1_5m_tmax.zip", f"wc2.1_5m_tmax_{m:02d}.tif"), lat, lon)
                  - sample(read_grid("wc2.1_5m_tmin.zip", f"wc2.1_5m_tmin_{m:02d}.tif"), lat, lon) for m in range(1, 13)])
    city_elev = np.array([c["elev"] if c["elev"] is not None else np.nan for c in cities], float)
    corr = np.where(np.isfinite(city_elev) & np.isfinite(elev_cell),
                    -LAPSE * np.clip(city_elev - elev_cell, -1500, 1500) / 1000.0, 0.0)
    T = T + corr
    ok = np.isfinite(T).all(0) & np.isfinite(P).all(0) & np.isfinite(D).all(0)
    print(f"{(~ok).sum()} cities dropped (no WorldClim land cell within ~35 km)")
    label_cities(cities)
    # same label twice (two towns of one name in one province): keep the larger
    seen, unique = set(), []
    for i in sorted(range(len(cities)), key=lambda i: -cities[i]["pop"]):
        key = (cities[i]["label"], cities[i]["country"])
        if key not in seen:
            seen.add(key)
            unique.append(i)
    ok &= np.isin(np.arange(len(cities)), unique)
    rows = []
    for i, c in enumerate(cities):
        if ok[i]:
            rows.append(dict(c, T=T[:, i], P=P[:, i], D=D[:, i], elev_used=city_elev[i] if np.isfinite(city_elev[i]) else elev_cell[i]))
    rows.sort(key=lambda r: (r["country"], r["label"]))
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("# Monthly normals at GeoNames cities (population >= 50,000 or national capital), sampled from\n"
                "# WorldClim 2.1 (1970-2000, 5 arc-min) and corrected to city elevation. Built by scripts/build_reference.py\n")
        w = csv.writer(f)
        w.writerow(["name", "region", "country", "lat", "lon", "elev", "population", "period"]
                   + [f"T{m}" for m in range(1, 13)] + [f"P{m}" for m in range(1, 13)]
                   + [f"D{m}" for m in range(1, 13)])
        for r in rows:
            w.writerow([r["label"], r["region"], r["country"], f"{r['lat']:.3f}", f"{r['lon']:.3f}",
                        "" if not np.isfinite(r["elev_used"]) else int(round(r["elev_used"])), r["pop"], "1970-2000"]
                       + [f"{v:.1f}" for v in r["T"]] + [f"{v:.0f}" for v in r["P"]] + [f"{v:.1f}" for v in r["D"]])
    print(f"wrote {len(rows)} cities to {OUT.relative_to(ROOT)}")
    cross_check(rows)


if __name__ == "__main__":
    main()
