"""Base map for the army tracker from the original drawing layers (4401 x 2037):
the user's height tiers softened toward paper, water, a coastline, rivers,
roads and settlement markers.

    python -I scripts/ravages_basemap.py ravages/base.webp
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ORIG = Path(__file__).resolve().parents[1] / "data" / "source" / "original"


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)


def main(out):
    t = Image.open(ORIG / "terrain.png")
    idx = np.array(t)
    pal = np.array(t.getpalette()).reshape(-1, 3)[:4].astype(float)
    land = idx < 4
    paper = rgb("#f1ece1")
    tiers = pal * 0.5 + paper * 0.5
    img = np.empty(idx.shape + (3,))
    img[:] = rgb("#c4d3db")
    for k in range(4):
        img[idx == k] = tiers[k]
    # water gets a little deeper away from the coast
    d = ndi.distance_transform_edt(~land)
    img[~land] = (rgb("#c4d3db")[None] * (1 - np.clip(d / 120, 0, 1)[..., None] * 0.35)
                  + rgb("#9fb6c4")[None] * (np.clip(d / 120, 0, 1)[..., None] * 0.35))[~land]
    coast = land & ~ndi.binary_erosion(land, iterations=1)
    img[coast] = img[coast] * 0.45 + rgb("#4a5a64") * 0.55

    def over(color, alpha):
        nonlocal img
        a = np.clip(alpha, 0, 1)[..., None]
        img = img * (1 - a) + rgb(color)[None, None] * a

    riv = np.array(Image.open(ORIG / "rivers.png"))[..., 3] / 255.0
    over("#5f84ad", riv * 0.9)
    rs = np.array(Image.open(ORIG / "roads_settlements.png"))
    a = rs[..., 3] / 255.0
    road = (rs[..., 0] > 200) & (rs[..., 1] > 80) & (rs[..., 1] < 140) & (rs[..., 2] < 60)
    over("#8b5e3c", a * road * 0.65)
    town = (rs[..., :3].min(-1) > 200)
    ring = ndi.binary_dilation(town & (a > 0.5), iterations=1) & ~(town & (a > 0.5))
    over("#2b2a27", ring * 0.8)
    over("#fbf8f1", a * town)
    special = (a > 0.5) & ~road & ~town
    img[special] = rs[..., :3][special]
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out, lossless=False, quality=92, method=6)
    print(out, Path(out).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1])
