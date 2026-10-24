"""Suggested unmarked towns and minor roads for the campaign map.

    python3 -I scripts/suggest_settlements.py --atlas atlases/free_fit --out output/settlements/free_fit

Rules in polity/settle.py. Writes:
  suggested_towns.csv      x, y on the 4401 x 2037 map canvas, polity, density,
                           catchment radius, a size guess and the site's assets
  overlay.png              a transparent layer on the map's own canvas (towns as
                           grey dots, tracks as brown lines) to paste into the .pdn
  suggested.png            a preview over the marked network
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from polity.fields import LAYERS, compute  # noqa: E402
from polity.settle import SEAT_PEOPLE, URBAN_SHARE  # noqa: E402

TRACK, TOWN, EDGE = (139, 90, 43, 255), (200, 200, 200, 255), (40, 40, 40, 255)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    r = compute(a.atlas)
    land, road, shape, cell_km = r["land"], r["road"], r["land"].shape, r["cell_km"]
    towns, coast_km, d = r["suggested"], r["coast_km"], r["smooth_density"]
    tracks, paths, edges = r["tracks"], r["routes"], r["links"]
    names = r["polity_names"]
    ids = r["polity_ids"]; info = r["polity_info"]
    a.out.mkdir(parents=True, exist_ok=True)
    W, H = 4401, 2037
    sx, sy = W / shape[1], H / shape[0]
    rows = []
    near_road = ndi.distance_transform_edt(~road) * cell_km
    for (y, x) in towns:
        pid = int(ids[y, x])
        polity = (info[pid]["name"] or "").split(" (")[0] if pid else ""
        radius = float(np.sqrt(SEAT_PEOPLE / (np.pi * max(d[y, x], 1e-9))))
        assets = [k for k, ok in (("river", r["water_distance"][y, x] <= 3.0), ("coast", coast_km[y, x] <= 6.0),
                                  ("on a marked road", near_road[y, x] <= 4.0)) if ok]
        rows.append(dict(x=round((x + 0.5) * sx, 1), y=round((y + 0.5) * sy, 1), polity=polity or "unclaimed",
                         density_per_km2=round(float(d[y, x]), 1), catchment_radius_km=round(radius, 1),
                         size_guess=int(round(SEAT_PEOPLE * URBAN_SHARE, -2)), assets=", ".join(assets)))
    with (a.out / "suggested_towns.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

    # the overlay on the map's own canvas
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(over)
    for path in paths:
        if len(path) < 2:
            continue
        pts = np.array([((c + 0.5) * sx, (q + 0.5) * sy) for q, c in path])
        if len(pts) >= 7:                       # soften the 8-neighbour zigzag, ends fixed
            k = np.ones(5) / 5
            for axis in (0, 1):
                sm = np.convolve(np.pad(pts[:, axis], 2, mode="edge"), k, "valid")
                pts[2:-2, axis] = sm[2:-2]
        dr.line([tuple(p) for p in pts], fill=TRACK, width=2, joint="curve")
    for row in rows:
        x, y = row["x"], row["y"]
        dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=TOWN, outline=EDGE, width=1)
    over.save(a.out / "overlay.png", optimize=True)

    # preview: the map's terrain and borders, marked network, suggestions
    base = Image.new("RGBA", (W, H), (110, 160, 230, 255))
    src = ROOT / "data/source/original"
    terrain = Image.open(src / "terrain.png").convert("RGBA")
    base = Image.alpha_composite(base, terrain)
    for layer in ("borders.png", "roads.png", "settlements.png"):
        base = Image.alpha_composite(base, Image.open(LAYERS / layer).convert("RGBA"))
    base = Image.alpha_composite(base, over)
    base.convert("RGB").resize((2200, 1018), Image.LANCZOS).save(a.out / "suggested.png")
    summary = dict(towns=len(rows), links=len(edges), track_cells=int(tracks.sum()), track_km=float(tracks.sum() * cell_km),
                   by_polity={p: sum(1 for x in rows if x["polity"] == p) for p in sorted({x["polity"] for x in rows})},
                   rules="polity/settle.py", seat_people=SEAT_PEOPLE)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
