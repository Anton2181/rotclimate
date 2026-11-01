"""Before/after maps for Earth regions from two benchmark runs: annual temperature bias and annual rain against WorldClim.

    python -I scripts/figure_region_change.py REF_RUN CAND_RUN OUT.png --regions najd_arabia algeria_sahara ... --title "..."
REF_RUN / CAND_RUN may list several run folders separated by commas (searched in order for each region).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, TwoSlopeNorm


def cells(runs, region):
    for r in runs.split(","):
        f = Path(r) / "cells" / f"{region}.npz"
        if f.exists():
            return np.load(f)
    raise FileNotFoundError(region)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ref"); ap.add_argument("cand"); ap.add_argument("out")
    ap.add_argument("--regions", nargs="+", required=True); ap.add_argument("--title", default="")
    ap.add_argument("--labels", default="r41|candidate"); ap.add_argument("--rain", action="store_true")
    a = ap.parse_args()
    la, lb = a.labels.split("|")
    cols = 5 if a.rain else 3
    fig, axes = plt.subplots(len(a.regions), cols, figsize=(3.1 * cols, 2.9 * len(a.regions)), constrained_layout=True, squeeze=False)
    tnorm = TwoSlopeNorm(0.0, -6, 6); pnorm = LogNorm(10, 2000)
    for row, region in zip(axes, a.regions):
        A, B = cells(a.ref, region), cells(a.cand, region)
        x, y = A["lon"], A["lat"]
        ba = (A["Ts"] - A["To"]).mean(0); bb = (B["Ts"] - B["To"]).mean(0)
        s = max(4, 1600 / len(x))
        panels = [(ba, f"{la}: T bias {ba.mean():+.1f} °C", "RdBu_r", tnorm), (bb, f"{lb}: T bias {bb.mean():+.1f} °C", "RdBu_r", tnorm),
                  (bb - ba, f"change {np.abs(bb).mean() - np.abs(ba).mean():+.2f} °C |err|", "PuOr_r", TwoSlopeNorm(0.0, -2, 2))]
        if a.rain:
            panels += [(B["Ps"].sum(0), f"{lb} rain {B['Ps'].sum(0).mean():.0f} mm ({la} {A['Ps'].sum(0).mean():.0f})", "YlGnBu", pnorm),
                       (A["Po"].sum(0), f"observed rain {A['Po'].sum(0).mean():.0f} mm", "YlGnBu", pnorm)]
        for ax, (v, title, cmap, norm) in zip(row, panels):
            sc = ax.scatter(x, y, c=v, s=s, marker="s", cmap=cmap, norm=norm, linewidths=0)
            ax.set_title(title, fontsize=8.5); ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect(1 / np.cos(np.radians(y.mean())))
        row[0].set_ylabel(region.replace("_", " "), fontsize=10)
    fig.colorbar(plt.cm.ScalarMappable(tnorm, "RdBu_r"), ax=axes[:, 0:2], shrink=0.5, label="annual T bias vs WorldClim (°C)")
    fig.colorbar(plt.cm.ScalarMappable(TwoSlopeNorm(0, -2, 2), "PuOr_r"), ax=axes[:, 2], shrink=0.5, label="change (°C)")
    if a.rain:
        fig.colorbar(plt.cm.ScalarMappable(pnorm, "YlGnBu"), ax=axes[:, 3:5], shrink=0.5, label="annual rain (mm)")
    fig.suptitle(a.title, fontsize=11)
    fig.savefig(a.out, dpi=110)


if __name__ == "__main__":
    main()
