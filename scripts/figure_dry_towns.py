"""Proposed towns in the painted hot-dry south before and after the dry-town water rule.

    python -I scripts/figure_dry_towns.py BEFORE.geojson AFTER.geojson OUT.png [--background atlases/earth_fit/data/corrected/koppen.webp]

Town positions are in the settlement map's pixels (4401 x 2037); the painted
zones come from rotclimate.geography.target_fullres (2000 x 926).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402
from rotclimate.geography import target_fullres  # noqa: E402

SRC_W = 4401.0


def towns(path):
    f = json.loads(Path(path).read_text())["features"]
    xy = np.array([t["geometry"]["coordinates"] for t in f]) * (2000.0 / SRC_W)
    return xy, np.array([not t["properties"]["marked"] for t in f])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before"); ap.add_argument("after"); ap.add_argument("out")
    ap.add_argument("--background", default=str(ROOT / "atlases/earth_fit/data/corrected/koppen.webp"))
    ap.add_argument("--labels", default="before the rule|after the rule")
    a = ap.parse_args()
    target = target_fullres()
    hot = target == 7
    ys, xs = np.nonzero(hot)
    y0, y1 = max(0, ys.min() - 40), min(hot.shape[0], ys.max() + 40)
    x0, x1 = max(0, xs.min() - 40), min(hot.shape[1], xs.max() + 40)
    bg = np.asarray(Image.open(a.background).convert("RGB").resize((hot.shape[1], hot.shape[0])))
    fig, axes = plt.subplots(1, 2, figsize=(13, 13 * (y1 - y0) / (2 * (x1 - x0)) + 1.2), constrained_layout=True)
    counts = {}
    for ax, path, label in zip(axes, (a.before, a.after), a.labels.split("|")):
        xy, un = towns(path)
        ix = np.clip(xy[:, 0].astype(int), 0, hot.shape[1] - 1); iy = np.clip(xy[:, 1].astype(int), 0, hot.shape[0] - 1)
        inside = hot[iy, ix]
        n_hot = int((un & inside).sum()); counts[label] = dict(proposed_total=int(un.sum()), proposed_in_hot_dry=n_hot)
        ax.imshow(bg, alpha=0.55)
        ax.contour(hot, levels=[0.5], colors="#7a4a00", linewidths=1.2)
        sel = un & (xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)
        ax.scatter(xy[sel & inside, 0], xy[sel & inside, 1], s=16, c="#b2182b", edgecolors="white", linewidths=0.5, label="proposed town in the painted hot-dry zone")
        ax.scatter(xy[sel & ~inside, 0], xy[sel & ~inside, 1], s=10, c="#2b2b2b", edgecolors="white", linewidths=0.4, label="proposed town elsewhere")
        ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{label}: {n_hot} proposed towns inside the painted hot-dry zone", fontsize=11)
    axes[0].legend(loc="lower left", fontsize=8, framealpha=0.85)
    fig.suptitle("Proposed (unmarked) towns in the south of the Earth-fit map; brown outline = painted hot-dry zone; background = Köppen", fontsize=10)
    fig.savefig(a.out, dpi=130)
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
