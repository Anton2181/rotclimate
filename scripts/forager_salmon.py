"""FORGE with salmon rivers (calibration/forager_binford_20261031/addendum_salmon_20261101.json).

    python -I scripts/forager_salmon.py --out output/forager_binford_20261031

S_salmon: Natural Earth 1:10m river length within 25 km of a group, counting
only river systems that reach the world ocean in the Northern Hemisphere where
the WOA18 annual sea surface is below 15 C. Configuration D of the aquatic
addendum plus a_salmon x S_salmon; a_salmon fitted on the Arctic, Subarctic
and western North American groups, tested on the Northwest Coast and
California (held out) and the rest of the world.
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
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from binford_aquatic_inputs import EARTH_KM, NE, chord, unit  # noqa: E402
from forager_earth_test import FIT_AREAS, binford, metrics, site_climate, worldclim_months  # noqa: E402
from foraging.forcing import daily_resources, miami_npp, specification  # noqa: E402
from foraging.models import ForagingParams, simulate_foraging  # noqa: E402

PLAN = ROOT / "calibration/forager_binford_20261031/addendum_salmon_20261101.json"
GRID = [0, 100, 300, 1000, 3000, 10000]


def river_systems():
    """Polylines, their union-find system id, and every polyline's points."""
    import shapefile
    lines = []
    for shape in shapefile.Reader(str(NE / "ne_10m_rivers_lake_centerlines.shp")).shapes():
        xy = np.asarray(shape.points, float)
        parts = list(shape.parts) + [len(xy)]
        for a, b in zip(parts[:-1], parts[1:]):
            if b - a >= 2:
                lines.append(xy[a:b][:, ::-1])          # (lat, lon)
    owner = np.concatenate([np.full(len(l), i) for i, l in enumerate(lines)])
    pts = np.concatenate(lines)
    tree = cKDTree(unit(pts[:, 0], pts[:, 1]))
    parent = list(range(len(lines)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, l in enumerate(lines):
        for end in (l[0], l[-1]):
            for j in tree.query_ball_point(unit(end[0], end[1]), chord(3.0)):
                a, b = find(i), find(int(owner[j]))
                if a != b:
                    parent[a] = b
    system = np.array([find(i) for i in range(len(lines))])
    return lines, system, pts, owner


def cold_systems(lines, system, pts, owner):
    """System ids that reach the world ocean (Northern Hemisphere) where WOA18's annual sea surface is below 15 C."""
    from rotclimate.earth import _wc, observed_sst
    from binford_aquatic_inputs import load_lakes
    water = ~np.isfinite(_wc("tavg", 1))
    lab, n = ndi.label(water, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel()); sizes[0] = 0
    # Deviation, recorded (the addendum said "the connected world ocean"): at 5' the
    # Salish Sea and other straits break off WorldClim's ocean, so the ocean is every
    # water body of >= 50 cells that is not a Natural Earth lake (half its cells inside
    # NE lake polygons)
    lakes = load_lakes()
    ny, nx = water.shape; res = 180.0 / ny
    ocean = np.zeros_like(water)
    rng = np.random.default_rng(0)
    for k in np.flatnonzero(sizes >= 50):
        ii, jj = np.nonzero(lab == k) if sizes[k] < 2_000_000 else (None, None)
        if ii is None:
            ocean |= lab == k; continue
        pick = rng.choice(len(ii), size=min(60, len(ii)), replace=False)
        lon_ = -180.0 + (jj[pick] + 0.5) * res; lat_ = 90.0 - (ii[pick] + 0.5) * res
        pts_ = np.stack([lon_, lat_], -1); hit = np.zeros(len(pick), bool)
        for box, paths in lakes:
            if box[0] > lon_.max() or box[2] < lon_.min() or box[1] > lat_.max() or box[3] < lat_.min():
                continue
            for path in paths:
                hit |= path.contains_points(pts_)
        if hit.mean() < 0.5:
            ocean[ii, jj] = True
    coast = ocean & ndi.binary_dilation(~water, structure=np.ones((3, 3)))
    ci, cj = np.nonzero(coast)
    clat, clon = 90.0 - (ci + 0.5) * res, -180.0 + (cj + 0.5) * res
    ctree = cKDTree(unit(clat, clon))
    # Deviation, recorded: Natural Earth's river lines stop 10-40 km short of WorldClim's
    # coast at deltas (the Yukon), so a mouth is a point within 40 km (addendum: 10 km)
    d, _ = ctree.query(unit(pts[:, 0], pts[:, 1]), distance_upper_bound=chord(40.0))
    at_sea = np.isfinite(d)
    cold = set()
    mouth_sst = {}
    for s in np.unique(system):
        members = np.flatnonzero(system == s)
        m = np.isin(owner, members) & at_sea & (pts[:, 0] > 0)
        if not m.any():
            continue
        sst = observed_sst(pts[m, 0], pts[m, 1])
        t = float(np.nanmean(sst)) if sst is not None else np.nan
        mouth_sst[int(s)] = t
        if np.isfinite(t) and t < 15.0:
            cold.add(int(s))
    return cold, mouth_sst


def salmon_index(sites, lines, system, cold, step_km=1.0, radius_km=25.0):
    rp, rw = [], []
    for i, l in enumerate(lines):
        if int(system[i]) not in cold:
            continue
        for (y0, x0), (y1, x1) in zip(l[:-1], l[1:]):
            length = EARTH_KM * math.acos(max(-1.0, min(1.0, float(unit(y0, x0) @ unit(y1, x1)))))
            k = max(1, int(math.ceil(length / step_km)))
            t = (np.arange(k) + 0.5) / k
            rp.append(np.stack([y0 + (y1 - y0) * t, x0 + (x1 - x0) * t], -1)); rw.append(np.full(k, length / k))
    rp, rw = np.concatenate(rp), np.concatenate(rw)
    tree = cKDTree(unit(rp[:, 0], rp[:, 1]))
    disc = math.pi * radius_km ** 2
    out = np.zeros(len(sites["lat"]))
    for k, (la, lo) in enumerate(zip(sites["lat"], sites["lon"])):
        near = tree.query_ball_point(unit(la, lo), chord(radius_km))
        out[k] = 100.0 * float(rw[near].sum()) / disc if near else 0.0
    return out


def run_D(sites, spec, a_salmon):
    run = dict(spec["run"]); run.update(years=600, averaging_years=300)
    forcing = daily_resources(sites["T"], sites["P"], sites["npp"], spec["adapter"])
    plant, meat = forcing["plant_supply"] * 0.5, forcing["meat_supply"] * 0.5
    marine = np.exp(-sites["d_coast_km"] / 25.0) * np.clip((28.0 - sites["sst_annual_c"]) / 20.0, 0.2, 1.0)
    annual = 3000.0 * marine + 100.0 * sites["w_fresh"] + a_salmon * sites["s_salmon"]
    fish = np.broadcast_to(annual / plant.shape[0], plant.shape).copy()
    return simulate_foraging(plant, meat, params=ForagingParams(**spec["kernel_parameters"]), display="mean",
                             aquatic_supply=fish, **run)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/forager_binford_20261031")
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
                         fishing=float(r["fishing"]), gathering=float(r["gatherin"]), hunting=float(r["hunting"]),
                         store=float("nan")))
        T.append(c[0]); P.append(c[1])
    sites = {k: np.array([row[k] for row in rows]) for k in rows[0]}
    sites["T"] = np.array(T).T; sites["P"] = np.array(P).T; sites["npp"] = miami_npp(sites["T"], sites["P"])
    inputs = {(s["name"], round(s["lat"], 4), round(s["lon"], 4)): s
              for s in json.loads((a.out / "aquatic_inputs.json").read_text())["sites"]}
    for key in ("d_coast_km", "sst_annual_c", "w_fresh"):
        sites[key] = np.array([float(inputs[(r["name"], round(r["lat"], 4), round(r["lon"], 4))][key]) for r in rows])
    lines, system, pts, owner = river_systems()
    cold, mouth_sst = cold_systems(lines, system, pts, owner)
    sites["s_salmon"] = salmon_index(sites, lines, system, cold)
    area = sites["area"]
    fit = np.isin(area, ["ARC", "NNA", "WNA"])
    calif = (area == "SW") & (sites["lon"] < -119.5) & (sites["lat"] > 32) & (sites["lat"] < 42.5)
    test_coast = (area == "BC NWC") | calif
    world = ~np.isin(area, list(FIT_AREAS))
    print("systems", len(set(system.tolist())), "cold-sea systems", len(cold), "| S_salmon > 0 at", int((sites["s_salmon"] > 0).sum()),
          "groups; fit", int(fit.sum()), "coast test", int(test_coast.sum()), "world test", int(world.sum()), flush=True)
    for nm, m in (("fit", fit), ("coast", test_coast), ("world", world)):
        print(f"  {nm}: S_salmon median {np.median(sites['s_salmon'][m]):.2f}, share > 0 {np.mean(sites['s_salmon'][m] > 0):.2f}", flush=True)
    spec = specification()
    res = {}
    for g in GRID:
        r_ = run_D(sites, spec, g)
        res[g] = {nm: metrics(r_["density_people_km2"], sites, m, r_) for nm, m in (("fit", fit), ("coast", test_coast), ("world", world))}
        print(g, {k: round(v["median_abs_log10_error"], 4) for k, v in res[g].items()},
              {k: round(v["median_log10_bias"], 3) for k, v in res[g].items()}, flush=True)
    best = min(GRID, key=lambda g: (round(res[g]["fit"]["median_abs_log10_error"], 6), g))
    c0, cb = res[0], res[best]
    ok = (best > 0 and cb["coast"]["median_abs_log10_error"] <= c0["coast"]["median_abs_log10_error"] - 0.05
          and cb["world"]["median_abs_log10_error"] <= c0["world"]["median_abs_log10_error"] + 0.01
          and cb["world"]["density_spearman"] >= c0["world"]["density_spearman"] - 0.01)
    report = dict(addendum=str(PLAN.relative_to(ROOT)), cold_systems=len(cold), groups_with_salmon=int((sites["s_salmon"] > 0).sum()),
                  a_salmon_fitted=best, results={str(g): v for g, v in res.items()}, adopted=bool(ok),
                  rule=json.loads(PLAN.read_text())["adopt_if"],
                  s_salmon={r["name"]: float(s) for r, s in zip(rows, sites["s_salmon"]) if s > 0})
    (a.out / "binford_salmon.json").write_text(json.dumps(report, indent=1, default=float))
    print(json.dumps(dict(a_salmon=best, adopted=ok, coast=[c0["coast"]["median_abs_log10_error"], cb["coast"]["median_abs_log10_error"]],
                          world=[c0["world"]["median_abs_log10_error"], cb["world"]["median_abs_log10_error"]]), indent=1))


if __name__ == "__main__":
    main()
