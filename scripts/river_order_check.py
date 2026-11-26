"""Owner rule (26 Nov 2026): undrawn rivers < drawn rivers, and within each river system a thin drawn river carries less
catchment than the thick stem it joins. Thin / thick come from the original drawing (data/source/original/rivers.png):
its skeleton is split into branches at junctions; a branch is thick when its median drawn width is >= 4 original px
(thin lines are 2-3 px, thick ~5). At each junction the outgoing branch is the one with the largest catchment; every
thin branch arriving where a thick branch also arrives must have a smaller catchment there than that thick branch.

    .venv/bin/python -I scripts/river_order_check.py <height map npz>      # uses its stored 'recv' or Priority-Flood
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
NB = np.array([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)], np.int64)
THICK_PX, TRIM, MIN_LEN = 4.0, 3, 10


def catchment(path, land, rivers):
    from rotclimate.routing import _accumulate, _flood, _topological
    d = np.load(path); H, W = land.shape
    lv = np.asarray(d["lake_level"], float) if "lake_level" in d.files else np.zeros((H, W)); through = ~land & (lv > 0)
    net = land | through
    if "recv" in d.files:
        recv = np.asarray(d["recv"], np.int64); order = _topological(recv, net.ravel())
    else:
        recv, order = _flood(np.where(land, np.asarray(d["z"], float), np.where(through, lv, -1e9)), net, NB)
    px = (1.143 * 1.609344) ** 2
    return (_accumulate(order, recv, land.ravel().astype(float)) * px).reshape(H, W)


def branches(land, rivers):
    from skimage.morphology import skeletonize
    H, W = land.shape
    im = np.array(Image.open(ROOT / "data/source/original/rivers.png").convert("RGBA")); m = im[..., 3] > 60
    oy, ox = m.shape
    dt = ndi.distance_transform_edt(m); sk = skeletonize(m); wid = 2 * dt - 1
    nbc = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    junction = sk & (nbc >= 3)
    jlab, nj = ndi.label(ndi.binary_dilation(junction, structure=np.ones((3, 3)), iterations=2), structure=np.ones((3, 3)))
    segs = sk & (jlab == 0)
    lab, nb = ndi.label(segs, structure=np.ones((3, 3)))
    gy = lambda y: np.clip(((y + 0.5) * H / oy).astype(int), 0, H - 1)
    gx = lambda x: np.clip(((x + 0.5) * W / ox).astype(int), 0, W - 1)
    # which junction blobs each branch touches (its end pixels next to a junction blob)
    touch = ndi.binary_dilation(segs, structure=np.ones((3, 3))) & (jlab > 0)
    ys, xs = np.nonzero(segs); ids = lab[ys, xs]; o = np.argsort(ids); ys, xs, ids = ys[o], xs[o], ids[o]
    bounds = np.searchsorted(ids, np.arange(1, nb + 2))
    out = []
    for k in range(nb):
        a, b = bounds[k], bounds[k + 1]
        if b - a < MIN_LEN:
            continue
        yk, xk = ys[a:b], xs[a:b]
        near = ndi.binary_dilation(lab == k + 1, structure=np.ones((3, 3))) & (jlab > 0) if False else None
        js = set(np.unique(jlab[np.clip(yk[:, None] + np.array([-1, 0, 1, -1, 1, -1, 0, 1]), 0, oy - 1),
                                np.clip(xk[:, None] + np.array([-1, -1, -1, 0, 0, 1, 1, 1]), 0, ox - 1)]).tolist()) - {0}
        out.append(dict(id=k + 1, n=int(b - a), thick=bool(np.median(wid[yk, xk]) >= THICK_PX), gy=gy(yk), gx=gx(xk), junctions=sorted(js)))
    return out


def check(path):
    from terrain_capped import layers
    L, tops, h0, land, rivers = layers()
    A = catchment(path, land, rivers)
    Atr = ndi.maximum_filter(np.where(rivers, A, 0.0), size=5)            # the trunk within 2 cells of the centre line
    br = branches(land, rivers)
    for b in br:
        a = np.sort(Atr[b["gy"], b["gx"]]); a = a[TRIM:-TRIM] if a.size > 2 * TRIM else a
        b["A_max"] = float(a.max()); b["A_min"] = float(a.min())
    byj = {}
    for b in br:
        for j in b["junctions"]:
            byj.setdefault(j, []).append(b)
    bad = []; checked = 0
    for j, bs in byj.items():
        if len(bs) < 2:
            continue
        out = max(bs, key=lambda b: b["A_max"]); inc = [b for b in bs if b is not out]
        thick_in = [b for b in inc if b["thick"]]; thin_in = [b for b in inc if not b["thick"]]
        if not thick_in or not thin_in:
            continue
        t = max(b["A_max"] for b in thick_in)
        for b in thin_in:
            checked += 1
            if b["A_max"] >= t:
                bad.append(dict(junction=int(j), thin_km2=round(b["A_max"]), thick_km2=round(t), y=int(b["gy"].mean()), x=int(b["gx"].mean())))
    thin_sizes = [b["A_max"] for b in br if not b["thick"]]
    res = dict(branches=len(br), thin=sum(not b["thick"] for b in br), thick=sum(b["thick"] for b in br),
               smallest_drawn_river_km2=round(min(b["A_max"] for b in br)), smallest_thin_km2=round(min(thin_sizes)),
               confluences_checked=checked, thin_not_below_thick=len(bad), examples=sorted(bad, key=lambda r: -r["thin_km2"] / max(r["thick_km2"], 1))[:10])
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    check(Path(sys.argv[1]))
