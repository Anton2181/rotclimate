"""Political reach fields for one atlas, from the campaign map's political layers.

compute(atlas) reads the atlas's terrain, potential biomes, snow months and
Harvest density (1000 x 463 cells of ~3.7 km), the painted swamp zone, and
data/source/ravages_v8 (roads and ferry routes, settlements by the map key,
polity fills, commanderies), and adds the unmarked towns and minor roads a
populated countryside implies (polity/settle.py). See polity/control.py for the travel model.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from .control import control, days_from, path_factor, terrain_coefficient, travel_graph
from .settle import minor_roads, place_towns

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "data/source/ravages_v8"
HELD_DAYS = 2.0          # a polity holds a place within two days of its own roads, towns and garrisons
CONTESTED_DAYS = 0.5     # ... contested where a rival is within half a day of the same


def rgba(name):
    return np.asarray(Image.open(LAYERS / name).convert("RGBA"))


def block_any(mask, shape, share=0.05):
    """Share of each analysis cell covered by a full-resolution mask, thresholded."""
    im = Image.fromarray((np.asarray(mask) * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.BOX)
    return np.asarray(im) / 255.0 > share


def settlements(shape):
    """Settlement symbols by the map key: purple rectangle with gold brackets =
    imperial capital, purple circle with gold brackets = major imperial city,
    purple square = imperial fort, green square = imperial monastery, large /
    small white circle = fortified city / town."""
    a = rgba("settlements.png"); m = a[..., 3] > 0
    lab, _ = ndi.label(m)
    H, W = m.shape
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        px = a[sl][lab[sl] == i][:, :3]
        colours = {tuple(int(v) for v in c) for c in px}
        size = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
        if (255, 216, 0) in colours:
            kind = "imperial capital" if size > 20 else "major imperial city"
        elif (178, 0, 255) in colours:
            kind = "imperial fort"
        elif (0, 168, 107) in colours:
            kind = "imperial monastery"
        else:
            kind = "fortified city" if size >= 13 else "fortified town"
        cy, cx = ndi.center_of_mass(lab[sl] == i)
        y, x = sl[0].start + cy, sl[1].start + cx
        out.append(dict(kind=kind, y_px=float(y), x_px=float(x),
                        row=int(min(shape[0] - 1, y * shape[0] / H)), col=int(min(shape[1] - 1, x * shape[1] / W))))
    return out


def polity_fills(shape):
    """Polity fills by colour on the analysis grid: id map, RGB and name of each id."""
    a = rgba("borders_fill.png")
    small = np.asarray(Image.fromarray(a).resize((shape[1], shape[0]), Image.NEAREST))
    m = small[..., 3] > 0
    keys = small[..., 0].astype(int) * 65536 + small[..., 1].astype(int) * 256 + small[..., 2]
    names = json.loads((LAYERS / "polities.json").read_text())["polities"]
    ids = np.zeros(shape, np.int16); info = {}
    values, counts = np.unique(keys[m], return_counts=True)
    for k, c in zip(values, counts):
        if c < 40:            # anti-aliased edges and label fringes
            continue
        i = len(info) + 1
        ids[m & (keys == k)] = i
        rgb = ((k >> 16) & 255, (k >> 8) & 255, k & 255)
        hexcode = "#%02x%02x%02x" % rgb
        info[i] = dict(rgb=rgb, hex=hexcode, name=names.get(hexcode))
    return ids, info


def compute(atlas):
    """All political reach fields of one atlas on its 1000 x 463 analysis grid."""
    from harvest.export import climate_arrays, geometry
    from population.export import decode_harvest
    from rotclimate.geography import target_fullres
    data = Path(atlas) / "data"; meta = json.loads((data / "atlas.json").read_text())
    arrays = climate_arrays(data, meta)
    elev = np.asarray(arrays["elev"], float); biome = np.asarray(arrays["biome"]); shape = elev.shape
    geo, _ = geometry(meta, shape)
    land = geo["land_fraction"] > 0.5
    cell_km = meta["width"] / shape[1] * meta["mi_per_px"] * 1.609344
    swamp = np.asarray(Image.fromarray((target_fullres() == 5).astype(np.uint8) * 255)
                       .resize((shape[1], shape[0]), Image.BOX)) > 127
    snow_share = (np.asarray(arrays["snow"], float) > 10).mean(0)       # months with lasting snow, climate grid
    snow_share = np.asarray(Image.fromarray(snow_share.astype(np.float32)).resize((shape[1], shape[0]), Image.BILINEAR))
    route = block_any(rgba("roads.png")[..., 3] > 0, shape)
    road = route & land
    ferry = ndi.binary_closing(route, iterations=2) & ~land        # dotted ferry routes, gaps closed
    hm, hf = decode_harvest(data)
    density = np.where(land, hf["settlement_base"] * hm["occupation"]["scenarios"]["central"], 0.0)
    paths = path_factor(density)
    towns = settlements(shape)
    _, nearest = ndi.distance_transform_edt(~land, return_indices=True)
    for t in towns:                                               # snap to land
        t["row"], t["col"] = int(nearest[0, t["row"], t["col"]]), int(nearest[1, t["row"], t["col"]])
    core = block_any(rgba("commanderies_core.png")[..., 3] > 128, shape, 0.5) & land
    frontier = block_any(rgba("commanderies_frontier.png")[..., 3] > 128, shape, 0.5) & land

    ids, info = polity_fills(shape)
    claimed = land & (ids > 0)
    # the unmarked towns and minor roads a populated countryside implies (polity/settle.py)
    open_eta = terrain_coefficient(biome, swamp, None)
    bare = travel_graph(elev, land, road, open_eta, cell_km, paths, ferry)
    marked = [(t["row"], t["col"]) for t in towns]
    suggested, coast_km, smooth_density = place_towns(density, land, geo["water_distance"], road, elev, cell_km, marked,
                                                      allowed=claimed)
    tracks, routes, links = minor_roads(bare, shape, road, suggested, marked)
    towns = towns + [dict(kind="unmarked town", row=int(y), col=int(x)) for y, x in suggested]
    network = [(r, c) for r, c in zip(*np.nonzero(road))] + [(t["row"], t["col"]) for t in towns]
    capital = [(t["row"], t["col"]) for t in towns if t["kind"] == "imperial capital"]
    f = {}
    for season, share in (("open", None), ("winter", snow_share)):
        eta = terrain_coefficient(biome, swamp, share)
        graph = travel_graph(elev, land, road, eta, cell_km, paths, ferry, tracks)
        f[f"days_{season}"] = days_from(graph, shape, network)
        f[f"capital_days_{season}"] = days_from(graph, shape, capital)
        if season == "open":
            open_graph = graph
    # each polity's reach from its own roads and towns, marked or unmarked (snow-free season)
    groups = {}
    for i, d in info.items():
        if d["name"]:
            groups.setdefault(d["name"].split(" (")[0], []).append(i)
    names = sorted(groups)
    reach = np.full((len(names),) + shape, np.inf)
    for k, name in enumerate(names):
        own = np.isin(ids, groups[name])
        src = [(r, c) for r, c in zip(*np.nonzero(road & own))]
        src += [(t["row"], t["col"]) for t in towns if own[t["row"], t["col"]]]
        reach[k] = days_from(open_graph, shape, src)
    best = np.argmin(reach, 0); best_days = np.min(reach, 0)
    second_days = np.partition(reach, 1, axis=0)[1] if len(names) > 1 else np.full(shape, np.inf)
    f["polity_best"] = np.where(np.isfinite(best_days), best, -1)
    f["polity_best_days"] = best_days
    f["polity_second_days"] = second_days
    colours = {}
    for name in names:
        colours[name] = info[groups[name][0]]["rgb"]
    with np.errstate(invalid="ignore"):
        contested = land & (best_days <= HELD_DAYS) & (second_days - best_days <= CONTESTED_DAYS)
    return dict(fields=f, land=land, road=road, ferry=ferry, tracks=tracks, routes=routes, links=links,
                suggested=suggested, coast_km=coast_km, smooth_density=smooth_density, graph_open=open_graph, eta_open=terrain_coefficient(biome, swamp, None),
                water_distance=geo["water_distance"], polity_ids=ids, polity_info=info, groups=groups,
                polity_names=names, polity_rgb=colours, towns=towns, core=core, frontier=frontier, swamp=swamp,
                snow_share=snow_share, density=density, paths=paths, cell_km=cell_km, elev=elev, meta=meta,
                held=land & (best_days <= HELD_DAYS),
                contested=contested,
                control_open=control(f["days_open"]), control_winter=control(f["days_winter"]))
