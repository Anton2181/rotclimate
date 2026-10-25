"""Political reach fields for one atlas, from the campaign map's political layers.

compute(atlas) reads the atlas's terrain, potential biomes, monthly climate
and winds and Harvest density (1000 x 463 cells of ~3.7 km), the painted
swamp zone, the navigable rivers, and data/source/ravages_v8 (roads and
ferry routes, settlements by the map key, polity fills, commanderies), and
adds the unmarked towns and minor roads a populated countryside implies
(polity/settle.py). Then, month by month (polity/network.py): walking with
the season's snow, mud, heat and floods, sailing by the month's winds and
storms, river boats, riders for the herding polities; places ranked, the
reach worn down in refuge terrain. Fitted on Earth in
scripts/polity_earth_check.py (calibration/polity_20261025).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from . import control as C
from . import network as N
from .control import control, days_from, path_factor, terrain_coefficient, travel_graph
from .settle import minor_roads, place_towns

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "data/source/ravages_v8"
# a polity holds a place within this many days of its own roads, towns and garrisons (year-round days). Han
# China's commanderies of AD 2 fitted 5 days (F1, seats only: the Han data has no roads), but on the Roman
# empire of AD 150, measured from its towns and roads as the map's network is, 5 days did worse than 2
# (balanced accuracy 0.76 against 0.82; best 1.5-2), so the threshold stays at 2 (calibration/polity_20261025)
HELD_DAYS = 2.0
CONTESTED_DAYS = 0.5     # ... contested where a rival is within half a day of the same
# 0: the seat of a commandery or above (capital, major city, fortified city,
# fort); 1: county level (fortified town, monastery, unmarked town, roads)
RANK = {"imperial capital": 0, "major imperial city": 0, "fortified city": 0, "imperial fort": 0,
        "fortified town": 1, "imperial monastery": 1, "unmarked town": 1}
# Which polities ride. The herders' share of the food their land could give (Harvest) did not tell the steppe
# peoples of AD 2-150 from their settled neighbours on Earth (Xiongnu 0.19, Xianbei 0.06, Huns 0.11 against
# Han 0.05 and Rome 0.05 by people; T4 accuracy 0.57), so riding is a matter of the map's lore: name them here.
MOUNTED = set()          # polity names as in polities.json, without the "(...)" part
HERDING_SHARE = 0.3      # reported only (F7)
CAMP_DENSITY = 0.5       # a riding polity's reach starts wherever its herds graze (people / km2)


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


def map_climate(data, meta, arrays, shape):
    """Monthly temperature (mean, max, min), rain, winds and storminess of the
    atlas on the analysis grid, the latitude of each cell and the navigable
    rivers."""
    from harvest.export import surface_months
    t, p, d, latitude = surface_months(meta, arrays)
    h, w = shape
    yy, xx = np.mgrid[:h, :w]
    px, py = (xx + .5) * meta["width"] / w, (yy + .5) * meta["height"] / h
    coords = [py / meta["cell_px"] - .5, px / meta["cell_px"] - .5]
    with np.load(data / "winds12.npz") as z:
        U = np.stack([ndi.map_coordinates(np.asarray(a, float), coords, order=1, mode="nearest") for a in z["U12"]])
        V = np.stack([ndi.map_coordinates(np.asarray(a, float), coords, order=1, mode="nearest") for a in z["V12"]])
    sigma = np.stack([N.storminess(latitude, m) for m in range(12)])
    return dict(T=t, Tmax=t + d / 2, Tmin=t - d / 2, P=p, u=U, v=V, sigma=sigma,
                wind=np.sqrt(U ** 2 + V ** 2 + sigma ** 2), lat=latitude)


def navigable_rivers(shape):
    from scripts.vector_rivers import river_classes
    original = np.asarray(Image.open(ROOT / "data/source/original/rivers.png"))[..., 3] / 255.
    _, navigable = river_classes(original)
    return block_any(navigable, shape, 0.05)


def compute(atlas, density=None):
    """All political reach fields of one atlas on its 1000 x 463 analysis grid.
    `density` (people per km², that grid) replaces the central occupation
    scenario, so other scenarios can be compared (scripts/control_scenarios.py).
    Year-round fields average control over the twelve months."""
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
    route = block_any(rgba("roads.png")[..., 3] > 0, shape)
    road = route & land
    ferry = ndi.binary_closing(route, iterations=2) & ~land        # dotted ferry routes, gaps closed
    hm, hf = decode_harvest(data)
    if density is None:
        density = hf["settlement_base"] * hm["occupation"]["scenarios"]["central"]
    density = np.where(land, density, 0.0)
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

    # the month-by-month world (polity/network.py)
    clim = map_climate(data, meta, arrays, shape)
    world = dict(elev=elev, land=land, biome=biome, swamp=swamp, density=density, cell_km=cell_km,
                 tilt=float(meta["world"]["tilt"]), river=navigable_rivers(shape), road=road, ferry=ferry,
                 tracks=tracks, **clim)
    st = N.statics(world); cl = N.climate(world, st)
    places = [(t["row"], t["col"]) for t in towns]
    from .transport import ports_of
    ports = ports_of(places, st["water"])
    near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
    river_places = [(y, x) for y, x in places if near_river[y, x]]
    W = shape[1]
    relief = ndi.maximum_filter(elev, 7) - ndi.minimum_filter(elev, 7)          # ~26 km, as on Earth (3 x 9 km)
    refuge = np.exp(C.REFUGE_PER_KM * relief / 1000.0)
    refuge_days = -C.CONTROL_DAYS * C.REFUGE_PER_KM * relief / 1000.0           # the same as extra days

    # sources: roads (county level) and places with their rank
    road_cells = np.flatnonzero(road.ravel())
    t_cells = np.array([t["row"] * W + t["col"] for t in towns])
    t_off = np.array([C.RANK_OFFSET_DAYS * RANK[t["kind"]] for t in towns])
    src_all = np.r_[road_cells, t_cells]; off_all = np.r_[np.full(len(road_cells), C.RANK_OFFSET_DAYS), t_off]
    capital = [t["row"] * W + t["col"] for t in towns if t["kind"] == "imperial capital"]

    # each polity's own roads and places; herding polities ride from their pastures
    groups = {}
    for i, d in info.items():
        if d["name"]:
            groups.setdefault(d["name"].split(" (")[0], []).append(i)
    names = sorted(groups)
    food = hf["crop_capacity"] * hf["clearance"] + hf["pastoral_capacity"]
    herd = np.divide(hf["pastoral_capacity"], food, out=np.zeros(shape), where=food > 0)
    own_src, mobile, herding = [], [], {}
    for name in names:
        own = np.isin(ids, groups[name])
        ppl = density * own
        herding[name] = dict(by_people=float((herd * ppl).sum() / max(ppl.sum(), 1e-9)),
                             by_area=float(herd[own & land].mean()) if (own & land).any() else 0.0)
        if name in MOUNTED:
            cells = np.flatnonzero((own & land & (density >= CAMP_DENSITY)).ravel())
            own_src.append((cells, np.zeros(len(cells)))); mobile.append(True)
        else:
            sel_r = own.ravel()[road_cells]; sel_t = own.ravel()[t_cells]
            own_src.append((np.r_[road_cells[sel_r], t_cells[sel_t]],
                            np.r_[np.full(int(sel_r.sum()), C.RANK_OFFSET_DAYS), t_off[sel_t]])); mobile.append(False)

    D = C.CONTROL_DAYS
    acc = np.zeros(land.size); worst = np.full(land.size, np.inf); worst_month = np.zeros(land.size, np.int8)
    months_in = np.zeros(land.size, np.int8); cap_sum = np.zeros(land.size); cap_worst = np.zeros(land.size)
    reach_acc = np.zeros((len(names), land.size))
    causes = []
    for m in range(12):
        net = N.month_network(world, st, cl, m, ports, river_places)
        d = net.days(src_all, off_all)
        acc += np.exp(-d / D)
        months_in += (d <= D)
        upd = d > np.where(np.isfinite(worst), worst, -1)
        worst = np.where(upd, d, worst); worst_month = np.where(upd, m, worst_month)
        if capital:
            dc = net.days(capital)
            cap_sum += np.minimum(dc, 999); cap_worst = np.maximum(cap_worst, np.minimum(dc, 999))
        horse = N.month_network(world, st, cl, m, horse=True) if any(mobile) else None
        for k, (src, off) in enumerate(own_src):
            reach_acc[k] += np.exp(-(horse if mobile[k] else net).days(src, off) / D)
        causes.append(N.cause(cl, st, m).ravel())
    with np.errstate(divide="ignore"):
        days_year = (-D * np.log(acc / 12)).reshape(shape)
        reach = -D * np.log(reach_acc / 12)
    reach = reach.reshape((len(names),) + shape) + refuge_days
    worst = worst.reshape(shape); worst_month = worst_month.reshape(shape)
    hardest_cause = np.take_along_axis(np.stack(causes), worst_month.ravel()[None], 0)[0].reshape(shape)
    f = dict(days_open=days_year, days_winter=worst, capital_days_open=(cap_sum / 12).reshape(shape),
             capital_days_winter=cap_worst.reshape(shape), months_within_day=months_in.reshape(shape),
             hardest_month=worst_month, hardest_cause=hardest_cause,
             sea_open_months=(cl["sea"] >= 1).sum(0) * st["water"])
    best = np.argmin(reach, 0); best_days = np.min(reach, 0)
    second_days = np.partition(reach, 1, axis=0)[1] if len(names) > 1 else np.full(shape, np.inf)
    masked = reach.copy(); np.put_along_axis(masked, best[None], np.inf, 0)
    second = np.argmin(masked, 0); del masked
    claim = np.full(shape, -1, np.int16)                   # de jure: the painted fill, by polity name
    for k, name in enumerate(names):
        claim[np.isin(ids, groups[name])] = k
    f["polity_best"] = np.where(np.isfinite(best_days), best, -1)
    f["polity_best_days"] = best_days
    f["polity_second_days"] = second_days
    colours = {name: info[groups[name][0]]["rgb"] for name in names}
    with np.errstate(invalid="ignore"):
        contested = land & (best_days <= HELD_DAYS) & (second_days - best_days <= CONTESTED_DAYS)
    control_year = np.exp(-days_year / D) * refuge
    control_worst = np.exp(-worst / D) * refuge
    return dict(fields=f, land=land, road=road, ferry=ferry, tracks=tracks, routes=routes, links=links,
                suggested=suggested, coast_km=coast_km, smooth_density=smooth_density, graph_open=bare,
                eta_open=open_eta, water_distance=geo["water_distance"], polity_ids=ids, polity_info=info,
                groups=groups, polity_names=names, polity_rgb=colours, towns=towns, core=core, frontier=frontier,
                swamp=swamp, density=density, paths=paths, cell_km=cell_km, elev=elev, meta=meta,
                held=land & (best_days <= HELD_DAYS), contested=contested, refuge=refuge, relief=relief,
                mobile={n: m_ for n, m_ in zip(names, mobile)}, herding=herding, river=world["river"],
                water=st["water"], ports=ports, control_open=control_year, control_winter=control_worst,
                world=world, statics=st, climate=cl, river_places=river_places, reach=reach, second=second,
                claim=np.where(land, claim, -1))
