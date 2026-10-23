"""Annual rain, observed against two model runs, for chosen Earth regions.

    python3 -I scripts/plot_rain_regions.py --runs r33=output/subgrid_eddy_20261023/reference \
        r34=output/subgrid_eddy_20261023/so3_bg0.75 --regions alps new_zealand pacific_nw japan \
        --out output/subgrid_eddy_20261023/rain_r33_r34.png

Reads the per-cell monthly arrays that scripts/benchmark_local.py saves
(DIR/cells/REGION.npz: WorldClim Po and model Ps per scored land cell, with
grid indices i, j). One row per region: WorldClim, each run, on one
logarithmic colour scale per row; the title gives each run's rainfall loss.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm  # noqa: E402

SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
RAIN = LinearSegmentedColormap.from_list("rain", ["#f3eddc", "#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])


def grid(z, values):
    i, j = z["i"].astype(int), z["j"].astype(int)
    img = np.full((i.max() - i.min() + 1, j.max() - j.min() + 1), np.nan)
    img[i - i.min(), j - j.min()] = values
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", required=True, help="NAME=DIR pairs")
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    runs = [r.split("=", 1) for r in a.runs]
    plt.rcParams.update({"font.size": 9, "text.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    fig, axs = plt.subplots(len(a.regions), 1 + len(runs), figsize=(3.6 * (1 + len(runs)), 3.0 * len(a.regions)),
                            constrained_layout=True, squeeze=False)
    for row, region in enumerate(a.regions):
        zs = [np.load(Path(d) / "cells" / f"{region}.npz") for _, d in runs]
        obs = zs[0]["Po"].sum(0)
        vals = [obs] + [z["Ps"].sum(0) for z in zs]
        lo, hi = np.percentile(np.concatenate(vals), [2, 98])
        norm = LogNorm(max(lo, 20), max(hi, lo * 2))
        losses = [json.loads((Path(d) / "summary.json").read_text())["regions"][region]["rain"]["loss"] for _, d in runs]
        titles = [f"{region.replace('_', ' ')}: WorldClim"] + [f"{n}: loss {l:.3f}" for (n, _), l in zip(runs, losses)]
        for col, (v, t) in enumerate(zip(vals, titles)):
            ax = axs[row, col]
            im = ax.imshow(grid(zs[0], v), cmap=RAIN, norm=norm, interpolation="nearest")
            ax.set_title(t, loc="left", fontsize=9.5)
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
        cb = fig.colorbar(im, ax=axs[row, :], shrink=0.85, pad=0.01)
        cb.set_label("mm per year", color=INK2)
    fig.suptitle("Annual rain at 56 km: WorldClim against the model", x=0.01, ha="left", fontsize=11.5)
    fig.savefig(a.out, dpi=110, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
