"""How well each population model ranks real places around 1-200 CE.

    python3 -I scripts/plot_population_scorecard.py --out output/population_cores/scorecard.png

Rank correlations (Spearman, tied ranks averaged) from
reports/POPULATION_20261023.md: HYDE 3.3 at 200 CE on 1-degree blocks, the
Han census of AD 2 by commandery, and Roman towns of AD 150 (Hanson 2016)
on 2-degree blocks. The Roman towns were opened only after every setting
was fixed.
"""
from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e7e6e2"
TESTS = [("HYDE 3.3, 200 CE", "#2a78d6"), ("Han census, AD 2", "#eb6834"), ("Roman towns, AD 150 (held out)", "#1baf7a")]
MODELS = [  # name, HYDE, Han, Roman
    ("Uniform over land", 0.03, -0.18, -0.10),
    ("Crops only", 0.53, 0.10, np.nan),
    ("Settlement base\n(crops, herding, clearance, rivers, malaria)", 0.575, 0.29, 0.19),
    ("× old cores, straight-line distance", 0.744, 0.82, 0.53),
    ("× old cores, travel cost", 0.746, 0.84, 0.62),
    ("HYDE 3.3 itself", np.nan, 0.72, 0.64),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plt.rcParams.update({"font.size": 9.5, "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK, "axes.edgecolor": GRID, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    fig, ax = plt.subplots(figsize=(10, 5.6), constrained_layout=True)
    y = np.arange(len(MODELS))[::-1]
    h = 0.24
    for k, (label, colour) in enumerate(TESTS):
        vals = np.array([m[1 + k] for m in MODELS], float)
        ok = np.isfinite(vals)
        ax.barh(y[ok] + (1 - k) * h, vals[ok], height=h * 0.9, color=colour, label=label, zorder=2)
        for yy, v in zip(y[ok] + (1 - k) * h, vals[ok]):
            ax.text(v + (0.012 if v >= 0 else -0.012), yy, f"{v:.2f}", va="center", ha="left" if v >= 0 else "right",
                    fontsize=8.5, color=INK2)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([m[0] for m in MODELS])
    ax.set_xlim(-0.25, 1.0)
    ax.set_xlabel("Rank correlation with the record (1 = same order of places)")
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper right", frameon=False)
    ax.set_title("Where people lived around 1-200 CE: the population models against three records", loc="left",
                 fontsize=11.5)
    fig.savefig(a.out, dpi=120, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
