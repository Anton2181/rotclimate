"""Detailed forest, stage 2 (SCENARIO, placement untested; reports/FOREST_DETAIL_20261116.md).

Regional forest amount: the published Earth-tested layer (C1b; scripts/forest_map.py), unchanged in ~25 km neighbourhood means.
Within neighbourhoods, forest moves (declared rule, not fitted):
  * away from people on gentle land: preference exp(-H x flat / 30 per km2), flat = 1 - clip(slope / 8 deg), H = the release-4
    rural people (per km2);
  * towns: about 1 ha of cleared land per resident (fields, meadow, fallow), taken from the cheapest land nearby
    (distance x (1 + slope / 3 deg)), so clearings follow flat ground and valleys;
  * onto slopes: preference x (1 + 1.5 x clip(slope / 10 deg, 0, 1)) on height map v2.1 (926 x 2000);
  * tree line and cold limit: the warmth ramp recomputed at full resolution with a 6.5 K/km lapse to the fine terrain;
  * a fine pixel holds at most its own climate potential (1.0 x moisture ramp x warmth ramp).
Wet valley floors (slope < 0.3 deg, drainage area in the top 3 % of land, moisture ramp >= 0.5) are flagged as wet woodland / marsh.

    .venv/bin/python -I scripts/forest_detail_map.py
"""
import copy, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.export import climate_arrays, surface_months
from rotclimate.geography import source_layers
import land_people as LP

DATA = ROOT / 'atlases/earth_fit/data'; OUT = ROOT / 'output/forest_detail_20261116'
R4 = ROOT / 'output/settlement_release4_20261116/release3'
TERRAIN = ROOT / 'output/terrain_erosion_20261107/map_height_v21.npz'
H0, TOWN_SIGMA_KM, SLOPE_GAIN, NEIGH_KM, LAPSE, FLAT_DEG, HA_PER_RESIDENT = 30.0, 6.0, 1.5, 25.0, 6.5e-3, 8.0, 1.0
STOPS = ['#f7f4e8', '#e4e9c7', '#c3d89e', '#93c07a', '#5f9f58', '#33793d', '#164f28']


def up(a, shape, order=1):
    zy, zx = shape[0] / a.shape[0], shape[1] / a.shape[1]
    return ndi.zoom(np.asarray(a, float), (zy, zx), order=order, mode='nearest')[:shape[0], :shape[1]]


