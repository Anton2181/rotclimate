"""Figure for calibration/runoff_amount_20261121: model/GRUN annual runoff, current rule vs adopted Fu (w 2.6)."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from runoff_grun import grun, climate
from runoff_amount_grun import runoff, to_half_degree
g = grun().sum(0); T, _, _, P, _, land = climate()
cur = to_half_degree(runoff('cap_k', 0.75, T, P), land); fu = to_half_degree(runoff('budyko_fu', 2.6, T, P), land)
blind = json.loads((ROOT / 'calibration/runoff_amount_20261121/blind.json').read_text())
fig = plt.figure(figsize=(13, 8.6), layout='constrained'); fig.patch.set_facecolor('#f6f5f0')
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1])
ext = [-12, 125, 0, 56]; norm = TwoSlopeNorm(vcenter=0, vmin=-2, vmax=2)
for k, (m, name, row) in enumerate([(cur, 'Current rule (rain minus 0.75 × potential evaporation, monthly)', blind['current']),
                                     (fu, 'Adopted: Budyko–Fu curve, w = 2.6 (annual)', blind['chosen'])]):
    ax = fig.add_subplot(gs[0, k]); ok = np.isfinite(m) & np.isfinite(g) & (g >= 5)
    im = ax.imshow(np.where(ok, np.log2((m + 10) / (g + 10)), np.nan), extent=ext, cmap='BrBG', norm=norm, aspect='auto')
    ax.set_title(name, fontsize=10.5); ax.set_facecolor('#dfe6ea')
    ax.text(0.01, 0.02, f"blind half: log error {row['primary']:.3f} · median model/observed {row['median_ratio']:.2f} · rank {row['rank']:.3f}",
            transform=ax.transAxes, fontsize=8.5, bbox=dict(fc='white', ec='none', alpha=.85))
    ax.set_xlabel('longitude'); ax.set_ylabel('latitude')
fig.colorbar(im, ax=fig.axes[:2], shrink=.8, label='log2(model / GRUN observed)   brown = too little, green = too much')
for k, (m, name) in enumerate([(cur, 'Current rule'), (fu, 'Adopted Fu rule')]):
    ax = fig.add_subplot(gs[1, k]); ok = np.isfinite(m) & np.isfinite(g) & (g >= 5)
    ax.hexbin(g[ok] + 1, m[ok] + 1, xscale='log', yscale='log', gridsize=60, bins='log', cmap='Greys', mincnt=1)
    ax.plot([5, 3000], [5, 3000], color='#b5523b', lw=1.2); ax.set(xlim=(5, 3000), ylim=(1, 3000), xlabel='GRUN observed annual runoff (mm)',
                                                                     ylabel='model annual runoff (mm)', title=name + ': every 0.5° land cell')
fig.suptitle('River runoff amount vs observation-based GRUN, 1970–2000 · Earth window 0–56° N, 12° W–125° E · blind gates G1, G2, G3 pass', fontsize=12.5)
out = ROOT / 'reports/figures/runoff_amount_20261121.png'; out.parent.mkdir(exist_ok=True, parents=True); fig.savefig(out, dpi=130); print(out)
