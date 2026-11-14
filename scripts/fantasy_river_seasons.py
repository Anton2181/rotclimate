"""Diagnostic (owner question, 14 Nov 2026): why do all fantasy rivers flood in winter?

1. Climate: month of maximum rain over land, and the share of land with a summer rain maximum.
2. Physical rivers: monthly runoff (polity.seasons.fields, with snow) routed down the full-resolution simulated drainage
   (rotclimate.routing Priority-Flood over the eroded terrain) to every river mouth; peak month of the largest rivers.
3. Comparison with the network proxy (mean runoff within 150 km of each drawn navigable river) used for the floodplain rule.
Months are counted from the winter-solstice month (0). No atlas file is changed."""
import copy, json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.export import climate_arrays, surface_months
from polity import seasons as S
from rotclimate import routing as R
from rotclimate.geography import source_layers
from settlement_locations_earth import sha, write

DATA = ROOT / 'atlases/earth_fit/data'; OUT = ROOT / 'output/fantasy_floodplain_20261114'


def main():
    original = json.loads((DATA / 'atlas.json').read_text()); meta = copy.deepcopy(original)
    for k in ('arrays', 'lapse12', 'cell_px', 'harvest'): meta[k] = original['corrected_climate'][k]
    arrays = climate_arrays(DATA / 'corrected', meta); t, p, d, lat = surface_months(meta, arrays)
    L = source_layers(); land_src = L['land'].astype(bool); H, W = land_src.shape; h, w = t.shape[1:]
    land = ndi.zoom(land_src.astype(float), (h / H, w / W), order=1) > .5
    pmax = p.argmax(0); share_max = {str(m): float(np.mean(pmax[land] == m)) for m in range(12)}
    summer = p[5:9].sum(0) / np.maximum(p.sum(0), 1e-9)                                  # months 5-8 after the solstice
    lat_band = {f'{a}-{a + 5}': float(np.mean(summer[land & (lat >= a) & (lat < a + 5)])) for a in range(20, 60, 5) if (land & (lat >= a) & (lat < a + 5)).any()}
    f = S.fields(t, t + d / 2, t - d / 2, p, lat, meta['world']['tilt']); runoff = np.where(land, f['runoff'], 0.0)
    terrain = meta['world']['terrain_file']; tier_tops = meta['world']['tier_tops']; width_mi = meta['width'] * meta['mi_per_px']
    z, landR, rivers = R.surface(tier_tops, terrain); level = R.lake_levels(terrain); through = ~landR & (level > 0); net = landR | through
    recv, order = R._flood(np.where(landR, z, np.where(through, level, -1e9)), net, R.NB)
    _, (iy, ix) = ndi.distance_transform_edt(~land, return_indices=True)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); coords = [(yy + .5) * h / H - .5, (xx + .5) * w / W - .5]
    up = lambda a: ndi.map_coordinates(a[iy, ix], coords, order=1, mode='nearest')
    annual = R._accumulate(order, recv, np.where(landR, up(runoff.sum(0)), 0.0).ravel())
    outlets = np.flatnonzero((recv < 0) & landR.ravel()); top = outlets[np.argsort(-annual[outlets])[:15]]
    monthly = np.zeros((12, len(top)))
    for m in range(12):
        monthly[m] = R._accumulate(order, recv, np.where(landR, up(runoff[m]), 0.0).ravel())[top]; print('month', m, flush=True)
    area = R._accumulate(order, recv, landR.ravel().astype(float))[top]
    rows = []
    for k, c in enumerate(top):
        q = monthly[:, k]; idx = q / max(q.mean(), 1e-12); y, x = divmod(int(c), W)
        rows.append(dict(mouth_row=y, mouth_col=x, catchment_share_of_land=float(area[k] / landR.sum()), flow_index=idx.round(3).tolist(), peak_month=int(q.argmax()),
                         months_above_mean=[m for m in range(12) if idx[m] > 1], summer_share_of_flow=float(q[5:9].sum() / max(q.sum(), 1e-12))))
    out = dict(status='diagnostic', climate=dict(share_of_land_by_month_of_max_rain=share_max, land_mean_summer_rain_share=float(np.mean(summer[land])),
               land_share_summer_rain_over_40pct=float(np.mean(summer[land] > .4)), summer_rain_share_by_latitude=lat_band),
               runoff_share_by_month=[float(runoff[m].sum() / runoff.sum()) for m in range(12)], rivers=rows, producer_sha256=sha(Path(__file__)))
    write(OUT / 'river_seasons.json', out)
    print(json.dumps(out['climate'], indent=1)); print('runoff by month', [round(v, 3) for v in out['runoff_share_by_month']])
    for r in rows: print(r['catchment_share_of_land'].__round__(3), 'peak', r['peak_month'], 'above', r['months_above_mean'], 'summer flow %.2f' % r['summer_share_of_flow'])


if __name__ == '__main__':
    main()
