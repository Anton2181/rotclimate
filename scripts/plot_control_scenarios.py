"""Figures for scripts/control_scenarios.py output.

    python3 -I scripts/plot_control_scenarios.py output/control/scenarios_free_fit

maps.png: effective control under six population scenarios (same scale as
the atlas's Political reach layer), unmarked towns as dots. polities.png:
each polity's people inside its drawn border and the share of them within
a day's march of a road or town, by occupation level and by placement.
"""
from __future__ import annotations

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

from polity.fields import LAYERS  # noqa: E402

SURFACE, INK, INK_SOFT, GRID, SEA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#d6e4f0"
BOUNDS = [0, 2, 5, 13, 22, 37, 50, 61, 78, 100.01]
CMAP = ListedColormap(["#4d1a17", "#8f3426", "#c8603a", "#e5a557", "#e8d98a", "#b7cf7a", "#7fb05a", "#4f8f4a", "#1f5f3a"])
# one colour per scenario across the figure; each panel's three validated all-pairs
LEVELS = [("frontier", "#eb6834"), ("central", "#2a78d6"), ("core", "#1baf7a")]
PLACES = [("central", "#2a78d6"), ("rural", "#e87ba4"), ("markets", "#008300")]
NAMES = {"frontier": "frontier occupation", "central": "central occupation", "core": "settled-core occupation"}
PLACE_NAMES = {"central": "dispersed (= central occupation)", "rural": "water and terrain", "markets": "market access"}


def main():
    out = Path(sys.argv[1])
    s = json.loads((out / "summary.json").read_text())
    z = np.load(out / "maps.npz")
    land = z["central_land"]; shape = land.shape
    borders = np.asarray(Image.open(LAYERS / "borders.png").convert("RGBA").resize((shape[1], shape[0]), Image.BOX))[..., 3] > 40
    plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": INK_SOFT,
                         "xtick.color": INK_SOFT, "ytick.color": INK_SOFT, "axes.edgecolor": GRID})
    panels = ["frontier", "central", "core", "rural", "markets", "cored"]
    fig, axes = plt.subplots(3, 2, figsize=(16, 11.5), constrained_layout=True, facecolor=SURFACE)
    norm = BoundaryNorm(BOUNDS, CMAP.N)
    for ax, key in zip(axes.ravel(), panels):
        r = s[key]
        ax.set_facecolor(SEA)
        im = ax.imshow(np.where(land, 100 * z[f"{key}_control"], np.nan), cmap=CMAP, norm=norm, interpolation="nearest")
        ax.imshow(np.where(borders, 1.0, np.nan), cmap=ListedColormap([INK]), alpha=0.55, interpolation="nearest")
        t = z[f"{key}_towns"]
        if len(t):
            ax.scatter(t[:, 1], t[:, 0], s=1.2, c=INK, linewidths=0, alpha=0.7)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{r['label']}: {r['people_M']:.0f} M people, {r['unmarked_towns']:,} unmarked towns\n"
                     f"land within a day {r['land_within_1_day']:.0%} · people within a day {r['people_within_1_day']:.0%}"
                     f" · held {r['held_land']:.0%}", loc="left", fontsize=9.5)
    cb = fig.colorbar(im, ax=axes, shrink=0.5, pad=0.01)
    cb.set_label("effective control, %  (exp(−days / 1 day) from the nearest road or town)")
    fig.savefig(out / "maps.png", dpi=100, facecolor=SURFACE)
    plt.close(fig)

    names = sorted(s["central"]["polities"], key=lambda n: -s["central"]["polities"][n]["people_in_border_M"])
    y = np.arange(len(names))
    fig, axes = plt.subplots(1, 3, figsize=(16, 7.5), sharey=True, constrained_layout=True, facecolor=SURFACE,
                             gridspec_kw=dict(width_ratios=[1.2, 1, 1]))
    ax = axes[0]
    for k, (key, colour) in enumerate(LEVELS):
        v = [s[key]["polities"][n]["people_in_border_M"] for n in names]
        ax.barh(y + (k - 1) * 0.27, v, height=0.25, color=colour, label=NAMES[key])
    ax.set_xscale("log"); ax.set_xlabel("people inside the drawn border, millions (log)")
    ax.set_title("People by occupation level", loc="left")
    for ax, group, labels, title in ((axes[1], LEVELS, NAMES, "Share of those people within a day:\nby occupation level"),
                                     (axes[2], PLACES, PLACE_NAMES, "... and by where the central total lives")):
        for key, colour in group:
            v = [100 * s[key]["polities"][n]["border_people_within_1_day"] for n in names]
            label = labels[key]
            ax.scatter(v, y, s=36, color=colour, edgecolors=SURFACE, linewidths=1.0, label=label, zorder=3)
        ax.set_xlim(0, 102); ax.set_xlabel("% of the polity's people within a day's march")
        ax.set_title(title, loc="left")
    for ax in axes:
        ax.set_facecolor(SURFACE); ax.grid(color=GRID, lw=0.6, axis="x")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=1, fontsize=8.5, frameon=False)
    axes[0].set_yticks(y, names); axes[0].invert_yaxis()
    fig.savefig(out / "polities.png", dpi=100, facecolor=SURFACE)
    print("wrote", out / "maps.png", out / "polities.png")


if __name__ == "__main__":
    main()
