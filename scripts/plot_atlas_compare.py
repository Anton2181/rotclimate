"""How the three climate calibrations move people and political reach.

    python3 -I scripts/plot_atlas_compare.py --out output/control/atlas_compare

Reads the central-occupation runs of scripts/control_scenarios.py for the
free, Earth and Whittaker fits (output/control/scenarios_<atlas>/) and
output/control/atlas_climate_by_polity.json. Writes:
maps.png (people and effective control per atlas), shift.png (people per km²
of the Earth and Whittaker fits over the free fit) and polities.png (each
polity's people, the share of them within a day's march, and its rain).
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

from polity.fields import LAYERS  # noqa: E402

SURFACE, INK, INK_SOFT, GRID, SEA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#d6e4f0"
ATLASES = [("free_fit", "Free fit", "#2a78d6"), ("earth_fit", "Earth fit", "#eb6834"), ("whittaker_fit", "Whittaker fit", "#1baf7a")]
CONTROL_BOUNDS = [0, 2, 5, 13, 22, 37, 50, 61, 78, 100.01]
CONTROL = ListedColormap(["#4d1a17", "#8f3426", "#c8603a", "#e5a557", "#e8d98a", "#b7cf7a", "#7fb05a", "#4f8f4a", "#1f5f3a"])
DENSITY_BOUNDS = [0, 2, 5, 10, 20, 40, 80, 160, 1e9]                    # people per km²
DENSITY = ListedColormap(["#ece9e2", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
SHIFT_BOUNDS = [-9, -2, -1, -0.4, 0.4, 1, 2, 9]                          # log2 ratio
SHIFT = ListedColormap(["#8c1f1e", "#e34948", "#f2a7a3", "#f0efec", "#86b6ef", "#2a78d6", "#0d366b"])


def style(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": INK_SOFT,
                         "xtick.color": INK_SOFT, "ytick.color": INK_SOFT, "axes.edgecolor": GRID})
    S, Z = {}, {}
    for key, _, _ in ATLASES:
        base = ROOT / "output/control" / f"scenarios_{key}"
        S[key] = json.loads((base / "summary.json").read_text())["central"]
        Z[key] = np.load(base / "maps.npz")
    land = Z["free_fit"]["central_land"]; shape = land.shape
    borders = np.asarray(Image.open(LAYERS / "borders.png").convert("RGBA").resize((shape[1], shape[0]), Image.BOX))[..., 3] > 40
    edge = np.where(borders, 1.0, np.nan)

    fig, axes = plt.subplots(2, 3, figsize=(18, 6.6), constrained_layout=True, facecolor=SURFACE)
    for col, (key, label, _) in enumerate(ATLASES):
        z, s = Z[key], S[key]
        ax = axes[0, col]; ax.set_facecolor(SEA)
        imd = ax.imshow(np.where(land, z["central_density"], np.nan), cmap=DENSITY, norm=BoundaryNorm(DENSITY_BOUNDS, DENSITY.N),
                        interpolation="nearest")
        ax.imshow(edge, cmap=ListedColormap([INK]), alpha=0.5, interpolation="nearest")
        ax.set_title(f"{label}: {s['people_M']:.0f} M people, {s['unmarked_towns']:,} unmarked towns", loc="left", fontsize=10)
        style(ax)
        ax = axes[1, col]; ax.set_facecolor(SEA)
        imc = ax.imshow(np.where(land, 100 * z["central_control"], np.nan), cmap=CONTROL,
                        norm=BoundaryNorm(CONTROL_BOUNDS, CONTROL.N), interpolation="nearest")
        ax.imshow(edge, cmap=ListedColormap([INK]), alpha=0.5, interpolation="nearest")
        ax.set_title(f"land within a day {s['land_within_1_day']:.0%} · people within a day {s['people_within_1_day']:.0%}"
                     f" · held {s['held_land']:.0%}", loc="left", fontsize=10)
        style(ax)
    fig.colorbar(imd, ax=axes[0], shrink=0.8, pad=0.01, ticks=DENSITY_BOUNDS[:-1]).set_label("people per km² (central)")
    fig.colorbar(imc, ax=axes[1], shrink=0.8, pad=0.01).set_label("effective control, %")
    fig.savefig(a.out / "maps.png", dpi=100, facecolor=SURFACE)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(16, 4.4), constrained_layout=True, facecolor=SURFACE)
    ref = Z["free_fit"]["central_density"]
    for ax, (key, label, _) in zip(axes, ATLASES[1:]):
        d = Z[key]["central_density"]
        ratio = np.log2((d + 0.5) / (ref + 0.5))
        ax.set_facecolor(SEA)
        im = ax.imshow(np.where(land, ratio, np.nan), cmap=SHIFT, norm=BoundaryNorm(SHIFT_BOUNDS, SHIFT.N), interpolation="nearest")
        ax.imshow(edge, cmap=ListedColormap([INK]), alpha=0.5, interpolation="nearest")
        ax.set_title(f"{label} against the free fit: people per km²", loc="left", fontsize=10)
        style(ax)
    cb = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.01, ticks=[-2, -1, -0.4, 0.4, 1, 2])
    cb.ax.set_yticklabels(["¼×", "½×", "0.75×", "1.3×", "2×", "4×"])
    cb.set_label("ratio to the free fit")
    fig.savefig(a.out / "shift.png", dpi=100, facecolor=SURFACE)
    plt.close(fig)

    clim = json.loads((ROOT / "output/control/atlas_climate_by_polity.json").read_text())
    names = sorted(S["free_fit"]["polities"], key=lambda n: -S["free_fit"]["polities"][n]["people_in_border_M"])
    y = np.arange(len(names))
    fig, axes = plt.subplots(1, 3, figsize=(17, 7.6), sharey=True, constrained_layout=True, facecolor=SURFACE,
                             gridspec_kw=dict(width_ratios=[1.2, 1, 1]))
    for k, (key, label, colour) in enumerate(ATLASES):
        axes[0].barh(y + (k - 1) * 0.27, [S[key]["polities"][n]["people_in_border_M"] for n in names], height=0.25,
                     color=colour, label=label)
        axes[1].scatter([100 * S[key]["polities"][n]["border_people_within_1_day"] for n in names], y, s=36, color=colour,
                        edgecolors=SURFACE, linewidths=1.0, label=label, zorder=3)
        axes[2].scatter([clim[n]["Pann"][k] for n in names], y, s=36, color=colour, edgecolors=SURFACE, linewidths=1.0,
                        label=label, zorder=3)
    axes[0].set_xscale("log"); axes[0].set_xlabel("people inside the drawn border, millions (central, log)")
    axes[0].set_title("People", loc="left")
    axes[1].set_xlim(0, 102); axes[1].set_xlabel("% of the polity's people within a day's march")
    axes[1].set_title("Reach", loc="left")
    axes[2].set_xscale("log"); axes[2].set_xlabel("mean annual rain inside the border, mm (log)")
    axes[2].set_title("The driver: rain", loc="left")
    for ax in axes:
        ax.set_facecolor(SURFACE); ax.grid(color=GRID, lw=0.6, axis="x")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=8.5, frameon=False)
    axes[0].set_yticks(y, names); axes[0].invert_yaxis()
    fig.savefig(a.out / "polities.png", dpi=100, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
