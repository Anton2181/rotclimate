"""e150: snow-free land surface albedo from the NCEP/NCAR Reanalysis 1 monthly long-term means of surface shortwave
(upward / downward), regridded from the T62 Gaussian grid to a regular 2-degree grid.

    curl -o data/cache/earth/ncep/dswrf.sfc.mon.ltm.nc \
        https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface_gauss/dswrf.sfc.mon.ltm.nc
    curl -o data/cache/earth/ncep/uswrf.sfc.mon.ltm.nc \
        https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface_gauss/uswrf.sfc.mon.ltm.nc
    python3 -I scripts/build_ncep_albedo.py     # needs h5py (tooling only; the model reads the .npz)
The background albedo is the lowest monthly albedo among months with >= 80 W m-2 of sunshine (snow is the model's own).
"""
from pathlib import Path
import numpy as np
import h5py
ROOT = Path(__file__).resolve().parents[1]
def read(name):
    with h5py.File(ROOT / f"data/cache/earth/ncep/{name}.sfc.mon.ltm.nc", "r") as f:
        v = f[name]; a = np.asarray(v[...], np.float64)
        sf = v.attrs.get("scale_factor"); ao = v.attrs.get("add_offset")
        if sf is not None: a = a * float(np.ravel(sf)[0]) + (float(np.ravel(ao)[0]) if ao is not None else 0.0)
        return a, np.asarray(f["lat"][...], float), np.asarray(f["lon"][...], float)
dn, lat, lon = read("dswrf"); up, _, _ = read("uswrf")
alb = np.where(dn >= 80.0, up / np.maximum(dn, 1e-6), np.nan)
bg = np.nanmin(alb, axis=0)                       # [lat, lon], Gaussian lats north -> south
bg = np.where(np.isfinite(bg), bg, np.nanmax(np.where(dn > 1, up / np.maximum(dn, 1e-6), np.nan), axis=0))
rlat = np.arange(89.0, -89.1, -2.0); order = np.argsort(lat)
reg = np.stack([np.interp(rlat, lat[order], bg[order, j]) for j in range(len(lon))], axis=1)
dst = ROOT / "data/cache/earth/ncep_albedo_2deg.npz"
np.savez_compressed(dst, albedo=reg.astype(np.float32), lat=rlat, lon=lon)
print(dst, reg.shape, float(np.nanmin(reg)), float(np.nanmax(reg)), "lon step", lon[1] - lon[0])
