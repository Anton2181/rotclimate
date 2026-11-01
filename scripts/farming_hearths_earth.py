"""Language areas from below, layer 2b: where farming starts, tested on Earth.

Frozen plan: calibration/language_areas_20261101/plan_2b.json.

FORGE (configuration D, as in layer 1) on a 1 deg world grid; four indices
(productivity, forager density, plant-fed density, and Testart's storing
plant foragers: plant-fed density x lean-season share) scored on how well
500 km discs around Diamond's nine homelands of domestication outrank
discs around random land cells.

    python -I scripts/farming_hearths_earth.py --out output/language_areas_20261101/layer2b
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import language_areas_earth as lae  # noqa: E402

PLAN = ROOT / "calibration" / "language_areas_20261101" / "plan_2b.json"
STEP = 1.0
R_KM = 6371.0
RADIUS = 500.0


def forge_world(cache: Path):
    if cache.exists():
        z = np.load(cache)
        return {k: z[k] for k in z.files}
    from binford_aquatic_inputs import RADIUS_KM, chord, coast_distance, lake_share, load_lakes, river_points, unit
    from rotclimate.earth import _wc, observed_sst
    from forager_salmon import run_D
    from foraging.forcing import miami_npp, specification
    lae.STEP = STEP
    cells = lae.grid(lambda la, lo: (la > -56) & (la < 72) & np.isfinite(lo))
    print(f"{len(cells)} cells", flush=True)
    water = ~np.isfinite(_wc("tavg", 1))
    rp, rw = river_points(); tree = cKDTree(unit(rp[:, 0], rp[:, 1])); lakes = load_lakes()
    disc = math.pi * RADIUS_KM ** 2
    s = dict(T=np.array([c[4] for c in cells]).T, P=np.array([c[5] for c in cells]).T)
    lat = np.array([c[2] for c in cells]); lon = np.array([c[3] for c in cells])
    s["npp"] = miami_npp(s["T"], s["P"])
    s["d_coast_km"] = np.array([coast_distance(water, a, o) for a, o in zip(lat, lon)])
    sst = observed_sst(lat, lon); s["sst_annual_c"] = np.nanmean(np.asarray(sst), 0)
    fresh = []
    for a, o in zip(lat, lon):
        near = tree.query_ball_point(unit(a, o), chord(RADIUS_KM))
        fresh.append(100.0 * float(rw[near].sum()) / disc + 10.0 * lake_share(a, o, lakes))
    s["w_fresh"] = np.array(fresh); s["s_salmon"] = np.zeros(len(cells))
    res = run_D(s, specification(), 0)
    out = dict(lat=lat, lon=lon, npp=np.asarray(s["npp"], float), density=np.asarray(res["density_people_km2"], float),
               fish=np.asarray(res["mean_fish_share"], float), meat=np.asarray(res["mean_meat_fraction"], float),
               scarcity=np.asarray(res["mean_scarcity_days_year"], float))
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **out)
    return out


def unit_xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def chord_km(d):
    return 2 * math.sin(d / R_KM / 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="output/language_areas_20261101/layer2b")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    plan = json.loads(PLAN.read_text())
    F = forge_world(out / "forge_world.npz")
    print(f"FORGE world ({time.time() - t0:.0f}s)", flush=True)
    lat, lon = F["lat"], F["lon"]
    plant = F["density"] * (1 - F["fish"]) * (1 - F["meat"])
    idx = dict(B1=F["npp"], B2=F["density"], B3=plant, H=plant * F["scarcity"] / 365.0)
    xyz = unit_xyz(lat, lon); tree = cKDTree(xyz)
    homes = plan["targets"]["points (lat, lon), placed here at each homeland's centre of early domestication"]
    hp = np.array([p for pts in homes.values() for p in pts])
    rng = np.random.default_rng(0)
    d_home = tree.query(unit_xyz(hp[:, 0], hp[:, 1]))[0]
    far = np.ones(len(lat), bool)
    for p in hp:
        far &= np.linalg.norm(xyz - unit_xyz([p[0]], [p[1]]), axis=1) > chord_km(1000.0)
    rand = rng.choice(np.flatnonzero(far), 2000, replace=False)
    disc_members = tree.query_ball_point(xyz, chord_km(RADIUS))

    def disc_mean(v, centres_xyz):
        return np.array([v[m].mean() if len(m) else np.nan for m in tree.query_ball_point(centres_xyz, chord_km(RADIUS))])
    res = {}
    for k, v in idx.items():
        rd = np.array([v[disc_members[i]].mean() for i in rand])
        hs = {}
        for name, pts in homes.items():
            pts = np.array(pts)
            hs[name] = float(np.nanmax(disc_mean(v, unit_xyz(pts[:, 0], pts[:, 1]))))
        auc = float(np.mean([np.mean(h > rd) + 0.5 * np.mean(h == rd) for h in hs.values()]))
        res[k] = dict(auc=auc, homeland_percentile={n: float(100 * np.mean(h > rd)) for n, h in hs.items()},
                      random_p95=float(np.percentile(rd, 95)))
        print(f"{k}: AUC {auc:.3f}  " + "  ".join(f"{n.split(' ')[0]} {res[k]['homeland_percentile'][n]:.0f}" for n in homes), flush=True)
    best_base = max(res[k]["auc"] for k in ("B1", "B2", "B3"))
    if res["H"]["auc"] >= 0.80 and res["H"]["auc"] >= best_base + 0.05:
        verdict = "H"
    elif res["B3"]["auc"] >= 0.80 and res["B3"]["auc"] >= max(res["B1"]["auc"], res["B2"]["auc"]) + 0.05:
        verdict = "B3"
    else:
        verdict = "owner"
    # strongest local maxima of each index's disc mean (false hearths are those far from every homeland)
    maxima = {}
    for k, v in idx.items():
        dm = np.array([v[m].mean() for m in disc_members])
        order = np.argsort(-dm); kept = []
        for i in order:
            if dm[i] < res[k]["random_p95"]:
                break
            if all(np.linalg.norm(xyz[i] - xyz[j]) > chord_km(1500.0) for j in kept):
                kept.append(i)
        maxima[k] = [dict(lat=float(lat[i]), lon=float(lon[i]), value=float(dm[i]),
                          homeland=bool(min(np.linalg.norm(unit_xyz(hp[:, 0], hp[:, 1]) - xyz[i], axis=1)) < chord_km(1000.0)))
                     for i in kept]
        np.save(out / f"disc_{k}.npy", dm.astype(np.float32))
    summary = dict(plan=str(PLAN.relative_to(ROOT)), frozen=plan["frozen"], cells=int(len(lat)), verdict=verdict,
                   homeland_point_to_cell_km=[float(2 * R_KM * math.asin(d / 2)) for d in d_home],
                   indices=res, maxima=maxima)
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f"verdict: {verdict}; H maxima: " + ", ".join(f"({m['lat']:.0f},{m['lon']:.0f}){'*' if m['homeland'] else ''}" for m in maxima["H"]))
    print(f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
