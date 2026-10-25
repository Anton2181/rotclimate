"""Figure: the gap fill on Earth (calibration/polity_20261025/fill.json).

    python3 -I scripts/plot_polity_fill.py
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
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    z = np.load(ROOT / "output/polity_earth/fill.npz")
    res = json.loads((ROOT / "calibration/polity_20261025/fill.json").read_text())
    # agreement / held outside the polygon / inside but unheld / neither
    cmap = ListedColormap(["#2a78d6", "#eb6834", "#1baf7a", "#f1efe8", "#c9d6e3"])
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.2), dpi=150)
    for row, (win, rs) in enumerate((("rome", (0, 2)), ("han", (0, 2)))):
        land = z[f"{win}_land"].astype(bool); inside = z[f"{win}_inside"].astype(bool)
        for col, r in enumerate(rs):
            held = z[f"{win}_r{r:g}"].astype(bool)
            cat = np.full(land.shape, 4)
            cat[land] = 3
            cat[land & held & inside] = 0
            cat[land & held & ~inside] = 1
            cat[land & ~held & inside] = 2
            ax = axes[row, col]
            ax.imshow(cat, cmap=cmap, vmin=0, vmax=4, interpolation="nearest")
            key = "T_fill2" if win == "han" else "T_fill1"
            ba = res[key]["by_r"][f"{r:g}"] if win == "han" else res["F_fill"]["by_r"][f"{r:g}"]
            ba_e = res["T_fill1"]["by_r"][f"{r:g}"] if win == "rome" else None
            title = (f"Roman empire AD 150 · gap fill {r:g} days\nbalanced accuracy west {ba:.3f} · east {ba_e:.3f}"
                     if win == "rome" else f"Han China AD 2 (held at 5 days from seats) · gap fill {r:g} days\n"
                                           f"balanced accuracy {ba:.3f}")
            ax.set_title(title, fontsize=10, color="#0b0b0b", loc="left")
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
    fig.legend(handles=[Patch(color="#2a78d6", label="held, inside the historians' polygon"),
                        Patch(color="#eb6834", label="held, outside it"),
                        Patch(color="#1baf7a", label="inside it, not held"),
                        Patch(color="#f1efe8", label="neither")],
               loc="lower center", ncol=4, frameon=False, fontsize=10)
    fig.suptitle("Bridging the gaps between held land barely changes the match to historical extents",
                 x=0.01, ha="left", fontsize=13, color="#0b0b0b")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    out = ROOT / "output/polity_earth/fill_check.png"
    fig.savefig(out); print(out)


if __name__ == "__main__":
    main()
