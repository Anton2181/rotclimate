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


if __name__ == "__main__":
    {"outlets": outlets}[sys.argv[1]]()
