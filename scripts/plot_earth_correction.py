"""Figures for the Earth temperature correction (held-out scores).

    python -I scripts/plot_earth_correction.py --dir output/earth_correction_20261030
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

MAPS = ["british_isles", "western_europe", "new_zealand", "patagonia", "pacific_nw", "iran_plateau", "north_india", "california"]


def grid_of(z, values):
    i, j = z["i"], z["j"]
    a = np.full((i.max() - i.min() + 1, j.max() - j.min() + 1), np.nan)
    a[i - i.min(), j - j.min()] = values
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    d = Path(ap.parse_args().dir)
    dev = json.loads((d / "eval_dev31_holdout.json").read_text())
    fine = json.loads((d / "eval_fine28_holdout.json").read_text())
    sealed = json.loads((d / "eval_sealed.json").read_text())

    # 1. per-region monthly MAE, raw vs held-out corrected
    regs = sorted(dev["regions"], key=lambda r: dev["regions"][r]["raw"]["monthly_mae_C"])
    raw = [dev["regions"][r]["raw"]["monthly_mae_C"] for r in regs]
    cor = [dev["regions"][r]["corrected"]["monthly_mae_C"] for r in regs]
    fig, ax = plt.subplots(figsize=(8, 10))
    y = np.arange(len(regs))
    ax.hlines(y, cor, raw, color="#bbb", lw=2, zorder=1)
    ax.scatter(raw, y, color="#c0392b", label="r39 raw", zorder=2)
    ax.scatter(cor, y, color="#2471a3", label="corrected (held-out cluster model)", zorder=3)
    for r, v in fine["regions"].items():                 # paired 28 km runs, held-out fold models
        for key, colour in (("raw", "#c0392b"), ("corrected", "#2471a3")):
            ax.scatter(v[key]["monthly_mae_C"], regs.index(r), marker="s", facecolor="none", edgecolor=colour, s=60, zorder=4)
    ticks = list(y)
    for k, (r, v) in enumerate(sealed["regions"].items()):  # sealed regions, final model
        yy = len(regs) + 1 + k
        ticks.append(yy)
        ax.hlines(yy, v["corrected"]["monthly_mae_C"], v["raw"]["monthly_mae_C"], color="#bbb", lw=2)
        ax.scatter(v["raw"]["monthly_mae_C"], yy, marker="D", color="#c0392b", zorder=4)
        ax.scatter(v["corrected"]["monthly_mae_C"], yy, marker="D", color="#2471a3", zorder=4)
    labels = regs + [f"{r} (sealed)" for r in sealed["regions"]]
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("monthly temperature MAE (°C)")
    a, b = dev["groups"]["all"]["monthly_mae_C"]["raw"], dev["groups"]["all"]["monthly_mae_C"]["corrected"]
    ax.set_title(f"Temperature error by region: {a:.2f} → {b:.2f} °C held out\n(open squares: paired 28 km runs; diamonds: sealed regions, final model)", fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=.3)
    plt.tight_layout()
    plt.savefig(d / "correction_by_region.png", dpi=90)
    plt.close(fig)

    # 2. maps of each cell's monthly MAE, raw vs corrected
    fig, axes = plt.subplots(len(MAPS) // 2, 4, figsize=(13, 13))
    for n, r in enumerate(MAPS):
        z = np.load(d / "eval_dev31_holdout" / f"{r}.npz")
        for k, (key, title) in enumerate((("Ts", "raw"), ("Tc", "corrected"))):
            ax = axes.flat[2 * n + k]
            err = np.abs(z[key] - z["To"]).mean(0)
            im = ax.imshow(grid_of(z, err), cmap="magma_r", vmin=0, vmax=4, interpolation="nearest")
            ax.set_title(f"{r.replace('_', ' ')}: {title} {err.mean():.2f} °C", fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
    fig.colorbar(im, ax=axes, orientation="horizontal", fraction=.03, pad=.02, label="mean |monthly T error| per cell (°C)")
    fig.suptitle("Held-out temperature correction: each region corrected by a model trained without its whole cluster", fontsize=11)
    plt.savefig(d / "correction_maps.png", dpi=80, bbox_inches="tight")
    plt.close(fig)

    # 3. seasonal cycles with the corrected curve
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.5), sharex=True)
    for ax, r in zip(axes.flat, MAPS):
        z = np.load(d / "eval_dev31_holdout" / f"{r}.npz")
        ax.plot(z["To"].mean(1), "k-o", ms=3, label="observed")
        ax.plot(z["Ts"].mean(1), "-o", color="#c0392b", ms=3, label="r39 raw")
        ax.plot(z["Tc"].mean(1), "-o", color="#2471a3", ms=3, label="corrected (held out)")
        ax.set_title(r.replace("_", " ")); ax.set_xticks(range(12)); ax.set_xticklabels(list("JFMAMJJASOND")); ax.grid(alpha=.3)
    axes.flat[0].legend(fontsize=8)
    fig.suptitle("Region-mean seasonal cycles before and after the held-out correction (southern regions mirrored)", fontsize=11)
    plt.tight_layout()
    plt.savefig(d / "correction_seasonal_cycles.png", dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    main()
