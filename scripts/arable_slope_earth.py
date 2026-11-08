"""Plan D1b (calibration/geography_control_20261107/plan_D1.json): the D1 arable rule on the Earth harness grid.

ETOPO 2022 60 arc-second elevation over the window of scripts/land_people_earth.py (0-56 N, 12 W-125 E), the slope at
that ~1.85 km scale, a(S) with the D1 parameters (data/arable_slope_model.json), averaged over the land sub-cells of each
5 arc-min cell. Cached in data/cache/arable_slope_earth/arable_5m.npz (rows from the north, as the harness).

    .venv/bin/python -I scripts/arable_slope_earth.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
URL = ("https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/60s/60s_surface_elev_netcdf/"
       "ETOPO_2022_v1_60s_N90W180_surface.nc.dods")
CACHE = ROOT / "data/cache/arable_slope_earth"
WINDOW = dict(lat=(0.0, 56.0), lon=(-12.0, 125.0))
DEG_M = 111320.0
log = lambda *a: print(*a, flush=True)  # noqa: E731


def etopo_window():
    path = CACHE / "etopo60_window.npy"
    if path.exists():
        return np.load(path)
    CACHE.mkdir(parents=True, exist_ok=True)
    i0, i1 = int(round((WINDOW["lat"][0] + 90) * 60)), int(round((WINDOW["lat"][1] + 90) * 60))
    j0, j1 = int(round((WINDOW["lon"][0] + 180) * 60)), int(round((WINDOW["lon"][1] + 180) * 60))
    rows = []
    for a in range(i0, i1, 120):
        b = min(a + 120, i1)
        for attempt in range(4):
            try:
                raw = urllib.request.urlopen(URL + f"?z[{a}:1:{b - 1}][{j0}:1:{j1 - 1}]", timeout=300).read(); break
            except Exception as e:                                       # noqa: BLE001
                log("retry", a, e); time.sleep(2 ** attempt * 2)
        k = raw.index(b"Data:\n") + 6; n = int(np.frombuffer(raw[k:k + 4], ">u4")[0])
        rows.append(np.frombuffer(raw[k + 8:k + 8 + 4 * n], ">f4").reshape(b - a, j1 - j0))
    z = np.concatenate(rows)[::-1].astype(np.float32)                    # rows from the north
    np.save(path, z); return z


def main():
    t0 = time.time()
    z = etopo_window().astype(float); log("ETOPO window", z.shape, f"({time.time() - t0:.0f}s)")
    m = json.loads((ROOT / "data/arable_slope_model.json").read_text())["params"]
    ny, nx = z.shape
    lat = WINDOW["lat"][1] - (np.arange(ny) + 0.5) / 60.0
    dy = DEG_M / 60.0; dx = (DEG_M / 60.0) * np.cos(np.radians(lat))[:, None]
    land = z > 0
    gy = np.gradient(np.where(land, z, 0.0), dy, axis=0); gx = np.gradient(np.where(land, z, 0.0), axis=1) / dx
    S = np.degrees(np.arctan(np.hypot(gy, gx)))
    a = m["lo"] + (m["hi"] - m["lo"]) / (1.0 + np.power(np.maximum(S, 1e-6) / m["S0"], m["k"]))
    blk = lambda v: v.reshape(ny // 5, 5, nx // 5, 5).sum((1, 3))
    n = blk(land.astype(float))
    arable = np.where(n > 0, blk(np.where(land, a, 0.0)) / np.maximum(n, 1), np.nan).astype(np.float32)
    np.savez_compressed(CACHE / "arable_5m.npz", arable=arable, land_subcells=n.astype(np.uint8),
                        params=json.dumps(m))
    log("arable 5'", arable.shape, "land-cell mean", float(np.nanmean(arable)), f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
