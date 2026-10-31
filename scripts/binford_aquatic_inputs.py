"""Aquatic-food inputs at Binford's hunter-gatherer groups, as the aquatic addendum defines them.

    python -I scripts/binford_aquatic_inputs.py --out output/forager_binford_20261031/aquatic_inputs.json

calibration/forager_binford_20261031/addendum_aquatic.json: distance to the
nearest WorldClim 5' water cell (ocean, and the large lakes WorldClim leaves
empty), WOA18 annual-mean sea-surface temperature at the nearest sea point,
and the freshwater index W_fresh = Natural Earth 1:10m river and lake-centre
line length within 25 km (km per 100 km2) + 10 x the share of that disc
covered by Natural Earth 1:10m lakes. Data only; no model is run.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

NE = ROOT / 'data/cache/naturalearth/x'
RADIUS_KM = 25.0
EARTH_KM = 6371.0


def unit(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1)


def chord(km):
    return 2 * math.sin(km / EARTH_KM / 2)


def river_points(step_km=1.0):
    """Points every ~step_km along every river and lake-centre line, each standing for its length."""
    import shapefile
    pts, wts = [], []
    for shape in shapefile.Reader(str(NE / 'ne_10m_rivers_lake_centerlines.shp')).shapes():
        xy = np.asarray(shape.points, float)
        parts = list(shape.parts) + [len(xy)]
        for a, b in zip(parts[:-1], parts[1:]):
            seg = xy[a:b]
            for (x0, y0), (x1, y1) in zip(seg[:-1], seg[1:]):
                length = EARTH_KM * math.acos(max(-1.0, min(1.0, float(unit(y0, x0) @ unit(y1, x1)))))
                n = max(1, int(math.ceil(length / step_km)))
                t = (np.arange(n) + 0.5) / n
                pts.append(np.stack([y0 + (y1 - y0) * t, x0 + (x1 - x0) * t], -1)); wts.append(np.full(n, length / n))
    return np.concatenate(pts), np.concatenate(wts)


def lake_share(lat, lon, lakes, spacing_km=2.0):
    """Share of the 25 km disc covered by lakes (point sampling)."""
    from matplotlib.path import Path as MPath
    n = int(RADIUS_KM / spacing_km)
    dy, dx = np.mgrid[-n:n + 1, -n:n + 1] * spacing_km
    inside = np.hypot(dy, dx) <= RADIUS_KM
    plat = lat + dy[inside] / 111.2
    plon = lon + dx[inside] / (111.2 * max(math.cos(math.radians(lat)), 0.05))
    pts = np.stack([plon, plat], -1)
    hit = np.zeros(len(pts), bool)
    for box, paths in lakes:
        if box[0] > plon.max() or box[2] < plon.min() or box[1] > plat.max() or box[3] < plat.min():
            continue
        for path in paths:
            hit |= path.contains_points(pts)
    return float(hit.mean())


def load_lakes():
    import shapefile
    from matplotlib.path import Path as MPath
    out = []
    for shape in shapefile.Reader(str(NE / 'ne_10m_lakes.shp')).shapes():
        xy = np.asarray(shape.points, float); parts = list(shape.parts) + [len(xy)]
        out.append((shape.bbox, [MPath(xy[a:b]) for a, b in zip(parts[:-1], parts[1:])]))
    return out


def coast_distance(water, lat, lon, max_km=600.0):
    ny, nx = water.shape; res = 180.0 / ny
    i0 = int((90.0 - lat) / res); j0 = int((lon + 180.0) / res)
    di = int(max_km / 111.2 / res) + 1
    dj = int(max_km / (111.2 * max(math.cos(math.radians(lat)), 0.05)) / res) + 1
    rows = np.arange(max(0, i0 - di), min(ny, i0 + di + 1)); cols = np.arange(j0 - dj, j0 + dj + 1) % nx
    sub = water[np.ix_(rows, cols)]
    if not sub.any():
        return max_km
    rr, cc = np.nonzero(sub)
    clat = 90.0 - (rows[rr] + 0.5) * res; clon = -180.0 + (cols[cc] + 0.5) * res
    d = EARTH_KM * np.arccos(np.clip(unit(clat, clon) @ unit(lat, lon), -1, 1))
    return float(min(d.min(), max_km))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/forager_binford_20261031/aquatic_inputs.json')
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT / 'scripts'))
    from forager_earth_test import binford
    from rotclimate.earth import _wc, observed_sst
    df = binford(); df = df[(df['subpop'] == 'n') & (df['density'].astype(float) > 0)]
    water = ~np.isfinite(_wc('tavg', 1))
    rp, rw = river_points(); tree = cKDTree(unit(rp[:, 0], rp[:, 1]))
    lakes = load_lakes()
    disc_km2 = math.pi * RADIUS_KM ** 2
    rows = []
    for _, r in df.iterrows():
        lat, lon = float(r['latitude']), float(r['longitude'])
        near = tree.query_ball_point(unit(lat, lon), chord(RADIUS_KM))
        river_km = float(rw[near].sum()) if near else 0.0
        share = lake_share(lat, lon, lakes)
        sst = observed_sst(np.array([lat]), np.array([lon]))
        rows.append(dict(name=str(r['name']), lat=lat, lon=lon, d_coast_km=coast_distance(water, lat, lon),
                         sst_annual_c=float(np.mean(sst)) if sst is not None else None,
                         river_km_per_100km2=100.0 * river_km / disc_km2, lake_share=share,
                         w_fresh=100.0 * river_km / disc_km2 + 10.0 * share))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(dict(definition=__doc__.split('\n\n')[1], radius_km=RADIUS_KM, sites=rows), indent=1))
    w = np.array([s['w_fresh'] for s in rows]); d = np.array([s['d_coast_km'] for s in rows])
    print(len(rows), 'sites; coast <25 km', int((d < 25).sum()), '; W_fresh p50/p90', np.percentile(w, [50, 90]).round(2))


if __name__ == '__main__':
    main()
