"""Mud with a rain-aware evaporation demand (calibration/polity_20261025/addendum_mud_pet_20261031.json).

    python -I scripts/polity_mud_pet.py --out output/polity_mud_20261031 [--no-t1]

Variants: A = the 25 mm topsoil layer with Hargreaves' PET (the first seasons
addendum), B = Droogers & Allen's (2002) PET, C = B with the topsoil layer.
Stations from WorldClim 2.1 5' point climate (scripts/polity_season_stations.py):
six blind rasputitsa stations, six blind dry controls, and the first
addendum's stations (seen). Reported, not gating: test T1 (Roman extent,
AD 150) with each variant and the share of each map's land in mud by month.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from polity import seasons as S  # noqa: E402
from polity_season_stations import station_climate  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025/addendum_mud_pet_20261031.json"
VARIANTS = {"current": dict(topsoil_mm=0.0, pet_method="hargreaves"),
            "A": dict(topsoil_mm=25.0, pet_method="hargreaves"),
            "B": dict(topsoil_mm=0.0, pet_method="droogers_allen"),
            "C": dict(topsoil_mm=25.0, pet_method="droogers_allen")}
SEEN = {"Kyiv": (50.45, 30.52), "Moscow": (55.75, 37.62)}
SEEN_CONTROLS = {"Rome": ((41.90, 12.50), "Jun-Sep"), "Patna": ((25.60, 85.10), "Oct-May"),
                 "Cairo": ((30.04, 31.24), "all"), "Beijing": ((39.90, 116.40), "Oct-Feb")}
M = S.MONTHS


def months(spec):
    if spec == "all":
        return list(M)
    a, b = spec.split("-"); i, j = M.index(a), M.index(b)
    return [M[k % 12] for k in range(i, i + (j - i) % 12 + 1)]


def station_mud(lat, lon):
    c = station_climate(lat, lon)
    out = {}
    for name, kw in VARIANTS.items():
        f = S.fields(c["tavg"], c["tmax"], c["tmin"], c["prec"], np.array([lat]), **kw)
        out[name] = dict(mud=[round(float(x), 2) for x in f["mud"][:, 0]], pet=[round(float(x), 1) for x in f["pet"][:, 0]])
    out["climate"] = {k: [round(float(x), 1) for x in v[:, 0]] for k, v in c.items()}
    return out


def map_mud_share(atlas):
    from harvest.export import climate_arrays, geometry
    from polity.fields import map_climate
    data = ROOT / atlas / "data"; meta = json.loads((data / "atlas.json").read_text())
    arrays = climate_arrays(data, meta)
    shape = np.asarray(arrays["elev"]).shape
    geo, _ = geometry(meta, shape)
    land = geo["land_fraction"] > 0.5
    mc = map_climate(data, meta, arrays, shape)
    out = {}
    for name, kw in VARIANTS.items():
        f = S.fields(mc["T"], mc["Tmax"], mc["Tmin"], mc["P"], mc["lat"], **kw)
        out[name] = [round(float((f["mud"][m][land] >= 0.5).mean()), 4) for m in range(12)]
    return out


def t1(variant):
    """T1 of plan.json (v2 control rule, balanced accuracy against the Roman polygon) under a variant."""
    import polity_earth_check as P
    from polity import earth as E
    from polity import control as C
    P.apply_sea()
    kw = VARIANTS[variant]
    S.TOPSOIL_MM, S.PET_METHOD = kw["topsoil_mm"], kw["pet_method"]
    fits = json.loads((P.PLAN / "fits.json").read_text())
    path = P.CACHEDIR / "rome.npz"
    if not path.exists():
        P.CACHEDIR.mkdir(parents=True, exist_ok=True)
        w = P.WINDOWS["rome"]
        g = E.window(w["lat0"], w["lon0"], w["width_km"], w["height_km"], w["cell_km"])
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in g.items()})
    g = P.load_window("rome")
    land = g["land"].astype(bool); W = land.shape[1]
    road = E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land
    towns = E.hanson_towns(150)
    r, c, ok = P.snap(g, np.array([t["lat"] for t in towns]), np.array([t["lon"] for t in towns]))
    towns = [dict(t, row=int(y), col=int(x)) for t, y, x, k in zip(towns, r, c, ok) if k]
    inside = E.inside_polygons(g, E.cliopatria("Roman Empire", 150)) & land
    world = P.world_of(g, road)
    st = P.N.statics(world)
    eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
    v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], st["paths"])
    flat_t = np.array([t["row"] * W + t["col"] for t in towns])
    from scipy.sparse.csgraph import dijkstra
    d1 = dijkstra(v1, directed=True, indices=np.unique(np.r_[flat_t, np.flatnonzero(road.ravel())]), min_only=True).reshape(land.shape)
    band = land & (d1 <= 15)
    adopted = fits["F2_ranks"]["adopted"]
    places = [(t["row"], t["col"]) for t in towns]
    st, cl, nets = P.monthly_nets(g, world, places)
    high = np.array([str(t.get("rank")) in ("1", "2", "1.0", "2.0") for t in towns])
    off_t = adopted["o_county"] * (~high)
    if adopted["lam"] > 0:
        rr, rc_, _ = P.snap(g, np.array([41.89]), np.array([12.49]))
        cap = P.year_days(nets, [int(rr[0]) * W + int(rc_[0])]).ravel()
        off_t = off_t + adopted["lam"] * np.nan_to_num(cap[flat_t], posinf=60)
    road_cells = np.flatnonzero(road.ravel())
    d2 = P.year_days(nets, np.r_[flat_t, road_cells], np.r_[off_t, np.full(len(road_cells), adopted["o_county"])]).reshape(land.shape)
    if fits["F4_refuge"]["adopted"]:
        d2 = d2 - C.CONTROL_DAYS * fits["F4_refuge"]["k_per_km"] * g["relief"] / 1000
    held = adopted["held_days"]
    mud_share = [float((cl["mud"][m][land] >= 0.5).mean()) for m in range(12)]
    S.TOPSOIL_MM, S.PET_METHOD = 0.0, "hargreaves"
    return dict(ba=P.balanced_accuracy(d2, inside, band, held), auc=P.auc(d2, inside, band), held=held,
                window_mud_share=[round(x, 4) for x in mud_share])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_mud_20261031")
    ap.add_argument("--no-t1", action="store_true")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(PLAN.read_text())
    blind = plan["stations_blind"]
    res = dict(addendum=str(PLAN.relative_to(ROOT)), stations={}, checks={})
    groups = dict(rasputitsa={k: tuple(v) for k, v in blind["rasputitsa"].items()},
                  controls={k: tuple(v[0]) for k, v in blind["controls"].items()}, seen=SEEN,
                  seen_controls={k: v[0] for k, v in SEEN_CONTROLS.items()})
    for group, sts in groups.items():
        for name, (la, lo) in sts.items():
            res["stations"][name] = dict(group=group, **station_mud(la, lo))
    mud = lambda name, v: dict(zip(M, res["stations"][name][v]["mud"]))
    for v in VARIANTS:
        rasp = {n: dict(spring=[m for m in ("Mar", "Apr", "May") if mud(n, v)[m] >= 0.5],
                        autumn=[m for m in ("Oct", "Nov") if mud(n, v)[m] >= 0.5]) for n in blind["rasputitsa"]}
        rasp_ok = {n: bool(r["spring"] and r["autumn"]) for n, r in rasp.items()}
        ctrl = {n: [m for m in months(spec) if mud(n, v)[m] >= 0.5] for n, (_, spec) in blind["controls"].items()}
        ctrl.update({n: [m for m in months(spec) if mud(n, v)[m] >= 0.5] for n, (_, spec) in SEEN_CONTROLS.items()})
        seen = {n: [m for m in M if mud(n, v)[m] >= 0.5] for n in SEEN}
        res["checks"][v] = dict(rasputitsa=rasp, rasputitsa_pass=rasp_ok, control_failures={k: x for k, x in ctrl.items() if x},
                                seen_mud_months=seen, passed=bool(all(rasp_ok.values()) and not any(ctrl.values())))
        print(v, "rasputitsa", sum(rasp_ok.values()), "/ 6", "control failures", {k: x for k, x in ctrl.items() if x},
              "Kyiv", seen["Kyiv"], "Moscow", seen["Moscow"], flush=True)
    passing = [v for v in ("B", "A", "C") if res["checks"][v]["passed"]]
    res["adopted"] = passing[0] if passing else None
    res["rule"] = plan["adopt_if"]
    res["map_mud_share"] = {atlas: map_mud_share(f"atlases/{atlas}") for atlas in ("free_fit", "earth_fit", "whittaker_fit")}
    (a.out / "mud_pet.json").write_text(json.dumps(res, indent=1))
    if not a.no_t1:
        res["T1_roman_extent"] = {}
        for v in VARIANTS:
            res["T1_roman_extent"][v] = t1(v)
            print("T1", v, res["T1_roman_extent"][v]["ba"], flush=True)
            (a.out / "mud_pet.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(adopted=res["adopted"]), indent=1))


if __name__ == "__main__":
    main()
