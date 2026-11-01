"""Figure for language layer 2: the farming wave on Earth against Pinhasi et al.'s dated sites.

    python -I scripts/figure_farming_spread.py output/language_areas_20261101/layer2 OUT.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--model", default="M0", choices=("M0", "M2", "M3"))
    a = ap.parse_args()
    z = np.load(a.run / "fields.npz")
    summ = json.loads((a.run / "summary.json").read_text())
    lat, lon, land, s = z["lat"], z["lon"], z["land"], z["s"]
    step = lat[0] - lat[1]
    ext = (lon[0] - step / 2, lon[-1] + step / 2, lat[-1] - step / 2, lat[0] + step / 2)
    sea = np.where(land, np.nan, 1.0)
    t = z["date"]
    fig, axs = plt.subplots(1, 3, figsize=(17.5, 6.2), constrained_layout=True)

    ax = axs[0]
    cm = LinearSegmentedColormap.from_list("crop", ["#efe9dc", "#d9cf8f", "#8fae5a", "#3f7a3a"])
    ax.imshow(np.where(land, s, np.nan), extent=ext, cmap=cm, vmin=0, vmax=1, interpolation="nearest")
    ax.imshow(sea, extent=ext, cmap=LinearSegmentedColormap.from_list("sea", ["#cfdbe6", "#cfdbe6"]), interpolation="nearest")
    sc = ax.scatter(z["site_lon"], z["site_lat"], c=t / 1000, cmap="plasma_r", s=11, edgecolor="#222", lw=0.3, vmin=6, vmax=11)
    fig.colorbar(sc, ax=ax, shrink=0.7, label="first farming, thousand years before present (calibrated)")
    ax.set_title("Wheat/barley suitability from the map's crop rules (green)\nand the 726 dated early-farming sites (Pinhasi et al. 2005)", fontsize=10)

    best = a.model
    ax = axs[1]
    if best == "M0":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from farming_spread_earth import great_circle, read_sites
        org = dict(read_sites()[1])[summ["models"]["M0"]["all_sites"]["origin"]]
        d = great_circle(z["site_lat"], z["site_lon"], *org)
        c = np.polyfit(d, t, 1)
        X, Y = np.meshgrid(lon, lat)
        arr = np.polyval(c, great_circle(Y, X, *org))
    else:
        arr = np.load(a.run / f"arrival_{best}.npy")
    if True:
        arr = np.where(np.isfinite(arr), arr, np.nan)
        ax.imshow(np.where(land, arr / 1000, np.nan), extent=ext, cmap="plasma_r", vmin=6, vmax=11, interpolation="nearest")
        ax.imshow(sea, extent=ext, cmap=LinearSegmentedColormap.from_list("sea", ["#cfdbe6", "#cfdbe6"]), interpolation="nearest")
        X, Y = np.meshgrid(lon, lat)
        cs = ax.contour(X, Y, np.where(land, arr / 1000, np.nan), levels=np.arange(6, 11.5, 0.5), colors="#222", linewidths=0.5)
        ax.clabel(cs, fmt="%.1f", fontsize=7)
    m = summ["models"][best]["all_sites"]
    label = {"M0": "great-circle distance", "M2": "terrain + sea", "M3": "terrain + sea + crops"}[best]
    ax.set_title(f"{best} ({label}) fitted to all sites: origin {m['origin']} {m['setting'] or ''},\n"
                 f"{m['km_per_year']:.2f} km per year, r = {m['r']:.2f}; contours every 500 years", fontsize=10)

    ax = axs[2]
    res = t - z[f"pred_{best}"]
    nrm = TwoSlopeNorm(0, -1500, 1500)
    ax.imshow(np.where(land, 1.0, np.nan), extent=ext, cmap=LinearSegmentedColormap.from_list("l", ["#ece8df", "#ece8df"]))
    ax.imshow(sea, extent=ext, cmap=LinearSegmentedColormap.from_list("sea", ["#cfdbe6", "#cfdbe6"]), interpolation="nearest")
    sc = ax.scatter(z["site_lon"], z["site_lat"], c=res, cmap="RdBu", norm=nrm, s=13, edgecolor="#222", lw=0.3)
    fig.colorbar(sc, ax=ax, shrink=0.7, label="observed - predicted, years (red: later than predicted)")
    rows = ", ".join(f"{k} {v['heldout_rmse']:.0f}" for k, v in summ["models"].items())
    ax.set_title(f"{best} held-out errors (each region predicted from the other six);\nheld-out RMSE (years): {rows}; verdict: {summ['verdict']}", fontsize=10)
    for ax in axs:
        ax.set_xlim(-12, 56); ax.set_ylim(24, 62); ax.set_aspect(1.4)
    fig.savefig(a.out, dpi=100)


if __name__ == "__main__":
    main()
