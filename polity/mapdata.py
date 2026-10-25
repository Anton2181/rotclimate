"""Vector map data for an atlas, for making one's own maps: de jure claims,
de facto holdings for each gap fill, claimed-but-unheld and contested land,
trade routes by traffic, the minor roads and the towns, as GeoJSON in the
source map's pixel coordinates and as one layered SVG (Inkscape layers).

    atlases/<atlas>/data/vectors/*.geojson, political.svg, README.txt
"""
from __future__ import annotations

import json

import numpy as np
from PIL import Image

from . import vectors as V
from .fields import LAYERS, rgba
from .render import smooth_labels

HATCH_PX = 9


def chaikin(points, rounds=2):
    p = np.asarray(points, float)
    for _ in range(rounds):
        if len(p) < 3:
            break
        q = 0.75 * p[:-1] + 0.25 * p[1:]; s = 0.25 * p[:-1] + 0.75 * p[1:]
        p = np.vstack([p[:1], np.column_stack([q, s]).reshape(-1, 2), p[-1:]])
    return p


def claims_full(names):
    """De jure claims at full resolution from the painted fill: polity index per pixel."""
    a = rgba("borders_fill.png")
    polities = json.loads((LAYERS / "polities.json").read_text())["polities"]
    out = np.full(a.shape[:2], -1, np.int16)
    for hexcode, label in polities.items():
        name = label.split(" (")[0]
        if name not in names:
            continue
        rgb = [int(hexcode[i:i + 2], 16) for i in (1, 3, 5)]
        m = (a[..., 0] == rgb[0]) & (a[..., 1] == rgb[1]) & (a[..., 2] == rgb[2]) & (a[..., 3] > 0)
        out[m] = names.index(name)
    return out


