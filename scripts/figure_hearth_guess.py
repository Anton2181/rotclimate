"""The current best guess for where farming reached the fantasy map (language layer 2d), on the
model's own picture of the map and its invented surroundings (around_koppen.webp, layout 1 of 3).

    python -I scripts/figure_hearth_guess.py atlases/earth_fit output/language_areas_20261101/layer2d OUT.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402
from PIL import Image  # noqa: E402

MARGIN = 296   # around_koppen.webp: the 1000 x 463 map grid with ~1,100 km on every side


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("atlas", type=Path); ap.add_argument("run", type=Path); ap.add_argument("out", type=Path)
    a = ap.parse_args()
    summ = json.loads((a.run / "hearths_map.json").read_text())
    im = np.asarray(Image.open(a.atlas / "data" / "around_koppen.webp").convert("RGB")).astype(float) / 255.0
    H, W = im.shape[:2]
    # soften the climate colours so the guess reads first
    grey = im.mean(-1, keepdims=True)
    base = 0.55 * im + 0.45 * (0.35 * grey + 0.65)
    fig, ax = plt.subplots(figsize=(13, 9.2), constrained_layout=True)
    ax.imshow(base, interpolation="bilinear")
    x0, y0, x1, y1 = MARGIN, MARGIN, W - MARGIN, H - MARGIN
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], ls="--", color="#5b4a2f", lw=1.2)
    ax.text(x0 + 6, y0 - 8, "the drawn map", color="#5b4a2f", fontsize=9, va="bottom")
    b = summ["beyond"]
    # entry arrows from beyond the edge; width by the fitted land share of that sector
    # short arrows that stop clear of the land-share labels printed on the base picture
    arrows = [("south-west", b["south"], (x0 + 0.22 * (x1 - x0), y1 + 100), (x0 + 0.22 * (x1 - x0), y1 - 55), "#b8432b", 1.0,
               f"From the south-west: {100 * b['south']:.0f} % land beyond,\nlower latitudes (likeliest)", (-24, -60)),
              ("south-east", b["southeast"], (x0 + 0.70 * (x1 - x0), y1 + 100), (x0 + 0.70 * (x1 - x0), y1 - 45), "#b8432b", 0.85,
               f"From the south-east: {100 * b['southeast']:.0f} % land,\nlower latitudes", (24, -40)),
              ("east", b["east"], (W - 25, y0 + 0.22 * (y1 - y0)), (x1 - 30, y0 + 0.22 * (y1 - y0)), "#8a7a6a", 0.5,
               f"East: {100 * b['east']:.0f} % land,\nbut the map's own latitudes", (-10, -70))]
    for name, share, start, end_, col, alpha, label, (dx, dy) in arrows:
        ax.add_patch(FancyArrowPatch(start, end_, arrowstyle="-|>", mutation_scale=28 + 30 * share, lw=4 + 12 * share,
                                     color=col, alpha=alpha))
        tx, ty = start
        ax.text(tx + dx, ty + dy, label, fontsize=10, ha="left" if dx > 0 else "right", va="center", color="#3a1f15",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.85))
    # on-map candidates (grid row/col + margin)
    c = summ["candidates"]
    marks = [(c[0], "1  West coast (35.8° N): best guess\n    if farming began on the map", "#c22f2f", "*", 30),
             (c[2], "2  South coast (29.7° N): runner-up", "#e08a2b", "*", 24),
             (c[1], "North edge (48.6° N): productive, but no\nEarth homeland lies this far north", "#7f7f7f", "X", 14)]
    offsets = [(-40, 70), (40, 40), (40, -55)]
    for (cand, text, col, mk, ms), (dx, dy) in zip(marks, offsets):
        x, y = cand["col"] + MARGIN, cand["row"] + MARGIN
        ax.plot(x, y, marker=mk, ms=ms, mfc=col, mec="white", mew=1.4, zorder=5)
        ax.annotate(text, (x, y), xytext=(x + dx, y + dy), fontsize=10, color="#222",
                    arrowprops=dict(arrowstyle="-", color="#555", lw=0.8),
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9),
                    ha="left" if dx > 0 else "right")
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"Best current guess: farming came in from beyond the map ({100 * summ['p_no_hearth']:.0f} %), most likely from the south;\n"
                 f"if it began on the map ({100 - 100 * summ['p_no_hearth']:.0f} %), the west coast. Expected independent hearths on the map: "
                 f"{summ['expected_hearths']:.2f} (Earth's rate, weighted by productivity, AUC 0.78).", fontsize=11)
    fig.text(0.01, 0.005, "Colours: the model's Köppen climates. Outside the dashed box: one of the model's three invented layouts of the "
             "surroundings; only each side's land share is fitted, the coastlines are random. Arrow widths follow those land shares.",
             fontsize=8.5, color="#444")
    fig.savefig(a.out, dpi=95)


if __name__ == "__main__":
    main()
