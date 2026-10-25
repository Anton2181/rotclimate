"""Vector layers for map-making: polygons, lines and points in the pixel
coordinates of the source map (data/source/ravages_v8: x right, y down,
origin at the top-left corner), as GeoJSON and as one layered SVG.

Polygons come from smoothly upsampled masks traced at the half level
(contourpy, which matplotlib ships) and thinned with Ramer-Douglas-Peucker.
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def rdp(points, eps):
    """Ramer-Douglas-Peucker on an (n, 2) array (closed rings keep both ends)."""
    pts = np.asarray(points, float)
    if len(pts) < 4 or eps <= 0:
        return pts
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        seg = pts[b] - pts[a]
        norm = np.hypot(*seg)
        rel = pts[a + 1:b] - pts[a]
        d = np.abs(seg[0] * rel[:, 1] - seg[1] * rel[:, 0]) / norm if norm > 0 else np.hypot(rel[:, 0], rel[:, 1])
        i = int(np.argmax(d))
        if d[i] > eps:
            m = a + 1 + i
            keep[m] = True
            stack += [(a, m), (m, b)]
    return pts[keep]


def upsample(mask, size, sigma=0.6):
    m = ndi.gaussian_filter(np.asarray(mask, np.float32), sigma)
    return np.asarray(Image.fromarray(m).resize(size, Image.BILINEAR))


def polygons(field, level=0.5, eps=1.0, min_area=30.0):
    """Polygons (list of rings, exterior first) where field >= level."""
    import contourpy
    z = np.pad(np.asarray(field, np.float64), 1, constant_values=0.0)
    gen = contourpy.contour_generator(z=z, fill_type=contourpy.FillType.OuterOffset)
    pts_list, offs_list = gen.filled(level, np.inf)
    out = []
    for pts, offs in zip(pts_list, offs_list):
        rings = []
        for a, b in zip(offs[:-1], offs[1:]):
            ring = rdp(pts[a:b] - 1.0 + 0.5, eps)          # undo the pad; pixel centres at +0.5
            if len(ring) >= 4:
                rings.append(ring)
        if rings and abs(ring_area(rings[0])) >= min_area:
            out.append(rings)
    return out


def ring_area(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def feature(geometry, props):
    return dict(type="Feature", geometry=geometry, properties=props)


def multipolygon(polys, nd=1):
    return dict(type="MultiPolygon",
                coordinates=[[[[round(float(x), nd), round(float(y), nd)] for x, y in ring] for ring in p]
                             for p in polys])


def linestring(points, nd=1):
    return dict(type="LineString", coordinates=[[round(float(x), nd), round(float(y), nd)] for x, y in points])


def point(x, y, nd=1):
    return dict(type="Point", coordinates=[round(float(x), nd), round(float(y), nd)])


def write_geojson(path, features, meta=None):
    fc = dict(type="FeatureCollection", features=features)
    if meta:
        fc["properties"] = meta
    path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")))


def chains(child, parent, flow, threshold):
    """Polylines through the edges with flow >= threshold: maximal chains
    whose inner nodes have exactly two such edges. Returns (nodes, flows)."""
    keep = flow >= threshold
    a, b, f = child[keep], parent[keep], flow[keep]
    if not len(a):
        return []
    adj = {}
    for u, v, w in zip(a.tolist(), b.tolist(), f.tolist()):
        adj.setdefault(u, {})[v] = adj.get(u, {}).get(v, 0.0) + w
        adj.setdefault(v, {})[u] = adj.get(v, {}).get(u, 0.0) + w
    seen = set(); out = []
    ends = [n for n, nb in adj.items() if len(nb) != 2]
    for start in ends + list(adj):
        for nxt in list(adj[start]):
            e = (min(start, nxt), max(start, nxt))
            if e in seen:
                continue
            path = [start]; fl = []; prev, cur = start, nxt
            while True:
                e = (min(prev, cur), max(prev, cur))
                if e in seen:
                    break
                seen.add(e); path.append(cur); fl.append(adj[prev][cur])
                if len(adj[cur]) != 2:
                    break
                nb = [n for n in adj[cur] if n != prev]
                prev, cur = cur, nb[0]
            if len(path) > 1:
                out.append((path, fl))
    return out


def svg(path, width, height, groups):
    """groups: list of (id, label, [svg element strings])."""
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    for gid, label, elements in groups:
        parts.append(f'<g id="{gid}" inkscape:groupmode="layer" inkscape:label="{label}">')
        parts += elements
        parts.append('</g>')
    parts.append('</svg>')
    path.write_text("\n".join(parts))


def svg_path(polys, nd=1):
    d = []
    for p in polys:
        for ring in p:
            d.append("M" + " L".join(f"{x:.{nd}f},{y:.{nd}f}" for x, y in ring) + " Z")
    return " ".join(d)
