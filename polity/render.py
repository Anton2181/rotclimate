"""Cartographic rendering of de facto against de jure control.

De facto: the holder's colour, laid over the land. De jure: the painted
borders as lines; land claimed but not held by the claimant carries the
claimant's colour as diagonal hatching (over the holder's colour where
another polity holds it); contested land carries the rival's colour as
hatching the other way. Labels are upsampled smoothly from the analysis grid
so the edges are not blocky at full resolution.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PAPER = np.array([0.945, 0.925, 0.875])
SEA = np.array([0.80, 0.87, 0.93])
BORDER = np.array([0.23, 0.18, 0.16])
FILL_ALPHA = 0.62
HATCH_ALPHA = 0.85


def smooth_labels(labels, size, sigma=0.6):
    """Label grid (-1 = none) resized to size (W, H) with smooth edges: each
    label's mask is upsampled bilinearly after a light blur; argmax wins."""
    W, H = size
    best = np.full((H, W), 0.5, np.float32); out = np.full((H, W), -1, np.int32)
    for k in np.unique(labels):
        if k < 0:
            continue
        m = ndi.gaussian_filter((labels == k).astype(np.float32), sigma)
        up = np.asarray(Image.fromarray(m).resize((W, H), Image.BILINEAR))
        win = up > best
        out[win] = k; best[win] = up[win]
    return out


def resize_bool(mask, size, sigma=0.6):
    m = ndi.gaussian_filter(np.asarray(mask, np.float32), sigma)
    return np.asarray(Image.fromarray(m).resize(size, Image.BILINEAR)) > 0.5


def hillshade(elev, size):
    e = np.asarray(Image.fromarray(np.asarray(elev, np.float32)).resize(size, Image.BILINEAR))
    gy, gx = np.gradient(e)
    scale = size[0] / elev.shape[1]
    return np.clip(.97 - .00018 * gx / scale + .00022 * gy / scale, .80, 1.06)


def stripes(size, period, width, direction=1):
    W, H = size
    y, x = np.mgrid[:H, :W]
    return ((x + direction * y) % period) < width


def defacto_rgb(held_by, claim, contested, second, colours, elev, land_full, borders_rgba, size,
                period=None):
    """RGB (H, W, 3) floats. held_by / claim / second: polity index per
    analysis cell (-1 none); contested: bool; colours: (n, 3) floats 0-1;
    land_full: the land mask at any resolution; borders_rgba: the painted
    borders layer (RGBA) at any resolution."""
    W, H = size
    period = period or max(6, int(round(W / 330)))
    width = max(2, period // 3)
    land = np.asarray(Image.fromarray(np.asarray(land_full, np.uint8) * 255).resize(size, Image.BILINEAR)) > 127
    hb = smooth_labels(np.asarray(held_by), size)
    cl = smooth_labels(np.asarray(claim), size)
    ct = resize_bool(contested, size) & (hb >= 0)
    sc = np.asarray(Image.fromarray(np.asarray(second, np.int32)).resize(size, Image.NEAREST))
    col = np.vstack([np.asarray(colours, float), PAPER])            # index -1 -> paper
    rgb = np.broadcast_to(PAPER, (H, W, 3)).copy()
    fill = hb >= 0
    rgb[fill] = PAPER * (1 - FILL_ALPHA) + col[hb[fill]] * FILL_ALPHA
    hatch = (cl >= 0) & (cl != hb) & stripes(size, period, width, 1)
    rgb[hatch] = rgb[hatch] * (1 - HATCH_ALPHA) + col[cl[hatch]] * HATCH_ALPHA
    rival = ct & (sc >= 0) & stripes(size, period, width, -1)
    rgb[rival] = rgb[rival] * (1 - HATCH_ALPHA) + col[sc[rival]] * HATCH_ALPHA
    rgb *= hillshade(elev, size)[..., None]
    rgb[~land] = SEA
    b = np.asarray(Image.fromarray(np.asarray(borders_rgba)).resize(size, Image.LANCZOS), float)[..., 3:4] / 255.0
    rgb = rgb * (1 - b) + BORDER * b
    return np.clip(rgb, 0, 1)
