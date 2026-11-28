"""e152f: NCEP/NCAR Reanalysis 1 long-term monthly mean omega at 700 hPa (Pa/s, 2.5 deg) -> npz cache.

Input  data/cache/earth/ncep/omega.mon.ltm.nc (downloads.psl.noaa.gov, ncep.reanalysis.derived/pressure)
Output data/cache/earth/ncep_omega700.npz  (omega [12, 73, 144] Pa/s, lat descending 90..-90, lon 0..357.5)
    .venv/bin/python -I scripts/build_ncep_omega700.py     # needs h5py (tooling only; the model reads the .npz)
"""
from pathlib import Path
import numpy as np
import h5py

ROOT = Path(__file__).resolve().parents[1]
with h5py.File(ROOT / "data/cache/earth/ncep/omega.mon.ltm.nc", "r") as f:
    lev = list(np.asarray(f["level"][:]))
    v = f["omega"]
    om = np.asarray(v[:, lev.index(700.0)], float) * float(v.attrs.get("scale_factor", 1.0)) + float(v.attrs.get("add_offset", 0.0))
    lat = np.asarray(f["lat"][:], float)
om = np.where(np.abs(om) > 1e3, np.nan, om)
assert om.shape == (12, 73, 144) and lat[0] > lat[-1]
np.savez_compressed(ROOT / "data/cache/earth/ncep_omega700.npz", omega=om.astype(np.float32), lat=lat)
print("omega700", np.nanmin(om), np.nanmax(om))
