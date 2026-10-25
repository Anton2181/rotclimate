"""Earth windows for testing the polity model: the same fields the map gives
polity/fields.py, on a square grid about a centre (azimuthal equidistant,
rotclimate.earth.forward / inverse), rows running south.

  terrain     WorldClim 2.1 5' elevation and its land mask
  climate     WorldClim monthly mean, maximum and minimum temperature and
              precipitation; biomes by rotclimate.biomes from the annual means
  people      the Earth land/people run's settlement base x the central
              occupation (as the map's Harvest density)
  relief      elevation range over 3 x 3 cells
  winds       NCEP/NCAR reanalysis 1981-2010 monthly long-term means at
              sigma 0.995: vector mean (uwnd, vwnd) and mean speed (wspd)
  rivers      Natural Earth 10 m river centre lines, scalerank <= 8

And readers for the historical data (Han AD 2 counties and commanderies,
Hanson's Roman towns, Itiner-e roads, Cliopatria polygons, ORBIS edges).
All data files are read as data only.
"""
from __future__ import annotations

import io
import json
import struct
import zipfile
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Poly
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache"
OCCUPATION_CENTRAL = 0.3245772699601042
RIVER_SCALERANK = 8


def grid(lat0, lon0, width_km, height_km, cell_km):
    from rotclimate.earth import inverse
    nx, ny = int(round(width_km / cell_km)), int(round(height_km / cell_km))
    x = (np.arange(nx) - (nx - 1) / 2) * cell_km
    y = ((ny - 1) / 2 - np.arange(ny)) * cell_km
    X, Y = np.meshgrid(x, y)
    lat, lon = inverse(X, Y, lat0, lon0)
    return dict(lat=lat, lon=lon, x=X, y=Y, cell_km=float(cell_km), lat0=lat0, lon0=lon0)


def sample_global(a, lat, lon, lat_top=90.0, lon_left=-180.0, step=None, order=0):
    """Sample a global lat/lon raster (rows from the north) at lat, lon."""
    step = 180.0 / a.shape[0] if step is None else step
    r = (lat_top - lat) / step - 0.5
    c = ((lon - lon_left) / step - 0.5) % a.shape[1]
    return ndi.map_coordinates(np.asarray(a, float), [r, c], order=order, mode="nearest")


def window(lat0, lon0, width_km, height_km, cell_km):
    from rotclimate import biomes
    from rotclimate.earth import _wc
    g = grid(lat0, lon0, width_km, height_km, cell_km)
    lat, lon = g["lat"], g["lon"]
    elev = sample_global(_wc("elev"), lat, lon)
    land = np.isfinite(elev)
    g["land"] = land; g["elev"] = np.nan_to_num(elev, nan=0.0)
    for var in ("tavg", "tmax", "tmin", "prec"):
        g[var] = np.stack([np.nan_to_num(sample_global(_wc(var, m + 1), lat, lon)) for m in range(12)])
    g["biome"] = biomes.classify(g["tavg"].mean(0), g["prec"].sum(0), land)
    e = g["elev"]
    g["relief"] = np.where(land, ndi.maximum_filter(e, 3) - ndi.minimum_filter(e, 3), 0.0)
    d, h, covered = earth_people(lat, lon)
    g["density"] = d * land; g["herders"] = h * land; g["covered"] = covered
    g.update(winds(lat, lon))
    g["river"] = rivers(g) & land
    return g


def earth_people(lat, lon):
    """People per km2 (the Earth run's settlement base x the central
    occupation) and the herders' share of the food (grazing over cleared
    crops + grazing), with the share of the window the run covers."""
    from harvest.models import settlement_fields
    from rotclimate import biomes
    z = np.load(ROOT / "output/land_people/earth/earth.npz")
    biome = biomes.classify(np.nan_to_num(z["T_ann"]), np.nan_to_num(z["P_ann"]), z["land"])
    water_km = np.minimum(-6.0 * np.log(np.maximum(np.nan_to_num(z["irr"]), 1e-12)), 300.0)
    f = settlement_fields(np.nan_to_num(z["capacity"]), np.nan_to_num(z["npp"]), biome, np.nan_to_num(z["arable"]),
                          water_km, np.nan_to_num(z["malaria"]))
    base = np.nan_to_num(f["settlement_base"]) * OCCUPATION_CENTRAL
    food = f["crop_capacity"] * f["clearance"] + f["pastoral_capacity"]
    herd = np.divide(f["pastoral_capacity"], food, out=np.zeros_like(food), where=food > 0)
    zl, zo = z["lat"], z["lon"]
    step = float(zl[0] - zl[1])
    r = (zl[0] + step / 2 - lat) / step - 0.5
    c = (lon - (zo[0] - step / 2)) / step - 0.5
    inside = (r >= -0.5) & (r <= len(zl) - 0.5) & (c >= -0.5) & (c <= len(zo) - 0.5)
    rc = [np.clip(r, 0, len(zl) - 1), np.clip(c, 0, len(zo) - 1)]
    d = np.where(inside, ndi.map_coordinates(base, rc, order=0), 0.0)
    h = np.where(inside, ndi.map_coordinates(np.nan_to_num(herd), rc, order=0), 0.0)
    return d, h, inside


