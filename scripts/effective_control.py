"""Effective control on the campaign map: days beyond the roads and towns.

    python3 -I scripts/effective_control.py --atlas atlases/free_fit --out output/control/free_fit

Inputs: the atlas's terrain and potential biomes (data/atlas.json + atlas.bin,
1000 x 463 cells of ~3.7 km), the painted swamp zone, its monthly snow cover,
and the campaign map's political layers (data/source/ravages_v8: roads,
settlements, polity fills, core and frontier commanderies). See
polity/control.py for the travel model. Writes fields.npz, summary.json and
maps.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from harvest.export import climate_arrays, geometry  # noqa: E402
from polity.control import control, days_from, path_factor, terrain_coefficient, travel_graph  # noqa: E402
from population.export import decode_harvest  # noqa: E402
from rotclimate.geography import target_fullres  # noqa: E402

LAYERS = ROOT / "data/source/ravages_v8"
INK, SURFACE, SEA = "#1b262c", "#fcfcfb", "#d6e4f0"


def rgba(name):
    return np.asarray(Image.open(LAYERS / name).convert("RGBA"))


def block_any(mask, shape, share=0.05):
    """Share of each analysis cell covered by a full-resolution mask, thresholded."""
    im = Image.fromarray((mask * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.BOX)
    return np.asarray(im) / 255.0 > share


def settlements(shape):
    """(row, col, kind) of each settlement symbol, kinds by colour and size."""
    a = rgba("settlements.png"); m = a[..., 3] > 0
    lab, n = ndi.label(m)
    out = []
    H, W = m.shape
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        px = a[sl][lab[sl] == i][:, :3]
        colours = {tuple(int(v) for v in c) for c in px}
        size = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
        # the map key: purple rectangle with gold brackets = imperial capital,
        # purple circle with gold brackets = major imperial city, purple square
        # = imperial fort, green square = imperial monastery, large / small
        # white circle = fortified city / town
        if (255, 216, 0) in colours:
            kind = "imperial capital" if size > 20 else "major imperial city"
        elif (178, 0, 255) in colours:
            kind = "imperial fort"
        elif (0, 168, 107) in colours:
            kind = "imperial monastery"
        else:
            kind = "fortified city" if size >= 13 else "fortified town"
        cy, cx = ndi.center_of_mass(m[sl] & (lab[sl] == i))
        y, x = sl[0].start + cy, sl[1].start + cx
        out.append(dict(kind=kind, y_px=float(y), x_px=float(x),
                        row=int(min(shape[0] - 1, y * shape[0] / H)), col=int(min(shape[1] - 1, x * shape[1] / W))))
    return out


def legions(shape):
    """(row, col) of the imperial legion markers."""
    m = rgba("legions.png")[..., 3] > 0
    lab, n = ndi.label(ndi.binary_closing(m, iterations=2))
    H, W = m.shape
    out = []
    for i, (y, x) in enumerate(ndi.center_of_mass(m, lab, range(1, n + 1)), 1):
        out.append(dict(kind="legion", y_px=float(y), x_px=float(x),
                        row=int(min(shape[0] - 1, y * shape[0] / H)), col=int(min(shape[1] - 1, x * shape[1] / W))))
    return out


def polities(shape):
    """Polity fills by colour on the analysis grid: id map and RGB of each id."""
    a = rgba("borders_fill.png")
    small = np.asarray(Image.fromarray(a).resize((shape[1], shape[0]), Image.NEAREST))
    m = small[..., 3] > 0
    keys = small[..., 0].astype(int) * 65536 + small[..., 1].astype(int) * 256 + small[..., 2]
    ids = np.zeros(shape, np.int16); colours = {}
    values, counts = np.unique(keys[m], return_counts=True)
    for k, c in zip(values, counts):
        if c < 40:            # anti-aliased edges and label fringes
            continue
        i = len(colours) + 1
        ids[m & (keys == k)] = i
        colours[i] = ((k >> 16) & 255, (k >> 8) & 255, k & 255)
    return ids, colours


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    data = a.atlas / "data"; meta = json.loads((data / "atlas.json").read_text())
    arrays = climate_arrays(data, meta)
    elev = np.asarray(arrays["elev"], float); biome = np.asarray(arrays["biome"]); shape = elev.shape
    geo, _ = geometry(meta, shape)
    land = geo["land_fraction"] > 0.5
    cell_km = meta["width"] / shape[1] * meta["mi_per_px"] * 1.609344
    target = target_fullres()
    swamp = np.asarray(Image.fromarray((target == 5).astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.BOX)) > 127
    snow = np.asarray(arrays["snow"], float)                       # local months on the 116 x 250 climate grid
    snow_share = (snow > 10).mean(0)
    snow_share = np.asarray(Image.fromarray(snow_share.astype(np.float32)).resize((shape[1], shape[0]), Image.BILINEAR))
    route = block_any(rgba("roads.png")[..., 3] > 0, shape)
    road = route & land
    # dotted ferry routes over water: close the gaps between the dots
    ferry = ndi.binary_closing(route, iterations=2) & ~land
    hm, hf = decode_harvest(data)
    density = hf["settlement_base"] * hm["occupation"]["scenarios"]["central"]   # people per km2, central scenario
    paths = path_factor(np.where(land, density, 0.0))
    towns = settlements(shape) + legions(shape)
    ids, colours = polities(shape)
    core = block_any(rgba("commanderies_core.png")[..., 3] > 128, shape, 0.5) & land
    frontier = block_any(rgba("commanderies_frontier.png")[..., 3] > 128, shape, 0.5) & land

    # snap settlements to land
    _, nearest = ndi.distance_transform_edt(~land, return_indices=True)
    for t in towns:
        t["row"], t["col"] = int(nearest[0, t["row"], t["col"]]), int(nearest[1, t["row"], t["col"]])
    network = [(r, c) for r, c in zip(*np.nonzero(road))] + [(t["row"], t["col"]) for t in towns]
    fields = {}
    for season, share in (("open", None), ("winter", snow_share)):
        eta = terrain_coefficient(biome, swamp, share)
        graph = travel_graph(elev, land, road, eta, cell_km, paths, ferry)
        fields[f"days_{season}"] = days_from(graph, shape, network)
        capital = [(t["row"], t["col"]) for t in towns if t["kind"] == "imperial capital"]
        fields[f"capital_days_{season}"] = days_from(graph, shape, capital)
    # each polity's reach from its own roads, settlements and garrisons (open season)
    names = json.loads((LAYERS / "polities.json").read_text())["polities"]
    base = lambda name: name.split(" (")[0]
    groups = {}
    for i, rgb in colours.items():
        name = names.get(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
        if name:
            groups.setdefault(base(name), []).append(i)
    eta = terrain_coefficient(biome, swamp, None)
    graph = travel_graph(elev, land, road, eta, cell_km, paths, ferry)
    polity_names = sorted(groups)
    reach = np.full((len(polity_names),) + shape, np.inf)
    for k, name in enumerate(polity_names):
        own = np.isin(ids, groups[name])
        src = [(r, c) for r, c in zip(*np.nonzero(road & own))]
        src += [(t["row"], t["col"]) for t in towns if own[t["row"], t["col"]]]
        reach[k] = days_from(graph, shape, src)
    best = np.argmin(reach, 0); best_days = np.min(reach, 0)
    second_days = np.partition(reach, 1, axis=0)[1]
    fields["polity_best"] = np.where(np.isfinite(best_days), best, -1).astype(float)
    fields["polity_best_days"] = best_days
    fields["polity_second_days"] = second_days
    for k in list(fields):
        fields[k] = np.where(land, fields[k], np.nan)
    a.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.out / "fields.npz", **fields, land=land, road=road, polity=ids, core=core, frontier=frontier,
                        swamp=swamp, snow_share=snow_share, density=density, paths=paths, ferry=ferry)

    days = fields["days_open"]; ctl = control(days)
    area = cell_km ** 2
    def share_within(mask, limit, key="days_open"):
        v = fields[key][mask & land]
        return float(np.mean(v <= limit)) if v.size else None
    summary = dict(cell_km=cell_km, settlements={k: sum(t["kind"] == k for t in towns) for k in sorted({t["kind"] for t in towns})},
                   road_cells=int(road.sum()), ferry_cells=int(ferry.sum()),
                   land=dict(within_1_day=share_within(land, 1), within_2_days=share_within(land, 2),
                             within_3_days=share_within(land, 3), winter_within_1_day=share_within(land, 1, "days_winter")),
                   commanderies=dict(
                       core=dict(cells=int(core.sum()), mean_days=float(np.nanmean(days[core])), mean_control=float(np.nanmean(ctl[core])),
                                 capital_days=float(np.nanmean(fields["capital_days_open"][core]))),
                       frontier=dict(cells=int(frontier.sum()), mean_days=float(np.nanmean(days[frontier])),
                                     mean_control=float(np.nanmean(ctl[frontier])),
                                     capital_days=float(np.nanmean(fields["capital_days_open"][frontier])))),
                   polities={})
    names = json.loads((LAYERS / "polities.json").read_text())["polities"]
    for i, rgb in colours.items():
        m = (ids == i) & land
        if m.sum() < 30:
            continue
        hexcode = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        summary["polities"][names.get(hexcode, hexcode)] = dict(
            area_km2=float(m.sum() * area), within_1_day=share_within(m, 1), within_2_days=share_within(m, 2),
            mean_control=float(np.nanmean(ctl[m])), winter_within_1_day=share_within(m, 1, "days_winter"))
    # de facto: who holds each place (within 2 days), contested where a rival is within half a day of it
    held = land & (best_days <= 2.0)
    contested = held & (second_days - best_days <= 0.5)
    drawn = {}
    for k, name in enumerate(polity_names):
        own = np.isin(ids, groups[name]) & land
        mine = held & (best == k)
        drawn[name] = dict(drawn_km2=float(own.sum() * area), held_km2=float(mine.sum() * area),
                           held_inside_km2=float((mine & own).sum() * area), held_beyond_km2=float((mine & ~own).sum() * area),
                           contested_km2=float((contested & (best == k)).sum() * area))
    summary["de_facto"] = dict(held_share_of_land=float(held.sum() / land.sum()), contested_share_of_land=float(contested.sum() / land.sum()),
                               polities=drawn)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1))
    (a.out / "polity_names.json").write_text(json.dumps(polity_names, ensure_ascii=False))
    (a.out / "settlements.json").write_text(json.dumps(towns, indent=1))
    print(json.dumps({k: summary[k] for k in ("settlements", "land", "commanderies")}, indent=1))

    # maps
    plt.rcParams.update({"font.size": 10, "text.color": INK, "figure.facecolor": SURFACE})
    bounds_c = [0, 2, 5, 13, 22, 37, 50, 61, 78, 100.01]
    cmap_c = ListedColormap(["#4d1a17", "#8f3426", "#c8603a", "#e5a557", "#e8d98a", "#b7cf7a", "#7fb05a", "#4f8f4a", "#1f5f3a"])
    norm_c = BoundaryNorm(bounds_c, cmap_c.N)
    borders = np.asarray(Image.open(LAYERS / "borders.png").convert("RGBA").resize((shape[1] * 2, shape[0] * 2), Image.BOX))[..., 3] > 40
    yy, xx = np.arange(shape[0]) + 0.5, np.arange(shape[1]) + 0.5
    ry, rx = np.nonzero(road)
    for key, title in (("days_open", "Effective control beyond the roads and towns, snow-free season"),
                       ("days_winter", "Effective control beyond the roads and towns, with the winter's snow")):
        fig, ax = plt.subplots(figsize=(16, 8), constrained_layout=True)
        ax.set_facecolor(SEA)
        ctl_map = np.where(land, 100 * control(fields[key]), np.nan)
        im = ax.imshow(ctl_map, cmap=cmap_c, norm=norm_c, interpolation="nearest", extent=(0, shape[1], shape[0], 0))
        ax.imshow(np.where(borders, 1.0, np.nan), cmap=ListedColormap([INK]), alpha=0.6, interpolation="nearest",
                  extent=(0, shape[1], shape[0], 0))
        ax.scatter(rx + 0.5, ry + 0.5, s=0.12, c="#5a2a12", marker="s", linewidths=0, alpha=0.7)
        fy, fx = np.nonzero(ferry)
        ax.scatter(fx + 0.5, fy + 0.5, s=1.5, c="#ff6a00", marker="s", linewidths=0)
        for kind, size, marker, colour in (("fortified town", 6, "o", "#ffffff"), ("fortified city", 16, "o", "#ffffff"),
                                           ("imperial fort", 14, "s", "#b200ff"), ("imperial monastery", 14, "s", "#00a86b"),
                                           ("legion", 34, "D", "#b200ff"), ("major imperial city", 34, "o", "#b200ff"),
                                           ("imperial capital", 80, "s", "#b200ff")):
            pts = [(t["col"], t["row"]) for t in towns if t["kind"] == kind]
            if pts:
                xs, ys = zip(*pts)
                ax.scatter(np.array(xs) + 0.5, np.array(ys) + 0.5, s=size, c=colour, marker=marker,
                           edgecolors="#ffd800" if kind in ("legion", "major imperial city", "imperial capital") else INK,
                           linewidths=0.8, label=kind)
        ax.contour(xx, yy, np.where(land, fields[key], 99), levels=[1, 2, 3], colors=[INK, INK, INK],
                   linewidths=[0.9, 0.6, 0.4], linestyles=["solid", "dashed", "dotted"])
        ax.set_xlim(0, shape[1]); ax.set_ylim(shape[0], 0)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title + " · lines: 1, 2 and 3 days on foot from the nearest road or settlement", loc="left")
        cb = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.01)
        cb.set_label("effective control, % (exp(-days / 1 day))")
        ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
        fig.savefig(a.out / f"control_{key.split('_')[1]}.png", dpi=110, facecolor=SURFACE)
        plt.close(fig)
    # de facto map: colour of the polity whose reach is nearest, faded by control, hatched where contested
    rgb_of = {}
    for i, rgb in colours.items():
        name = names.get(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")
        if name and base(name) not in rgb_of:
            rgb_of[base(name)] = np.array(rgb) / 255.0
    img = np.ones(shape + (3,)) * np.array([0.84, 0.89, 0.94])
    strength = np.clip(control(best_days), 0, 1)
    for k, name in enumerate(polity_names):
        m = land & (best == k)
        col = rgb_of.get(name, np.array([0.6, 0.6, 0.6]))
        img[m] = col * strength[m, None] + np.array([0.93, 0.91, 0.86]) * (1 - strength[m, None])
    img[land & ~np.isfinite(best_days)] = [0.93, 0.91, 0.86]
    fig, ax = plt.subplots(figsize=(16, 8), constrained_layout=True)
    ax.imshow(img, interpolation="nearest", extent=(0, shape[1], shape[0], 0))
    ax.imshow(np.where(borders, 1.0, np.nan), cmap=ListedColormap([INK]), alpha=0.75, interpolation="nearest",
              extent=(0, shape[1], shape[0], 0))
    cy, cx = np.nonzero(contested[::3, ::3])
    ax.scatter(cx * 3 + 1.5, cy * 3 + 1.5, s=1.2, c=INK, marker="x", linewidths=0.4)
    for k, name in enumerate(polity_names):
        m = land & (best == k) & held
        if m.sum() > 300:
            r, c = np.nonzero(m)
            ax.text(np.median(c), np.median(r), name, fontsize=7.5, ha="center", va="center", color=INK,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Who reaches where: each place takes the polity whose own roads, towns and garrisons are nearest in days; "
                 "pale = weak reach, x = contested (a rival within half a day); dark lines: the drawn borders", loc="left", fontsize=10)
    fig.savefig(a.out / "de_facto.png", dpi=110, facecolor=SURFACE)
    plt.close(fig)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
