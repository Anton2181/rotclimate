"""Polity v2 on Earth, in four panels: Casson's sailing times, ORBIS' sea
edges, the Roman empire's extent by threshold, and the months of hard going.

    python3 -I scripts/plot_polity_earth.py --out output/polity_earth/earth_checks.png

Reads calibration/polity_20261025/{sea,tests}.json (scripts/polity_earth_check.py).
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

SURFACE, INK, INK_SOFT, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


def style(ax, title):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.tick_params(colors=INK_SOFT, length=0)
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    plan = ROOT / "calibration/polity_20261025"
    sea = json.loads((plan / "sea.json").read_text()); tests = json.loads((plan / "tests.json").read_text())
    plt.rcParams.update({"font.size": 9.5, "text.color": INK, "axes.labelcolor": INK_SOFT})
    fig, ax = plt.subplots(2, 2, figsize=(13, 10), facecolor=SURFACE, constrained_layout=True)

    # A: Casson's sailing times
    rows = sea["T6_casson"]["routes"]
    c = np.array([r["casson"] for r in rows]); m = np.array([r["model"] for r in rows])
    A = ax[0, 0]; style(A, f"Sailing times, Casson (1951) Table 1 · Spearman {sea['T6_casson']['spearman']:.2f}")
    lim = [1, 100]
    A.fill_between(lim, [0.67, 67], [1.5, 150], color=GRID, alpha=0.6, lw=0)
    A.plot(lim, lim, color=INK_SOFT, lw=1)
    A.scatter(c, m, s=40, color=SERIES[0], edgecolor=SURFACE, lw=1.5, zorder=3)
    # a few routes named: the slow west and the too-easy run home against the Etesian winds
    named = {"Rome-Tarraco": (-70, 6), "Narbo-Rome": (6, -10), "Gibraltar-Rome": (-80, 6), "Alexandria-Rome": (-40, 10),
             "Rome-Alexandria": (6, -4), "Rhodes-Rome": (6, -10)}
    for r in rows:
        if r["route"] in named:
            A.annotate(r["route"].replace("-", " → "), (r["casson"], r["model"]), fontsize=8, color=INK_SOFT,
                       xytext=named[r["route"]], textcoords="offset points")
    A.set_xscale("log"); A.set_yscale("log"); A.set_xlim(lim); A.set_ylim(lim)
    A.set_xlabel("Casson's days (mid-range), sailing season"); A.set_ylabel("model days, mean of May–September")
    A.text(1.15, 75, "band: ×0.67 to ×1.5", fontsize=8, color=INK_SOFT)

    # B: ORBIS edges are summarised (only n and medians were kept); show the medians against Casson's
    B = ax[0, 1]; style(B, "Model ÷ reference, median")
    t7 = sea["T7_orbis"]
    labels = ["Casson routes (May–Sep)", "ORBIS coastal edges (July)", "ORBIS open-sea edges (July)",
              "Pliny's record runs (July)"]
    pl = sea["pliny"]
    vals = [sea["T6_casson"]["median_ratio"], t7["by_kind"]["coastal"]["median_ratio"],
            t7["by_kind"]["overseas"]["median_ratio"], float(np.median([p["model_july"] / p["pliny"] for p in pl]))]
    ns = [len(rows), t7["by_kind"]["coastal"]["n"], t7["by_kind"]["overseas"]["n"], len(pl)]
    y = np.arange(len(vals))[::-1]
    B.barh(y, vals, height=0.55, color=SERIES[0])
    B.axvline(1, color=INK_SOFT, lw=1)
    for yy, v, n in zip(y, vals, ns):
        B.text(v + 0.04, yy, f"{v:.2f}× · n = {n}", va="center", fontsize=9, color=INK)
    B.set_yticks(y, labels); B.set_xlim(0, 3.3); B.set_xlabel("model days ÷ reference days (1 = the same)")
    B.grid(axis="y", visible=False)

    # C: the Roman extent by threshold
    C = ax[1, 0]
    t1 = tests["T1_roman_extent"]; ph = t1["post_hoc"]
    style(C, "Roman empire AD 150: land inside / outside, from days to the network")
    hs = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    names = [("v1 days", "v1: walking, snow-free season"), ("v2 days, no refuge", "v2: months, boats, rivers"),
             ("v2 seasons on foot, no boats, no refuge", "v2 without boats"),
             ("v2 days, with refuge", "v2 + refuge factor (Han fit)")]
    for k, (key, lab) in enumerate(names):
        C.plot(hs, [ph[key][f"held {h:g}"] for h in hs], color=SERIES[k], lw=2, marker="o", ms=6,
               markeredgecolor=SURFACE, label=lab, ls="--" if k == 2 else "-")
    C.axvline(2, color=INK_SOFT, lw=1, ls=":"); C.axvline(5, color=INK_SOFT, lw=1, ls=":")
    C.text(2.05, 0.835, "v1 and the map: 2 days", fontsize=8, color=INK_SOFT)
    C.text(4.05, 0.835, "Han fit: 5 days", fontsize=8, color=INK_SOFT)
    C.set_xlabel("held within … days"); C.set_ylabel("balanced accuracy"); C.set_ylim(0.64, 0.845)
    C.legend(frameon=False, fontsize=8.5, loc="lower right")

    # D: months of hard going
    D = ax[1, 1]; style(D, "Travel cost off the roads by month (snow, mud, heat)")
    s = tests["T8_seasons"]
    for k, place in enumerate(["Moscow", "Kyiv", "Beijing", "Rome", "Patna"]):
        D.plot(range(12), s[place]["cost"], color=SERIES[k], lw=2, marker="o", ms=5, markeredgecolor=SURFACE,
               label=f"{place} · {s[place]['snow_months']} snow months")
    D.set_xticks(range(12), MONTHS); D.set_ylim(0.9, 3.2); D.set_yticks([1, 1.5, 2, 2.5])
    D.set_ylabel("× the going of a dry, snow-free month"); D.legend(frameon=False, fontsize=8.5, loc="upper center",
                                                                  ncol=3)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
