"""Preview: forager language territories (layer 1 model) on an atlas's FORGE density, with the drawn de jure polity borders on top.

    python -I scripts/figure_language_preview.py atlases/earth_fit OUT.png [--sub corrected] [--nmax 3000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from figure_lifeways import load  # noqa: E402
from language_areas_earth import simulate_fast  # noqa: E402

SRC_W = 4401.0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("atlas", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--sub", default="corrected"); ap.add_argument("--nmax", type=float, default=3000.0); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    f = load(a.atlas / "data", a.sub)
    land = f["land_fraction"] > 0; h, w = land.shape
    K = (f["density_people_km2"] * f["cell_area_km2"])[land]
    ys, xs = np.nonzero(land); index = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    nbrs = [[index[(y + dy, x + dx)] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (y + dy, x + dx) in index] for y, x in zip(ys, xs)]
    coords = np.column_stack([xs, ys]).astype(float)
    counts = []
    for s in range(10):
        o, g, e = simulate_fast(K, nbrs, coords, a.nmax, s); counts.append(len(g) + int(e.sum()))
    owner, groups, extra = simulate_fast(K, nbrs, coords, a.nmax, a.seed)
    rng = np.random.default_rng(7); pal = rng.random((owner.max() + 1, 3)) * 0.55 + 0.4
    img = np.ones((h, w, 3)) * np.array([0.84, 0.89, 0.94]); img[ys, xs] = pal[owner]
    fig, ax = plt.subplots(figsize=(13, 6.6), constrained_layout=True)
    ax.imshow(img, interpolation="nearest", extent=(0, w, h, 0))
    claims = json.loads((a.atlas / "data/vectors/dejure_claims.geojson").read_text())["features"]
    sc = w / SRC_W
    for ft in claims:
        geom = ft["geometry"]; polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ring = np.array(poly[0]) * sc
            ax.plot(ring[:, 0], ring[:, 1], color="#1b1b1b", lw=1.1)
    ax.set_xlim(0, w); ax.set_ylim(h, 0); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"Preview, not adopted: forager language territories grown from FORGE density (split at {a.nmax:.0f} people, the North American calibration; "
                 f"{np.mean(counts):.0f} languages on average); black = the drawn de jure polities", fontsize=10)
    fig.savefig(a.out, dpi=105)
    print(dict(languages_mean=float(np.mean(counts)), population=float(K.sum()), polities=len(claims)))


if __name__ == "__main__":
    main()
