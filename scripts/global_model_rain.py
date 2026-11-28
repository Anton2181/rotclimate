"""T10 / option A: a global MODEL rain climatology on Earth geography (no observed fields), and the two-pass fields
derived from it.

    .venv/bin/python -I scripts/global_model_rain.py PARAMS OUT_NPZ [CELL_KM]

Tiles 40 S - 40 N (and beyond, to 45 deg) with 6,000 x 5,000 km regional runs (rows centred 22 S, 0, 22 N; every 40 deg
of longitude), each run world-legal (ROTCLIMATE_WORLD_LEGAL=1: no NCEP fields) with PARAMS (a world parameter set,
e.g. r64bw). Each tile's in-map cells (land AND sea) are binned to a 1-degree globe, weighted by closeness to the tile
centre; southern tiles run mirrored and are turned back (real latitude, months shifted back by six).
Writes OUT_NPZ: rain [12, 180, 360] mm/day (NaN where no tile reached), lat (90 -> -90 centres), lon (-180 -> 180)
and omega_wtg [12, 180, 360] Pa/s: the weak-temperature-gradient 500 hPa sinking from the 1,000 km smoothed model rain,
FIXED (two-pass: no within-run feedback), = 0.03 x clip(1 - P_s / 3 mm/day, 0, 1).
"""
import json, os, sys, time
from pathlib import Path
os.environ["ROTCLIMATE_WORLD_LEGAL"] = "1"
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import numpy as np
from scipy import ndimage as ndi
from rotclimate import earth
from rotclimate.config import Params
from benchmark_local import monthly_stats

W_KM, H_KM, ROWS, LON_STEP = 6000.0, 5000.0, (-22.0, 0.0, 22.0), 40.0
OMEGA_MAX, P0, SMOOTH_KM = 0.03, 3.0, 1000.0


def main():
    p = Params(**json.loads((ROOT / sys.argv[1]).read_text())); out = ROOT / sys.argv[2]
    cell = float(sys.argv[3]) if len(sys.argv) > 3 else 112.0
    acc = np.zeros((12, 180, 360)); wsum = np.zeros((180, 360)); t0 = time.time()
    for la in ROWS:
        for lo in np.arange(-180.0, 180.0, LON_STEP):
            name = f"gtile_{int(la)}_{int(lo)}"
            earth.REGIONS[name] = dict(lat0=la if la != 0 else 0.001, lon0=float(lo), width_km=W_KM, height_km=H_KM)
            c = earth.region_case(name, cell); g = c.grid
            r = earth.run_case(p, c, steps=p.steps_per_year); pr = r.params
            st = monthly_stats(r.T, r.P, r.days, pr.year_days, summer_solstice=pr.winter_solstice_day + pr.year_days / 2)
            Pm = np.asarray(st["Pm"], float) / 30.4              # mm/month -> mm/day
            lat, lon = np.asarray(g.lat, float), np.asarray(c.lon, float)
            if la < 0:
                lat = -lat; Pm = np.roll(Pm, 6, axis=0)        # mirrored run: back to real latitude and months
            m = g.inmap & np.isfinite(Pm).all(0)
            i = np.clip((90.0 - lat[m]).astype(int), 0, 179); j = np.clip(((lon[m] + 180.0) % 360.0).astype(int), 0, 359)
            xs = np.indices(lat.shape)[1][m] - lat.shape[1] / 2; ys = np.indices(lat.shape)[0][m] - lat.shape[0] / 2
            w = np.clip(1.0 - np.hypot(xs / (lat.shape[1] / 2), ys / (lat.shape[0] / 2)), 0.05, 1.0)   # centre-weighted
            for k in range(12):
                np.add.at(acc[k], (i, j), w * Pm[k][m])
            np.add.at(wsum, (i, j), w)
            print(name, f"{time.time() - t0:.0f}s", flush=True)
    rain = np.where(wsum > 0, acc / np.maximum(wsum, 1e-9), np.nan)
    glat = 89.5 - np.arange(180); glon = -179.5 + np.arange(360)
    # two-pass WTG omega: smooth the (filled) model rain over SMOOTH_KM, wrapping in longitude
    filled = np.where(np.isfinite(rain), rain, 0.0)
    om = np.zeros_like(filled)
    for k in range(12):
        sig_lat = SMOOTH_KM / 111.2
        Ps = ndi.gaussian_filter(filled[k], (sig_lat, sig_lat), mode=("nearest", "wrap"))   # ~1,000 km (lon widens poleward)
        om[k] = OMEGA_MAX * np.clip(1.0 - Ps / P0, 0.0, 1.0)
    om = np.where(np.isfinite(rain), om, np.nan)
    np.savez_compressed(out, rain=rain.astype(np.float32), omega_wtg=om.astype(np.float32), lat=glat, lon=glon,
                        params=sys.argv[1], cell_km=cell)
    print("covered", int(np.isfinite(rain[0]).sum()), "of 64800 1-deg cells;", out)


if __name__ == "__main__":
    main()
