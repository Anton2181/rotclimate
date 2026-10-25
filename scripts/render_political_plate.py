"""An atlas plate of political control: de facto holdings, de jure claims,
claimed-but-unheld and contested land, trade routes and towns, at the source
map's full resolution, from the arrays polity/export.py caches.

    python3 -I scripts/render_political_plate.py whittaker_fit [--fill 0] [--out output/polity_map/plate.png]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from polity import render as R                      # noqa: E402
from polity import vectors as V                     # noqa: E402
from polity.fields import LAYERS, rgba              # noqa: E402
from polity.mapdata import chaikin                  # noqa: E402

INK = "#2a2320"
LAND_ROUTE = "#7a2e12"
SEA_ROUTE = "#1d4a7a"
SOFT_ALPHA = 0.46


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("atlas")
    ap.add_argument("--fill", type=float, default=0.0)
    ap.add_argument("--out")
    ap.add_argument("--scale", type=float, default=1.0, help="output size relative to the source map")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import patheffects as pe
    from matplotlib.collections import LineCollection
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import Patch, Rectangle
    from matplotlib.lines import Line2D

    z = np.load(ROOT / f"output/polity_map/{a.atlas}.npz", allow_pickle=False)
    meta = json.loads((ROOT / f"atlases/{a.atlas}/data/atlas.json").read_text())
    man = json.loads((LAYERS / "manifest.json").read_text())
    W0, H0 = man["width"], man["height"]
    W, H = int(W0 * a.scale), int(H0 * a.scale)
    gh, gw = z["land"].shape
    sx, sy = W / gw, H / gh
    tag = f"{int(round(a.fill * 10)):02d}"
    names = [str(n) for n in z["names"]]
    cols = z["rgb"] / 255.0
    from rotclimate.geography import source_layers
    coast = source_layers()["land"]
    old = R.FILL_ALPHA
    R.FILL_ALPHA = SOFT_ALPHA
    base = R.defacto_rgb(z[f"held_by_{tag}"], z["claim"], z[f"contested_{tag}"], z["second"], cols, z["elev"], coast,
                         rgba("borders.png"), (W, H), period=max(7, int(W / 420)))
    R.FILL_ALPHA = old
    # the source map's own rivers, in blue
    riv = np.asarray(Image.open(ROOT / "data/source/original/rivers.png").convert("RGBA").resize((W, H), Image.LANCZOS),
                     float)[..., 3:4] / 255.0
    base = base * (1 - 0.8 * riv) + np.array([0.33, 0.52, 0.72]) * 0.8 * riv

    dpi = 200
    fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    ax.imshow(base, extent=(0, W, H, 0), interpolation="bilinear")
    lw = W / 4401
    # trade routes
    cc, pc, fl = z["e_child"], z["e_parent"], z["e_flow"]
    water = z["water"].ravel()
    qs = np.quantile(fl, [0.80, 0.95, 0.99])
    for thr, width, alpha in ((qs[0], 0.9, 0.55), (qs[1], 1.8, 0.7), (qs[2], 3.2, 0.85)):
        segs_l, segs_s = [], []
        for nodes, _ in V.chains(cc, pc, fl, thr):
            yx = np.array([divmod(int(n), gw) for n in nodes])
            pts = chaikin(np.column_stack([(yx[:, 1] + .5) * sx, (yx[:, 0] + .5) * sy]), 3)
            (segs_s if water[np.asarray(nodes)].mean() > 0.5 else segs_l).append(pts)
        ax.add_collection(LineCollection(segs_l, colors=LAND_ROUTE, linewidths=width * lw * 2, alpha=alpha,
                                         capstyle="round", joinstyle="round"))
        ax.add_collection(LineCollection(segs_s, colors=SEA_ROUTE, linewidths=width * lw * 2, alpha=alpha,
                                         linestyles=(0, (4, 2)), capstyle="round"))
    # towns: size by the people they serve
    towns = z["towns"]; mass = z["t_mass"]; kinds = [str(k) for k in z["kinds"]]
    big = np.quantile(mass, [0.5, 0.9, 0.98])
    order = np.argsort(mass)
    xs = (towns[order, 1] + .5) * sx; ys = (towns[order, 0] + .5) * sy
    cls = np.searchsorted(big, mass[order])
    size = (np.array([3.0, 6.0, 11.0, 18.0])[cls] * lw * 4) ** 1.0
    marked = np.array([kinds[i] != "unmarked town" for i in order])
    ax.scatter(xs[~marked], ys[~marked], s=size[~marked], c="#fbf8f0", edgecolors="#555", linewidths=0.4 * lw * 2,
               zorder=5)
    ax.scatter(xs[marked], ys[marked], s=size[marked] * 1.6, c="#fbf8f0", edgecolors=INK, linewidths=0.9 * lw * 2,
               zorder=6)
    # polity names at the most interior point of each polity's largest held area
    font = FontProperties(fname="/usr/share/fonts/truetype/freefont/FreeSerif.ttf")
    held = z[f"held_by_{tag}"]
    for k, name in enumerate(names):
        m = held == k
        if m.sum() < 30:
            continue
        lab, n = ndi.label(m)
        biggest = 1 + int(np.argmax(np.bincount(lab.ravel())[1:]))
        dist = ndi.distance_transform_edt(lab == biggest)
        y, x = np.unravel_index(int(np.argmax(dist)), dist.shape)
        fs = float(np.clip(5 + 1.1 * np.sqrt(m.sum()) / 6, 6, 20)) * lw * 2.2
        ax.text((x + .5) * sx, (y + .5) * sy, name.upper(), fontproperties=font, fontsize=fs, color=INK, ha="center",
                va="center", zorder=8, alpha=0.9,
                path_effects=[pe.withStroke(linewidth=fs * 0.28, foreground="#f6f2e8", alpha=0.85)])
    # legend
    paper = R.PAPER
    swatch = lambda k: tuple(paper * (1 - SOFT_ALPHA) + cols[k] * SOFT_ALPHA)
    handles = [Patch(facecolor=swatch(0), edgecolor="none", label="held (de facto): the holder's colour"),
               Patch(facecolor=tuple(paper), edgecolor=tuple(cols[0]), hatch="////",
                     label="claimed, not held: the claimant's colour, hatched"),
               Patch(facecolor=swatch(0), edgecolor="#555", hatch="\\\\\\\\", label="contested: a rival within half a day"),
               Line2D([], [], color=tuple(R.BORDER), lw=1.4, label="claims and provinces (de jure, as painted)"),
               Line2D([], [], color=LAND_ROUTE, lw=3, label="trade by road and river (width: traffic)"),
               Line2D([], [], color=SEA_ROUTE, lw=2, ls=(0, (4, 2)), label="trade by sea"),
               Line2D([], [], marker="o", ls="none", markerfacecolor="#fbf8f0", markeredgecolor=INK, markersize=7,
                      label="marked town (size: people served)"),
               Line2D([], [], marker="o", ls="none", markerfacecolor="#fbf8f0", markeredgecolor="#555", markersize=4,
                      label="suggested unmarked town")]
    leg = ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.012, 0.03), frameon=True, fontsize=8 * lw * 2.2,
                    prop=FontProperties(fname="/usr/share/fonts/truetype/freefont/FreeSerif.ttf", size=8 * lw * 2.2),
                    title=f"Political reach c. AD 200 · gap fill {a.fill:g} days", title_fontproperties=FontProperties(
                        fname="/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf", size=9 * lw * 2.2))
    leg.get_frame().set_facecolor("#f6f2e8"); leg.get_frame().set_edgecolor(INK); leg.get_frame().set_alpha(0.92)
    # scale bar: miles per source pixel
    mi_px = meta["mi_per_px"] * meta["width"] / W
    bar_mi = 200
    bx, by = W * 0.86, H * 0.965
    L = bar_mi / mi_px
    for i in range(4):
        ax.add_patch(Rectangle((bx + i * L / 4, by), L / 4, H * 0.006, facecolor=INK if i % 2 == 0 else "#f6f2e8",
                               edgecolor=INK, lw=0.6 * lw * 2, zorder=9))
    ax.text(bx + L / 2, by - H * 0.008, f"{bar_mi} miles", ha="center", va="bottom", fontproperties=font,
            fontsize=8 * lw * 2.2, color=INK, zorder=9)
    out = Path(a.out) if a.out else ROOT / f"output/polity_map/{a.atlas}_political_fill{tag}.png"
    fig.savefig(out, dpi=dpi)
    print("plate written to", out)


if __name__ == "__main__":
    main()
