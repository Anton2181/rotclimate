"""FORGE with HydroRIVERS salmon streams and a cold-climate land-food limit, fitted jointly
(calibration/forager_binford_20261031/addendum_salmon2_20261101.json).

    python -I scripts/forager_salmon2.py --out output/forager_binford_20261031
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from binford_aquatic_inputs import chord, unit  # noqa: E402
from forager_earth_test import FIT_AREAS, binford, metrics, site_climate, worldclim_months  # noqa: E402
from foraging.forcing import daily_resources, miami_npp, specification  # noqa: E402
from foraging.models import ForagingParams, simulate_foraging  # noqa: E402

PLAN = ROOT / "calibration/forager_binford_20261031/addendum_salmon2_20261101.json"
HR = ROOT / "data/cache/hydrorivers/x"
GAMMAS = [0, 0.5, 1, 1.5]
SALMON = [0, 30, 100, 300, 1000]


SST_MIN = -99.0      # addendum salmon6 sets 2.0 (ice-covered seas excluded)


def salmon_points(step_km=1.0):
    """Points along HydroRIVERS salmon streams (each standing for its length) for the frozen definition."""
    import shapefile
    from rotclimate.earth import observed_sst
    keep_pts, keep_w, keep_d = [], [], []
    stats = {}
    for tile in ("na", "as", "ar"):
        rdr = shapefile.Reader(str(HR / f"HydroRIVERS_v10_{tile}_shp" / f"HydroRIVERS_v10_{tile}.shp"))
        names = [f[0] for f in rdr.fields[1:]]
        ix = {k: names.index(k) for k in ("HYRIV_ID", "NEXT_DOWN", "MAIN_RIV", "DIST_DN_KM", "ENDORHEIC", "DIS_AV_CMS")}
        recs = rdr.records()
        # outlets: the segment of each system with NEXT_DOWN 0; its last point is the mouth
        outlet_pt = {}
        cand = [i for i, r in enumerate(recs) if r[ix["NEXT_DOWN"]] == 0 and r[ix["ENDORHEIC"]] == 0]
        for i in cand:
            s = rdr.shape(i)
            outlet_pt[recs[i][ix["MAIN_RIV"]]] = s.points[-1]
        ids = list(outlet_pt)
        if ids:
            pts = np.array([outlet_pt[k] for k in ids])            # lon, lat
            north = pts[:, 1] > 0
            sst = np.full(len(ids), np.nan)
            if north.any():
                v = observed_sst(pts[north, 1], pts[north, 0])
                sst[north] = np.nanmean(v, axis=0) if v is not None else np.nan
            cold = {k for k, t, n in zip(ids, sst, north) if n and np.isfinite(t) and SST_MIN <= t < 15.0}
        else:
            cold = set()
        n_seg = 0
        for i, r in enumerate(recs):
            if (r[ix["ENDORHEIC"]] != 0 or r[ix["DIS_AV_CMS"]] < 1.0 or r[ix["DIST_DN_KM"]] > 1500.0
                    or r[ix["MAIN_RIV"]] not in cold):
                continue
            xy = np.asarray(rdr.shape(i).points, float)
            for (x0, y0), (x1, y1) in zip(xy[:-1], xy[1:]):
                length = 6371.0 * math.acos(max(-1.0, min(1.0, float(unit(y0, x0) @ unit(y1, x1)))))
                k = max(1, int(math.ceil(length / step_km)))
                t = (np.arange(k) + 0.5) / k
                keep_pts.append(np.stack([y0 + (y1 - y0) * t, x0 + (x1 - x0) * t], -1)); keep_w.append(np.full(k, length / k))
                keep_d.append(np.full(k, float(r[ix["DIST_DN_KM"]])))
            n_seg += 1
        stats[tile] = dict(outlets=len(ids), cold_systems=len(cold), salmon_segments=n_seg)
        print(tile, stats[tile], flush=True)
    return np.concatenate(keep_pts), np.concatenate(keep_w), stats, np.concatenate(keep_d)


def run_D(sites, spec, gamma, a_salmon):
    run = dict(spec["run"]); run.update(years=600, averaging_years=300)
    forcing = daily_resources(sites["T"], sites["P"], sites["npp"], spec["adapter"])
    f = np.clip(sites["gs"] / 6.0, 0.1, 1.0) ** gamma
    plant, meat = forcing["plant_supply"] * 0.5 * f, forcing["meat_supply"] * 0.5 * f
    marine = np.exp(-sites["d_coast_km"] / 25.0) * np.clip((28.0 - sites["sst_annual_c"]) / 20.0, 0.2, 1.0)
    marine = marine * sites.get("open_share", 1.0)
    annual = 3000.0 * marine + 100.0 * sites["w_fresh"] + a_salmon * sites["s_salmon"]
    fish = np.broadcast_to(annual / plant.shape[0], plant.shape).copy()
    return simulate_foraging(plant, meat, params=ForagingParams(**spec["kernel_parameters"]), display="mean",
                             aquatic_supply=fish, **run)


def stage2(a, sites, sets, calif, spec, stats):
    plan = ROOT / "calibration/forager_binford_20261031/addendum_salmon3_20261101.json"
    nwc = sites["area"] == "BC NWC"
    groups = dict(calif=calif, interior=sets["fit"], nwc=nwc, world=sets["world"])
    res = {}

    def ev(g, s):
        if (g, s) not in res:
            r_ = run_D(sites, spec, g, s)
            res[(g, s)] = {k: metrics(r_["density_people_km2"], sites, m, r_) for k, m in groups.items()}
            print(g, s, {k: (round(v["median_abs_log10_error"], 3), round(v["median_log10_bias"], 2)) for k, v in res[(g, s)].items()}, flush=True)
        return res[(g, s)]
    s1 = min([0, 30, 100, 300, 1000], key=lambda s: (round(ev(0, s)["calif"]["median_abs_log10_error"], 6), s))
    g2 = min([0, 0.5, 1, 1.5, 2], key=lambda g: (round(ev(g, s1)["interior"]["median_abs_log10_error"], 6), g))
    b, z = ev(g2, s1), ev(0, 0)
    ok = (s1 > 0 and b["nwc"]["median_abs_log10_error"] <= z["nwc"]["median_abs_log10_error"] - 0.05
          and b["world"]["median_abs_log10_error"] <= z["world"]["median_abs_log10_error"] + 0.01
          and b["world"]["density_spearman"] >= z["world"]["density_spearman"] - 0.01
          and b["interior"]["median_abs_log10_error"] <= z["interior"]["median_abs_log10_error"])
    out = dict(addendum=str(plan.relative_to(ROOT)), hydrorivers=stats, fitted=dict(a_salmon=s1, gamma=g2),
               results={f"{g}_{s}": v for (g, s), v in res.items()}, adopted=bool(ok), rule=json.loads(plan.read_text())["adopt_if"],
               n=dict(calif=int(calif.sum()), interior=int(sets["fit"].sum()), nwc=int(nwc.sum()), world=int(sets["world"].sum())))
    (a.out / "binford_salmon3.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(dict(fitted=out["fitted"], adopted=ok, nwc=[z["nwc"]["median_abs_log10_error"], b["nwc"]["median_abs_log10_error"]],
                          interior=[z["interior"]["median_abs_log10_error"], b["interior"]["median_abs_log10_error"]],
                          world=[z["world"]["median_abs_log10_error"], b["world"]["median_abs_log10_error"]]), indent=1))


def stage4(a, sites, sets, calif, spec, stats):
    plan = ROOT / "calibration/forager_binford_20261031/addendum_salmon4_20261101.json"
    nwc = sites["area"] == "BC NWC"
    groups = dict(calif=calif, interior=sets["fit"], nwc=nwc, world=sets["world"])
    disc = math.pi * 25.0 ** 2
    base = None; table = {}
    for L in [100, 200, 400, 800, 1600]:
        wL = sites["_rw"] * np.exp(-sites["_rd"] / L)
        sites["s_salmon"] = np.array([100.0 * float(wL[n_].sum()) / disc for n_ in sites["_near"]])
        rows = {}
        for s in [0, 30, 100, 300, 1000]:
            if s == 0 and base is not None:
                rows[s] = base; continue
            r_ = run_D(sites, spec, 0, s)
            rows[s] = {k: metrics(r_["density_people_km2"], sites, m, r_) for k, m in groups.items()}
            if s == 0:
                base = rows[s]
            print(L, s, {k: (round(v["median_abs_log10_error"], 3), round(v["median_log10_bias"], 2)) for k, v in rows[s].items()}, flush=True)
        s1 = min(rows, key=lambda s: (round(rows[s]["calif"]["median_abs_log10_error"], 6), s))
        table[L] = (s1, rows[s1], rows)
    L2 = min(table, key=lambda L: (round(table[L][1]["interior"]["median_abs_log10_error"], 6), L))
    s1, b, _ = table[L2]
    z = base
    ok = (s1 > 0 and b["nwc"]["median_abs_log10_error"] <= z["nwc"]["median_abs_log10_error"] - 0.05
          and b["world"]["median_abs_log10_error"] <= z["world"]["median_abs_log10_error"] + 0.01
          and b["world"]["density_spearman"] >= z["world"]["density_spearman"] - 0.01
          and b["interior"]["median_abs_log10_error"] <= z["interior"]["median_abs_log10_error"])
    out = dict(addendum=str(plan.relative_to(ROOT)), fitted=dict(L_km=L2, a_salmon=s1),
               by_L={str(L): dict(a_salmon=v[0], best=v[1], grid={str(s): r for s, r in v[2].items()}) for L, v in table.items()},
               none=z, adopted=bool(ok), rule=json.loads(plan.read_text())["adopt_if"])
    (a.out / "binford_salmon4.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(dict(fitted=out["fitted"], adopted=ok, nwc=[z["nwc"]["median_abs_log10_error"], b["nwc"]["median_abs_log10_error"]],
                          interior=[z["interior"]["median_abs_log10_error"], b["interior"]["median_abs_log10_error"]],
                          world=[z["world"]["median_abs_log10_error"], b["world"]["median_abs_log10_error"]],
                          world_rank=[z["world"]["density_spearman"], b["world"]["density_spearman"]]), indent=1))


def stage5(a, sites, sets, calif, spec):
    plan = ROOT / "calibration/forager_binford_20261031/addendum_salmon5_20261101.json"
    nwc = sites["area"] == "BC NWC"
    groups = dict(calif=calif, interior=sets["fit"], nwc=nwc, world=sets["world"])
    disc = math.pi * 25.0 ** 2
    cache = {}

    def ev(L, g, s):
        key = (L if s else 0, g, s)
        if key not in cache:
            wL = sites["_rw"] * np.exp(-sites["_rd"] / L)
            sites["s_salmon"] = np.array([100.0 * float(wL[n_].sum()) / disc for n_ in sites["_near"]])
            r_ = run_D(sites, spec, g, s)
            cache[key] = {k: metrics(r_["density_people_km2"], sites, m, r_) for k, m in groups.items()}
            print(key, {k: (round(v["median_abs_log10_error"], 3), round(v["median_log10_bias"], 2)) for k, v in cache[key].items()}, flush=True)
        return cache[key]
    stage1 = {L: min([0, 30, 100, 300, 1000], key=lambda s: (round(ev(L, 0, s)["calif"]["median_abs_log10_error"], 6), s))
              for L in [100, 200, 400, 800]}
    pairs = [(L, g) for L in stage1 for g in [0, 0.5, 1, 1.5, 2]]
    L2, g2 = min(pairs, key=lambda q: (round(ev(q[0], q[1], stage1[q[0]])["interior"]["median_abs_log10_error"], 6), q))
    s1 = stage1[L2]
    b, z = ev(L2, g2, s1), ev(100, 0, 0)
    ok = (s1 > 0 and b["nwc"]["median_abs_log10_error"] <= z["nwc"]["median_abs_log10_error"] - 0.05
          and b["world"]["median_abs_log10_error"] <= z["world"]["median_abs_log10_error"] + 0.01
          and b["world"]["density_spearman"] >= z["world"]["density_spearman"] - 0.01
          and b["interior"]["median_abs_log10_error"] <= z["interior"]["median_abs_log10_error"])
    out = dict(addendum=str(plan.relative_to(ROOT)), stage1=stage1, fitted=dict(L_km=L2, gamma=g2, a_salmon=s1),
               results={f"{k[0]}_{k[1]}_{k[2]}": v for k, v in cache.items()}, adopted=bool(ok), rule=json.loads(plan.read_text())["adopt_if"])
    (a.out / "binford_salmon5.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(dict(fitted=out["fitted"], adopted=ok, nwc=[z["nwc"]["median_abs_log10_error"], b["nwc"]["median_abs_log10_error"]],
                          interior=[z["interior"]["median_abs_log10_error"], b["interior"]["median_abs_log10_error"]],
                          world=[z["world"]["median_abs_log10_error"], b["world"]["median_abs_log10_error"]],
                          world_rank=[z["world"]["density_spearman"], b["world"]["density_spearman"]],
                          calif=[z["calif"]["median_abs_log10_error"], b["calif"]["median_abs_log10_error"]]), indent=1))


def crossval(a, sites, spec, stats, base_override=None, tag="salmon6"):
    plan = ROOT / f"calibration/forager_binford_20261031/addendum_{tag}_20261101.json"
    disc = math.pi * 25.0 ** 2
    area = sites["area"]
    folds = {k: area == k for k in ("ARC", "NNA", "WNA", "BC NWC", "SW")}
    folds["world"] = ~np.isin(area, list(FIT_AREAS))
    obs = sites["density_km2"]
    pred = {}
    base = run_D(sites, spec, 0, 0)["density_people_km2"]
    for L in [100, 200, 400, 800]:
        wL = sites["_rw"] * np.exp(-sites["_rd"] / L)
        sites["s_salmon"] = np.array([100.0 * float(wL[n_].sum()) / disc for n_ in sites["_near"]])
        for s in [30, 100, 300, 1000]:
            pred[(s, L)] = run_D(sites, spec, 0, s)["density_people_km2"]
            print(L, s, {k: round(float(np.median(np.abs(np.log10(np.maximum(pred[(s, L)][m], 1e-9) / obs[m])))), 3) for k, m in folds.items()}, flush=True)
    pred[(0, 0)] = base
    if base_override is not None:          # judge against configuration D as adopted
        base = base_override
    err = lambda d, m: float(np.median(np.abs(np.log10(np.maximum(d[m], 1e-9) / obs[m]))))
    held = np.zeros_like(obs); choice = {}
    for k, m in folds.items():
        others = np.zeros_like(m)
        for k2, m2 in folds.items():
            if k2 != k:
                others |= m2
        best = min(pred, key=lambda q: (round(err(pred[q], others), 6), q))
        choice[k] = dict(a_salmon=best[0], L_km=best[1])
        held[m] = pred[best][m]
    allm = np.zeros_like(obs, dtype=bool)
    for m in folds.values():
        allm |= m
    cv = err(held, allm); cv0 = err(base, allm)
    per = {k: dict(heldout=err(held, m), baseline=err(base, m), choice=choice[k]) for k, m in folds.items()}
    ok = (cv <= cv0 - 0.02 and all(v["heldout"] <= v["baseline"] + 0.05 for v in per.values())
          and per["world"]["heldout"] <= per["world"]["baseline"] + 0.01)
    final = min(pred, key=lambda q: (round(err(pred[q], allm), 6), q))
    out = dict(addendum=str(plan.relative_to(ROOT)), hydrorivers=stats, cv_error=cv, baseline_error=cv0, folds=per,
               final_fit=dict(a_salmon=final[0], L_km=final[1]), adopted=bool(ok), rule=json.loads(plan.read_text())["adopt_if"])
    out["ice_only_error"] = err(pred[(0, 0)], allm)
    out["ice_only_folds"] = {k: err(pred[(0, 0)], m) for k, m in folds.items()}
    (a.out / f"binford_{tag}.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(dict(cv=cv, baseline=cv0, folds={k: (round(v["heldout"], 3), round(v["baseline"], 3), v["choice"]) for k, v in per.items()},
                          final=out["final_fit"], adopted=ok), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/forager_binford_20261031")
    ap.add_argument("--stage2", action="store_true", help="addendum_salmon3: fit salmon on California, the cold limit on the interior")
    ap.add_argument("--stage4", action="store_true", help="addendum_salmon4: salmon thins upstream (decay length on the interior)")
    ap.add_argument("--stage5", action="store_true", help="addendum_salmon5: upstream thinning and the cold limit on the interior")
    ap.add_argument("--cv", action="store_true", help="addendum_salmon6: outlets 2-15 C, leave-one-area-out cross-validation")
    ap.add_argument("--ice", action="store_true", help="addendum_salmon7: marine supply x open-sea share of the year")
    a = ap.parse_args()
    df = binford(); df = df[(df["subpop"] == "n") & (df["density"].astype(float) > 0)].copy()
    tavg, prec = worldclim_months()
    rows, T, P = [], [], []
    for _, r in df.iterrows():
        lat, lon = float(r["latitude"]), float(r["longitude"])
        c = site_climate(tavg, prec, lat, lon)
        if c is None:
            continue
        rows.append(dict(name=str(r["name"]), area=str(r["wc.area"]), lat=lat, lon=lon, density_km2=float(r["density"]) / 100.0,
                         fishing=float(r["fishing"]), gathering=float(r["gatherin"]), hunting=float(r["hunting"]), store=float("nan")))
        T.append(c[0]); P.append(c[1])
    sites = {k: np.array([row[k] for row in rows]) for k in rows[0]}
    sites["T"] = np.array(T).T; sites["P"] = np.array(P).T; sites["npp"] = miami_npp(sites["T"], sites["P"])
    sites["gs"] = (sites["T"] >= 5.0).sum(0).astype(float)
    inputs = {(s["name"], round(s["lat"], 4), round(s["lon"], 4)): s
              for s in json.loads((a.out / "aquatic_inputs.json").read_text())["sites"]}
    for key in ("d_coast_km", "sst_annual_c", "w_fresh"):
        sites[key] = np.array([float(inputs[(r["name"], round(r["lat"], 4), round(r["lon"], 4))][key]) for r in rows])
    global SST_MIN
    if a.cv:
        SST_MIN = 2.0
    rp, rw, stats, rd = salmon_points()
    tree = cKDTree(unit(rp[:, 0], rp[:, 1])); disc = math.pi * 25.0 ** 2
    near = [tree.query_ball_point(unit(la, lo), chord(25.0)) for la, lo in zip(sites["lat"], sites["lon"])]
    sites["s_salmon"] = np.array([100.0 * float(rw[n_].sum()) / disc for n_ in near])
    sites["_near"], sites["_rw"], sites["_rd"] = near, rw, rd
    area = sites["area"]
    calif = (area == "SW") & (sites["lon"] < -119.5) & (sites["lat"] > 32) & (sites["lat"] < 42.5)
    sets = dict(fit=np.isin(area, ["ARC", "NNA", "WNA"]), coast=(area == "BC NWC") | calif, world=~np.isin(area, list(FIT_AREAS)))
    for k, m in sets.items():
        print(f"{k}: n {m.sum()}, S_salmon median {np.median(sites['s_salmon'][m]):.2f}, share > 0 {np.mean(sites['s_salmon'][m] > 0):.2f}", flush=True)
    spec = specification(); res = {}
    if a.stage2:
        return stage2(a, sites, sets, calif, spec, stats)
    if a.stage4:
        return stage4(a, sites, sets, calif, spec, stats)
    if a.stage5:
        return stage5(a, sites, sets, calif, spec)
    if a.cv and a.ice:
        from rotclimate.earth import observed_sst
        v = observed_sst(sites["lat"], sites["lon"])          # [12, n] at each group's nearest sea point
        base_no_ice = run_D(sites, spec, 0, 0)["density_people_km2"]
        sites["open_share"] = (np.asarray(v) > -1.0).sum(0) / 12.0
        print("open share by area", {k: round(float(np.median(sites['open_share'][sites['area'] == k])), 2) for k in ("ARC", "NNA", "WNA", "BC NWC", "SW")}, flush=True)
        return crossval(a, sites, spec, stats, base_override=base_no_ice, tag="salmon7")
    if a.cv:
        return crossval(a, sites, spec, stats)
    for g in GAMMAS:
        for s in SALMON:
            r_ = run_D(sites, spec, g, s)
            res[(g, s)] = {k: metrics(r_["density_people_km2"], sites, m, r_) for k, m in sets.items()}
            print(g, s, {k: (round(v["median_abs_log10_error"], 3), round(v["median_log10_bias"], 2)) for k, v in res[(g, s)].items()}, flush=True)
    best = min(res, key=lambda k: (round(res[k]["fit"]["median_abs_log10_error"], 6), k))
    b, z = res[best], res[(0, 0)]
    ok = (best != (0, 0) and b["coast"]["median_abs_log10_error"] <= z["coast"]["median_abs_log10_error"] - 0.05
          and b["world"]["median_abs_log10_error"] <= z["world"]["median_abs_log10_error"] + 0.01
          and b["world"]["density_spearman"] >= z["world"]["density_spearman"] - 0.01)
    out = dict(addendum=str(PLAN.relative_to(ROOT)), hydrorivers=stats, fitted=dict(gamma=best[0], a_salmon=best[1]),
               results={f"{g}_{s}": v for (g, s), v in res.items()}, adopted=bool(ok), rule=json.loads(PLAN.read_text())["adopt_if"],
               s_salmon_by_area={k: float(np.median(sites["s_salmon"][m])) for k, m in sets.items()})
    (a.out / "binford_salmon2.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(dict(fitted=out["fitted"], adopted=ok, coast=[z["coast"]["median_abs_log10_error"], b["coast"]["median_abs_log10_error"]],
                          world=[z["world"]["median_abs_log10_error"], b["world"]["median_abs_log10_error"]]), indent=1))


if __name__ == "__main__":
    main()