def _ncep(var):
    import h5py
    with h5py.File(CACHE / "ncep_ltm" / f"{var}.mon.ltm.nc", "r") as f:
        a = np.asarray(f[var][:], float)
        lat = np.asarray(f["lat"][:], float); lon = np.asarray(f["lon"][:], float)
    return a, lat, lon


def winds(lat, lon):
    out = {}
    for var, key in (("uwnd", "u"), ("vwnd", "v"), ("wspd", "wind")):
        a, la, lo = _ncep(var)
        step = float(la[0] - la[1])
        r = (la[0] - lat) / step
        c = ((lon - lo[0]) / step) % len(lo)
        out[key] = np.stack([ndi.map_coordinates(a[m], [r, c], order=1, mode="wrap") for m in range(12)])
    out["wind"] = np.maximum(out["wind"], np.hypot(out["u"], out["v"]))
    out["sigma"] = np.sqrt(np.maximum(out["wind"] ** 2 - out["u"] ** 2 - out["v"] ** 2, 0.0))
    return out


def to_cells(g, lat, lon):
    """(row, col) of points; None where outside the window."""
    from rotclimate.earth import forward
    x, y = forward(np.asarray(lat, float), np.asarray(lon, float), g["lat0"], g["lon0"])
    ny, nx = g["lat"].shape
    col = np.round(x / g["cell_km"] + (nx - 1) / 2).astype(int)
    row = np.round((ny - 1) / 2 - y / g["cell_km"]).astype(int)
    ok = (row >= 0) & (row < ny) & (col >= 0) & (col < nx)
    return row, col, ok


def draw_lines(g, lines, width=1):
    """Rasterise polylines (lists of (lat, lon)) onto the window."""
    ny, nx = g["lat"].shape
    mask = np.zeros((ny, nx), bool)
    for line in lines:
        a = np.asarray(line, float)
        if len(a) < 2:
            continue
        # densify to half a cell
        from rotclimate.earth import forward
        x, y = forward(a[:, 0], a[:, 1], g["lat0"], g["lon0"])
        cx = x / g["cell_km"] + (nx - 1) / 2; cy = (ny - 1) / 2 - y / g["cell_km"]
        for k in range(len(a) - 1):
            n = int(np.ceil(2 * np.hypot(cx[k + 1] - cx[k], cy[k + 1] - cy[k]))) + 1
            t = np.linspace(0, 1, n)
            rr = np.round(cy[k] + t * (cy[k + 1] - cy[k])).astype(int)
            cc = np.round(cx[k] + t * (cx[k + 1] - cx[k])).astype(int)
            ok = (rr >= 0) & (rr < ny) & (cc >= 0) & (cc < nx)
            mask[rr[ok], cc[ok]] = True
    return ndi.binary_dilation(mask, iterations=width - 1) if width > 1 else mask


def rivers(g):
    d = json.loads((CACHE / "naturalearth_dl/ne_10m_rivers_lake_centerlines.geojson").read_text())
    lines = []
    for f in d["features"]:
        if (f["properties"].get("scalerank") or 99) > RIVER_SCALERANK or not f["geometry"]:
            continue
        geo = f["geometry"]
        parts = [geo["coordinates"]] if geo["type"] == "LineString" else geo["coordinates"]
        for p in parts:
            lines.append([(lat, lon) for lon, lat in p])
    return draw_lines(g, lines)


def inside_polygons(g, rings_lonlat):
    """Cells inside any of the polygons (each a list of rings; even-odd)."""
    pts = np.column_stack([g["lon"].ravel(), g["lat"].ravel()])
    inside = np.zeros(len(pts), bool)
    for rings in rings_lonlat:
        hit = np.zeros(len(pts), bool)
        for ring in rings:
            ring = np.asarray(ring, float)
            bb = ((pts[:, 0] >= ring[:, 0].min()) & (pts[:, 0] <= ring[:, 0].max()) &
                  (pts[:, 1] >= ring[:, 1].min()) & (pts[:, 1] <= ring[:, 1].max()))
            if bb.any():
                h = np.zeros(len(pts), bool)
                h[bb] = Poly(ring).contains_points(pts[bb])
                hit ^= h
        inside |= hit
    return inside.reshape(g["lat"].shape)


