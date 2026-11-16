"""Forest map (workstream C1b, adopted on Earth 7 Nov 2026: reports via calibration/geography_control_20261107/plan_C1.json):
forest share = 0.60 x clip((P/PET - 0.3)/0.2, 0, 1) x clip((GDD5 - 300)/300, 0, 1), P/PET with Hargreaves PET and GDD5 the
degree days above 5 C, from the atlas's own monthly climate (raw and corrected), on the planet's own tilt and calendar.
Earth: blind open-land RMSE 0.326 (REVEALS TW6, c. 250 BCE - 250 CE); population clearing not adopted.

    .venv/bin/python -I scripts/forest_map.py [--publish]
"""
import copy, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.export import climate_arrays, surface_months
from rotclimate.geography import source_layers
import land_people as LP
DATA = ROOT / 'atlases/earth_fit/data'; OUT = ROOT / 'output/forest_map_20261116'
STOPS = ['#f7f4e8', '#e4e9c7', '#c3d89e', '#93c07a', '#5f9f58', '#33793d', '#164f28']
LAYER = dict(id='land_forest', label='Forest (AD 200 potential)', kind='ramp', unit='% of land in forest, Earth-fitted (moisture x warmth)',
             vmin=0, vmax=60, stops=STOPS, group='Harvest',
             note='Forest share = 60 % x a moisture ramp (rain over potential evaporation 0.3 to 0.5) x a warmth ramp (degree days above 5 C, '
                  '300 to 600). Fitted on Earth against pollen-based land cover of the Roman period (REVEALS, Europe, c. 250 BCE - 250 CE; '
                  'blind open-land error 0.33). Potential cover: clearing for farms is not subtracted (it did not test better on Earth).')


def forest(mode):
    o = json.loads((DATA / 'atlas.json').read_text()); meta = copy.deepcopy(o); folder = DATA
    if mode == 'corrected':
        for k in ('arrays', 'lapse12', 'cell_px', 'harvest'): meta[k] = o['corrected_climate'][k]
        folder = DATA / 'corrected'
    a = climate_arrays(folder, meta); t, p, d, lat = surface_months(meta, a)
    tilt = o['world']['tilt']; ws = float(o.get('solstice_day', 22.0))
    shp = t.shape[1:]
    PET = LP.hargreaves(t.reshape(12, -1), np.maximum(d, 0.1).reshape(12, -1), LP.sunlight_top(np.broadcast_to(lat, shp).ravel(), tilt, ws)).reshape(t.shape)
    ai = p.sum(0) / np.maximum(PET.sum(0), 1.0); gdd = np.sum(np.maximum(t - 5.0, 0.0), 0) * LP.DAYS
    f = 0.60 * np.clip((ai - 0.3) / 0.2, 0, 1) * np.clip((gdd - 300.0) / 300.0, 0, 1)
    return f, ai, gdd, o


def render(f, o, path):
    import matplotlib.colors as mc
    cmap = mc.LinearSegmentedColormap.from_list('f', STOPS); rgb = cmap(np.clip(f / 0.60, 0, 1))[..., :3]
    img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((o['width'], o['height']), Image.Resampling.NEAREST)
    px = np.array(img); coast = source_layers()['land']; px[~coast] = [214, 227, 240]
    Image.fromarray(px).save(path, 'WEBP', quality=88, method=4)


def main(publish):
    OUT.mkdir(parents=True, exist_ok=True); res = {}
    for mode in ('raw', 'corrected'):
        f, ai, gdd, o = forest(mode)
        land = source_layers()['land']; h, w = f.shape
        lm = land[(np.arange(h) * land.shape[0] // h)][:, (np.arange(w) * land.shape[1] // w)]
        res[mode] = dict(mean_forest_share_land=float(f[lm].mean()), share_land_over_30pct=float((f[lm] > 0.3).mean()), share_land_zero=float((f[lm] <= 0.01).mean()))
        np.savez_compressed(OUT / f'forest_{mode}.npz', forest=f.astype(np.float32), aridity=ai.astype(np.float32), gdd5=gdd.astype(np.float32))
        render(f, o, OUT / f'forest_{mode}.webp')
        if publish:
            target = DATA / ('corrected/' if mode == 'corrected' else '') / 'land_forest.webp'; target.write_bytes((OUT / f'forest_{mode}.webp').read_bytes())
    if publish:
        meta = json.loads((DATA / 'atlas.json').read_text())
        for layers, file in ((meta['layers'], 'land_forest.webp'), (meta['corrected_climate']['layers'], 'corrected/land_forest.webp')):
            layers[:] = [l for l in layers if l['id'] != 'land_forest']
            i = next((k for k, l in enumerate(layers) if l['id'] == 'land_npp'), len(layers) - 1) + 1
            layers.insert(i, dict(LAYER, file=file))
        (DATA / 'atlas.json').write_text(json.dumps(meta))
    (OUT / 'summary.json').write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main('--publish' in sys.argv)
