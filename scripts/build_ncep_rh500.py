"""e152: NCEP/NCAR Reanalysis 1 long-term monthly mean relative humidity at 500 hPa (2.5 deg) -> npz cache.

Input  data/cache/earth/ncep/rhum/rhum.mon.ltm.nc (downloads.psl.noaa.gov, ncep.reanalysis.derived/pressure)
Output data/cache/earth/ncep_rh500.npz  (rh [12, 73, 144] percent, lat descending 90..-90, lon 0..357.5)
    .venv/bin/python -I scripts/build_ncep_rh500.py     # needs h5py (tooling only; the model reads the .npz)
"""
from pathlib import Path
import numpy as np
import h5py

ROOT = Path(__file__).resolve().parents[1]
with h5py.File(ROOT / "data/cache/earth/ncep/rhum/rhum.mon.ltm.nc", "r") as f:
    lev = list(np.asarray(f["level"][:]))
    rh = np.asarray(f["rhum"][:, lev.index(500.0)], float)
    lat = np.asarray(f["lat"][:], float)
rh = np.where(np.abs(rh) > 1e30, np.nan, rh)
assert rh.shape == (12, 73, 144) and lat[0] > lat[-1]
np.savez_compressed(ROOT / "data/cache/earth/ncep_rh500.npz", rh=rh.astype(np.float32), lat=lat)
print("rh500", np.nanmin(rh), np.nanmax(rh))