# ------------------------------------------------------------ historical data
def cliopatria(name, year):
    d = json.loads((CACHE / "cliopatria/geo/subset_ad2_117_150.json").read_text())
    out = []
    for p in d["polities"]:
        if p["name"] == name and year in p["years"]:
            geo = p["geometry"]
            polys = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
            out.extend(polys)
    return out


def cliopatria_polities(year):
    d = json.loads((CACHE / "cliopatria/geo/subset_ad2_117_150.json").read_text())
    names = sorted({p["name"] for p in d["polities"] if year in p["years"]})
    return {n: cliopatria(n, year) for n in names}


def _tm_inverse(x, y, a, f, lon0, k0=1.0, false_easting=0.0):
    """Inverse transverse Mercator (Snyder 1987, eqs. 8-12 to 8-25)."""
    e2 = 2 * f - f * f; ep2 = e2 / (1 - e2)
    x = np.asarray(x, float) - false_easting
    M = np.asarray(y, float) / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - np.sqrt(1 - e2)) / (1 + np.sqrt(1 - e2))
    p1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * np.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * np.sin(4 * mu)
          + (151 * e1 ** 3 / 96) * np.sin(6 * mu) + (1097 * e1 ** 4 / 512) * np.sin(8 * mu))
    C1 = ep2 * np.cos(p1) ** 2; T1 = np.tan(p1) ** 2
    N1 = a / np.sqrt(1 - e2 * np.sin(p1) ** 2); R1 = a * (1 - e2) / (1 - e2 * np.sin(p1) ** 2) ** 1.5
    D = x / (N1 * k0)
    lat = p1 - (N1 * np.tan(p1) / R1) * (D ** 2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24
                                         + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720)
    lon = np.radians(lon0) + (D - (1 + 2 * T1 + C1) * D ** 3 / 6
                             + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120) / np.cos(p1)
    return np.degrees(lat), np.degrees(lon)


def han_seats():
    """The AD 2 county and commandery seats: lat, lon, type, commandery, people."""
    import shapefile
    r = shapefile.Reader(str(CACHE / "han_ad2/shp/CountyPointsWithPopulation"), encoding="utf-8")
    out = []
    for shp, rec in zip(r.iterShapes(), r.iterRecords()):
        d = rec.as_dict()
        if d["YEAR"] != "2AD":
            continue
        x, y = shp.points[0]
        # Xian 1980, Gauss-Kruger zone 19 (central meridian 111 E, false easting 19,500 km)
        lat, lon = _tm_inverse(x, y, 6378140.0, 1 / 298.257, 111.0, 1.0, 19500000.0)
        out.append(dict(lat=float(lat), lon=float(lon), type=d["TYPE"], commandery=d["PrefNAM"],
                        name=d["CountyNAM"], people=float(d["CountyPOP"])))
    return out


def han_commanderies(g):
    """AD 2 commanderies: per cell the commandery index (-1 outside) and the list."""
    import shapefile
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from han_census_check import albers_forward
    X, Y = albers_forward(g["lat"].ravel(), g["lon"].ravel())
    pts = np.column_stack([X, Y])
    r = shapefile.Reader(str(CACHE / "han_ad2/shp/ResearchArea"), encoding="utf-8")
    ids = np.full(len(pts), -1); rows = []
    for shp, rec in zip(r.iterShapes(), r.iterRecords()):
        d = rec.as_dict()
        if d["YEAR"] != "2AD":
            continue
        inside = np.zeros(len(pts), bool)
        parts = list(shp.parts) + [len(shp.points)]
        for k in range(len(parts) - 1):
            ring = np.asarray(shp.points[parts[k]:parts[k + 1]])
            bb = ((pts[:, 0] >= ring[:, 0].min()) & (pts[:, 0] <= ring[:, 0].max()) &
                  (pts[:, 1] >= ring[:, 1].min()) & (pts[:, 1] <= ring[:, 1].max()))
            if bb.any():
                h = np.zeros(len(pts), bool)
                h[bb] = Poly(ring).contains_points(pts[bb])
                inside ^= h
        ids[inside & (ids < 0)] = len(rows)
        rows.append(dict(name=d["PrefNAM"], people=float(d["POP"]), area_km2=float(d["AREA"])))
    return ids.reshape(g["lat"].shape), rows


def hanson_towns(year=150):
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import roman_cities_check as rc
    old = rc.YEAR; rc.YEAR = year
    try:
        return rc.towns(str(CACHE / "hanson2016/cities.xlsx"))
    finally:
        rc.YEAR = old


