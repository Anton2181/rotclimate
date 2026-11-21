"""Herders and farmers layer (calibration/herders_20261120/plan_v2.json, adopted 20 Nov 2026: blind Spearman 0.42 vs -0.06).

Herding share of food = b + a x clip((240 - LGP) / 210, 0, 1), LGP the map's growing-season days (raw / corrected harvest),
averaged over ~27 km as on Earth (3 x 3 cells of 5 arc-min). Includes livestock kept by farmers (Ethnographic Atlas definition).

    .venv/bin/python -I scripts/herders_layer.py [--publish]
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
DATA = ROOT / 'atlases/earth_fit/data'; OUT = ROOT / 'output/herders_20261120'
SPEC = json.loads((OUT / 'v2_dev.json').read_text())['chosen']
STOPS = ['#2f7d4f', '#8fb86a', '#e8dc9a', '#d9a24f', '#a8552d']
LAYER = dict(id='land_herding', label='Herders and farmers', kind='ramp', unit='% of food from livestock (Earth-calibrated)',
             vmin=0, vmax=60, stops=STOPS, group='Harvest',
             note='Share of food from livestock, from the length of the growing season: about 21 % where crops grow most of the year '
                  '(farmers keep animals too), rising to about 54 % where the season is a month or shorter. Above 50 %: mainly herders. '
                  'Fitted on 546 societies of the Ethnographic Atlas (Old World north of the equator) and tested blind on 145 African '
                  'societies south of the equator (rank correlation 0.42; the earlier grazing-based share scored -0.06). Ethnographic '
                  'present (around 1900), used as the environment-driven split; the grazing allowance and population are unchanged.')


from polity.herding import share  # noqa: E402  (one rule for the layer and the per-polity statistics)


def render(h, land, meta, path):
    import matplotlib.colors as mc
    from rotclimate.geography import source_layers
    cmap = mc.LinearSegmentedColormap.from_list('h', STOPS); rgb = cmap(np.clip(h / 0.6, 0, 1))[..., :3]
    img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
    px = np.array(img); coast = source_layers()['land']; px[~coast] = [214, 227, 240]
    Image.fromarray(px).save(path, 'WEBP', quality=88, method=4)


def main(publish):
    from population.export import decode_harvest
    meta = json.loads((DATA / 'atlas.json').read_text()); res = {}
    for mode, folder in (('raw', DATA), ('corrected', DATA / 'corrected')):
        hm, hf = decode_harvest(folder); lgp = hf['lgp_days']; land = np.isfinite(lgp) & (hf['food_capacity'] >= 0)
        from rotclimate.geography import source_layers
        L = source_layers()['land']; h0, w0 = lgp.shape
        land = L[(np.arange(h0) * L.shape[0] // h0)][:, (np.arange(w0) * L.shape[1] // w0)]
        cell_km = meta['width'] / w0 * meta['mi_per_px'] * 1.609344
        h = share(lgp, land, cell_km)
        np.savez_compressed(OUT / f'herding_{mode}.npz', herding=h.astype(np.float32))
        render(h, land, meta, OUT / f'herding_{mode}.webp')
        res[mode] = dict(mean_share_land=float(h[land].mean()), mainly_herders_land=float((h[land] > 0.5).mean()),
                         over_40pct_land=float((h[land] > 0.4).mean()))
        if publish:
            (folder / 'land_herding.webp').write_bytes((OUT / f'herding_{mode}.webp').read_bytes())
    if publish:
        for layers, file in ((meta['layers'], 'land_herding.webp'), (meta['corrected_climate']['layers'], 'corrected/land_herding.webp')):
            layers[:] = [l for l in layers if l['id'] != 'land_herding']
            i = next((k for k, l in enumerate(layers) if l['id'] == 'land_pastoral_capacity'), len(layers) - 1) + 1
            layers.insert(i, dict(LAYER, file=file))
        (DATA / 'atlas.json').write_text(json.dumps(meta))
    (OUT / 'layer_summary.json').write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main('--publish' in sys.argv)
