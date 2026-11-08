"""Deltas on the map (owner, 8 Nov 2026: "I don't see why we couldn't have a Nile-like delta in our world").

Earth basis: the Edmonds et al. (2020) global delta polygons (Nat. Commun. 11:4741, CC BY 4.0; geomorphic area of 2,174
deltas) joined to HydroRIVERS v1.0 mean discharge at the river mouth (Lehner & Grill 2013): how big a delta a river of a
given size builds.

    .venv/bin/python -I scripts/delta_fans.py outlets      # HydroRIVERS outlet reaches -> data/cache/deltas/outlets.npz
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
HR = ROOT / "data/cache/hydrorivers"
DD = ROOT / "data/cache/deltas"
OUT = ROOT / "output/delta_fans_20261108"
REGIONS = ("af", "ar", "as", "au", "eu", "na", "sa")
log = lambda *a: print(*a, flush=True)  # noqa: E731


def outlets():
    """Every HydroRIVERS reach that ends at the sea or in an endorheic sink (NEXT_DOWN = 0) with its mouth point and mean
    discharge."""
    import shapefile
    rows = []
    for r in REGIONS:
        zf = zipfile.ZipFile(HR / f"HydroRIVERS_v10_{r}_shp.zip")
        names = {Path(n).suffix: n for n in zf.namelist() if Path(n).stem.startswith(f"HydroRIVERS_v10_{r}")}
        rd = shapefile.Reader(shp=io.BytesIO(zf.read(names[".shp"])), shx=io.BytesIO(zf.read(names[".shx"])),
                              dbf=io.BytesIO(zf.read(names[".dbf"])))
        f = [x[0] for x in rd.fields[1:]]; i_next, i_dis, i_up, i_endo = (f.index(k) for k in ("NEXT_DOWN", "DIS_AV_CMS", "UPLAND_SKM", "ENDORHEIC"))
        n = 0
        for k, rec in enumerate(rd.iterRecords()):
            if rec[i_next] == 0 and rec[i_dis] >= 1.0:
                x, y = rd.shape(k).points[-1]
                rows.append((y, x, float(rec[i_dis]), float(rec[i_up]), int(rec[i_endo]))); n += 1
        log(r, n, "outlets with >= 1 m3/s")
    a = np.array(rows)
    DD.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(DD / "outlets.npz", lat=a[:, 0], lon=a[:, 1], q=a[:, 2], upland_km2=a[:, 3], endorheic=a[:, 4].astype(np.int8))
    log("wrote", DD / "outlets.npz", len(a))


def table():
    """The Edmonds deltas with their mouth discharge."""
    import openpyxl
    ws = openpyxl.load_workbook(DD / "edmonds2020_deltas.xlsx", read_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))[3:]
    o = np.load(DD / "outlets.npz")
    olat, olon, oq = np.radians(o["lat"]), np.radians(o["lon"]), o["q"]
    out = []
    for r in rows:
        if r[0] is None or r[1] is None or r[16] is None:
            continue
        la, lo = np.radians(float(r[1])), np.radians(float(r[2]))
        d = 6371.0 * 2 * np.arcsin(np.sqrt(np.sin((olat - la) / 2) ** 2 + np.cos(la) * np.cos(olat) * np.sin((olon - lo) / 2) ** 2))
        near = d <= 30.0
        q = float(oq[near].max()) if near.any() else 0.0
        out.append(dict(id=str(r[0]), lat=float(r[1]), lon=float(r[2]), area_km2=float(r[16]), q=q, region=r[12]))
    return out


def fit():
    rows = table()
    oceania = lambda r: r["lat"] < -10 and r["lon"] > 110  # noqa: E731
    dev = [r for r in rows if r["lon"] >= -30 and not oceania(r)]; held = [r for r in rows if not (r["lon"] >= -30 and not oceania(r))]
    use = lambda rs: [r for r in rs if r["q"] >= 10.0 and r["area_km2"] > 0]  # noqa: E731
    D, Hd = use(dev), use(held)
    x, y = np.log10([r["q"] for r in D]), np.log10([r["area_km2"] for r in D])
    b, la = np.polyfit(x, y, 1); med = float(np.median(y))
    xh, yh = np.log10([r["q"] for r in Hd]), np.log10([r["area_km2"] for r in Hd])
    rm = lambda e: float(np.sqrt(np.mean(np.square(e))))  # noqa: E731
    res = dict(deltas=len(rows), dev=len(D), held=len(Hd), left_out_no_discharge=len([r for r in rows if r["q"] < 10.0]),
               a=float(10 ** la), b=float(b), dev_rmse_log10=rm(y - (la + b * x)), dev_r2=float(1 - np.var(y - (la + b * x)) / np.var(y)),
               held_rmse_fit=rm(yh - (la + b * xh)), held_rmse_constant=rm(yh - med), held_r2=float(1 - np.mean((yh - (la + b * xh)) ** 2) / np.var(yh)),
               dev_median_area_km2=float(10 ** med))
    res["use_fit"] = res["held_rmse_fit"] < res["held_rmse_constant"]
    nile = [r for r in rows if r["id"] == "0001"][0]
    res["nile"] = dict(q=nile["q"], area_km2=nile["area_km2"], predicted_km2=float(10 ** (la + b * np.log10(nile["q"]))))
    for n in (20, 100, 300, 1000, 3000):
        res[f"A_at_{n}_m3s_km2"] = float(10 ** (la + b * np.log10(n)))
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "fit.json").write_text(json.dumps(res, indent=1))
    (OUT / "deltas.json").write_text(json.dumps(rows))
    log(json.dumps(res, indent=1))


def _wc_grid(var):
    """WorldClim 2.1 5 arc-min global grid (rows from 90 N, columns from 180 W); NaN at sea."""
    import land_people_earth as E
    a = E.wc(var)
    if var == "elev":                      # WorldClim marks the sea with -32768 in elevation (NaN elsewhere)
        a = np.where(a < -1000, np.nan, a)
    return a


def _sample(grid, lat, lon):
    r = np.clip(((90.0 - np.asarray(lat)) * 12).astype(int), 0, grid.shape[0] - 1)
    c = np.clip(((np.asarray(lon) + 180.0) * 12).astype(int), 0, grid.shape[1] - 1)
    return grid[r, c]


def basins():
    """Per HydroRIVERS outlet: discharge, upstream area, relief (highest reach head upstream minus the mouth) and the
    catchment-weighted mean annual temperature at the reach heads (plan DF amendment 1)."""
    import numba
    import shapefile
    elev = _wc_grid("elev")
    import land_people_earth as E
    tann = np.nanmean(np.stack([E.wc("tavg", m) for m in range(1, 13)]), axis=0)

    @numba.njit(cache=True)
    def propagate(order, down, maxe, sta, sa):
        for i in order:
            j = down[i]
            if j >= 0:
                if maxe[i] > maxe[j]:
                    maxe[j] = maxe[i]
                sta[j] += sta[i]; sa[j] += sa[i]
    rows = []
    for r in REGIONS:
        zf = zipfile.ZipFile(HR / f"HydroRIVERS_v10_{r}_shp.zip")
        names = {Path(n).suffix: n for n in zf.namelist() if Path(n).stem.startswith(f"HydroRIVERS_v10_{r}")}
        rd = shapefile.Reader(shp=io.BytesIO(zf.read(names[".shp"])), shx=io.BytesIO(zf.read(names[".shx"])),
                              dbf=io.BytesIO(zf.read(names[".dbf"])))
        f = [x[0] for x in rd.fields[1:]]
        ix = {k: f.index(k) for k in ("HYRIV_ID", "NEXT_DOWN", "CATCH_SKM", "UPLAND_SKM", "DIS_AV_CMS")}
        recs = rd.records()
        rid = np.array([x[ix["HYRIV_ID"]] for x in recs], np.int64); nxt = np.array([x[ix["NEXT_DOWN"]] for x in recs], np.int64)
        catch = np.array([x[ix["CATCH_SKM"]] for x in recs], float); up = np.array([x[ix["UPLAND_SKM"]] for x in recs], float)
        dis = np.array([x[ix["DIS_AV_CMS"]] for x in recs], float)
        head = np.empty((len(rid), 2)); mouth = np.empty((len(rid), 2))
        for k, shp in enumerate(rd.iterShapes()):
            pts = shp.points; head[k] = pts[0]; mouth[k] = pts[-1]
        srt = np.argsort(rid); pos = np.searchsorted(rid[srt], nxt); pos = np.clip(pos, 0, len(rid) - 1)
        down = np.where((nxt != 0) & (rid[srt][pos] == nxt), srt[pos], -1).astype(np.int64)
        eh = np.nan_to_num(_sample(elev, head[:, 1], head[:, 0]), nan=0.0); th = _sample(tann, head[:, 1], head[:, 0])
        th = np.where(np.isfinite(th), th, np.nanmean(th))
        maxe = eh.copy(); sta = th * catch; sa = catch.copy()
        propagate(np.argsort(up, kind="stable").astype(np.int64), down, maxe, sta, sa)
        out = np.flatnonzero((nxt == 0) & (dis >= 1.0))
        em = np.nan_to_num(_sample(elev, mouth[out, 1], mouth[out, 0]), nan=0.0)
        for k, e0 in zip(out, em):
            rows.append((mouth[k, 1], mouth[k, 0], dis[k], up[k], max(maxe[k] - max(e0, 0.0), 0.0) / 1000.0, sta[k] / max(sa[k], 1e-9)))
        log(r, len(rid), "reaches,", len(out), "outlets")
    a = np.array(rows)
    np.savez_compressed(DD / "outlet_basins.npz", lat=a[:, 0], lon=a[:, 1], q=a[:, 2], area_km2=a[:, 3], relief_km=a[:, 4], t_c=a[:, 5])
    log("wrote", DD / "outlet_basins.npz", len(a))


def bqart(q_m3s, area_km2, relief_km, t_c):
    """Pristine sediment load, Mt/yr (Syvitski & Milliman 2007, B = 1)."""
    qk = np.asarray(q_m3s) * 365.25 * 86400 / 1e9
    base = 0.0006 * qk ** 0.31 * np.asarray(area_km2) ** 0.5 * np.maximum(np.asarray(relief_km), 0.01)
    return np.where(np.asarray(t_c) >= 2.0, base * np.asarray(t_c), 2.0 * base)


def exposure(lat, lon, land, step_km=5.0, reach_km=1500.0, n=32):
    """Share of n directions from a mouth whose open-water fetch reaches reach_km (land: True on a 5 arc-min grid)."""
    hits = 0
    for k in range(n):
        az = 2 * np.pi * k / n; at_sea = False; ok = False
        for s in np.arange(step_km, reach_km + step_km, step_km):
            la = lat + s * np.cos(az) / 111.32; lo = lon + s * np.sin(az) / (111.32 * max(np.cos(np.radians(lat)), 0.05))
            if la > 89.9 or la < -89.9:
                ok = at_sea; break
            lo = (lo + 180.0) % 360.0 - 180.0
            on_land = land[min(max(int((90.0 - la) * 12), 0), land.shape[0] - 1), min(max(int((lo + 180.0) * 12), 0), land.shape[1] - 1)]
            if not on_land:
                at_sea = True
            elif at_sea or s > 10.0:
                break
        else:
            ok = at_sea
        hits += ok
    return hits / n


def drivers():
    """Each Edmonds delta with its river's BQART load and the exposure of its mouth (plan DF amendment 1)."""
    rows = json.loads((OUT / "deltas.json").read_text())
    b = np.load(DD / "outlet_basins.npz")
    blat, blon = np.radians(b["lat"]), np.radians(b["lon"])
    land = np.isfinite(_wc_grid("elev"))
    for r in rows:
        la, lo = np.radians(r["lat"]), np.radians(r["lon"])
        d = 6371.0 * 2 * np.arcsin(np.sqrt(np.sin((blat - la) / 2) ** 2 + np.cos(la) * np.cos(blat) * np.sin((blon - lo) / 2) ** 2))
        near = np.flatnonzero(d <= 30.0)
        if near.size:
            k = near[np.argmax(b["q"][near])]
            r.update(q=float(b["q"][k]), basin_km2=float(b["area_km2"][k]), relief_km=float(b["relief_km"][k]), t_c=float(b["t_c"][k]))
            r["qs_mt"] = float(bqart(r["q"], r["basin_km2"], r["relief_km"], r["t_c"]))
        r["exposure"] = exposure(r["lat"], r["lon"], land)
    (OUT / "deltas_drivers.json").write_text(json.dumps(rows))
    log("wrote", OUT / "deltas_drivers.json", sum(1 for r in rows if "qs_mt" in r), "with a river")


