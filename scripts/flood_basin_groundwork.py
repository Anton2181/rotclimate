"""Groundwork for a flood-basin irrigation rule: how much low land lies beside the Nile in the terrain data.

Diagnostic only. Height above the nearest mapped river (HAND) from ETOPO 60", by distance band, in the Nile
valley and delta, compared with the irrigable area the current rules give. No model is changed or fitted.
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import land_people_earth as L
from arable_slope_earth import etopo_window

OUT = ROOT / 'output/flood_basin_irrigation_20261113'
BOXES = {'Nile delta': (30.0, 31.6, 29.5, 32.5), 'Nile valley': (24.0, 30.0, 30.4, 33.2), 'Lower Mesopotamia': (30.0, 34.0, 43.5, 48.0)}

if __name__ == '__main__':
    shape = (int((L.WINDOW['lat'][1] - L.WINDOW['lat'][0]) * L.RES), int((L.WINDOW['lon'][1] - L.WINDOW['lon'][0]) * L.RES))
    nav, stream = L.river_masks(shape); z = etopo_window().astype(float); n = L.RES * L.SUB; out = {}
    grids = {k: np.load(ROOT / f'output/land_people/{k}/earth.npz') for k in ('earth', 'earth_deltas') if (ROOT / f'output/land_people/{k}/earth.npz').exists()}
    for name, (la0, la1, lo0, lo1) in BOXES.items():
        r0, r1 = int((L.WINDOW['lat'][1] - la1) * n), int((L.WINDOW['lat'][1] - la0) * n); c0, c1 = int((lo0 - L.WINDOW['lon'][0]) * n), int((lo1 - L.WINDOW['lon'][0]) * n)
        pad = 60; rs, cs = slice(max(r0 - pad, 0), r1 + pad), slice(max(c0 - pad, 0), c1 + pad)
        lat = L.WINDOW['lat'][1] - (np.arange(rs.start, rs.stop) + 0.5) / n; samp = (L.KM_DEG / n, L.KM_DEG * np.cos(np.radians(lat.mean())) / n)
        river = nav[rs, cs]; zz = z[rs, cs]
        dist, (iy, ix) = ndi.distance_transform_edt(~river, sampling=samp, return_indices=True)
        hand = zz - zz[iy, ix]; inner = (slice(r0 - rs.start, r1 - rs.start), slice(c0 - cs.start, c1 - cs.start))
        land = zz[inner] > 0; d = dist[inner]; hnd = hand[inner]; cell = samp[0] * samp[1]
        row = dict(land_km2=float(land.sum() * cell), navigable_river_cells=int(river[inner].sum()))
        for h in (2, 5, 10):
            for km in (10, 30, 100):
                row[f'hand_le_{h}m_within_{km}km_km2'] = float((land & (hnd <= h) & (d <= km)).sum() * cell)
        for k, g in grids.items():
            LA, LO = np.meshgrid(g['lat'], g['lon'], indexing='ij'); m = (LA > la0) & (LA < la1) & (LO > lo0) & (LO < lo1) & g['land']
            c5 = (L.KM_DEG / L.RES) ** 2 * np.cos(np.radians(LA))
            row[f'model_irrigated_equivalent_km2_{k}'] = float((g['irr'] * c5)[m].sum()); row[f'model_capacity_m_{k}'] = float(np.nansum(g['capacity'][m] * c5[m]) / 1e6)
        out[name] = row; print(name, {k: round(v) if v > 50 else round(v, 2) for k, v in row.items()}, flush=True)
    (OUT / 'groundwork.json').write_text(json.dumps(dict(status='diagnostic_only_no_fit', source='ETOPO 2022 60 arc-second; Natural Earth navigable rivers (scalerank <= 4)', boxes=BOXES, results=out), indent=1) + '\n')
