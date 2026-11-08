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


if __name__ == "__main__":
    {"outlets": outlets, "fit": fit}[sys.argv[1]]()
