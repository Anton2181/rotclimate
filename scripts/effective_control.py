"""Effective control on the campaign map: figures and statistics.

    python3 -I scripts/effective_control.py --atlas atlases/free_fit --out output/control/free_fit

The fields come from polity/fields.py (travel model in polity/control.py):
the marked roads, ferry routes and settlements of the campaign map, plus the
unmarked seats a populated countryside implies (one per 40,000 people,
polity/control.py:unmarked_days). Writes
summary.json, settlements.json and the maps.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from PIL import Image  # noqa: E402

from polity.control import control  # noqa: E402
from polity.fields import LAYERS, compute  # noqa: E402

INK, SURFACE, SEA = "#1b262c", "#fcfcfb", "#d6e4f0"
MARKERS = (("fortified town", 6, "o", "#ffffff"), ("fortified city", 16, "o", "#ffffff"),
           ("imperial fort", 14, "s", "#b200ff"), ("imperial monastery", 14, "s", "#00a86b"),
           ("major imperial city", 34, "o", "#b200ff"), ("imperial capital", 80, "s", "#b200ff"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    r = compute(a.atlas)
    f, land, road, ferry, towns = r["fields"], r["land"], r["road"], r["ferry"], r["towns"]
    shape = land.shape; area = r["cell_km"] ** 2
    days, ctl = f["days_open"], r["control_open"]
    core, frontier = r["core"], r["frontier"]

    def share_within(mask, limit, key="days_open"):
        v = f[key][mask & land]
        return float(np.mean(v <= limit)) if v.size else None
    summary = dict(cell_km=r["cell_km"],
                   settlements={k: sum(t["kind"] == k for t in towns) for k in sorted({t["kind"] for t in towns})},
                   road_cells=int(road.sum()), ferry_cells=int(ferry.sum()),
                   land=dict(within_1_day=share_within(land, 1), within_2_days=share_within(land, 2),
                             within_3_days=share_within(land, 3), winter_within_1_day=share_within(land, 1, "days_winter")),
                   commanderies={name: dict(cells=int(m.sum()), mean_days=float(np.mean(days[m])),
                                            mean_control=float(np.mean(ctl[m])),
                                            capital_days=float(np.mean(f["capital_days_open"][m])))
                                 for name, m in (("core", core), ("frontier", frontier))},
                   polities={}, de_facto={})
    best = f["polity_best"]
    for k, name in enumerate(r["polity_names"]):
        own = np.isin(r["polity_ids"], r["groups"][name]) & land
        mine = r["held"] & (best == k)
        summary["polities"][name] = dict(
            drawn_km2=float(own.sum() * area), within_1_day=share_within(own, 1), within_2_days=share_within(own, 2),
            mean_control=float(ctl[own].mean()), held_km2=float(mine.sum() * area),
            held_beyond_border_km2=float((mine & ~own).sum() * area),
            contested_km2=float((r["contested"] & (best == k)).sum() * area))
    summary["de_facto"] = dict(held_share_of_land=float(r["held"].sum() / land.sum()),
                               contested_share_of_land=float(r["contested"].sum() / land.sum()))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    (a.out / "settlements.json").write_text(json.dumps(towns, indent=1))
    print(json.dumps({k: summary[k] for k in ("settlements", "land", "commanderies", "de_facto")}, indent=1))

    plt.rcParams.update({"font.size": 10, "text.color": INK, "figure.facecolor": SURFACE})
    bounds = [0, 2, 5, 13, 22, 37, 50, 61, 78, 100.01]
    cmap = ListedColormap(["#4d1a17", "#8f3426", "#c8603a", "#e5a557", "#e8d98a", "#b7cf7a", "#7fb05a", "#4f8f4a", "#1f5f3a"])
    norm = BoundaryNorm(bounds, cmap.N)
    borders = np.asarray(Image.open(LAYERS / "borders.png").convert("RGBA").resize((shape[1] * 2, shape[0] * 2), Image.BOX))[..., 3] > 40
    yy, xx = np.arange(shape[0]) + 0.5, np.arange(shape[1]) + 0.5
    ext = (0, shape[1], shape[0], 0)

    def network(ax):
        for mask, colour, size in ((road, "#5a2a12", 0.14), (ferry, "#ff6a00", 1.5)):
            py, px = np.nonzero(mask)
            ax.scatter(px + 0.5, py + 0.5, s=size, c=colour, marker="s", linewidths=0, alpha=0.8)
        for kind, size, marker, colour in MARKERS:
            pts = [(t["col"], t["row"]) for t in towns if t["kind"] == kind]
            if pts:
                xs, ys = zip(*pts)
                ax.scatter(np.array(xs) + 0.5, np.array(ys) + 0.5, s=size, c=colour, marker=marker, linewidths=0.6,
                           edgecolors="#ffd800" if kind in ("major imperial city", "imperial capital") else INK, label=kind)

    for key, title in (("days_open", "Effective control beyond the roads and towns, snow-free season"),
                       ("days_winter", "Effective control beyond the roads and towns, with the winter's snow")):
        fig, ax = plt.subplots(figsize=(16, 8), constrained_layout=True)
        ax.set_facecolor(SEA)
        im = ax.imshow(np.where(land, 100 * control(f[key]), np.nan), cmap=cmap, norm=norm, interpolation="nearest", extent=ext)
        ax.imshow(np.where(borders, 1.0, np.nan), cmap=ListedColormap([INK]), alpha=0.6, interpolation="nearest", extent=ext)
        network(ax)
        ax.contour(xx, yy, np.where(land, f[key], 99), levels=[1, 2, 3], colors=[INK] * 3,
                   linewidths=[0.9, 0.6, 0.4], linestyles=["solid", "dashed", "dotted"])
        ax.set_xlim(0, shape[1]); ax.set_ylim(shape[0], 0); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title + " · lines: 1, 2 and 3 days on foot from the nearest road or settlement, marked or unmarked",
                     loc="left")
        fig.colorbar(im, ax=ax, shrink=0.7, pad=0.01).set_label("effective control, % (exp(-days / 1 day))")
        ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
        fig.savefig(a.out / f"control_{key.split('_')[1]}.png", dpi=110, facecolor=SURFACE)
        plt.close(fig)

    img = np.ones(shape + (3,)) * np.array([0.93, 0.91, 0.86])
    strength = np.clip(np.exp(-np.nan_to_num(f["polity_best_days"], nan=99, posinf=99)), 0, 1)
    for k, name in enumerate(r["polity_names"]):
        m = land & (best == k)
        img[m] = np.array(r["polity_rgb"][name]) / 255.0 * strength[m, None] + np.array([0.93, 0.91, 0.86]) * (1 - strength[m, None])
    img[~land] = [0.84, 0.89, 0.94]
    fig, ax = plt.subplots(figsize=(16, 8), constrained_layout=True)
    ax.imshow(img, interpolation="nearest", extent=ext)
    ax.imshow(np.where(borders, 1.0, np.nan), cmap=ListedColormap([INK]), alpha=0.75, interpolation="nearest", extent=ext)
    cy, cx = np.nonzero(r["contested"][::3, ::3])
    ax.scatter(cx * 3 + 1.5, cy * 3 + 1.5, s=1.2, c=INK, marker="x", linewidths=0.4)
    for k, name in enumerate(r["polity_names"]):
        m = r["held"] & (best == k)
        if m.sum() > 300:
            ry, rx = np.nonzero(m)
            ax.text(np.median(rx), np.median(ry), name, fontsize=7.5, ha="center", va="center", color=INK,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Who reaches where: each place takes the polity whose own roads, towns and unmarked seats are nearest in "
                 "days; pale = weak reach, x = contested (a rival within half a day); dark lines: the drawn borders",
                 loc="left", fontsize=10)
    fig.savefig(a.out / "de_facto.png", dpi=110, facecolor=SURFACE)
    plt.close(fig)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
