"""Which regions each new mechanism helps and hurts, side by side.

    python3 -I scripts/plot_mechanism_trades.py --out output/mechanism_trades/trades.png

Reads benchmark folders (summary.json) of the probes and gates of the
2026-10-24 round, each against its own reference, and draws two heatmaps:
the change of each region's rainfall loss and of its monthly temperature
error (%), blue = better, red = worse, empty = not run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402

SURFACE, INK, INK_SOFT, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BOUNDS = [-200, -20, -10, -3, 3, 10, 20, 200]
CMAP = ListedColormap(["#0d366b", "#2a78d6", "#86b6ef", "#f0efec", "#f2a7a3", "#e34948", "#8c1f1e"])
DARK = {0, 1, 5, 6}                                      # bins dark enough for white ink
# (label, reference run, candidate run)
RUNS = [
    ("e48 cold\nhighs (r37)", "output/cold_high_20261024/reference", "output/cold_high_20261024/cc0.1"),
    ("e39 crest\nwind", "output/crest_wind_20261024/reference", "output/crest_wind_20261024/free1"),
    ("e47 tropical\nstorms", "output/tropical_probe/base", "output/tropical_probe/ts1"),
    ("e49 monsoon\ndescent", "output/descent_probe/base", "output/descent_probe/md0.02"),
    ("e50 deep-sea\noverturn", "output/winter_mixing_probe/base", "output/winter_mixing_probe/wm1d"),
    ("e51 sea-\nwarmed air", "output/unstable_sea_probe/base", "output/unstable_sea_probe/tu1"),
    ("observed sea\n(diagnostic)", "output/obs_sea_probe/base", "output/obs_sea_probe/obs_sea"),
]
NAMES = {"north_india": "north India", "east_china": "east China", "southeast_us": "south-east US", "us_midwest": "US Midwest",
         "north_china_plain": "North China Plain", "pacific_nw": "Pacific NW", "sw_australia": "SW Australia",
         "east_australia": "east Australia", "south_brazil": "south Brazil", "iran_plateau": "Iran", "texas_plains": "Texas",
         "great_basin": "Great Basin", "british_isles": "British Isles", "western_europe": "western Europe",
         "eastern_europe": "eastern Europe", "central_asia": "Central Asia", "new_zealand": "New Zealand"}


def regions_of(path):
    return json.loads((ROOT / path / "summary.json").read_text())["regions"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    policy = json.loads((ROOT / "calibration/local_accuracy_20261023/policy_v2.json").read_text())["groups"]
    order = [r for g in ("training", "holdout", "midlatitude", "dev12") for r in policy[g]]
    rain = np.full((len(order), len(RUNS)), np.nan); temp = rain.copy()
    for j, (_, ref, cand) in enumerate(RUNS):
        R, C = regions_of(ref), regions_of(cand)
        for i, r in enumerate(order):
            if r in C and r in R:
                rain[i, j] = 100 * (C[r]["rain"]["loss"] / R[r]["rain"]["loss"] - 1)
                temp[i, j] = 100 * (C[r]["temperature"]["monthly_mae_C"] / R[r]["temperature"]["monthly_mae_C"] - 1)
    plt.rcParams.update({"font.size": 9.5, "text.color": INK, "axes.labelcolor": INK_SOFT,
                         "xtick.color": INK_SOFT, "ytick.color": INK_SOFT, "axes.edgecolor": GRID})
    fig, axes = plt.subplots(1, 2, figsize=(15, 11.5), sharey=True, constrained_layout=True, facecolor=SURFACE)
    norm = BoundaryNorm(BOUNDS, CMAP.N)
    for ax, M, title in ((axes[0], rain, "Rainfall loss, % change"), (axes[1], temp, "Monthly temperature error, % change")):
        ax.set_facecolor(SURFACE)
        im = ax.imshow(np.ma.masked_invalid(M), cmap=CMAP, norm=norm, aspect="auto", interpolation="nearest")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                v = M[i, j]
                if np.isfinite(v) and abs(v) >= 3:
                    b = int(np.digitize(v, BOUNDS[1:-1]))
                    ax.text(j, i, f"{v:+.0f}", ha="center", va="center", fontsize=8,
                            color=SURFACE if b in DARK else INK)
        ax.set_xticks(range(len(RUNS)), [r[0] for r in RUNS], fontsize=8.5)
        ax.xaxis.tick_top()
        ax.set_xticks(np.arange(-0.5, len(RUNS)), minor=True); ax.set_yticks(np.arange(-0.5, len(order)), minor=True)
        ax.grid(which="minor", color=SURFACE, lw=2); ax.tick_params(which="minor", length=0); ax.tick_params(length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.set_title(title, loc="left", fontsize=11, pad=8)
        y = 0
        for g in ("training", "holdout", "midlatitude", "dev12"):
            y += len(policy[g])
            if y < len(order):
                ax.axhline(y - 0.5, color=INK_SOFT, lw=1.2)
    axes[0].set_yticks(range(len(order)), [NAMES.get(r, r.replace("_", " ").capitalize()) for r in order])
    y = 0
    for g, label in (("training", "training"), ("holdout", "former holdout"), ("midlatitude", "mid-latitude"), ("dev12", "dev12")):
        axes[1].text(len(RUNS) - 0.35, y - 0.5 + 0.1, label, ha="left", va="top", fontsize=8.5, color=INK_SOFT)
        y += len(policy[g])
    cb = fig.colorbar(im, ax=axes, location="bottom", shrink=0.45, pad=0.02, ticks=BOUNDS[1:-1])
    cb.set_label("change against each run's own reference, %  (blue: better, red: worse; empty: not run)")
    cb.outline.set_visible(False)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=100, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
