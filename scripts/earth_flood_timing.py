"""Groundwork diagnostic: does the atlas's own river model put the floods in the right months on Earth?

The freight network's monthly river flow (polity.seasons.fields runoff -> polity.transport.river_network/catchments ->
polity.seasons.basin_flow, the code the fantasy map uses) is run on the Earth harvest window with WorldClim 2.1 and
Natural Earth navigable rivers, and compared with RivDIS gauge climatologies where cached (Aswan, Hit, Mosul).
A flood-timing driver for a floodplain rule is only computable on the fantasy map if this timing is right on Earth.
Nothing is fitted or changed."""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import land_people_earth as L
from polity import seasons as S, transport as X
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/flood_basin_irrigation_20261113'
POINTS = {'Nile at Aswan': (24.09, 32.90), 'Euphrates at Hit': (33.64, 42.83), 'Tigris at Mosul': (36.34, 43.13),
          'Yellow River at Huayuankou': (34.91, 113.66), 'Indus at Kotri': (25.36, 68.31), 'Niger at Dire': (16.27, -3.40), 'Ganges at Farakka': (24.81, 87.93)}
LITERATURE_PEAK = {'Yellow River at Huayuankou': [7, 8], 'Indus at Kotri': [7, 8], 'Niger at Dire': [10, 11, 12], 'Ganges at Farakka': [8, 9]}


def gauges():
    seas = json.loads((ROOT / 'output/flood_basin_seasonality_20261113/results.json').read_text())['rows']
    out = {('Nile at Aswan' if r['id'] == 'aswan' else 'Euphrates at Hit'): np.array(r['mean_monthly_flow_m3s']) for r in seas if r['id'] in ('aswan', 'hit')}
    import csv, collections
    by = collections.defaultdict(list)
    for row in csv.DictReader(open(ROOT / 'output/tigris_gauge_20261114/gauge_monthly.csv')):
        if row['station'] == 'mosul': by[int(row['date'][5:7])].append(float(row['monthly_mean_m3s']))
    out['Tigris at Mosul'] = np.array([np.mean(by[m]) for m in range(1, 13)]); return out


def main():
    rs, cs = L.window_slices()
    T = np.stack([L.wc('tavg', m)[rs, cs] for m in range(1, 13)]); P = np.stack([L.wc('prec', m)[rs, cs] for m in range(1, 13)])
    Tx = np.stack([L.wc('tmax', m)[rs, cs] for m in range(1, 13)]); Tn = np.stack([L.wc('tmin', m)[rs, cs] for m in range(1, 13)])
    land = np.isfinite(T).all(0) & np.isfinite(P).all(0); shape = land.shape
    lat = L.WINDOW['lat'][1] - (np.arange(shape[0]) + .5) / L.RES; lon = L.WINDOW['lon'][0] + (np.arange(shape[1]) + .5) / L.RES
    LAT = np.broadcast_to(lat[:, None], shape)
    f = S.fields(np.nan_to_num(T), np.nan_to_num(Tx), np.nan_to_num(Tn), np.nan_to_num(P), LAT)
    runoff = np.where(land, f['runoff'], 0.0); print('runoff done', flush=True)
    nav, _ = L.river_masks(shape); nav = nav.reshape(shape[0], L.SUB, shape[1], L.SUB).any((1, 3)) & land
    elev = np.nan_to_num(L.wc('elev')[rs, cs]); cell_km = L.KM_DEG / L.RES
    basin, n, steps = X.river_network(nav, land, ~land, elev); catchment = X.catchments(basin, land, cell_km)
    flow = S.basin_flow(runoff, catchment, n); print('basins', n, flush=True)
    obs = gauges(); rows = {}
    for name, (la, lo) in POINTS.items():
        r, c = int((L.WINDOW['lat'][1] - la) * L.RES), int((lo - L.WINDOW['lon'][0]) * L.RES)
        win = basin[max(r - 6, 0):r + 7, max(c - 6, 0):c + 7]; ids, counts = np.unique(win[win > 0], return_counts=True)
        if not len(ids): rows[name] = dict(basin=None); continue
        b = int(ids[counts.argmax()]); q = flow[:, b]
        row = dict(basin=b, catchment_cells=int((catchment == b).sum()), river_cells=int((basin == b).sum()), model_flow_index=q.round(4).tolist(), model_peak_month=int(q.argmax()) + 1,
                   model_months_above_mean=[m + 1 for m in range(12) if q[m] > 1])
        if name in obs:
            g = obs[name] / obs[name].mean(); row.update(gauge_flow_index=g.round(4).tolist(), gauge_peak_month=int(g.argmax()) + 1, correlation=float(np.corrcoef(q, g)[0, 1]),
                                                     peak_shift_months=int((q.argmax() - g.argmax() + 6) % 12 - 6))
        else:
            row.update(literature_peak_months=LITERATURE_PEAK[name], peak_in_literature_window=bool(int(q.argmax()) + 1 in LITERATURE_PEAK[name]))
        rows[name] = row; print(name, {k: v for k, v in row.items() if 'index' not in k}, flush=True)
    write(OUT / 'flood_timing.json', dict(status='diagnostic_only_no_fit', model='polity.seasons.fields runoff, polity.transport.river_network + catchments (150 km), polity.seasons.basin_flow (no travel lag)',
        inputs=dict(worldclim='wc2.1_5m tavg/tmax/tmin/prec/elev', rivers='Natural Earth 10m centerlines, scalerank <= navigable rank'), producer_sha256=sha(Path(__file__)), rows=rows))


if __name__ == '__main__':
    main()
