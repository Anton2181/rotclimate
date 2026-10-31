"""Dry-land towns need water (calibration/polity_20261025/addendum_dry_towns_20261031.json).

    python -I scripts/polity_dry_towns.py --out output/polity_dry_towns_20261031

F3 (fit): Han AD 2 county seats per commandery against the seats placed by
polity.settle.place_towns with the adopted seat parameters, for a dry-land
water reach W in {inf, 40, 25, 15} km. T3 (blind): Roman towns of AD 150 per
22 x 22-cell block inside the Roman polygon, the fitted W against inf, over
all blocks and over the dry blocks alone. Aridity: annual rain over
Hargreaves evaporation (polity.seasons) from the window's WorldClim climate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

import polity_earth_check as P  # noqa: E402
from polity import earth as E  # noqa: E402
from polity import network as N  # noqa: E402
from polity import seasons as S  # noqa: E402
from polity import settle  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025/addendum_dry_towns_20261031.json"
WS = [None, 40.0, 25.0, 15.0]


def window(name):
    path = P.CACHEDIR / f"{name}.npz"
    if not path.exists():
        P.CACHEDIR.mkdir(parents=True, exist_ok=True)
        w = P.WINDOWS[name]
        g = E.window(w["lat0"], w["lon0"], w["width_km"], w["height_km"], w["cell_km"])
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in g.items()})
    return P.load_window(name)


def aridity(g):
    pet = S.hargreaves(np.nan_to_num(g["tavg"]), np.nan_to_num(g["tmax"]), np.nan_to_num(g["tmin"]), g["lat"]).sum(0)
    return np.nan_to_num(g["prec"]).sum(0) / np.maximum(pet, 1.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_dry_towns_20261031")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    P.apply_sea()
    fits = json.loads((P.PLAN / "fits.json").read_text())
    b3 = fits["F3_seats"]["best"]
    res = dict(addendum=str(PLAN.relative_to(ROOT)), seat_people=b3["seat_people"], max_radius_km=b3["max_radius_km"])
    # ---- F3 on Han AD 2
    g = window("han")
    world = P.world_of(g); land = world["land"]
    st = N.statics(world)
    seats = E.han_seats()
    r, c, ok = P.snap(g, np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
    seats = [dict(s, row=int(y), col=int(x)) for s, y, x, k in zip(seats, r, c, ok) if k]
    ids, rows = E.han_commanderies(g)
    inside = ids >= 0
    water_km = ndi.distance_transform_edt(~((st["basin"] > 0) | st["water"])) * world["cell_km"]
    ai = aridity(g)
    coverage = np.array([g["covered"][ids == k].mean() if (ids == k).any() else 0 for k in range(len(rows))])
    ncells = np.bincount(ids[ids >= 0], minlength=len(rows))
    use = (coverage >= 0.9) & (ncells >= 4)
    actual = np.bincount([ids[s["row"], s["col"]] for s in seats if ids[s["row"], s["col"]] >= 0], minlength=len(rows))
    dry_cm = np.array([ai[ids == k].mean() < settle.DRY_ARIDITY if (ids == k).any() else False for k in range(len(rows))])
    seat_water = np.array([water_km[s["row"], s["col"]] for s in seats])
    seat_dry = np.array([ai[s["row"], s["col"]] < settle.DRY_ARIDITY for s in seats])
    res["han_seats"] = dict(n=len(seats), dry=int(seat_dry.sum()),
                            dry_seat_water_km_quantiles=np.quantile(seat_water[seat_dry], [0.5, 0.9, 1.0]).round(1).tolist() if seat_dry.any() else None,
                            dry_land_water_km_median=float(np.median(water_km[inside & (ai < settle.DRY_ARIDITY)])) if (inside & (ai < settle.DRY_ARIDITY)).any() else None)
    f3 = {}
    for W in WS:
        towns, _, _ = settle.place_towns(world["density"], land, water_km, np.zeros(land.shape, bool), world["elev"],
                                         world["cell_km"], [], allowed=inside, seat_people=b3["seat_people"],
                                         max_radius_km=b3["max_radius_km"], aridity=ai, dry_water_km=W)
        pred = np.bincount([ids[y, x] for y, x in towns if ids[y, x] >= 0], minlength=len(rows))
        key = "inf" if W is None else f"{W:g}"
        f3[key] = dict(deviance=P.poisson_deviance(actual[use], pred[use]), placed=int(pred[use].sum()), actual=int(actual[use].sum()),
                       dry_deviance=P.poisson_deviance(actual[use & dry_cm], pred[use & dry_cm]) if (use & dry_cm).any() else None,
                       dry_placed=int(pred[use & dry_cm].sum()), dry_actual=int(actual[use & dry_cm].sum()))
        print("F3", key, f3[key], flush=True)
    res["F3"] = f3
    best = min(f3, key=lambda k: (round(f3[k]["deviance"], 6), -(1e9 if k == "inf" else float(k))))
    res["W_fitted"] = best
    del world, st, g
    # ---- T3 on Rome AD 150
    g = window("rome")
    land = g["land"].astype(bool)
    road = E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land
    towns = E.hanson_towns(150)
    r, c, ok = P.snap(g, np.array([t["lat"] for t in towns]), np.array([t["lon"] for t in towns]))
    towns = [dict(t, row=int(y), col=int(x)) for t, y, x, k in zip(towns, r, c, ok) if k]
    inside = E.inside_polygons(g, E.cliopatria("Roman Empire", 150)) & land
    world = P.world_of(g, road); st = N.statics(world)
    water_km = ndi.distance_transform_edt(~((st["basin"] > 0) | st["water"])) * g["cell_km"]
    ai = aridity(g)
    B = 22; ny, nx = land.shape[0] // B, land.shape[1] // B
    blocks = lambda a_: a_[:ny * B, :nx * B].reshape(ny, B, nx, B).sum((1, 3))
    cnt = np.zeros((ny, nx))
    for t in towns:
        i, j = t["row"] // B, t["col"] // B
        if i < ny and j < nx:
            cnt[i, j] += 1
    lb = blocks(land.astype(float)); ib = blocks(inside.astype(float))
    okb = (lb >= 0.3 * B * B) & (ib >= 0.5 * lb) & (blocks(g["covered"].astype(float) * land) >= 0.9 * lb)
    dryb = okb & (blocks(np.where(land, ai, 0.0)) / np.maximum(lb, 1) < settle.DRY_ARIDITY)
    t_dry = np.array([ai[t["row"], t["col"]] < settle.DRY_ARIDITY for t in towns])
    t_water = np.array([water_km[t["row"], t["col"]] for t in towns])
    res["roman_towns"] = dict(n=len(towns), dry=int(t_dry.sum()),
                              dry_town_water_km_quantiles=np.quantile(t_water[t_dry], [0.5, 0.9, 1.0]).round(1).tolist() if t_dry.any() else None)
    t3 = {}
    for key in dict.fromkeys(["inf", best]):
        W = None if key == "inf" else float(key)
        pt, _, _ = settle.place_towns(g["density"], land, water_km, road, g["elev"], g["cell_km"], [], allowed=inside,
                                      seat_people=b3["seat_people"], max_radius_km=b3["max_radius_km"], aridity=ai, dry_water_km=W)
        pc = np.zeros((ny, nx))
        for y, x in pt:
            if y // B < ny and x // B < nx:
                pc[y // B, x // B] += 1
        t3[key] = dict(deviance=P.poisson_deviance(cnt[okb], pc[okb]), placed=int(pc[okb].sum()), actual=int(cnt[okb].sum()),
                       dry_deviance=P.poisson_deviance(cnt[dryb], pc[dryb]) if dryb.any() else None,
                       dry_placed=int(pc[dryb].sum()), dry_actual=int(cnt[dryb].sum()), dry_blocks=int(dryb.sum()))
        print("T3", key, t3[key], flush=True)
    res["T3"] = t3
    gain_f3 = 1.0 - f3[best]["deviance"] / f3["inf"]["deviance"]
    adopted = best != "inf" and gain_f3 >= 0.02 and t3[best]["deviance"] <= t3["inf"]["deviance"]
    res.update(F3_gain=gain_f3, adopted=bool(adopted), rule=json.loads(PLAN.read_text())["adopt_if"])
    (a.out / "dry_towns.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(W=best, F3_gain=gain_f3, adopted=adopted), indent=1))


if __name__ == "__main__":
    main()
