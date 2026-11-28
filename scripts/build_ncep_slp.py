"""e140/e141: NCEP/NCAR reanalysis monthly long-term means on the 2.5 degree grid: sea-level pressure (e140) and
500 hPa vertical velocity omega (e141).

    curl -o data/cache/earth/ncep/slp.mon.ltm.nc \
        https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface/slp.mon.ltm.nc
    curl -o data/cache/earth/ncep/omega.mon.ltm.nc \
        https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/pressure/omega.mon.ltm.nc
    python3 -I scripts/build_ncep_slp.py        # needs h5py (tooling only; the model reads the .npz)
"""
from pathlib import Path
import numpy as np
import h5py
ROOT = Path(__file__).resolve().parents[1]
src, dst = ROOT / "data/cache/earth/ncep/slp.mon.ltm.nc", ROOT / "data/cache/earth/ncep_slp_2p5.npz"
with h5py.File(src, "r") as f:
    v = f["slp"]; slp = np.asarray(v[...], np.float32)
    sf = v.attrs.get("scale_factor"); ao = v.attrs.get("add_offset")
    if sf is not None: slp = slp * float(np.ravel(sf)[0]) + (float(np.ravel(ao)[0]) if ao is not None else 0.0)
    lat = np.asarray(f["lat"][...], float); lon = np.asarray(f["lon"][...], float)
np.savez_compressed(dst, slp=slp, lat=lat, lon=lon)
print(dst, slp.shape, float(slp.min()), float(slp.max()))
src = ROOT / "data/cache/earth/ncep/omega.mon.ltm.nc"
if src.exists():
    dst = ROOT / "data/cache/earth/ncep_omega500_2p5.npz"
    with h5py.File(src, "r") as f:
        k = list(np.asarray(f["level"][...], float)).index(500.0)
        om = np.asarray(f["omega"][:, k], np.float32)
        lat = np.asarray(f["lat"][...], float); lon = np.asarray(f["lon"][...], float)
    np.savez_compressed(dst, omega=om, lat=lat, lon=lon)
    print(dst, om.shape, float(om.min()), float(om.max()))
