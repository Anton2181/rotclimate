"""Progress of a gate_calibrate search: each candidate's score against the reference.

    python3 -I scripts/plot_search_progress.py --search calibration/stable_land_20261025/search \
        --out output/stable_land_20261025/progress.png

S is the mean of the temperature and rain losses over the reference's (1 =
the adopted physics); a candidate passes the gate only below 0.995 with no
group (training, former holdout, mid-latitude, dev12) worse.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SURFACE, INK, INK_SOFT, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--search", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--title", default="Sea + stable-land + continentality search")
    a = ap.parse_args()
    rows = [json.loads(line) for line in (a.search / "evals.jsonl").read_text().splitlines() if line.strip()]
    n = np.arange(1, len(rows) + 1)
    S = np.array([r["S"] for r in rows])
    worst = np.array([max(r["groups"].values()) for r in rows])
    ok = worst <= 1.0
    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor=SURFACE, constrained_layout=True)
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(colors=INK_SOFT, length=0)
    lim = (0.96, 1.06)
    shown = np.clip(S, *lim)
    ax.scatter(n[~ok], shown[~ok], s=36, color=ORANGE, edgecolor=SURFACE, lw=1.2, zorder=3,
               label="some group worse than the reference")
    ax.scatter(n[ok], shown[ok], s=36, color=BLUE, edgecolor=SURFACE, lw=1.2, zorder=4,
               label="no group worse")
    ax.axhline(1.0, color=INK_SOFT, lw=1); ax.axhline(0.995, color=INK_SOFT, lw=1, ls=":")
    ax.text(len(rows) + 0.5, 1.0, " r37", va="center", fontsize=9, color=INK_SOFT)
    ax.text(len(rows) + 0.5, 0.995, " gate", va="center", fontsize=9, color=INK_SOFT)
    best = int(np.argmin(np.where(ok & (np.arange(len(rows)) > 0), S, np.inf)))
    if ok[best] and best > 0:
        ax.annotate(f"best passing so far: S {S[best]:.4f}", (n[best], S[best]), xytext=(8, -14),
                    textcoords="offset points", fontsize=9, color=INK)
    lowest = int(np.argmin(S))
    ax.annotate(f"lowest S {S[lowest]:.4f} (worst group {worst[lowest]:.3f})", (n[lowest], shown[lowest]),
                xytext=(8, -14), textcoords="offset points", fontsize=9, color=INK)
    ax.set_ylim(*lim); ax.set_xlim(0, len(rows) + 6)
    ax.set_xlabel("candidate"); ax.set_ylabel("S, temperature and rain loss vs r37 (clipped to 0.96–1.06)",
                                               color=INK_SOFT)
    ax.set_title(f"{a.title} · {len(rows)} candidates", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110, facecolor=SURFACE)
    print("wrote", a.out, "| passing candidates:", int((ok & (S < 0.995)).sum()))


if __name__ == "__main__":
    main()