def fit2():
    rows = [r for r in json.loads((OUT / "deltas_drivers.json").read_text()) if r.get("q", 0) >= 10.0 and r["area_km2"] > 0 and "qs_mt" in r]
    oceania = lambda r: r["lat"] < -10 and r["lon"] > 110  # noqa: E731
    dev = [r for r in rows if r["lon"] >= -30 and not oceania(r)]; held = [r for r in rows if not (r["lon"] >= -30 and not oceania(r))]
    X = lambda rs, m: np.column_stack([np.ones(len(rs))] + ([np.log10([r["q"] for r in rs])] if m == "M3" else [])  # noqa: E731
                                     + [np.log10([max(r["qs_mt"], 1e-6) for r in rs])] + ([np.array([r["exposure"] for r in rs])] if m in ("M2", "M3") else []))
    y = lambda rs: np.log10([r["area_km2"] for r in rs])  # noqa: E731
    rng = np.random.default_rng(20261108); fold = rng.integers(0, 5, len(dev))
    rm = lambda e: float(np.sqrt(np.mean(np.square(e))))  # noqa: E731
    res = dict(dev=len(dev), held=len(held), models={})
    for m in ("M1", "M2", "M3"):
        Xd, yd = X(dev, m), y(dev)
        cv = np.concatenate([yd[fold == k] - Xd[fold == k] @ np.linalg.lstsq(Xd[fold != k], yd[fold != k], rcond=None)[0] for k in range(5)])
        beta = np.linalg.lstsq(Xd, yd, rcond=None)[0]
        res["models"][m] = dict(coef=beta.tolist(), cv_rmse=rm(cv), dev_r2=float(1 - np.var(yd - Xd @ beta) / np.var(yd)))
    best = min(res["models"], key=lambda m: res["models"][m]["cv_rmse"]); res["chosen"] = best
    beta = np.array(res["models"][best]["coef"]); Xh, yh = X(held, best), y(held)
    f1 = json.loads((OUT / "fit.json").read_text())
    q1 = np.log10(f1["a"]) + f1["b"] * np.log10([r["q"] for r in held])
    res["held"] = dict(rmse_chosen=rm(yh - Xh @ beta), rmse_discharge_only=rm(yh - q1), rmse_constant=rm(yh - np.log10(f1["dev_median_area_km2"])),
                       r2_chosen=float(1 - np.mean((yh - Xh @ beta) ** 2) / np.var(yh)))
    res["use_drivers"] = res["held"]["rmse_chosen"] < res["held"]["rmse_discharge_only"]
    nile = [r for r in rows if r["id"] == "0001"]
    if nile:
        n = nile[0]; res["nile"] = dict(area_km2=n["area_km2"], qs_mt=n["qs_mt"], exposure=n["exposure"], q=n["q"],
                                        predicted_km2=float(10 ** (X([n], best) @ beta)[0]))
    (OUT / "fit2.json").write_text(json.dumps(res, indent=1)); log(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"outlets": outlets, "fit": fit, "basins": basins, "drivers": drivers, "fit2": fit2}[sys.argv[1]]()
