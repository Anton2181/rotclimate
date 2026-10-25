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
    ap.add_argument("--reference-label",default="reference")
    a = ap.parse_args()
    rows = [json.loads(line) for line in (a.search / "evals.jsonl").read_text().splitlines(keepends=True)
            if line.strip() and line.endswith('\n')]
    if not rows or 'S' not in rows[0]:
        raise ValueError('A successful reference control is required before plotting')
    n = np.arange(1, len(rows) + 1)
    S = np.array([r.get('S',np.nan) for r in rows])
    worst = np.array([max(r.get('groups',{}).values(),default=np.inf) for r in rows])
    component_ok=np.array([r.get('T',np.inf)<=1.01*rows[0]['T'] and
                           r.get('P',np.inf)<=1.01*rows[0]['P'] for r in rows])
    ok = np.isfinite(S) & (worst <= 1.0) & component_ok
    passing=ok & (S<=.995) & (n>1)
    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor=SURFACE, constrained_layout=True)
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(colors=INK_SOFT, length=0)
    lim = (0.96, 1.06)
    shown = np.where(np.isfinite(S),np.clip(S, *lim),lim[1])
    ax.scatter(n[~ok], shown[~ok], s=36, color=ORANGE, edgecolor=SURFACE, lw=1.2, zorder=3,
               label="fails a group, component or numerical protection")
    ax.scatter(n[ok], shown[ok], s=36, color=BLUE, edgecolor=SURFACE, lw=1.2, zorder=4,
               label="all group and component protections met")
    ax.axhline(1.0, color=INK_SOFT, lw=1); ax.axhline(0.995, color=INK_SOFT, lw=1, ls=":")
    ax.text(len(rows) + 0.5, 1.0, " "+a.reference_label, va="center", fontsize=9, color=INK_SOFT)
    ax.text(len(rows) + 0.5, 0.995, " gate", va="center", fontsize=9, color=INK_SOFT)
    best = int(np.argmin(np.where(passing, S, np.inf)))
    if passing.any():
        ax.annotate(f"best search-screen candidate: S {S[best]:.4f}", (n[best], shown[best]), xytext=(8, -14),
                    textcoords="offset points", fontsize=9, color=INK)
    else:
        ax.text(.02,.03,'No candidate meets the development selection limits yet',transform=ax.transAxes,
                color=INK_SOFT,fontsize=9)
    lowest = int(np.nanargmin(S))
    if lowest != best:
        align_left=n[lowest]<len(rows)/2
        ax.annotate(f"lowest S {S[lowest]:.4f} (worst group {worst[lowest]:.3f})", (n[lowest], shown[lowest]),
                    xytext=(8 if align_left else -8, -28), ha="left" if align_left else "right",
                    textcoords="offset points", fontsize=9, color=INK)
    ax.set_ylim(*lim); ax.set_xlim(0, len(rows) + 6)
    ax.set_xlabel("candidate, including initial control"); ax.set_ylabel(f"S, temperature and rain loss vs {a.reference_label} (clipped to 0.96–1.06)",
                                               color=INK_SOFT)
    ax.set_title(a.title if "candidates" in a.title else f"{a.title} · {len(rows)} candidates", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110, facecolor=SURFACE)
    print("wrote", a.out, "| search-screen candidates:", int(passing.sum()))


if __name__ == "__main__":
    main()