def write(r, dfs, tr, outdir, default_fill=0.0):
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((LAYERS / "manifest.json").read_text())
    W, H = manifest["width"], manifest["height"]
    gh, gw = r["land"].shape
    sx, sy = W / gw, H / gh
    names = r["polity_names"]
    hexes = {n: "#%02x%02x%02x" % tuple(r["polity_rgb"][n]) for n in names}
    meta = dict(crs="pixels of the source map (x right, y down, origin top-left)", width=W, height=H,
                miles_per_pixel=r["meta"]["mi_per_px"] * r["meta"]["width"] / W, model="polity v2 + de facto + trade")
    if tr is not None and tr.get('model'):
        meta['trade_model']=tr['model']
        meta['market_access_direction']=tr.get('market_access_direction','outbound')
    svg_groups = []
    # de jure
    claim = claims_full(names)
    feats, els = [], []
    for k, name in enumerate(names):
        polys = V.polygons((claim == k).astype(np.float32), eps=1.0)
        if not polys:
            continue
        feats.append(V.feature(V.multipolygon(polys), dict(polity=name, colour=hexes[name])))
        els.append(f'<path d="{V.svg_path(polys)}" fill="none" stroke="#3b2f2a" stroke-width="2" '
                   f'fill-rule="evenodd"><title>{name} (claim)</title></path>')
    V.write_geojson(outdir / "dejure_claims.geojson", feats, meta)
    dejure_lines = els
    # de facto for each fill
    defs = ['<defs>'] + [f'<pattern id="hatch{k}" width="{HATCH_PX}" height="{HATCH_PX}" patternUnits="userSpaceOnUse" '
                         f'patternTransform="rotate(45)"><rect width="3" height="{HATCH_PX}" fill="{hexes[n]}"/></pattern>'
                         for k, n in enumerate(names)] + ['</defs>']
    for c, d in dfs.items():
        tag = f"fill{int(round(c * 10)):02d}"
        hb = smooth_labels(d["held_by"], (W, H))
        ct = (np.asarray(Image.fromarray(d["contested"].astype(np.float32)).resize((W, H), Image.BILINEAR)) > 0.5) & (hb >= 0)
        f_def, f_unh, f_con, e_def, e_unh, e_con = [], [], [], [], [], []
        for k, name in enumerate(names):
            polys = V.polygons((hb == k).astype(np.float32), eps=1.0)
            if polys:
                f_def.append(V.feature(V.multipolygon(polys), dict(polity=name, colour=hexes[name], gap_fill_days=c)))
                e_def.append(f'<path d="{V.svg_path(polys)}" fill="{hexes[name]}" fill-opacity="0.6" stroke="none" '
                             f'fill-rule="evenodd"><title>{name} (held)</title></path>')
            polys = V.polygons(((claim == k) & (hb != k)).astype(np.float32), eps=1.0, min_area=60)
            if polys:
                f_unh.append(V.feature(V.multipolygon(polys), dict(claimant=name, colour=hexes[name], gap_fill_days=c)))
                e_unh.append(f'<path d="{V.svg_path(polys)}" fill="url(#hatch{k})" fill-opacity="0.85" stroke="none" '
                             f'fill-rule="evenodd"><title>{name}: claimed, not held</title></path>')
            polys = V.polygons((ct & (hb == k)).astype(np.float32), eps=1.0, min_area=60)
            if polys:
                f_con.append(V.feature(V.multipolygon(polys), dict(holder=name, gap_fill_days=c)))
                e_con.append(f'<path d="{V.svg_path(polys)}" fill="none" stroke="#2b2b2b" stroke-width="1.5" '
                             f'stroke-dasharray="4 3" fill-rule="evenodd"><title>contested ({name} nearest)</title></path>')
        V.write_geojson(outdir / f"defacto_held_{tag}.geojson", f_def, meta)
        V.write_geojson(outdir / f"claimed_unheld_{tag}.geojson", f_unh, meta)
        V.write_geojson(outdir / f"contested_{tag}.geojson", f_con, meta)
        if c == default_fill:
            svg_groups += [("defacto", f"De facto held (gap fill {c:g} days)", defs + e_def),
                           ("unheld", "Claimed, not held (hatched)", e_unh),
                           ("contested", "Contested (dashed outline)", e_con)]
    svg_groups.append(("dejure", "De jure claims (outlines)", dejure_lines))
    # minor roads between places (the suggested network)
    feats, els = [], []
    for path in r["routes"]:
        if len(path) > 1:
            pts = chaikin([((x + .5) * sx, (y + .5) * sy) for y, x in path])
            pts = V.rdp(pts, 1.0)
            feats.append(V.feature(V.linestring(pts), dict(kind="minor road (suggested)")))
            els.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                       + '" fill="none" stroke="#8b5a2b" stroke-width="1" stroke-opacity="0.7"/>')
    V.write_geojson(outdir / "minor_roads.geojson", feats, meta)
    svg_groups.append(("minor_roads", "Minor roads (suggested)", els))
    # trade routes
    if tr is not None:
        from . import routes as RT
        feats, els,sea_halos = [], [], []
        widths = {"local": 1.2, "regional": 2.4, "main": 4.0}
        for kind, cls, pts, rel in RT.lines(tr, r["water"], r["land"].shape):
            p = V.rdp(chaikin(np.array([((x + .5) * sx, (y + .5) * sy) for y, x in pts])), 1.0)
            feats.append(V.feature(V.linestring(p), dict(mode="sea" if kind == "sea" else "land or river",
                                                         route_class=cls, relative_traffic=round(rel, 4))))
            if kind=='sea':
                sea_halos.append('<polyline points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in p)
                           +f'" fill="none" stroke="#f3f8fc" stroke-width="{widths[cls]+2.4}" '
                            'stroke-linecap="round" stroke-linejoin="round"/>')
            els.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in p)
                       + f'" fill="none" stroke="{"#1d4a7a" if kind == "sea" else "#7a2e12"}" '
                         f'stroke-width="{widths[cls]}" stroke-linecap="round" stroke-linejoin="round" '
                         f'stroke-opacity="0.95"/>')
        V.write_geojson(outdir / "trade_routes.geojson", feats,
                        dict(meta, note="gravity flows P_i P_j exp(-cost / scale) between towns, cost in road-km "
                                        f"equivalents (sea : river : road = 1 : 5 : 28), scale {tr['scale']:g}; classes: "
                                        "segments with at least 5, 12 and 30 % of the busiest segment's traffic; "
                                        "sea lanes bundled (blurred and thinned)"))
        svg_groups.append(("trade", "Trade routes (width = traffic class)", sea_halos+els))
    # towns
    feats, els = [], []
    hb0 = dfs[default_fill]["held_by"]
    for i, t in enumerate(r["towns"]):
        x, y = (t["col"] + .5) * sx, (t["row"] + .5) * sy
        if "x_px" in t:
            x, y = t["x_px"], t["y_px"]
        props = dict(kind=t["kind"], marked=t["kind"] != "unmarked town",
                     port=(t["row"], t["col"]) in set(map(tuple, r["ports"])),
                     held_by=names[hb0[t["row"], t["col"]]] if hb0[t["row"], t["col"]] >= 0 else None,
                     claimed_by=names[r["claim"][t["row"], t["col"]]] if r["claim"][t["row"], t["col"]] >= 0 else None)
        if tr is not None:
            props.update(catchment_people=round(float(tr["mass"][i])), market_access=float(tr["ma"][i]),
                         local_access=float(tr["ma_local"][i]))
            if tr.get("area_ha") is not None:
                props["predicted_area_ha"] = round(float(tr["area_ha"][i]), 1)
        feats.append(V.feature(V.point(x, y), props))
        rad = 2.0 if t["kind"] == "unmarked town" else 3.5
        if tr is not None and tr.get("area_ha") is not None:
            rad = float(np.clip(1.2 * np.sqrt(tr["area_ha"][i]) ** 0.6, 1.5, 9.0))
        els.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="#fbf8f0" stroke="#222" stroke-width="0.8">'
                   f'<title>{t["kind"]}</title></circle>')
    V.write_geojson(outdir / "towns.geojson", feats, meta)
    svg_groups.append(("towns", "Towns (marked and suggested)", els))
    V.svg(outdir / "political.svg", W, H, svg_groups)
    (outdir / "README.txt").write_text(
        "Vector map data for this atlas (polity v2 with de facto control and trade).\n"
        f"Coordinates: pixels of the source map, {W} x {H}, x right, y down, origin top-left; "
        f"{meta['miles_per_pixel']:.3f} miles per pixel.\n"
        "GeoJSON (load in QGIS as a non-georeferenced layer, or read with any JSON tool):\n"
        "  dejure_claims            the painted claims, one MultiPolygon per polity\n"
        "  defacto_held_fillNN      held land for gap fill NN/10 days (00, 05, 10, 20)\n"
        "  claimed_unheld_fillNN    land a polity claims but does not hold\n"
        "  contested_fillNN         held land with a rival within half a day\n"
        "  trade_routes             routes by traffic class (local / regional / main)\n"
        "  minor_roads              the suggested unmarked roads\n"
        "  towns                    marked and suggested towns with holder, claimant, port, catchment people,\n"
        "                           market access\n"
        "political.svg: the same as Inkscape layers over a blank canvas of the map's size; place the source map\n"
        "underneath (same pixel size) and restyle freely.\n")
    if tr is not None and tr.get('model')=='inbound-directed':
        with (outdir/'README.txt').open('a') as stream:
            stream.write('Catchment people use goods travelling into town. Gravity shipments are ordered '
                         'pairs with direction-specific costs; weights are relative, not tonnes. '
                         'The market_access and local_access indicators retain their outward (town-to-people) direction.\n')
