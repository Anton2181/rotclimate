"""Warmest- and coldest-month temperature error, model minus WorldClim, for
chosen Earth regions under several runs.

    python3 -I scripts/plot_temp_regions.py --runs r34=output/dry_coupling_20261023/reference \
        r35=output/dry_coupling_20261023/dry2.5_e33 --regions sw_australia iberia cape north_india \
        --out output/dry_coupling_20261023/temp_r34_r35.png

Reads the per-cell monthly arrays that scripts/benchmark_local.py saves
(DIR/cells/REGION.npz). Each cell's warmest and coldest months are its
observed ones. One row per region: for each run, the warmest-month error,
then the coldest-month error, on one diverging scale (blue too cold, red
too warm); titles give the region-mean error.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
DIVERGE = LinearSegmentedColormap.from_list(
    "err", ["#0d366b", "#256abf", "#86b6ef", "#f1f0ec", "#f2a07b", "#d4532a", "#8a2a10"])


def grid(z, values):
    i, j = z["i"].astype(int), z["j"].astype(int)
    img = np.full((i.max() - i.min() + 1, j.max() - j.min() + 1), np.nan)
    img[i - i.min(), j - j.min()] = values
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", required=True, help="NAME=DIR pairs")
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--limit", type=float, default=6.0, help="colour scale limit, deg C")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    runs = [r.split("=", 1) for r in a.runs]
    plt.rcParams.update({"font.size": 9, "text.color": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    ncol = 2 * len(runs)
    fig, axs = plt.subplots(len(a.regions), ncol, figsize=(2.9 * ncol, 2.7 * len(a.regions)),
                            constrained_layout=True, squeeze=False)
    norm = TwoSlopeNorm(0.0, -a.limit, a.limit)
    for row, region in enumerate(a.regions):
        for k, (name, d) in enumerate(runs):
            z = np.load(Path(d) / "cells" / f"{region}.npz")
            To, Ts = z["To"], z["Ts"]
            n = np.arange(To.shape[1])
            for c, (label, idx) in enumerate((("warmest", np.argmax(To, 0)), ("coldest", np.argmin(To, 0)))):
                err = (Ts - To)[idx, n]
                ax = axs[row, 2 * k + c]
                im = ax.imshow(grid(z, err), cmap=DIVERGE, norm=norm, interpolation="nearest")
                head = f"{region.replace('_', ' ')}\n" if k == 0 and c == 0 else "\n"
                ax.set_title(f"{head}{name}, {label} month: {err.mean():+.1f} °C", loc="left", fontsize=9)
                ax.set_xticks([]); ax.set_yticks([])
                for s in ax.spines.values():
                    s.set_visible(False)
    cb = fig.colorbar(im, ax=axs, shrink=0.5, pad=0.01)
    cb.set_label("model minus WorldClim, °C", color=INK2)
    fig.suptitle("Warmest- and coldest-month temperature error at 56 km", x=0.01, ha="left", fontsize=11.5)
    fig.savefig(a.out, dpi=110, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
