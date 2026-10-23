"""Per-region monthly temperature error and rainfall loss under r29 to r35.

    python3 -I scripts/plot_local_progress.py --out output/local_20261023/progress_r29_r35.png

Reads the 56 km benchmark summaries of output/local_20261023: r29 (baseline_56km
+ dev12_r29 + sealed6_baseline), r30 (r30_dev31 + sealed6_r30sea) and r31
(v2_cet0.8_off-0.5 + sealed6_r31cet) and r32 (output/continental_cold_20261023: cm4_cet1.1 +
sealed6_r32), r33 (output/continental_range_20261023: lat30 + sealed6_r33) and r34
(output/subgrid_eddy_20261023: so3_bg0.75 + sealed6_r34) and r35 (output/dry_coupling_20261023:
dry2.5_e33 + sealed6_r35). Regions are grouped as in policy_v2,
plus the sealed six (evaluated once per adopted milestone).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "output/local_20261023"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e7e6e2"
C29 = "#a3a29b"
TICKS = ["#eb6834", "#1baf7a", "#e87ba4", "#8a63d2", "#e0a321"]   # r30..r34
CLAST = "#2a78d6"


def regions(*names):
    out = {}
    for n in names:
        out.update(json.loads(((ROOT / n) if "/" in n else (D / n)).joinpath("summary.json").read_text())["regions"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    runs = {"r29": regions("baseline_56km", "dev12_r29", "sealed6_baseline"),
            "r30": regions("r30_dev31", "sealed6_r30sea"),
            "r31": regions("v2_cet0.8_off-0.5", "sealed6_r31cet"),
            "r32": regions("output/continental_cold_20261023/cm4_cet1.1", "output/continental_cold_20261023/sealed6_r32"),
            "r33": regions("output/continental_range_20261023/lat30", "output/continental_range_20261023/sealed6_r33"),
            "r34": regions("output/subgrid_eddy_20261023/so3_bg0.75", "output/subgrid_eddy_20261023/sealed6_r34"),
            "r35": regions("output/dry_coupling_20261023/dry2.5_e33", "output/dry_coupling_20261023/sealed6_r35")}
    names = list(runs)
    labels_run = ["r29", "r30 (calmer sea)", "r31 (+ cross-equatorial transport)", "r32 (+ continental winter cold)",
                  "r33 (+ dark-winter ramp)", "r34 (+ sub-grid hills)", "r35 (+ dry-ground coupling)"]
    policy = json.loads((ROOT / "calibration/local_accuracy_20261023/policy_v2.json").read_text())["groups"]
    groups = dict(policy, sealed=["norway", "southeast_africa", "caucasus", "yunnan", "northeast_us", "tasmania"])
    rows = []
    for g, members in groups.items():
        rows.append((g, None))
        rows += [(g, n) for n in sorted(members, key=lambda n: -runs["r29"][n]["temperature"]["monthly_mae_C"])]
    plt.rcParams.update({"font.size": 8.5, "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK, "axes.edgecolor": GRID, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    fig, axs = plt.subplots(1, 2, figsize=(11, 11.5), sharey=True, constrained_layout=True)
    metrics = [("temperature", "monthly_mae_C", "Monthly temperature error (°C)"),
               ("rain", "loss", "Rainfall loss (lower is better)")]
    ys = list(range(len(rows)))[::-1]
    labels = []
    for ax, (block, key, title) in zip(axs, metrics):
        for y, (g, n) in zip(ys, rows):
            if n is None:
                continue
            v = [runs[r][n][block][key] for r in names]
            ax.plot([v[0], v[-1]], [y, y], color=GRID, lw=2, zorder=1, solid_capstyle="round")
            ax.plot(v[0], y, "o", ms=6, mfc=SURFACE, mec=C29, mew=1.5, zorder=2)
            for x, c in zip(v[1:-1], TICKS):
                ax.plot(x, y, "|", ms=8, color=c, mew=2, zorder=3)
            ax.plot(v[-1], y, "o", ms=6, mfc=CLAST, mec=SURFACE, mew=1, zorder=4)
        ax.set_title(title, loc="left", fontsize=10)
        ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
    for g, n in rows:
        labels.append(f"{g.upper()}" if n is None else n.replace("_", " "))
    axs[0].set_yticks(ys); axs[0].set_yticklabels(labels)
    for t, (g, n) in zip(axs[0].get_yticklabels(), rows):
        if n is None:
            t.set_fontweight("bold"); t.set_color(INK2)
    handles = ([plt.Line2D([], [], marker="o", ls="", mfc=SURFACE, mec=C29, mew=1.5, ms=6, label=labels_run[0])]
               + [plt.Line2D([], [], marker="|", ls="", color=c, mew=2, ms=8, label=l) for c, l in zip(TICKS, labels_run[1:-1])]
               + [plt.Line2D([], [], marker="o", ls="", mfc=CLAST, mec=SURFACE, ms=6, label=labels_run[-1])])
    fig.legend(handles=handles, loc="upper left", ncol=4, frameon=False, bbox_to_anchor=(0.0, 1.06))
    fig.suptitle("Per-region error, 56 km, r29 → r35 (sealed six run once per milestone)", x=0.01, ha="left",
                 fontsize=11.5, y=1.09)
    fig.savefig(a.out, dpi=110, bbox_inches="tight", facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