def _mercator_inverse(x, y, a=6378137.0, f=1 / 298.257223563):
    e = np.sqrt(2 * f - f * f)
    lon = np.degrees(np.asarray(x) / a)
    t = np.exp(-np.asarray(y) / a)
    phi = np.pi / 2 - 2 * np.arctan(t)
    for _ in range(8):
        phi = np.pi / 2 - 2 * np.arctan(t * ((1 - e * np.sin(phi)) / (1 + e * np.sin(phi))) ** (e / 2))
    return np.degrees(phi), lon


def _wkb_lines(b):
    """LineString / MultiLineString WKB (2D, Z or M) to lists of (x, y)."""
    out = []

    def read(off):
        bo = "<" if b[off] == 1 else ">"
        t = struct.unpack_from(bo + "I", b, off + 1)[0]
        base, kind = t % 1000, t // 1000
        dims = 2 + (kind in (1, 3)) + (kind in (2, 3))
        off += 5
        if base == 2:
            n = struct.unpack_from(bo + "I", b, off)[0]; off += 4
            pts = np.frombuffer(b, dtype=bo + "f8", count=n * dims, offset=off).reshape(n, dims)[:, :2]
            out.append(pts); off += 8 * n * dims
        elif base == 5:
            n = struct.unpack_from(bo + "I", b, off)[0]; off += 4
            for _ in range(n):
                off = read(off)
        return off
    read(0)
    return out


def itinere_roads(year=150):
    """Roman roads standing in `year` (undated segments included), as (lat, lon) polylines, with their type."""
    import sqlite3
    path = CACHE / "itinere/itinere_roads.gpkg"
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    out = []
    for geom, kind, lo, up in con.execute(
            'select geom, Type, Lower_Date, Upper_Date from "itinere_roads_simplify"'):
        lo = None if lo is None or lo >= 9999 else lo; up = None if up is None or up >= 9999 else up
        if (lo is not None and lo > year) or (up is not None and up < year):
            continue
        flags = geom[3]
        env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((flags >> 1) & 7, 0)
        for pts in _wkb_lines(bytes(geom[8 + env:])):
            lat, lon = _mercator_inverse(pts[:, 0], pts[:, 1])
            out.append((kind, list(zip(lat, lon))))
    con.close()
    return out


def orbis_edges():
    """ORBIS network edges with their summer durations (days) and endpoints."""
    import csv
    t = (CACHE / "orbis/o_sites.csv").read_text(encoding="utf-8", errors="replace").replace("\r", "\n")
    sites = {int(r["id"]): dict(name=r["label"], lon=float(r["x"]), lat=float(r["y"]))
             for r in csv.DictReader(io.StringIO(t)) if r["id"].strip()}
    d = json.loads((CACHE / "orbis/new_routes.topojson").read_text())
    sc, tr = d["transform"]["scale"], d["transform"]["translate"]
    arcs = [np.cumsum(np.asarray(a, float), 0) * sc + tr for a in d["arcs"]]
    out = []
    for geo in d["objects"]["base_routes"]["geometries"]:
        if geo["type"] != "LineString":
            continue
        pts = np.concatenate([arcs[i] if i >= 0 else arcs[~i][::-1] for i in geo["arcs"]])
        p = geo["properties"]
        # river and sea nodes are the site id + 100,000 and + 200,000
        out.append(dict(kind=p["t"], source=int(p["sid"]) % 100000, target=int(p["tid"]) % 100000,
                        days=float(p["s"]), line=[(la, lo) for lo, la in pts]))
    return sites, out


# narrow straits that a 9 km grid closes: carved as water and crossed by ferry
STRAITS = {"Bosporus": [(40.88, 28.95), (41.10, 29.05), (41.32, 29.15)],
           "Dardanelles": [(39.95, 26.05), (40.20, 26.40), (40.45, 26.75), (40.62, 27.10), (40.75, 27.50)],
           "Messina": [(38.02, 15.60), (38.15, 15.63), (38.28, 15.67)],
           "Gulf of Corinth": [(38.15, 21.05), (38.22, 21.45), (38.32, 21.78), (38.30, 22.10), (38.18, 22.50),
                               (38.05, 22.80), (37.93, 22.92)],
           "Euripus": [(38.65, 23.20), (38.46, 23.59), (38.30, 23.80), (38.18, 24.05)],
           "Kerch": [(45.10, 36.40), (45.33, 36.55), (45.55, 36.70)],
           "Bonifacio": [(41.33, 9.05), (41.36, 9.22), (41.38, 9.40)]}


def straits(g):
    return draw_lines(g, list(STRAITS.values()), width=2)
