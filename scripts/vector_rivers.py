"""Rivers as smooth curves: the drawing's rivers are 1-3 px pixel lines with
stair steps. Thin them to centre lines (Zhang-Suen), trace the centre lines
into polylines, smooth those and draw them anti-aliased at any scale, each
with the river's drawn width.
"""
from __future__ import annotations

import numpy as np
from numba import njit
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

_NB = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]   # P2..P9 clockwise


@njit(cache=True)
def _thin(img):
    """Zhang-Suen thinning of a 0/1 uint8 image, in place."""
    H, W = img.shape
    changed = True
    while changed:
        changed = False
        for step in range(2):
            kill = []
            for y in range(1, H - 1):
                for x in range(1, W - 1):
                    if img[y, x] == 0:
                        continue
                    p = (img[y - 1, x], img[y - 1, x + 1], img[y, x + 1], img[y + 1, x + 1],
                         img[y + 1, x], img[y + 1, x - 1], img[y, x - 1], img[y - 1, x - 1])
                    b = p[0] + p[1] + p[2] + p[3] + p[4] + p[5] + p[6] + p[7]
                    if b < 2 or b > 6:
                        continue
                    a = 0
                    for i in range(8):
                        if p[i] == 0 and p[(i + 1) % 8] == 1:
                            a += 1
                    if a != 1:
                        continue
                    if step == 0:
                        if p[0] * p[2] * p[4] != 0 or p[2] * p[4] * p[6] != 0:
                            continue
                    else:
                        if p[0] * p[2] * p[6] != 0 or p[0] * p[4] * p[6] != 0:
                            continue
                    kill.append(y * W + x)
            for k in kill:
                img[k // W, k % W] = 0
            if len(kill):
                changed = True
    return img


@njit(cache=True)
def _drop_corners(img):
    """Remove staircase corner pixels a thinned line does not need: a pixel
    with two perpendicular orthogonal neighbours, whose other neighbours all
    touch one of those two, can go without breaking the line."""
    H, W = img.shape
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if img[y, x] == 0:
                continue
            n, e, s_, w = img[y - 1, x], img[y, x + 1], img[y + 1, x], img[y, x - 1]
            for a_dy, a_dx, b_dy, b_dx in ((-1, 0, 0, 1), (0, 1, 1, 0), (1, 0, 0, -1), (0, -1, -1, 0)):
                if img[y + a_dy, x + a_dx] == 0 or img[y + b_dy, x + b_dx] == 0:
                    continue
                ok = True
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if (dy == 0 and dx == 0) or img[y + dy, x + dx] == 0:
                            continue
                        if (dy == a_dy and dx == a_dx) or (dy == b_dy and dx == b_dx):
                            continue
                        if not ((abs(dy - a_dy) <= 1 and abs(dx - a_dx) <= 1) or (abs(dy - b_dy) <= 1 and abs(dx - b_dx) <= 1)):
                            ok = False
                if ok:
                    img[y, x] = 0
                    break
    return img


def trace(skel):
    """Polylines (lists of (y, x)) along a one-pixel skeleton, split at
    junctions and ends."""
    pts = set(zip(*np.nonzero(skel)))
    nbrs = lambda p: [(p[0] + dy, p[1] + dx) for dy, dx in _NB if (p[0] + dy, p[1] + dx) in pts]
    deg = {p: len(nbrs(p)) for p in pts}
    seen_edge = set()
    lines = []
    starts = [p for p in pts if deg[p] != 2] or list(pts)[:1]
    for s in starts:
        for n in nbrs(s):
            if (s, n) in seen_edge:
                continue
            line, prev, cur = [s], s, n
            seen_edge.add((s, n)); seen_edge.add((n, s))
            while True:
                line.append(cur)
                if deg[cur] != 2:
                    break
                nxt = [q for q in nbrs(cur) if q != prev]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                if (prev, cur) in seen_edge:
                    break
                seen_edge.add((prev, cur)); seen_edge.add((cur, prev))
            lines.append(line)
    # loops with no ends or junctions
    left = pts - {p for l in lines for p in l}
    while left:
        s = left.pop(); line, prev, cur = [s], None, s
        while True:
            nxt = [q for q in nbrs(cur) if q != prev and q in left]
            if not nxt:
                break
            prev, cur = cur, nxt[0]; left.discard(cur); line.append(cur)
        lines.append(line)
    return [l for l in lines if len(l) >= 2]


def smooth_path(a, sigma=2.5):
    """Gaussian smoothing along a polyline (arc index), ends held fixed."""
    a = np.asarray(a, float)
    if len(a) < 4:
        return a
    b = np.stack([ndi.gaussian_filter1d(a[:, k], sigma, mode="nearest") for k in range(2)], 1)
    # pull the ends back to where they were (they meet other rivers or the sea)
    t = np.minimum(np.arange(len(a)), np.arange(len(a))[::-1]) / max(1.0, 2 * sigma)
    w = np.clip(t, 0, 1)[:, None]
    return a * (1 - w) + b * w


def river_alpha(rivers, scale, min_width=1.1, max_width=3.0, supersample=2):
    """Anti-aliased river coverage (0..1) at `scale` times the drawing's size:
    centre lines traced into long polylines, smoothed along their length and
    drawn round-capped, one width per river system (its drawn width)."""
    mask = rivers > 0.3
    dt = ndi.distance_transform_edt(mask)
    skel = _drop_corners(_thin(mask.astype(np.uint8).copy()))
    lab, n = ndi.label(skel, structure=np.ones((3, 3)))
    med = np.atleast_1d(ndi.median(2.0 * dt, lab, index=np.arange(1, n + 1)))
    lines = trace(skel)
    H, W = rivers.shape
    f = scale * supersample
    img = Image.new("L", (W * f, H * f), 0)
    draw = ImageDraw.Draw(img)
    for line in lines:
        w = float(np.clip(med[lab[line[0]] - 1], min_width, max_width)) * f
        a = smooth_path(line)
        xy = [((x + 0.5) * f, (y + 0.5) * f) for y, x in a]
        draw.line(xy, fill=255, width=max(1, round(w)), joint="curve")
        for x, y in (xy[0], xy[-1]):
            draw.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=255)
    if supersample > 1:
        img = img.resize((W * scale, H * scale), Image.BOX)
    return np.asarray(img, np.float32) / 255.0, len(lines)
