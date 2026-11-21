"""Pastoral nomads layer (T9 N1, calibration/nomads_20261121/plan_n1.json; adopted: out-of-fold AUC 0.92 on 632
Ethnographic Atlas societies, 48 pastoral nomads).

p(pastoral nomads) = logistic(a + b (H - mean) / sd), H the map's herding share (scripts/herders_layer.py).

    .venv/bin/python -I scripts/nomads_layer.py [--publish]     # run after herders_layer.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
DATA = ROOT / 'atlases/earth_fit/data'
HERD = ROOT / 'output/herders_20261120'
OUT = ROOT / 'output/nomads_20261121'
FIT = json.loads((ROOT / 'calibration/nomads_20261121/n1_results.json').read_text())
STOPS = ['#f4efe2', '#e6c98a', '#d08a3e', '#9a4a22', '#5c2414']
LAYER = dict(id='land_nomads', label='Pastoral nomads', kind='ramp', unit='% chance herders here move with their herds (Earth-calibrated)',
             vmin=0, vmax=100, stops=STOPS, group='Harvest',
             note='Chance that the people here are pastoral nomads (nomadic or seminomadic, living mainly from herds), from the '
                  'herding share of food. Fitted on 632 Ethnographic Atlas societies (Old World and Africa; 48 pastoral nomads), '
                  'cross-validated by 10-degree tiles (AUC 0.92). Ethnographic present; population is unchanged.')


def probability(h):
    m = FIT['models']['P0']['coefficients']
    mu, sd = FIT['standardise']['H']
    return 1 / (1 + np.exp(-(m['const'] + m['H'] * (h - mu) / sd)))


def render(p, meta, path):
    import matplotlib.colors as mc
    from rotclimate.geography import source_layers
    rgb = mc.LinearSegmentedColormap.from_list('n', STOPS)(np.clip(p, 0, 1))[..., :3]
    img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
    px = np.array(img)
    px[~source_layers()['land']] = [214, 227, 240]
    Image.fromarray(px).save(path, 'WEBP', quality=88, method=4)


def main(publish):
    from rotclimate.geography import source_layers
    meta = json.loads((DATA / 'atlas.json').read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    L = source_layers()['land']
    for mode, folder in (('raw', DATA), ('corrected', DATA / 'corrected')):
        h = np.load(HERD / f'herding_{mode}.npz')['herding'].astype(float)
        h0, w0 = h.shape
        land = L[(np.arange(h0) * L.shape[0] // h0)][:, (np.arange(w0) * L.shape[1] // w0)]
        p = probability(h)
        np.savez_compressed(OUT / f'nomads_{mode}.npz', nomads=p.astype(np.float32))
        render(p, meta, OUT / f'nomads_{mode}.webp')
        res[mode] = dict(mean_land=float(p[land].mean()), over_half_land=float((p[land] > 0.5).mean()),
                         over_quarter_land=float((p[land] > 0.25).mean()))
        if publish:
            (folder / 'land_nomads.webp').write_bytes((OUT / f'nomads_{mode}.webp').read_bytes())
    if publish:
        for layers, file in ((meta['layers'], 'land_nomads.webp'), (meta['corrected_climate']['layers'], 'corrected/land_nomads.webp')):
            layers[:] = [l for l in layers if l['id'] != 'land_nomads']
            i = next((k for k, l in enumerate(layers) if l['id'] == 'land_herding'), len(layers) - 1) + 1
            layers.insert(i, dict(LAYER, file=file))
        (DATA / 'atlas.json').write_text(json.dumps(meta))
    (OUT / 'layer_summary.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main('--publish' in sys.argv)
