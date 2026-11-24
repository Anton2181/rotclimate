"""Convert the NCEP/NCAR Reanalysis 1 monthly long-term-mean precipitable water (whole column, 2.5 deg;
NOAA PSL, public domain) into a numpy cache for Earth regional cases (e116: observed humidity at land map edges).

    curl -o data/cache/earth/ncep/pr_wtr.mon.ltm.nc \
        https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface/pr_wtr.mon.ltm.nc
    python3 -I scripts/build_ncep_pw.py        # needs h5py (tooling only; the model reads the .npz)
"""
from pathlib import Path
import numpy as np
import h5py
ROOT = Path(__file__).resolve().parents[1]
src, dst = ROOT / "data/cache/earth/ncep/pr_wtr.mon.ltm.nc", ROOT / "data/cache/earth/ncep_pw_2p5.npz"
with h5py.File(src, "r") as f:
    pw = np.asarray(f["pr_wtr"][...], np.float32); lat = np.asarray(f["lat"][...], float); lon = np.asarray(f["lon"][...], float)
pw = np.maximum(pw, 0.0)
np.savez_compressed(dst, pw=pw, lat=lat, lon=lon)
print(dst, pw.shape, float(pw.min()), float(pw.max()))
