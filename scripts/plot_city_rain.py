"""Two runs' rain at the real cities, side by side.

    python3 -I scripts/plot_city_rain.py BEFORE AFTER --labels r35 r36 \
        --highlight north_india east_china --out output/city_rain/r35_r36.png

BEFORE and AFTER are benchmark_local.py output folders (cells/*.npz); the
cities and the matching are scripts/city_rain.py's. Left and middle: each
city's observed against modelled annual rain (log axes; the shaded band is
within 25 %). Right: the first highlighted region's monthly rain, the mean
over its cities.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from city_rain import cities, match, stats  # noqa: E402

SURFACE, INK, INK_SOFT, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#eb6834", "#2a78d6", "#1baf7a"]          # reference categorical slots 2, 1, 3
OTHER = "#b9b8b2"
NAMES = {"north_india": "north India", "east_china": "east China", "southeast_us": "south-east US"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs=2, type=Path)
    ap.add_argument("--labels", nargs=2, default=["before", "after"])
    ap.add_argument("--highlight", nargs="+", default=["north_india"])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    towns = cities()
    rows = [match(r, towns) for r in a.runs]
    plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": INK_SOFT,
                         "xtick.color": INK_SOFT, "ytick.color": INK_SOFT, "axes.edgecolor": GRID})
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.6), gridspec_kw=dict(width_ratios=[1, 1, 1.15]),
                             constrained_layout=True, facecolor=SURFACE)
    lo, hi = 20, 6000
    for ax, rr, label in zip(axes[:2], rows, a.labels):
        obs = np.array([r["obs"].sum() for r in rr]); sim = np.array([r["sim"].sum() for r in rr])
        reg = np.array([r["region"] for r in rr])
        s = stats(np.array([r["obs"] for r in rr]), np.array([r["sim"] for r in rr]))
        x = np.geomspace(lo, hi, 50)
        ax.fill_between(x, x * 0.75, x * 1.25, color=GRID, lw=0, zorder=0)
        ax.plot(x, x, color=INK_SOFT, lw=1, zorder=1)
        rest = ~np.isin(reg, a.highlight)
        ax.scatter(obs[rest], np.maximum(sim[rest], lo), s=7, color=OTHER, lw=0, label="other cities", zorder=2)
        for k, g in enumerate(a.highlight):
            m = reg == g
            ax.scatter(obs[m], np.maximum(sim[m], lo), s=10, color=SERIES[k], lw=0.3, edgecolors=SURFACE,
                       label=NAMES.get(g, g), zorder=3)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.set_aspect("equal")
        ax.set_facecolor(SURFACE); ax.grid(color=GRID, lw=0.6)
        ax.set_xlabel("observed annual rain, mm (WorldClim)"); ax.set_ylabel("modelled, mm")
        ax.set_title(f"{label}: log RMSE {s['annual_log_rmse']:.2f}, median bias {s['annual_bias_pct']:+.0f} %,"
                     f" {100 * s['within_25pct']:.0f} % within 25 %", loc="left", fontsize=10)
        ax.legend(loc="upper left", fontsize=8.5, frameon=False, markerscale=1.8)
    ax = axes[2]
    g = a.highlight[0]
    months = np.arange(1, 13)
    first = [r for r in rows[0] if r["region"] == g]
    ax.plot(months, np.mean([r["obs"] for r in first], 0), color=INK, lw=2, label="observed")
    for rr, label, colour, style in zip(rows, a.labels, [OTHER, SERIES[0]], ["--", "-"]):
        sel = [r for r in rr if r["region"] == g]
        ax.plot(months, np.mean([r["sim"] for r in sel], 0), color=colour, lw=2, ls=style, label=label)
    ax.set_xticks(months, list("JFMAMJJASOND")); ax.set_xlim(0.6, 12.4); ax.set_ylim(0, None)
    ax.set_facecolor(SURFACE); ax.grid(color=GRID, lw=0.6, axis="y")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_ylabel("mm a month")
    ax.set_title(f"{NAMES.get(g, g)}: mean of its {len(first)} cities", loc="left", fontsize=10)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
