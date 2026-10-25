"""Figure: people each polity claims (de jure) and holds (de facto), from an
atlas's data/polities.csv (polity/export.py).

    python3 -I scripts/plot_polity_people.py whittaker_fit [--fill 0]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLAIMED = "#2a78d6"
HELD = "#eb6834"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("atlas"); ap.add_argument("--fill", default="0")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [r for r in csv.DictReader(open(ROOT / f"atlases/{a.atlas}/data/polities.csv"))
            if r["gap_fill_days"] in (a.fill, a.fill + ".0")]
    rows.sort(key=lambda r: float(r["claimed_people"]))
    names = [r["polity"] for r in rows]
    claimed = np.array([float(r["claimed_people"]) for r in rows]) / 1e6
    held = np.array([float(r["held_people"]) for r in rows]) / 1e6
    unheld = np.array([float(r["claimed_unheld_people"]) for r in rows]) / 1e6
    beyond = np.array([float(r["held_outside_claim_people"]) for r in rows]) / 1e6
    fig, ax = plt.subplots(figsize=(12.5, 7.2), dpi=150)
    y = np.arange(len(rows))
    ax.hlines(y, np.minimum(claimed, held), np.maximum(claimed, held), color="#c3c2b7", lw=2, zorder=1)
    ax.scatter(claimed, y, s=46, color=CLAIMED, zorder=3, label="claimed (de jure)", edgecolors="#fcfcfb", linewidths=1.5)
    ax.scatter(held, y, s=46, color=HELD, zorder=3, label="held (de facto)", edgecolors="#fcfcfb", linewidths=1.5)
    ax.set_xscale("log")
    ax.set_yticks(y, names, fontsize=9, color="#0b0b0b")
    for yi, c, h, u, b in zip(y, claimed, held, unheld, beyond):
        note = []
        if u >= 0.05:
            note.append(f"{u:.1f} M claimed, unheld")
        if b >= 0.05:
            note.append(f"{b:.1f} M held beyond the claim")
        ax.text(1.02, yi, f"{h:.1f} M held of {c:.1f} M" + (" · " + "; ".join(note) if note else ""),
                va="center", fontsize=7.5, color="#52514e", transform=ax.get_yaxis_transform(), clip_on=False)
    ax.set_xlim(0.25, 40)
    ax.set_xticks([0.3, 1, 3, 10, 30], ["0.3 M", "1 M", "3 M", "10 M", "30 M"])
    ax.tick_params(axis="x", labelsize=8, colors="#52514e"); ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color="#e4e2dc", lw=0.6); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    fill = float(a.fill)
    ax.set_title(f"People each polity claims and holds, c. AD 200 ({a.atlas.replace('_', ' ')} atlas, central occupation, "
                 f"gap fill {fill:g} days)", fontsize=10.5, loc="left", color="#0b0b0b")
    fig.subplots_adjust(left=0.17, right=0.6, top=0.93, bottom=0.07)
    out = ROOT / f"output/polity_map/{a.atlas}_people_fill{int(round(fill * 10)):02d}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out); print(out)


if __name__ == "__main__":
    main()
