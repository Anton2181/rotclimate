"""Figure for calibration/crop_yield_gaez_20261121: model rain-fed wheat vs GAEZ v4 low-input."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from runoff_grun import climate
from land_people import CROPS, hargreaves, sunlight_top, bucket
from crop_yield_gaez import gaez, half, grain
T, Tx, Tn, P, _, land = climate(); Th, Ph, Dh = half(T, land), half(P, land), half(Tx - Tn, land)
lat = 56 - (np.arange(112) + .5) * .5; lon = -12 + (np.arange(274) + .5) * .5; LA, LO = np.meshgrid(lat, lon, indexing='ij')
ok = np.isfinite(Th).all(0); Tf, Pf, Df = (np.nan_to_num(a) for a in (Th, Ph, Dh))
PET = hargreaves(Tf, Df, sunlight_top(LA, 23.44, 355.0)); S0 = bucket(Pf, PET)
ai = Pf.sum(0) / np.maximum(PET.sum(0), 1); cold = np.clip((Tf.mean(0) + 2) / 12, 0, 1)
b = json.loads((ROOT / 'calibration/crop_yield_gaez_20261121/blind.json').read_text())['current']
fig, axes = plt.subplots(2, 2, figsize=(13, 7.6), layout='constrained'); fig.patch.set_facecolor('#f6f5f0'); ext = [-12, 125, 0, 56]
for row, crop, code in [(0, 'wheat', 'yxLr0_whe'), (1, 'barley', 'yxLr0_brl')]:
    m = grain(Tf, Pf, PET, S0, CROPS[crop], .8, (.3, .5), 0) * cold * np.clip(ai / .35, 0, 1); o = gaez(code)
    v = ok & np.isfinite(o)
    for k, (a, name, vmax) in enumerate([(m, f'Model rain-fed {crop} (c.200 AD ceiling {CROPS[crop]["grain"]:.0f} t/ha)', 1.0), (o, f'GAEZ v4 low-input rain-fed {crop}, 1971–2000', 3.0)]):
        ax = axes[row, k]; im = ax.imshow(np.where(v, a, np.nan), extent=ext, cmap='YlGn', vmin=0, vmax=vmax, aspect='auto'); ax.set_facecolor('#dfe6ea')
        ax.set_title(name, fontsize=10.5); fig.colorbar(im, ax=ax, shrink=.85, label='t/ha')
    c = b['crops'][crop]
    axes[row, 0].text(.01, .02, f"blind half: Spearman {c['spearman']:.3f} · model/GAEZ level {c['level']:.2f}", transform=axes[row, 0].transAxes, fontsize=8.5, bbox=dict(fc='white', ec='none', alpha=.85))
fig.suptitle('Rain-fed cereal yield pattern vs GAEZ v4 low input · current response validated (no variant gained the +0.03 required) · colour scales differ: level is a period assumption', fontsize=11.5)
out = ROOT / 'reports/figures/crop_yield_gaez_20261121.png'; fig.savefig(out, dpi=130); print(out)
