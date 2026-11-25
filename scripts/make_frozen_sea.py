"""e129: winter-frozen sea fraction (0-1) on the WOA 1-degree grid, from the WOA18 monthly sea-surface
temperature: the share of a 4-month winter in which the surface sits at the freezing point (<= -1.0 C).
Seas WOA leaves blank poleward of 70 deg (the Arctic pack) count as frozen. Writes a derived field to
data/cache/earth/frozen_sea_1deg.npz (ignored; never redistribute). Usage: make_frozen_sea.py WOA_SST_NPZ"""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
z = np.load(sys.argv[1])
sst, lat, lon = z['sst'], z['lat'], z['lon']
n = np.sum(np.nan_to_num(sst, nan=99.0) <= -1.0, axis=0)
frozen = np.clip(n / 4.0, 0.0, 1.0)
blank = np.all(~np.isfinite(sst), axis=0) & (np.abs(lat)[:, None] >= 70.0)
frozen = np.where(blank, 1.0, frozen)
out = ROOT / 'data/cache/earth/frozen_sea_1deg.npz'
np.savez_compressed(out, frozen=frozen.astype(np.float32), lat=lat, lon=lon)
print(out, 'frozen share of ocean cells %.3f' % frozen[np.isfinite(sst[0]) | blank].mean())
