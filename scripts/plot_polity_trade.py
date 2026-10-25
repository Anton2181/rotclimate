"""Figure: market access against Roman town size (calibration/polity_20261025/trade.json).

    python3 -I scripts/plot_polity_trade.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import spearmanr
    z = np.load(ROOT / "output/polity_earth/trade.npz")
    res = json.loads((ROOT / "calibration/polity_20261025/trade.json").read_text())
    scales = list(z["scales"]); ma = np.log10(np.maximum(z["ma"], 1)); y = z["area"]; lon = z["lon"]
    k = scales.index(res["F_trade"]["c_fit"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), dpi=150, sharey=True)
    for ax, (label, sel) in zip(axes, (("West of 20° E (fit)", lon < 20), ("East of 20° E (test)", lon >= 20))):
        ax.scatter(ma[k][sel], y[sel], s=10, color="#2a78d6", alpha=0.55, edgecolors="none")
        rho = spearmanr(ma[k][sel], y[sel]).statistic
        ax.set_title(f"{label} · {sel.sum()} towns · Spearman {rho:+.2f}", fontsize=10, loc="left", color="#0b0b0b")
        ax.set_xlabel(f"log10 market access (people, scale {scales[k]:g} road-km)", fontsize=9, color="#52514e")
        ax.grid(color="#e4e2dc", lw=0.6); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=8, colors="#52514e")
    axes[0].set_ylabel("log10 town area (ha), Hanson 2016", fontsize=9, color="#52514e")
    fig.suptitle("Market access over the Price Edict network does not explain Roman town size (AD 150)",
                 x=0.01, ha="left", fontsize=12, color="#0b0b0b")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = ROOT / "output/polity_earth/trade_check.png"
    fig.savefig(out); print(out)


if __name__ == "__main__":
    main()
