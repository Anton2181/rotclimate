"""The de facto gap fill on Earth (calibration/polity_20261025/plan_fill.json):
held land bridged by a closing in travel time, against Cliopatria's Roman
empire of AD 150 (fit west of 20 E, test east of it) and Han China's
commanderies of AD 2.

    python3 -I scripts/polity_fill_check.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import polity_earth_check as P                    # noqa: E402
from polity import control as C                    # noqa: E402
from polity import defacto as F                    # noqa: E402
from polity import earth as E                      # noqa: E402
from polity import network as N                    # noqa: E402

PLAN = ROOT / "calibration/polity_20261025"
OUT = PLAN / "fill.json"
plan = json.loads((PLAN / "plan_fill.json").read_text())
GRID = plan["operation"]["grid_r_days"]
log = P.log


def bridged_all(held, land, world, st, cl):
    t = time.time()
    foot = [N.month_network(world, st, cl, m, boats=False) for m in range(12)]
    dil = F.foot_days(foot, np.flatnonzero(held.ravel()), limit=max(GRID) + 6).reshape(held.shape)
    out = {}
    for r in GRID:
        out[r] = F.bridge(held, land, foot, r, dil)
        log(f"   r {r:g}: held share {out[r][land].mean():.3f} ({time.time() - t:.0f}s)")
    return out


def scores(by_r, inside, band):
    return {str(r): P.balanced_accuracy(np.where(b, 0.0, 99.0), inside, band, 1.0) for r, b in by_r.items()}


def rome():
    P.apply_sea()
    g = P.load_window("rome")
    land = g["land"].astype(bool); W = land.shape[1]
    road = E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land
    towns = E.hanson_towns(150)
    r, c, ok = P.snap(g, np.array([t["lat"] for t in towns]), np.array([t["lon"] for t in towns]))
    towns = [(int(y), int(x)) for y, x, k in zip(r, c, ok) if k]
    inside = E.inside_polygons(g, E.cliopatria("Roman Empire", 150)) & land
    world = P.world_of(g, road)
    st = N.statics(world)
    eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
    v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], st["paths"])
    flat_t = np.array([y * W + x for y, x in towns])
    srcs = np.unique(np.r_[flat_t, np.flatnonzero(road.ravel())])
    from scipy.sparse.csgraph import dijkstra
    d1 = dijkstra(v1, directed=True, indices=srcs, min_only=True).reshape(land.shape)
    band = land & (d1 <= 15)
    st, cl, nets = P.monthly_nets(g, world, towns)
    d2 = P.year_days(nets, srcs).reshape(land.shape)
    held = land & (d2 <= 2.0)
    del nets
    by_r = bridged_all(held, land, world, st, cl)
    west = band & (g["lon"] < 20.0); east = band & (g["lon"] >= 20.0)
    return dict(g=g, land=land, inside=inside, by_r=by_r, west=west, east=east)


def han(r_fit, held_days):
    P.apply_sea()
    g = P.load_window("han")
    world = P.world_of(g); land = world["land"]; W = land.shape[1]
    seats = E.han_seats()
    r, c, ok = P.snap(g, np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
    places = [(int(y), int(x)) for y, x, k in zip(r, c, ok) if k]
    ids, _ = E.han_commanderies(g)
    inside = ids >= 0
    st, cl, nets = P.monthly_nets(g, world, places)
    flat = np.array([y * W + x for y, x in places])
    base = P.year_days(nets, flat).reshape(land.shape)
    band = land & (base <= 15)
    held = land & (base <= held_days)
    del nets
    by_r = bridged_all(held, land, world, st, cl)
    return dict(g=g, land=land, inside=inside & land, by_r=by_r, band=band)


def main():
    out = dict(plan="plan_fill.json")
    R = rome()
    fit = scores(R["by_r"], R["inside"], R["west"])
    best = max(fit, key=fit.get)
    r_fit = float(best) if fit[best] - fit["0"] >= 0.005 else 0.0
    out["F_fill"] = dict(by_r=fit, best=float(best), adopted=r_fit)
    log("F_fill (Rome west):", {k: round(v, 4) for k, v in fit.items()}, "adopted", r_fit)
    (OUT).write_text(json.dumps(out, indent=1))
    t1 = scores(R["by_r"], R["inside"], R["east"])
    out["T_fill1"] = dict(by_r=t1, at_fit=t1[str(r_fit) if r_fit else "0"], at_zero=t1["0"],
                          passed=bool(t1[str(r_fit) if r_fit else "0"] >= t1["0"]),
                          open_regions_km2=F.open_regions(R["by_r"][r_fit if r_fit else 0], R["inside"],
                                                          R["g"]["cell_km"]))
    log("T_fill1 (Rome east):", {k: round(v, 4) for k, v in t1.items()}, "passed", out["T_fill1"]["passed"])
    OUT.write_text(json.dumps(out, indent=1))
    fits = json.loads((PLAN / "fits.json").read_text())
    H = han(r_fit, fits["F1_held_days"]["held_days"])
    t2 = scores(H["by_r"], H["inside"], H["band"])
    key = str(r_fit) if r_fit else "0"
    out["T_fill2"] = dict(by_r=t2, at_fit=t2[key], at_zero=t2["0"], passed=bool(t2[key] >= t2["0"]),
                          held_days=fits["F1_held_days"]["held_days"],
                          open_regions_km2=F.open_regions(H["by_r"][r_fit if r_fit else 0], H["inside"],
                                                          H["g"]["cell_km"]))
    log("T_fill2 (Han):", {k: round(v, 4) for k, v in t2.items()}, "passed", out["T_fill2"]["passed"])
    OUT.write_text(json.dumps(out, indent=1))
    np.savez_compressed(ROOT / "output/polity_earth/fill.npz",
                        rome_inside=R["inside"], rome_land=R["land"],
                        **{f"rome_r{r:g}": b for r, b in R["by_r"].items()},
                        han_inside=H["inside"], han_land=H["land"],
                        **{f"han_r{r:g}": b for r, b in H["by_r"].items()})


if __name__ == "__main__":
    main()
