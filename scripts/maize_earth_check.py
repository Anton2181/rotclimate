"""WP6 maize Earth check declared in calibration/maize_20261116/plan.json.

    python3 -I scripts/maize_earth_check.py output/maize_20261116/mexico
T1 rank: model maize kcal/ha vs MapSPAM 2010 rain-fed maize physical area share; T2 coverage; T3 season start in central Mexico.
"""
import io, json, sys, zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.stats import spearmanr
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import land_people as LP
import land_people_earth as LE

out = Path(sys.argv[1]); d = np.load(out / 'earth.npz')
lat, lon, land = d['lat'], d['lon'], d['land']; km = np.nan_to_num(d['kcal_maize'])
Image.MAX_IMAGE_PIXELS = None
z = zipfile.ZipFile(ROOT / 'data/cache/mapspam2010/phys_area_geotiff.zip')
spam = np.array(Image.open(io.BytesIO(z.read('spam2010V2r0_global_A_MAIZ_R.tif'))), float)   # ha per 5' cell, global, rows from 90 N
spam[spam < 0] = 0.0
r0 = int(round((90 - lat[0] - 0.5 / 12) * 12)); c0 = int(round((lon[0] - 0.5 / 12 + 180) * 12))
S = spam[r0:r0 + len(lat), c0:c0 + len(lon)]
assert S.shape == km.shape, (S.shape, km.shape)
cell_ha = (LE.KM_DEG / 12) ** 2 * np.cos(np.radians(lat))[:, None] * 100.0
share = S / cell_ha
m = land & np.isfinite(km)
rho = float(spearmanr(km[m], share[m]).correlation)
cover = float(S[m & (km > 0)].sum() / max(S[m].sum(), 1e-9))
# T3: season start, central Mexican highlands, rain-fed (irr 0)
LAT2, LON2 = np.meshgrid(lat, lon, indexing='ij')
box = m & (LAT2 >= 19) & (LAT2 <= 21) & (LON2 >= -101) & (LON2 <= -97) & (km > 0)
LE.WINDOW.update(lat=(float(round(lat[-1] - 0.5 / 12)), float(round(lat[0] + 0.5 / 12))), lon=(float(round(lon[0] - 0.5 / 12)), float(round(lon[-1] + 0.5 / 12))))
rs, cs = LE.window_slices()
T = np.stack([LE.wc('tavg', k)[rs, cs] for k in range(1, 13)])[:, box]
P = np.stack([LE.wc('prec', k)[rs, cs] for k in range(1, 13)])[:, box]
D = np.stack([LE.wc('tmax', k)[rs, cs] - LE.wc('tmin', k)[rs, cs] for k in range(1, 13)])[:, box]
PET = LP.hargreaves(T, D, LP.sunlight_top(LAT2[box], LE.TILT, LE.WS_DAY))
S0 = np.zeros_like(T)
_, mask = LP.crop_yield(T, P, PET, S0, np.zeros(T.shape[1:]), LP.MAIZE)
start = []
for j in range(mask.shape[1]):
    mm = mask[:, j]
    if mm.any():
        st = [k for k in range(12) if mm[k] and not mm[k - 1]]
        start.append(st[0] + 1 if st else 1)
med = int(np.median(start)) if start else None
res = dict(T1_spearman=rho, T1_pass=rho >= 0.30, T2_coverage=cover, T2_pass=cover >= 0.80,
           T3_median_start_month=med, T3_cells=len(start), T3_pass=med in (5, 6),
           cells=int(m.sum()), maize_cells=int((m & (km > 0)).sum()), spam_rainfed_maize_mha=float(S[m].sum() / 1e6))
(out / 'maize_check.json').write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(res, indent=1))
