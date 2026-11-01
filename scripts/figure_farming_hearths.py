"""Figure for language layer 2b: FORGE's storing plant foragers (H) and productivity (B1) against Diamond's nine homelands.

    python -I scripts/figure_farming_hearths.py output/language_areas_20261101/layer2b OUT.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path); ap.add_argument("out", type=Path)
    a = ap.parse_args()
    z = np.load(a.run / "forge_world.npz"); summ = json.loads((a.run / "summary.json").read_text())
    plan = json.loads((ROOT / summ["plan"]).read_text())
    homes = plan["targets"]["points (lat, lon), placed here at each homeland's centre of early domestication"]
    lat, lon = z["lat"], z["lon"]
    fig, axs = plt.subplots(2, 1, figsize=(13, 10.4), constrained_layout=True)
    for ax, k, title in ((axs[0], "H", "Testart's storing plant foragers: FORGE plant-fed density x lean-season share"),
                         (axs[1], "B1", "Productivity (Miami NPP)")):
        dm = np.load(a.run / f"disc_{k}.npy")
        img = np.full((128, 360), np.nan)
        img[(72 - lat - 0.5).astype(int), (lon + 180 - 0.5).astype(int)] = dm
        pct = np.nanpercentile(dm, [2, 98])
        ax.set_facecolor("#dfe6ec")
        im = ax.imshow(img, extent=(-180, 180, -56, 72), cmap="YlGn", vmin=pct[0], vmax=pct[1], interpolation="nearest")
        fig.colorbar(im, ax=ax, shrink=0.6, label="500 km disc mean")
        for name, pts in homes.items():
            for p in pts:
                ax.plot(p[1], p[0], "o", ms=13, mfc="none", mec="#b0222a", mew=2)
            ax.annotate(name, (pts[0][1], pts[0][0]), xytext=(7, 7), textcoords="offset points", fontsize=8, color="#b0222a")
        for m in summ["maxima"][k]:
            ax.plot(m["lon"], m["lat"], "^", ms=8, mfc="#222" if not m["homeland"] else "#b0222a", mec="white", mew=0.8)
        r = summ["indices"][k]
        ax.set_title(f"{title}\nAUC against random land {r['auc']:.2f}; red rings = Diamond's nine homelands; "
                     f"triangles = strongest maxima above the random 95th percentile (black = no homeland within 1,000 km)", fontsize=10)
        ax.set_xlim(-180, 180); ax.set_ylim(-56, 72); ax.set_xticks([]); ax.set_yticks([])
    aucs = ", ".join(f"{k} {v['auc']:.2f}" for k, v in summ["indices"].items())
    fig.suptitle(f"Layer 2b: does FORGE place farming's homelands? AUC {aucs}; bar 0.80 and +0.05 over the best baseline; verdict: {summ['verdict']}", fontsize=11)
    fig.savefig(a.out, dpi=95)


if __name__ == "__main__":
    main()