def build(mode):
    o = json.loads((DATA / 'atlas.json').read_text()); meta = copy.deepcopy(o); folder = DATA
    if mode == 'corrected':
        for k in ('arrays', 'lapse12', 'cell_px', 'harvest'): meta[k] = o['corrected_climate'][k]
        folder = DATA / 'corrected'
    a = climate_arrays(folder, meta); t, p, d, lat = surface_months(meta, a)
    tilt = o['world']['tilt']; ws = float(o.get('solstice_day', 22.0)); shp = t.shape[1:]
    pet = LP.hargreaves(t.reshape(12, -1), np.maximum(d, 0.1).reshape(12, -1), LP.sunlight_top(np.broadcast_to(lat, shp).ravel(), tilt, ws)).reshape(t.shape)
    moist = np.clip((p.sum(0) / np.maximum(pet.sum(0), 1.0) - 0.3) / 0.2, 0, 1)
    gdd = np.sum(np.maximum(t - 5.0, 0.0), 0) * LP.DAYS
    f_reg = np.load(OUT.parent / f'forest_map_20261116/forest_{mode}.npz')['forest']
    z = np.load(TERRAIN)['z'].astype(float); area = np.load(TERRAIN)['area'].astype(float); fine = z.shape
    land = np.asarray(Image.fromarray(source_layers()['land'].astype(np.uint8) * 255).resize((fine[1], fine[0]), Image.NEAREST)) > 127
    cell_km = o['width'] / shp[1] * o['mi_per_px'] * 1.609344; fkm = cell_km * shp[0] / fine[0]
    # warmth at full resolution: monthly temperature lapsed from the climate-grid elevation to the fine terrain
    dz = z - up(np.asarray(a['elev'], float), fine)
    tf = np.stack([up(t[m], fine) - LAPSE * dz for m in range(12)])
    warm = np.clip((np.sum(np.maximum(tf - 5.0, 0.0), 0) * LP.DAYS - 300.0) / 300.0, 0, 1)
    pot = up(moist, fine) * warm
    # people: rural (per km2) plus towns over a 3 km Gaussian
    f4 = np.load(R4 / f'placed_{mode}_fields.npz'); sites = json.loads((R4 / f'placed_{mode}_sites.json').read_text())['sites']
    rural = up(f4['rural_central'] / cell_km ** 2, fine)
    gy, gx = np.gradient(z, fkm * 1000.0); slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    flat = 1.0 - np.clip(slope / FLAT_DEG, 0, 1)                 # people clear gentle land first
    # towns: a cleared-land budget (HA_PER_RESIDENT) spent on the cheapest land nearby, cost = distance x (1 + slope / 3 deg)
    cleared = np.zeros(fine); px_km2 = fkm ** 2; rad = int(np.ceil(40.0 / fkm))
    for s, r in zip(sites, f4['residents_central']):
        y, x = min(fine[0] - 1, int(s['row'] * fine[0] / shp[0])), min(fine[1] - 1, int(s['column'] * fine[1] / shp[1]))
        n = int(round(r * HA_PER_RESIDENT / 100.0 / px_km2))
        if n < 1:
            continue
        y0, y1, x0, x1 = max(0, y - rad), min(fine[0], y + rad + 1), max(0, x - rad), min(fine[1], x + rad + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        cost = np.hypot(yy - y, xx - x) * (1 + slope[y0:y1, x0:x1] / 3.0) + (cleared[y0:y1, x0:x1] >= 0.999) * 1e3
        cost = np.where(land[y0:y1, x0:x1], cost, np.inf)
        order = np.argsort(cost, axis=None)[:n]; ok = np.isfinite(cost.ravel()[order])
        sub = cleared[y0:y1, x0:x1].ravel(); sub[order[ok]] = 1.0; cleared[y0:y1, x0:x1] = sub.reshape(y1 - y0, x1 - x0)
    cleared = ndi.gaussian_filter(cleared, 0.7)
    H = rural
    pref = np.exp(-H * flat / H0) * (1 + SLOPE_GAIN * np.clip(slope / 10.0, 0, 1)) * (1 - 0.9 * np.clip(cleared, 0, 1))
    reg = up(f_reg, fine); cap = np.minimum(1.0, pot)
    s_ = NEIGH_KM / fkm; m = land.astype(float)
    smooth = lambda v: ndi.gaussian_filter(v * m, s_) / np.maximum(ndi.gaussian_filter(m, s_), 1e-6)
    forest = np.minimum(cap, reg * pref / np.maximum(smooth(pref), 1e-6))
    for _ in range(4):                                          # restore the neighbourhood means, respecting the caps
        forest = np.minimum(cap, forest * smooth(reg) / np.maximum(smooth(forest), 1e-6))
    forest = np.where(land, forest, 0.0)
    a_land = area[land]; wet = land & (slope < 0.3) & (area >= np.percentile(a_land, 97)) & (up(moist, fine) >= 0.5)
    wet = ndi.binary_opening(wet, iterations=1) | (wet & ndi.binary_dilation(wet, iterations=1))
    # woodland mosaic (display): score = 0.83 x local standardised log-preference + 0.55 x smooth seeded noise (5 px);
    # a pixel is wood where the score exceeds the normal quantile of its neighbourhood's open share (share kept on average)
    from scipy.stats import norm
    lp = ndi.gaussian_filter(np.log(np.maximum(pref, 1e-4)), 1.2); s2 = 6.0 / fkm * 3
    mu = ndi.gaussian_filter(lp * m, s2) / np.maximum(ndi.gaussian_filter(m, s2), 1e-6)
    sd = np.sqrt(np.maximum(ndi.gaussian_filter((lp - mu) ** 2 * m, s2) / np.maximum(ndi.gaussian_filter(m, s2), 1e-6), 1e-6))
    zp = np.clip((lp - mu) / sd, -3, 3)
    noise = ndi.gaussian_filter(np.random.default_rng(20261116).standard_normal(fine), 5.0); noise = (noise - noise.mean()) / noise.std()
    score = 0.83 * zp + 0.55 * noise
    share = np.clip(ndi.gaussian_filter(forest * m, 2.0) / np.maximum(ndi.gaussian_filter(m, 2.0), 1e-6), 1e-4, 1 - 1e-4)
    woods = land & (score > norm.ppf(1 - share)) & (pot > 0.05)
    return dict(forest=forest, wet=wet, woods=woods, land=land, reg=np.where(land, reg, 0.0), H=H, slope=slope, pot=pot, fkm=fkm)


def render(r, path, field='forest'):
    import matplotlib.colors as mc
    cmap = mc.LinearSegmentedColormap.from_list('f', STOPS); rgb = cmap(np.clip(r[field] / 0.85, 0, 1))[..., :3]
    px = (rgb * 255).astype(np.uint8)
    if field == 'forest':
        px[r['wet']] = (np.array([118, 170, 160]) * 0.6 + px[r['wet']] * 0.4).astype(np.uint8)
    px[~r['land']] = [214, 227, 240]
    Image.fromarray(px).save(path)


def render_mosaic(r, path):
    px = np.zeros(r['land'].shape + (3,), np.uint8); px[:] = [236, 231, 205]
    dry = r['pot'] < 0.15; px[dry] = [240, 232, 208]
    px[r['woods']] = [52, 110, 60]
    px[r['wet'] & ~r['woods']] = [150, 190, 175]; px[r['wet'] & r['woods']] = [45, 120, 105]
    px[~r['land']] = [214, 227, 240]
    Image.fromarray(px).save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True); summary = {}
    for mode in ('raw', 'corrected'):
        r = build(mode); L = r['land']
        np.savez_compressed(OUT / f'forest_detail_{mode}.npz', forest=r['forest'].astype(np.float32), wet=r['wet'], woods=r['woods'])
        render(r, OUT / f'forest_detail_{mode}.png'); render_mosaic(r, OUT / f'woodland_mosaic_{mode}.png'); render(r, OUT / f'forest_regional_{mode}.png', 'reg')
        n = ndi.gaussian_filter(L.astype(float), 25 / r['fkm'])
        summary[mode] = dict(mean_forest_regional=float(r['reg'][L].mean()), mean_forest_detail=float(r['forest'][L].mean()),
            share_closed_over_60pct=float((r['forest'][L] > 0.6).mean()), share_open_under_10pct=float((r['forest'][L] < 0.1).mean()),
            wet_share=float(r['wet'][L].mean()), fine_km=float(r['fkm']),
            corr_forest_people=float(np.corrcoef(r['forest'][L], np.log1p(r['H'][L]))[0, 1]),
            corr_forest_slope=float(np.corrcoef(r['forest'][L], r['slope'][L])[0, 1]))
    (OUT / 'detail_summary.json').write_text(json.dumps(summary, indent=1)); print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
