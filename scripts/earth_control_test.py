"""Earth test of the atlas's de facto control options (calibration/earth_control_20261106/plan.json).

The atlas chain (rural cereal -> collection -> settlement allocation -> staffed institutional
sources -> paired seasonal reach) runs unchanged on the Earth windows of
scripts/polity_earth_check.py, with Hanson's towns (Rome, AD 150) and the Han county seats (AD 2)
as the sources, then each option is scored against Cliopatria's Roman empire (AD 150) and the
Han commanderies (AD 2).

    .venv/bin/python -I scripts/earth_control_test.py run rome     # food, cases, reach, legacy
    .venv/bin/python -I scripts/earth_control_test.py run han
    .venv/bin/python -I scripts/earth_control_test.py score        # results.json + decision
    .venv/bin/python -I scripts/earth_control_test.py figure
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

PLAN = ROOT / "calibration/earth_control_20261106/plan.json"
OUT = ROOT / "output/earth_control_20261106"
CASES = ["reference", "joint365", "fert_bare", "fert_legume"]
FOOD_CASES = ["joint365", "fert_bare", "fert_legume"]
log = lambda *a: print(*a, flush=True)  # noqa: E731


def sources(name, g):
    import polity_earth_check as P
    from polity import earth as E
    W = g["land"].shape[1]
    if name == "rome":
        pts = E.hanson_towns(150); weight_key = "area_ha"
    else:
        pts = E.han_seats(); weight_key = "people"
    r, c, ok = P.snap(g, np.array([p["lat"] for p in pts]), np.array([p["lon"] for p in pts]))
    flat = (r * W + c)[ok]
    weights = np.array([float(p.get(weight_key) or 0) for p, k in zip(pts, ok) if k])
    nodes, inv = np.unique(flat, return_inverse=True)
    node_weight = np.bincount(inv, weights=weights, minlength=len(nodes))
    return nodes, node_weight, int(ok.sum())


def food_fields(g, land):
    """Cereal production (kcal/yr), harvest calendar bits and fertility factors per window cell."""
    import fertility_integration as FI
    import land_people_earth as LPE
    from harvest.crop_sequences import crop_windows
    from harvest.work_maps import tied_harvest_boundaries
    from land_people import CROPS, FALLOW, FARMED_SHARE, bucket, hargreaves, sunlight_top
    full = np.load(ROOT / "output/land_people/earth/earth.npz")
    elat, elon = full["lat"], full["lon"]
    lat, lon = g["lat"], g["lon"]

    def nearest(axis, x):
        order = np.argsort(axis); a = axis[order]
        i = np.clip(np.searchsorted(a, x), 1, len(a) - 1)
        i = np.where(np.abs(a[i - 1] - x) < np.abs(a[i] - x), i - 1, i)
        return order[i]
    inside = (lat >= elat.min() - 1 / 24) & (lat <= elat.max() + 1 / 24) & (lon >= elon.min() - 1 / 24) & (lon <= elon.max() + 1 / 24)
    ri = nearest(elat, lat); ci = nearest(elon, lon)
    names = [str(x) for x in full["crops"]]
    main = np.nan_to_num(full["main_crop"][ri, ci], nan=-1).astype(int)
    ok = land & inside & full["land"][ri, ci] & (main >= 0)
    cells = np.flatnonzero(ok.ravel())
    crop = np.array([names[m] for m in main.ravel()[cells]])
    kcal = np.array([full["kcal_" + c][ri, ci].ravel()[k] for c, k in zip(crop, cells)], float)
    kcal = np.nan_to_num(kcal)
    arable = np.nan_to_num(full["arable"][ri, ci].ravel()[cells])
    irr = np.nan_to_num(full["irr"][ri, ci].ravel()[cells])
    T = g["tavg"].reshape(12, -1)[:, cells].astype(float); P_ = g["prec"].reshape(12, -1)[:, cells].astype(float)
    D = (g["tmax"] - g["tmin"]).reshape(12, -1)[:, cells].astype(float)
    PET = hargreaves(T, D, sunlight_top(lat.ravel()[cells], LPE.TILT, LPE.WS_DAY))
    soil = bucket(P_, PET)
    bits = np.zeros(len(cells), np.uint16)
    for c in sorted(set(crop)):
        sel = crop == c
        cat = crop_windows(T[:, sel], P_[:, sel], PET[:, sel], soil[:, sel], irr[sel], crops={c: CROPS[c]})
        _, b = tied_harvest_boundaries(cat)
        bits[sel] = b
    annual = kcal * 100 * g["cell_km"] ** 2 * arable * FARMED_SHARE * FALLOW
    usable = (annual > 0) & (bits > 0)
    log(f"   food cells {usable.sum():,} of {len(cells):,} cropped ({(annual[~usable] > 0).sum()} with production but no calendar dropped)")
    cells, crop, annual, bits, T, P_, PET = cells[usable], crop[usable], annual[usable], bits[usable], T[:, usable], P_[:, usable], PET[:, usable]
    kcal = kcal[usable]
    model = np.isin(crop, list(FI.SEASON))
    A0 = np.zeros(len(cells))
    for c in FI.SEASON:
        sel = crop == c
        cc = CROPS[c]
        A0[sel] = kcal[sel] / (1000 * cc["edible"] * cc["kcal"] * (1 - cc["seed"]))
    model &= A0 > 0
    hb = FI.lowest_bit(bits)
    F = {"joint365": np.ones(len(cells)), "fert_bare": np.ones(len(cells)), "fert_legume": np.ones(len(cells))}
    m = np.flatnonzero(model)
    for s0 in range(0, len(m), 30000):
        sl = m[s0:s0 + 30000]
        t = time.time()
        fb, ref = FI.factor(T[:, sl], P_[:, sl], PET[:, sl], hb[sl], A0[sl], crop[sl], "bare")
        fl, _ = FI.factor(T[:, sl], P_[:, sl], PET[:, sl], hb[sl], A0[sl], crop[sl], "legume", ref=ref)
        F["fert_bare"][sl] = fb; F["fert_legume"][sl] = fl
        log(f"   factors {s0 + len(sl):,}/{len(m):,} ({time.time() - t:.0f}s)")
    return dict(cells=cells, crop=crop, annual=annual, bits=bits, **{"F_" + k: v for k, v in F.items()})


def run(name):
    import polity_earth_check as P
    from scipy import ndimage as ndi
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    from harvest.field_support import fixed_rural_food
    from polity import control as C, earth as E, network as N, seasons as S, transport as X
    from polity.administrative_hierarchy import month_graph
    from polity.settlement_support import allocate_settlement, paired_reach
    from polity.sustained_presence import fixed_path_days, stored_collection
    OUT.mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT / "data/settlement_integration_model.json").read_text())
    t0 = time.time()
    P.apply_sea()
    g = P.load_window(name)
    land0 = g["land"].astype(bool); shape = land0.shape; W = shape[1]
    road = (E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land0) if name == "rome" else np.zeros(shape, bool)
    world = P.world_of(g, road); land = world["land"]
    nodes, node_weight, raw_count = sources(name, g)
    on_land = land.ravel()[nodes]                 # cells carved as ferried straits are not land
    nodes, node_weight = nodes[on_land], node_weight[on_land]
    n = len(nodes)
    log(f"{name}: {n} source cells ({raw_count} points), {int(road.sum())} road cells, land {int(land.sum()):,}")
    st = N.statics(world); cl = N.climate(world, st)
    cell_km = world["cell_km"]
    # ---- collection partition and monthly access (atlas code, Earth fields)
    def collection_graph(m):
        cross = np.where(st["basin"] > 0, S.CROSS_DAYS * (1 + S.FLOOD_GAIN * S.flood_index(cl["flow"][m][st["basin"]])), 0.)
        a, b, d = C.foot_edges(world["elev"], land, road, S.month_terrain(st["eta"], cl, m), cell_km, np.full(shape, C.OFF_PATH),
                               road_factor=1 + (S.MUD_ROAD - 1) * cl["mud"][m], cross=cross)
        return csr_matrix((d, (a, b)), shape=(land.size, land.size))
    base = collection_graph(spec["collection_base_bin"])
    days, parent, source = dijkstra(base.T.tocsr(), indices=nodes, min_only=True, return_predecessors=True, directed=True)
    parent[nodes] = nodes
    lookup = np.zeros(land.size, np.uint16); lookup[nodes] = np.arange(1, n + 1)
    valid = land.ravel() & np.isfinite(days) & (days <= spec["collection_maximum_days_each_way"])
    assignment = np.zeros(land.size, np.uint16); assignment[valid] = lookup[source[valid]]
    order = np.flatnonzero(valid & (parent != np.arange(land.size))); order = order[np.argsort(days[order])]
    access = np.zeros((12, land.size), bool)
    for m in range(12):
        gm = base if m == spec["collection_base_bin"] else collection_graph(m)
        outward, inward = fixed_path_days(gm, parent, order)
        access[m] = valid & (outward <= spec["collection_maximum_days_each_way"]) & (inward <= spec["collection_maximum_days_each_way"])
    del base, gm
    people = (g["density"] * cell_km ** 2 * land).ravel()
    served = np.bincount(assignment[valid], weights=people[valid], minlength=n + 1)[1:]
    request = np.maximum(spec["minimum_civilian_request_people"], spec["civilian_request_share_of_served_people"] * served)
    affiliated = np.ones(n, bool)
    log(f"   collection partition: {valid.sum():,} cells within {spec['collection_maximum_days_each_way']} day; served people {served.sum() / 1e6:.2f} M ({time.time() - t0:.0f}s)")
    # ---- food fields and the food-constrained cases
    cache = OUT / f"{name}_food.npz"
    if cache.exists():
        ff = dict(np.load(cache))
    else:
        ff = food_fields(g, land); np.savez_compressed(cache, **ff)
    idx = ff["cells"]
    keep = assignment[idx] > 0
    log(f"   food cells in a collection area: {keep.sum():,} of {len(idx):,}")
    reference_kcal = ff["annual"]
    fixed_need = reference_kcal * spec["rural_demand_fraction_of_cereal_production"]
    active = {"reference": affiliated.copy()}
    case_out = {}
    for case in FOOD_CASES:
        F = ff["F_" + case]
        produced = reference_kcal * F
        rr = fixed_rural_food(produced, ff["bits"], fixed_need, reserve_days=spec["rural_store_demand_days"],
                              loss_fraction_year=spec["annual_stored_energy_loss_fraction"], year_days=spec["year_days"])
        available = rr.exportable
        freight = np.bincount(assignment[idx], weights=available.sum(0), minlength=n + 1)[1:]
        flow = stored_collection(available, assignment[idx], access[:, idx], n, collection_fraction=.1, freight_capacity=freight,
                                 retention=spec["delivery_retention"], delay_bins=spec["delivery_delay_bins"], store_days=365.,
                                 loss_fraction_year=spec["annual_stored_energy_loss_fraction"], year_days=spec["year_days"])
        p = allocate_settlement(flow["arrivals"], request, affiliated, institutional_request=spec["institutional_request_people"],
                                minimum_community=spec["minimum_community_people"], kcal_day=spec["ration_kcal_person_day"],
                                store_days=spec["destination_store_demand_days"], loss_fraction_year=spec["annual_stored_energy_loss_fraction"],
                                year_days=spec["year_days"])
        active[case] = p.institutional_active
        case_out[case] = dict(staffed=int(p.institutional_active.sum()), viable=int(p.community_viable.sum()),
                              civilian_people=float(p.civilian_people.sum()), institutional_people=float(p.institutional_people.sum()),
                              production_ratio=float(produced.sum() / reference_kcal.sum()), factor_median=float(np.median(F)),
                              rural_unmet_kcal=float(rr.year.unmet.sum()), rural_need_kcal=float(fixed_need.sum()),
                              ceiling_people=p.food_ceiling_people.tolist())
        log(f"   {case}: production x{case_out[case]['production_ratio']:.3f}, staffed {case_out[case]['staffed']} of {n} ({time.time() - t0:.0f}s)")
    # ---- paired seasonal reach from staffed sources (atlas rule), all cases at once
    ports = X.ports_of([(int(v) // W, int(v) % W) for v in nodes], st["water"])
    near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
    river_places = [(int(v) // W, int(v) % W) for v in nodes if near_river.ravel()[v]]
    landnodes = np.flatnonzero(land.ravel())
    bins = {c: np.zeros(land.size, np.uint8) for c in CASES}
    leg, ration = spec["patrol_days_each_leg"], spec["patrol_ration_days"]
    for m in range(12):
        gm, _ = month_graph(world, st, cl, m, ports, river_places)
        rev = gm.T.tocsr()
        covered = {c: np.zeros(land.size, bool) for c in CASES}
        for s0 in range(0, n, 40):
            ch = np.arange(s0, min(s0 + 40, n))
            o = dijkstra(gm, directed=True, indices=nodes[ch], limit=leg)[:, :land.size]
            i = dijkstra(rev, directed=True, indices=nodes[ch], limit=leg)[:, :land.size]
            ok = paired_reach(o, i, leg_days=leg, ration_days=ration)
            for c in CASES:
                use = active[c][ch]
                if use.any():
                    covered[c] |= ok[use].any(0)
        for c in CASES:
            bins[c] += (covered[c] & land.ravel()).astype(np.uint8)
        log(f"   reach month {m + 1} ({time.time() - t0:.0f}s)")
    # ---- legacy: year-round effective days from towns (+ roads) on the monthly networks
    places = [(int(v) // W, int(v) % W) for v in nodes]
    st2, cl2, nets = P.monthly_nets(g, world, places)
    srcs = np.unique(np.r_[nodes, np.flatnonzero(road.ravel())])
    year = P.year_days(nets, srcs).reshape(shape)
    del nets
    if name == "rome":
        eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
        v1 = C.travel_graph(world["elev"], land, road, eta, cell_km, st["paths"])
        d1 = dijkstra(v1, directed=True, indices=srcs, min_only=True).reshape(shape)
        band = land & (d1 <= 15)
        inside = E.inside_polygons(g, E.cliopatria("Roman Empire", 150)) & land
    else:
        band = land & (year <= 15)
        ids, _ = E.han_commanderies(g)
        inside = (ids >= 0) & land
    np.savez_compressed(OUT / f"{name}_result.npz", land=land, band=band, inside=inside, year_days=year,
                        lon=g["lon"], lat=g["lat"], nodes=nodes, node_weight=node_weight,
                        **{"bins_" + c: bins[c].reshape(shape) for c in CASES}, **{"active_" + c: active[c] for c in CASES})
    (OUT / f"{name}_cases.json").write_text(json.dumps(dict(region=name, sources=n, source_points=raw_count, road_cells=int(road.sum()),
                                                            served_people=float(served.sum()), cases=case_out), indent=1))
    log(f"{name} done ({time.time() - t0:.0f}s)")


def score():
    import polity_earth_check as P
    plan = json.loads(PLAN.read_text())
    census = {"fert_bare": 0.459, "joint365": 0.538, "fert_legume": 0.685}
    res = dict(plan=str(PLAN.relative_to(ROOT)), regions={})
    for name in ("rome", "han"):
        z = dict(np.load(OUT / f"{name}_result.npz"))
        meta = json.loads((OUT / f"{name}_cases.json").read_text())
        land, band, inside = z["land"], z["band"], z["inside"]
        bands = {"all": band}
        if name == "rome":
            bands.update(west=band & (z["lon"] < 20.0), east=band & (z["lon"] >= 20.0))

        def m1(held, b):
            tpr = float((held & inside & b).sum() / max((inside & b).sum(), 1)); tnr = float((~held & ~inside & b).sum() / max((~inside & b).sum(), 1))
            return dict(ba=0.5 * (tpr + tnr), tpr=tpr, tnr=tnr)
        out = {}
        legacy = land & (z["year_days"] <= 2.0)
        out["legacy_0"] = {k: m1(legacy, b) for k, b in bands.items()}
        out["legacy_0"]["held_km2"] = float((legacy & band).sum() * 81)
        if name == "han":
            out["legacy_han_5d_reproduction"] = m1(land & (z["year_days"] <= 5.0), band)
        for c in CASES:
            held = z["bins_" + c] >= 12
            r = {k: m1(held, b) for k, b in bands.items()}
            r["held_km2"] = float((held & band).sum() * 81)
            r["auc_bins"] = P.auc(12.0 - z["bins_" + c].astype(float), inside, band)
            act = z["active_" + c]
            r["staffed"] = int(act.sum()); r["staffed_share"] = float(act.mean())
            w = z["node_weight"]
            r["staffed_share_weighted"] = float(w[act].sum() / max(w.sum(), 1e-9))
            out[c] = r
        res["regions"][name] = dict(sources=meta["sources"], cases=out, chain=meta["cases"])
    # decision rule (plan.json)
    gates = {}
    for c in FOOD_CASES:
        g1 = all(res["regions"][r]["cases"][c]["staffed_share"] >= 0.75 for r in ("rome", "han"))
        g2 = all(res["regions"][r]["cases"][c]["all"]["ba"] >= res["regions"][r]["cases"]["legacy_0"]["all"]["ba"] - 0.02 for r in ("rome", "han"))
        gates[c] = dict(G1=g1, G2=g2, census_error=census[c])
    passing = [c for c in FOOD_CASES if gates[c]["G1"] and gates[c]["G2"]]
    default = min(passing, key=lambda c: census[c]) if passing else "legacy_0"
    res["decision"] = dict(gates=gates, passing=passing, default=default, rule=plan["decision_rule"]["choice"])
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
    for name, r in res["regions"].items():
        log(f"== {name} ({r['sources']} sources)")
        for c, v in r["cases"].items():
            if c == "legacy_han_5d_reproduction":
                log(f"   {c:26s} BA {v['ba']:.3f}"); continue
            extra = f" staffed {v['staffed']:5d} ({v['staffed_share']:.0%}, weighted {v['staffed_share_weighted']:.0%})" if "staffed" in v else ""
            parts = " ".join(f"{k} {v[k]['ba']:.3f}" for k in v if isinstance(v[k], dict))
            log(f"   {c:12s} BA {parts}  TPR {v['all']['tpr']:.3f} TNR {v['all']['tnr']:.3f} held {v['held_km2'] / 1e6:.2f} M km2{extra}")
    log("decision:", json.dumps(res["decision"]))


def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = json.loads((OUT / "results.json").read_text())
    cols = ["legacy_0", "reference", "joint365", "fert_bare", "fert_legume"]
    fig, axes = plt.subplots(2, 5, figsize=(22, 8.6))
    for i, name in enumerate(("rome", "han")):
        z = dict(np.load(OUT / f"{name}_result.npz"))
        land, inside, band = z["land"], z["inside"], z["band"]
        for j, c in enumerate(cols):
            held = (land & (z["year_days"] <= 2.0)) if c == "legacy_0" else (z["bins_" + c] >= 12)
            img = np.ones(land.shape + (3,)) * np.array([0.84, 0.89, 0.94])
            img[land] = [0.93, 0.92, 0.88]
            img[land & inside & ~held] = [0.96, 0.78, 0.62]     # claimed, not held: missed
            img[land & ~inside & held] = [0.55, 0.62, 0.85]     # held outside the polygon
            img[land & inside & held] = [0.45, 0.62, 0.38]      # held inside
            img[land & ~band] = img[land & ~band] * 0.94
            ax = axes[i, j]; ax.imshow(img[::-1], interpolation="nearest"); ax.set_xticks([]); ax.set_yticks([])
            v = res["regions"][name]["cases"][c]
            staffed = f", staffed {v['staffed_share']:.0%}" if "staffed" in v else ""
            ax.set_title(f"{name.title()} · {c}\nBA {v['all']['ba']:.3f}{staffed}", fontsize=10)
    fig.suptitle("Earth control test: held land (green inside, blue outside the polygon; orange = claimed but not held). "
                 "Rome: Cliopatria AD 150 + Hanson towns; Han: AD 2 commanderies + county seats", fontsize=11)
    fig.tight_layout(); fig.savefig(OUT / "earth_control.png", dpi=90)
    log("figure", OUT / "earth_control.png")


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2]), "score": score, "figure": figure}[sys.argv[1]]()
