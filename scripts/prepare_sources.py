"""Derive the 2000 x 926 working layers from the lossless originals.

The originals (data/source/original/, 4401 x 2037 unless noted) are:
  terrain.png             transparent = water, 4 flat colours = height tiers
  target.png              the painted climate zones (2483 x 1152)
  rivers.png              river lines (one colour, soft edges)
  hexes.png               the hex grid lines
  roads_settlements.png   roads and settlement markers

Working layers written to data/source/ (lossless PNG):
  elevation.png   tier colours by majority vote over each output pixel's
                  footprint (water counts as a class), so coasts and tier
                  edges stay exact colours with no blending
  rivers.png      alpha averaged over the footprint (box filter)
  roads.png       box filtered (drawing only)
  climate_target.png  the target, nearest-neighbour (keeps paint colours exact)

It also measures the hex grid from the line image: hex centres are the
local maxima of the distance to the nearest line; their spacing gives the
map scale (15-mile hex sides).

Run with:  python -I scripts/prepare_sources.py <repo root>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SRC = ROOT / "data" / "source"
ORIG = SRC / "original"
W, H = 2000, 926
TIER_COLORS = np.array([(185, 215, 117), (251, 239, 175), (243, 152, 79), (205, 91, 65)])


def box(a: np.ndarray) -> np.ndarray:
    """Area-average a 2-D float array to W x H."""
    return np.array(Image.fromarray(a.astype(np.float32), mode="F").resize((W, H), Image.BOX))


def elevation():
    a = np.array(Image.open(ORIG / "terrain.png").convert("RGBA")).astype(int)
    land = a[..., 3] > 0
    d = ((a[..., None, :3] - TIER_COLORS[None, None]) ** 2).sum(-1)
    cls = np.where(land, d.argmin(-1) + 1, 0)
    print(f"terrain: largest colour distance to a tier colour {np.sqrt(d.min(-1)[land].max()):.1f}")
    votes = np.stack([box((cls == k).astype(float)) for k in range(5)])
    out_cls = votes.argmax(0)
    rgba = np.zeros((H, W, 4), np.uint8)
    for k in range(1, 5):
        rgba[out_cls == k, :3] = TIER_COLORS[k - 1]
        rgba[out_cls == k, 3] = 255
    Image.fromarray(rgba).save(SRC / "elevation.png", optimize=True)
    return out_cls


def soft_layer(name, out):
    a = np.array(Image.open(ORIG / name).convert("RGBA")).astype(float)
    alpha = a[..., 3] / 255.0
    rgb = np.stack([box(a[..., c] * alpha) for c in range(3)], -1)
    al = box(alpha)
    rgb = np.where(al[..., None] > 1e-6, rgb / np.maximum(al[..., None], 1e-6), 0)
    rgba = np.dstack([np.clip(rgb, 0, 255), np.clip(al * 255, 0, 255)]).round().astype(np.uint8)
    Image.fromarray(rgba).save(SRC / out, optimize=True)


def target():
    im = Image.open(ORIG / "target.png").convert("RGB")
    im.resize((W, H), Image.NEAREST).save(SRC / "climate_target.png", optimize=True)


def hex_scale():
    a = np.array(Image.open(ORIG / "hexes.png").convert("RGBA"))
    ink = a[..., 3] > 60
    # the grid lines form one connected network; the hex numbers are small blobs
    lab0, n0 = ndi.label(ink)
    sizes = ndi.sum(ink, lab0, range(1, n0 + 1))
    line = np.isin(lab0, 1 + np.flatnonzero(sizes > 5000))
    dist = ndi.distance_transform_edt(~line)
    peak = (dist == ndi.maximum_filter(dist, size=31)) & (dist > 12)
    lab, n = ndi.label(peak)
    c = np.array(ndi.center_of_mass(peak, lab, range(1, n + 1)))        # (y, x)
    # rows: cluster centre y; columns: spacing within a row
    ys = np.sort(c[:, 0])
    gaps = np.diff(ys)
    row_breaks = gaps > 8
    row_y = np.array([g.mean() for g in np.split(ys, np.flatnonzero(row_breaks) + 1)])
    dy = np.median(np.diff(row_y))
    dxs = []
    for ry in row_y:
        xs = np.sort(c[np.abs(c[:, 0] - ry) < 5, 1])
        if xs.size > 3:
            dxs.append(np.median(np.diff(xs)))
    dx = np.median(dxs)
    sx, sy = a.shape[1] / W, a.shape[0] / H
    print(f"hexes: {n} centres in {row_y.size} rows; spacing {dx:.2f} x {dy:.2f} original px "
          f"(ratio {dy / dx:.4f}, regular hexes 0.8660)")
    print(f"       = {dx / sx:.3f} x {dy / sy:.3f} map px; with 15-mile sides: "
          f"{np.sqrt(3) * 15 / (dx / sx):.4f} mi/px across, {22.5 / (dy / sy):.4f} mi/px down")
    print(f"       map size {np.sqrt(3) * 15 / dx * a.shape[1]:.1f} x {22.5 / dy * a.shape[0]:.1f} mi")
    # exact lattice in map px: index every centre on the previous (label-fitted)
    # lattice, which fixes the hex numbering, then refit origin and spacing
    import json
    gpath = ROOT / "data" / "hexgrid.json"
    g = json.loads(gpath.read_text())
    X, Y = c[:, 1] / sx, c[:, 0] / sy
    for _ in range(2):
        r = np.round((Y - g["y0"]) / g["dy"]).astype(int)
        col = np.round((X - g["x0"]) / g["dx"] - 0.5 * (r % 2)).astype(int)
        ax = np.stack([np.ones_like(X), col + 0.5 * (r % 2)], 1)
        ay = np.stack([np.ones_like(Y), r.astype(float)], 1)
        (x0, gdx), *_ = np.linalg.lstsq(ax, X, rcond=None)
        (y0, gdy), *_ = np.linalg.lstsq(ay, Y, rcond=None)
        g.update(x0=float(x0), dx=float(gdx), y0=float(y0), dy=float(gdy))
    res = np.hypot(ax @ [x0, gdx] - X, ay @ [y0, gdy] - Y)
    print(f"       lattice x0={x0:.2f} dx={gdx:.4f} y0={y0:.2f} dy={gdy:.4f} map px; "
          f"median residual {np.median(res):.2f} px, max {res.max():.2f} px")
    g["source"] = "measured from the hex lines (data/source/original/hexes.png)"
    gpath.write_text(json.dumps(g))
    return dx / sx, dy / sy


def main():
    old_tier = None
    if (SRC / "elevation.webp").exists():
        e = np.array(Image.open(SRC / "elevation.webp").convert("RGBA")).astype(int)
        d = ((e[..., None, :3] - TIER_COLORS[None, None]) ** 2).sum(-1)
        old_tier = np.where(e[..., 3] > 128, d.argmin(-1) + 1, 0)
    cls = elevation()
    if old_tier is not None:
        print(f"elevation vs old lossy layer: land agrees on {np.mean((cls > 0) == (old_tier > 0)):.2%} of pixels, "
              f"tier on {np.mean(cls == old_tier):.2%}")
    soft_layer("rivers.png", "rivers.png")
    soft_layer("roads_settlements.png", "roads.png")
    target()
    hex_scale()


if __name__ == "__main__":
    main()
