"""Figure for calibration/forage_season_20261121: forage-growth cycle vs FLUXCOM-X GPP, current vs adopted."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from runoff_grun import climate
from forage_season_gpp import gpp, half, weights, blocks, CURRENT
obs, _ = gpp(); T, _, _, P, _, land = climate(); Th, Ph = half(T, land), half(P, land)
bl = json.loads((ROOT / 'calibration/forage_season_20261121/blind.json').read_text()); NEW = tuple(bl['chosen']['variant'])
base = np.isfinite(obs).all(0) & np.isfinite(Th).all(0) & (np.nansum(obs, 0) * 30.4 >= 100)
def corr(v):
    w = weights(Th, Ph, *v); ok = base & (w.sum(0) > 0)
    mb, valid = blocks(w / np.where(ok, w.sum(0), 1), ok); gb, _ = blocks(obs / np.where(ok, obs.sum(0), 1), ok)
    a, b = mb - mb.mean(0), gb - gb.mean(0); r = (a * b).sum(0) / np.sqrt((a * a).sum(0) * (b * b).sum(0) + 1e-30)
    return np.where(valid, r, np.nan), mb, gb
rc, mc, gc = corr(CURRENT); rn, mn, _ = corr(NEW)
fig = plt.figure(figsize=(13, 8.4), layout='constrained'); fig.patch.set_facecolor('#f6f5f0'); gs = fig.add_gridspec(2, 4)
ext = [-12, 123, 1, 56]
for k, (r, name, row) in enumerate([(rc, 'Current proxy: floor 0 °C, span 15 °C, rain ½-sat 50 mm', bl['current']),
                                     (rn, 'Adopted: span 20 °C, rain ½-sat 100 mm, 1-month rain memory', bl['chosen'])]):
    ax = fig.add_subplot(gs[0, 2 * k:2 * k + 2]); im = ax.imshow(r, extent=ext, cmap='RdYlGn', vmin=-1, vmax=1, aspect='auto')
    ax.set_facecolor('#dfe6ea'); ax.set_title(name, fontsize=10.5)
    ax.text(.01, .02, f"blind half: median r {row['primary']:.3f} · peak month ±1 in {100*row['peak']:.0f} % of blocks", transform=ax.transAxes, fontsize=8.5, bbox=dict(fc='white', ec='none', alpha=.85))
fig.colorbar(im, ax=fig.axes[:2], shrink=.8, label='correlation of 12-month cycle with observed GPP (2.5° blocks)')
lat = 56 - (np.arange(22) + .5) * 2.5; lon = -12 + (np.arange(54) + .5) * 2.5
for k, (name, la, lo) in enumerate([('Sahel (14 N, 2 E)', 14, 2), ('Kazakh steppe (49 N, 67 E)', 49, 67), ('North India (27 N, 80 E)', 27, 80), ('Anatolia (39 N, 34 E)', 39, 34)]):
    i, j = np.argmin(abs(lat - la)), np.argmin(abs(lon - lo)); ax = fig.add_subplot(gs[1, k]); m = np.arange(1, 13)
    ax.plot(m, gc[:, i, j], color='#222', lw=2.2, label='observed GPP'); ax.plot(m, mc[:, i, j], color='#b5523b', lw=1.4, ls='--', label='current')
    ax.plot(m, mn[:, i, j], color='#2f7a6d', lw=1.6, label='adopted'); ax.set(title=name, xticks=[1, 4, 7, 10], xticklabels=['Jan', 'Apr', 'Jul', 'Oct'], ylabel='share of annual growth' if k == 0 else None)
    if k == 0: ax.legend(fontsize=8)
fig.suptitle('Forage-growth season vs FLUXCOM-X GPP (2001–2021) · Earth window 0–56° N · blind gates G1, G2 pass', fontsize=12.5)
out = ROOT / 'reports/figures/forage_season_20261121.png'; fig.savefig(out, dpi=130); print(out)
