"""Groundwork (diagnostic only): would a terrain + flood-timing basin rule inflate the North China Plain or Wei valley?

Extends flood_basin_groundwork.py to the two Han regions whose census the model already matches (the North China
Plain set FALLOW, so it is fitted). For each box: low land beside navigable rivers (HAND), the model's current
irrigated area and capacity, and how much rain falls in the river's flood months (land under a rain-fed crop
when the flood comes cannot be a flood basin). Flood months: Nile and Euphrates/Tigris from the cached gauges
(reports/TIGRIS_GAUGE_20261114.md); Yellow and Wei rivers from literature (summer monsoon flood, July-September),
not from a gauge. No model is changed or fitted.
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import land_people_earth as L
from arable_slope_earth import etopo_window

OUT = ROOT / 'output/flood_basin_irrigation_20261113'
BOXES = {'Nile delta': ((30.0, 31.6, 29.5, 32.5), (8, 9, 10)), 'Nile valley': ((24.0, 30.0, 30.4, 33.2), (8, 9, 10)),
         'Lower Mesopotamia': ((30.0, 34.0, 43.5, 48.0), (4, 5)), 'North China Plain': ((34.0, 40.0, 113.5, 119.5), (7, 8, 9)),
         'Wei valley': ((34.0, 35.0, 106.5, 110.5), (7, 8, 9))}
FLOOD_SOURCE = {'Nile delta': 'Aswan gauge (cached RivDIS page)', 'Nile valley': 'Aswan gauge (cached RivDIS page)', 'Lower Mesopotamia': 'Hit and Mosul gauges (cached RivDIS pages)',
                'North China Plain': 'literature: Yellow River summer flood season, not a gauge', 'Wei valley': 'literature: Wei summer flood season, not a gauge'}

if __name__ == '__main__':
    shape = (int((L.WINDOW['lat'][1] - L.WINDOW['lat'][0]) * L.RES), int((L.WINDOW['lon'][1] - L.WINDOW['lon'][0]) * L.RES))
    nav, stream = L.river_masks(shape); z = etopo_window().astype(float); n = L.RES * L.SUB; out = {}
    rs5, cs5 = L.window_slices(); P = np.stack([L.wc('prec', m)[rs5, cs5] for m in range(1, 13)])
    g = np.load(ROOT / 'output/land_people/earth/earth.npz'); LA, LO = np.meshgrid(g['lat'], g['lon'], indexing='ij'); c5 = (L.KM_DEG / L.RES) ** 2 * np.cos(np.radians(LA))
    for name, ((la0, la1, lo0, lo1), months) in BOXES.items():
        r0, r1 = int((L.WINDOW['lat'][1] - la1) * n), int((L.WINDOW['lat'][1] - la0) * n); c0, c1 = int((lo0 - L.WINDOW['lon'][0]) * n), int((lo1 - L.WINDOW['lon'][0]) * n)
        pad = 60; rs, cs = slice(max(r0 - pad, 0), r1 + pad), slice(max(c0 - pad, 0), c1 + pad)
        lat = L.WINDOW['lat'][1] - (np.arange(rs.start, rs.stop) + 0.5) / n; samp = (L.KM_DEG / n, L.KM_DEG * np.cos(np.radians(lat.mean())) / n)
        river = nav[rs, cs]; zz = z[rs, cs]
        dist, (iy, ix) = ndi.distance_transform_edt(~river, sampling=samp, return_indices=True)
        hand = zz - zz[iy, ix]; inner = (slice(r0 - rs.start, r1 - rs.start), slice(c0 - cs.start, c1 - cs.start))
        land = zz[inner] > 0; cell = samp[0] * samp[1]
        m = (LA > la0) & (LA < la1) & (LO > lo0) & (LO < lo1) & g['land']
        flood_rain = P[[k - 1 for k in months]][:, m].sum(0); annual = P[:, m].sum(0); w = c5[m]
        out[name] = dict(flood_months=list(months), flood_month_source=FLOOD_SOURCE[name], land_km2=float(land.sum() * cell),
            hand_le_5m_within_30km_km2=float((land & (hand[inner] <= 5) & (dist[inner] <= 30)).sum() * cell),
            model_irrigated_equivalent_km2=float((g['irr'] * c5)[m].sum()), model_capacity_m=float(np.nansum(g['capacity'][m] * w) / 1e6),
            rain_in_flood_months_mm=float(np.average(flood_rain, weights=w)), annual_rain_mm=float(np.average(annual, weights=w)),
            model_growing_period_days=float(np.average(np.nan_to_num(g['lgp_days'][m]), weights=w)))
        print(name, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in out[name].items()}, flush=True)
    (OUT / 'constraints.json').write_text(json.dumps(dict(status='diagnostic_only_no_fit', source='ETOPO 2022 60 arc-second; Natural Earth navigable rivers (scalerank <= 4); WorldClim 2.1 5m precipitation; output/land_people/earth/earth.npz',
        boxes={k: v[0] for k, v in BOXES.items()}, results=out), indent=1) + '\n')
