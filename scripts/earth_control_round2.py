"""Earth control round 2 (calibration/earth_control_20261106/plan_round2.json): scaled rural ledger and
four reach rules on the Rome AD 150 / Han AD 2 development pools.

    .venv/bin/python -I scripts/earth_control_round2.py run rome
    .venv/bin/python -I scripts/earth_control_round2.py run han
    .venv/bin/python -I scripts/earth_control_round2.py score

Shared with the blind test (scripts/earth_control_blind.py): `chain()` (food -> staffed sources)
and `reach()` (the reach rules) take any Earth window and source list.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/earth_control_20261106/round2"
FOOD_CASES = ["joint365", "fert_bare", "fert_legume"]
RULES = ["P0", "P1", "P2", "P3"]
log = lambda *a: print(*a, flush=True)  # noqa: E731


def setup(g, nodes, road):
    """World, statics, climate, collection partition and monthly access for a window and its sources."""
    import polity_earth_check as P
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C, network as N, seasons as S
    from polity.sustained_presence import fixed_path_days
    spec = json.loads((ROOT / "data/settlement_integration_model.json").read_text())
    world = P.world_of(g, road); land = world["land"]; shape = land.shape
    st = N.statics(world); cl = N.climate(world, st); cell_km = world["cell_km"]
    n = len(nodes)

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
    people = (g["density"] * cell_km ** 2 * land).ravel()
    served = np.bincount(assignment[valid], weights=people[valid], minlength=n + 1)[1:]
    request = np.maximum(spec["minimum_civilian_request_people"], spec["civilian_request_share_of_served_people"] * served)
    return dict(world=world, st=st, cl=cl, land=land, shape=shape, assignment=assignment, access=access, request=request, spec=spec, n=n)


def chain(S_, ff, F, scaled):
    """Staffed sources for one food case. scaled=True: rural claim 0.6 x produced (L1); False: 0.6 x reference."""
    from harvest.field_support import fixed_rural_food
    from polity.settlement_support import allocate_settlement
    from polity.sustained_presence import stored_collection
    spec, n, idx = S_["spec"], S_["n"], ff["cells"]
    produced = ff["annual"] * F
    need = (produced if scaled else ff["annual"]) * spec["rural_demand_fraction_of_cereal_production"]
    rr = fixed_rural_food(produced, ff["bits"], need, reserve_days=spec["rural_store_demand_days"],
                          loss_fraction_year=spec["annual_stored_energy_loss_fraction"], year_days=spec["year_days"])
    available = rr.exportable
    asg = S_["assignment"][idx]
    freight = np.bincount(asg, weights=available.sum(0), minlength=n + 1)[1:]
    flow = stored_collection(available, asg, S_["access"][:, idx], n, collection_fraction=.1, freight_capacity=freight,
                             retention=spec["delivery_retention"], delay_bins=spec["delivery_delay_bins"], store_days=365.,
                             loss_fraction_year=spec["annual_stored_energy_loss_fraction"], year_days=spec["year_days"])
    p = allocate_settlement(flow["arrivals"], S_["request"], np.ones(n, bool), institutional_request=spec["institutional_request_people"],
                            minimum_community=spec["minimum_community_people"], kcal_day=spec["ration_kcal_person_day"],
                            store_days=spec["destination_store_demand_days"], loss_fraction_year=spec["annual_stored_energy_loss_fraction"],
                            year_days=spec["year_days"])
    return p.institutional_active, dict(production_ratio=float(produced.sum() / ff["annual"].sum()),
                                        rural_unmet_share=float(rr.year.unmet.sum() / max(need.sum(), 1)))


def reach(g, S_, nodes, road, actives):
    """Held masks per case and rule. actives: {case: bool array over nodes}."""
    import polity_earth_check as P
    from scipy import ndimage as ndi
    from scipy.sparse.csgraph import dijkstra
    from polity import transport as X
    from polity.administrative_hierarchy import month_graph
    from polity.settlement_support import paired_reach
    world, st, cl, land, shape, spec = S_["world"], S_["st"], S_["cl"], S_["land"], S_["shape"], S_["spec"]
    W = shape[1]; n = len(nodes)
    out = {c: {} for c in actives}
    # P0: paired patrols in every month
    ports = X.ports_of([(int(v) // W, int(v) % W) for v in nodes], st["water"])
    near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
    river_places = [(int(v) // W, int(v) % W) for v in nodes if near_river.ravel()[v]]
    bins = {c: np.zeros(land.size, np.uint8) for c in actives}
    leg, ration = spec["patrol_days_each_leg"], spec["patrol_ration_days"]
    for m in range(12):
        gm, _ = month_graph(world, st, cl, m, ports, river_places); rev = gm.T.tocsr()
        cov = {c: np.zeros(land.size, bool) for c in actives}
        for s0 in range(0, n, 40):
            ch = np.arange(s0, min(s0 + 40, n))
            o = dijkstra(gm, directed=True, indices=nodes[ch], limit=leg)[:, :land.size]
            i = dijkstra(rev, directed=True, indices=nodes[ch], limit=leg)[:, :land.size]
            ok = paired_reach(o, i, leg_days=leg, ration_days=ration)
            for c, act in actives.items():
                use = act[ch]
                if use.any():
                    cov[c] |= ok[use].any(0)
        for c in actives:
            bins[c] += (cov[c] & land.ravel()).astype(np.uint8)
    for c in actives:
        out[c]["P0"] = (bins[c] >= 12).reshape(shape) & land
    # P1-P3: year-round effective days on the legacy monthly networks
    places = [(int(v) // W, int(v) % W) for v in nodes]
    _, _, nets = P.monthly_nets(g, world, places)
    roads = np.flatnonzero(road.ravel() & land.ravel())
    for c, act in actives.items():
        staffed = nodes[act]
        if len(staffed) == 0:
            for r in ("P1", "P2", "P3"):
                out[c][r] = np.zeros(shape, bool)
            continue
        d1 = P.year_days(nets, staffed).ravel()
        out[c]["P1"] = (d1 <= 2.0).reshape(shape) & land
        if len(roads):
            near = roads[d1[roads] <= 2.0]
            out[c]["P2"] = (P.year_days(nets, np.unique(np.r_[staffed, near])).ravel() <= 2.0).reshape(shape) & land
            out[c]["P3"] = (P.year_days(nets, np.unique(np.r_[staffed, roads])).ravel() <= 2.0).reshape(shape) & land
        else:
            out[c]["P2"] = out[c]["P1"]; out[c]["P3"] = out[c]["P1"]
    del nets
    return out


def run(name):
    import polity_earth_check as P
    import earth_control_test as T
    from polity import earth as E
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    P.apply_sea()
    g = P.load_window(name)
    land0 = g["land"].astype(bool)
    road = (E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land0) if name == "rome" else np.zeros(land0.shape, bool)
    world0 = P.world_of(g, road)
    nodes, weight, _ = T.sources(name, g)
    on_land = world0["land"].ravel()[nodes]; nodes, weight = nodes[on_land], weight[on_land]
    S_ = setup(g, nodes, road)
    ff = dict(np.load(T.OUT / f"{name}_food.npz"))          # round-1 food fields (same windows, same code)
    actives, chain_info = {"reference": np.ones(len(nodes), bool)}, {}
    for scaled in (False, True):
        for c in FOOD_CASES:
            key = f"{c}_{'scaled' if scaled else 'fixed'}"
            actives[key], chain_info[key] = chain(S_, ff, ff["F_" + c], scaled)
            log(f"{name} {key}: staffed {actives[key].sum()} of {len(nodes)}, rural unmet {chain_info[key]['rural_unmet_share']:.3f} ({time.time() - t0:.0f}s)")
    held = reach(g, S_, nodes, road, actives)
    log(f"{name} reach done ({time.time() - t0:.0f}s)")
    base = dict(np.load(T.OUT / f"{name}_result.npz"))
    np.savez_compressed(OUT / f"{name}.npz", **{f"{c}__{r}": m for c, d in held.items() for r, m in d.items()},
                        **{f"active__{c}": a for c, a in actives.items()}, band=base["band"], inside=base["inside"], land=base["land"],
                        lon=base["lon"], year_days=base["year_days"])
    (OUT / f"{name}_chain.json").write_text(json.dumps(chain_info, indent=1))


def score():
    res = dict(plan="calibration/earth_control_20261106/plan_round2.json", regions={})
    for name in ("rome", "han"):
        z = dict(np.load(OUT / f"{name}.npz"))
        band, inside, land = z["band"], z["inside"], z["land"]

        def m1(h):
            tpr = float((h & inside & band).sum() / max((inside & band).sum(), 1)); tnr = float((~h & ~inside & band).sum() / max((~inside & band).sum(), 1))
            return dict(ba=0.5 * (tpr + tnr), tpr=tpr, tnr=tnr, held_km2=float((h & band).sum() * 81))
        r = {"legacy_0": m1(land & (z["year_days"] <= 2.0))}
        for k in z:
            if "__P" in k:
                c, rule = k.split("__")
                r.setdefault(c, {})[rule] = m1(z[k])
        for k in z:
            if k.startswith("active__"):
                c = k.split("__")[1]; r[c]["staffed_share"] = float(z[k].mean())
        r["chain"] = json.loads((OUT / f"{name}_chain.json").read_text())
        res["regions"][name] = r
    mean = {rule: float(np.mean([res["regions"][g][f"{c}_scaled"][rule]["ba"] for g in ("rome", "han") for c in FOOD_CASES])) for rule in RULES}
    r_star = max(mean, key=mean.get)
    res["selection"] = dict(mean_ba_by_rule=mean, R_star=r_star)
    (OUT / "results_round2.json").write_text(json.dumps(res, indent=1))
    for name, r in res["regions"].items():
        log(f"== {name}: legacy_0 BA {r['legacy_0']['ba']:.3f} (TPR {r['legacy_0']['tpr']:.2f} TNR {r['legacy_0']['tnr']:.2f})")
        for c in ["reference"] + [f"{c}_{l}" for l in ("fixed", "scaled") for c in FOOD_CASES]:
            row = " ".join(f"{rule} {r[c][rule]['ba']:.3f}" for rule in RULES)
            log(f"   {c:20s} staffed {r[c]['staffed_share']:.0%}  {row}")
    log("mean BA by rule (scaled food cases):", {k: round(v, 4) for k, v in mean.items()}, "R* =", r_star)


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2]), "score": score}[sys.argv[1]]()
