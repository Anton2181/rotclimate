"""Exploration (development region only): does HID 1900 irrigated area along arid rivers track the river's discharge?
Discharge = WorldClim runoff (the climate model's own rule, rotclimate.routing.runoff_from_months) routed over ETOPO 60"."""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import numpy as np
from scipy import ndimage as ndi
import irrigation_reach_d2b as D
import land_people_earth as E
from rotclimate import routing as R
t0 = time.time(); reg = sys.argv[1] if len(sys.argv) > 1 else 'development'; ws = D.REGIONS[reg]
PADDEG = 8.0                                                                # route over a wider domain so basins are whole
w = dict(lat=(max(ws['lat'][0] - PADDEG, -56.0), min(ws['lat'][1] + PADDEG, 80.0)), lon=(ws['lon'][0] - PADDEG, ws['lon'][1] + PADDEG))
D.REGIONS[reg + '_wide'] = w
z = D.etopo(reg + '_wide').astype(float); H, W = z.shape
nav, stream = D.rivers(reg + '_wide', z.shape); river = nav | stream
r0, r1 = int(round((90 - w['lat'][1]) * 12)), int(round((90 - w['lat'][0]) * 12)); c0, c1 = int(round((w['lon'][0] + 180) * 12)), int(round((w['lon'][1] + 180) * 12))
T = np.stack([E.wc('tavg', m)[r0:r1, c0:c1] for m in range(1, 13)]); P = np.stack([E.wc('prec', m)[r0:r1, c0:c1] for m in range(1, 13)])
land5 = np.isfinite(T).all(0) & np.isfinite(P).all(0)
days = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])[:, None, None]
ro5 = np.where(land5, R.runoff_from_months(np.nan_to_num(T), np.nan_to_num(P), days), 0.0)
up = lambda a: np.repeat(np.repeat(a, 5, 0), 5, 1)
land = up(land5); ro = up(ro5)
lab, n = ndi.label(~land); size = np.bincount(lab.ravel())
lake = (~land) & (size[lab] < 30000) & (lab > 0)                           # WorldClim masks lakes (Nasser, Tana): flow passes through
land = land | lake; print('lake cells', int(lake.sum()))
lat1 = w['lat'][1] - (np.arange(H) + 0.5) / 60.0
area = (1852.0 ** 2) * np.cos(np.radians(lat1))[:, None] * np.ones((1, W))
src = ro / 1000.0 * area / (365.25 * 86400.0)
recv, order = R._flood(np.where(land, np.where(river, z - R.BURN_M, z), -1e9), land, R.NB)   # stream burning, as rotclimate.routing
q = R._accumulate(order, recv, src.ravel()).reshape(H, W)
q_r = np.where(river, ndi.maximum_filter(q, 3), 0.0)                       # river cell discharge (flow paths may sit off the NE line)
qn = np.zeros((H, W), np.float32)
band, pad = 240, 60
for b0 in range(0, H, band):
    lo, hi = max(b0 - pad, 0), min(b0 + band + pad, H)
    _, (iy, ix) = ndi.distance_transform_edt(~river[lo:hi], return_indices=True)
    s = slice(b0 - lo, b0 - lo + min(band, H - b0)); qn[b0:b0 + min(band, H - b0)] = q_r[lo:hi][iy, ix][s]
q5w = np.median(qn.reshape(H // 5, 5, W // 5, 5), axis=(1, 3))
oi, oj = int(round((w['lat'][1] - ws['lat'][1]) * 12)), int(round((ws['lon'][0] - w['lon'][0]) * 12))
q5 = q5w[oi:oi + int(round((ws['lat'][1] - ws['lat'][0]) * 12)), oj:oj + int(round((ws['lon'][1] - ws['lon'][0]) * 12))]
(ROOT / "output/irrigation_reach_d2b").mkdir(parents=True, exist_ok=True); np.savez_compressed(ROOT / f"output/irrigation_reach_d2b/discharge_{reg}.npz", q5=q5.astype(np.float32))
f = dict(np.load(ROOT / f'output/irrigation_reach_d2b/fields_{reg}.npz'))
arid = f['land'] & (f['dmin'] <= 30) & (f['ai'] < 0.2)
bins = [0, 3, 10, 30, 100, 300, 1000, 1e9]
print(f'{reg}: routed in {time.time() - t0:.0f}s')
for a, b in zip(bins[:-1], bins[1:]):
    m = arid & (q5 >= a) & (q5 < b)
    hid = (f['hid'] * f['area'])[m].sum(); mod = (f['L6_H10'] * f['area'])[m].sum(); mod5 = (f['L6_H5'] * f['area'])[m].sum()
    print(f'Q {a:>6g}-{b:<6g} m3/s: cells {m.sum():6d}  HID {hid:8.0f} km2  rule(H10) {mod:8.0f}  rule(H5) {mod5:8.0f}  ratio {mod / max(hid, 1):6.2f}')

lat5 = ws['lat'][1] - (np.arange(H // 5) + 0.5) / 12; lon5 = ws['lon'][0] + (np.arange(W // 5) + 0.5) / 12
for name, (la, lo) in {'Nile Aswan': (24.1, 32.9), 'Nile Cairo': (30.05, 31.25), 'Euphrates Hit': (33.6, 42.8), 'Tigris Baghdad': (33.3, 44.4), 'Niger Timbuktu': (16.8, -3.0)}.items():
    i, j = int((ws['lat'][1] - la) * 12), int((lo - ws['lon'][0]) * 12)
    print(f'{name:16s} Q5 {q5[i-2:i+3, j-2:j+3].max():8.0f} m3/s')
