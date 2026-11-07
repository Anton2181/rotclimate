"""Earth test of the eroded height map (calibration/geography_control_20261107/plan_B2.json): posterize real terrain
into a hand-map-like sketch (four tiers + the biggest rivers), rebuild it, and compare with the truth.

    .venv/bin/python -I scripts/terrain_earth_b2.py fetch          # ETOPO 2022 60" windows (development + blind)
    .venv/bin/python -I scripts/terrain_earth_b2.py dev            # grid over the evolve() settings, development windows
    .venv/bin/python -I scripts/terrain_earth_b2.py blind          # the single blind evaluation of C* against the ramps
"""
from __future__ import annotations

import itertools
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_B2.json"
CACHE = ROOT / "data/cache/etopo2022_60s"
OUT = ROOT / "output/terrain_earth_b2_20261107"
URL = "https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc.ascii"
DX_KM = 1.85
TIER_SHARES = (0.705, 0.121, 0.107, 0.067)
log = lambda *a: print(*a, flush=True)  # noqa: E731


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    wins = json.loads(PLAN.read_text())["windows"]
    for group in ("development", "blind"):
        for name, (s, n, w, e) in wins[group].items():
            path = CACHE / f"{name}.npz"
            if path.exists():
                continue
            i0, i1 = int(np.floor((s + 90) * 60)), int(np.ceil((n + 90) * 60)) - 1
            j0, j1 = int(np.floor((w + 180) * 60)), int(np.ceil((e + 180) * 60)) - 1
            q = f"?z%5B{i0}:1:{i1}%5D%5B{j0}:1:{j1}%5D"
            txt = urllib.request.urlopen(URL + q, timeout=300).read().decode()
            body = txt.split("z.z[")[1].split("z.lat[")[0].splitlines()[1:]
            z = np.array([[float(v) for v in line.split(",")[1:]] for line in body if line.startswith("[")], np.float32)
            lat = -90 + (np.arange(i0, i1 + 1) + 0.5) / 60; lon = -180 + (np.arange(j0, j1 + 1) + 0.5) / 60
            np.savez_compressed(path, z=z, lat=lat, lon=lon)
            log(f"{name}: {z.shape}, elevation {np.nanmin(z):.0f} to {np.nanmax(z):.0f} m")


def window(name):
    """True elevation on a local equal-area grid of DX_KM, land mask."""
    d = np.load(CACHE / f"{name}.npz"); z, lat, lon = d["z"], d["lat"], d["lon"]
    lat0 = float(lat.mean()); k = np.cos(np.radians(lat0))
    W = (lon[-1] - lon[0]) * 111.32 * k; H = (lat[-1] - lat[0]) * 111.32
    nx, ny = int(W / DX_KM), int(H / DX_KM)
    x = np.arange(nx) * DX_KM; y = np.arange(ny) * DX_KM
    X, Y = np.meshgrid(x, y)
    la = lat[-1] - Y / 111.32; lo = lon[0] + X / (111.32 * k)          # rows from the north
    ri = (la - lat[0]) / (lat[1] - lat[0]); ci = (lo - lon[0]) / (lon[1] - lon[0])
    zz = ndi.map_coordinates(z.astype(float), [ri, ci], order=1, mode="nearest")
    land = zz > 0
    land = ndi.binary_opening(land, np.ones((2, 2))) | (land & ndi.binary_erosion(land))
    return np.where(land, np.maximum(zz, 1.0), 0.0), land


def ramps(tier, tops, land):
    """Today's tier-ramp construction (rotclimate.geography._tier_ramps + elevation_fullres) on any tier map."""
    t = [0.0] + list(tops); h = np.zeros(tier.shape)
    for k in range(1, 5):
        inside = tier == k
        if not inside.any():
            continue
        d_lo = ndi.distance_transform_edt(tier >= k); higher = tier > k
        if higher.any():
            d_hi = ndi.distance_transform_edt(~higher); s = d_lo / (d_lo + d_hi + 1e-9)
            s = np.minimum(s, 1 - np.exp(-d_lo / 60.0)) if k == 1 else s
        else:
            s = 1 - np.exp(-d_lo / 8.0)
        h += np.where(inside, t[k - 1] + (t[k] - t[k - 1]) * s, 0.0)
    h = ndi.gaussian_filter(h, 2.0)
    return np.where(land, np.maximum(h, 1.0), 0.0)


def route(z, land, dx_m):
    import fastscapelib as fs
    status = {(int(i), int(j)): fs.NodeStatus.FIXED_VALUE for i, j in zip(*np.nonzero(~land))}
    grid = fs.RasterGrid(list(z.shape), [dx_m, dx_m], fs.NodeStatus.FIXED_VALUE, status)
    flow = fs.FlowGraph(grid, [fs.SingleFlowRouter(), fs.MSTSinkResolver()])
    flow.update_routes(z.astype(float))
    return flow.accumulate(dx_m * dx_m), flow.basins()


def map_river_ratio():
    from rotclimate.geography import source_layers
    L = source_layers(); return float(L["rivers"].sum() / L["land"].sum())


def sketch(z, land, ratio):
    zs = ndi.gaussian_filter(np.where(land, z, 0.0), 5.0 / DX_KM) / np.maximum(ndi.gaussian_filter(land.astype(float), 5.0 / DX_KM), 1e-6)
    cuts = np.quantile(zs[land], np.cumsum(TIER_SHARES)[:-1])
    tier = np.where(land, 1 + np.searchsorted(cuts, zs, side="right"), 0).astype(int)
    top4 = float(np.percentile(z[land & (tier == 4)], 95)) if (land & (tier == 4)).any() else float(cuts[-1] * 1.5)
    tops = [float(c) for c in cuts] + [max(top4, float(cuts[-1]) + 1)]
    A, _ = route(z, land, DX_KM * 1000)
    n = int(round(ratio * land.sum()))
    rivers = np.zeros(land.shape, bool); idx = np.argsort(A.ravel())[::-1][:n]; rivers.ravel()[idx] = True
    return tier, tops, ramps(tier, tops, land), rivers & land


def divides(basins, A, land):
    basins = np.asarray(basins).astype(np.int64).reshape(land.shape)
    ids, counts = np.unique(basins[land], return_counts=True)
    big = set(ids[counts * DX_KM ** 2 >= 500])
    b = np.where(land & np.isin(basins, list(big)), basins, -1)
    d = np.zeros(b.shape, bool)
    for dy, dx in ((0, 1), (1, 0)):
        a1, a2 = b[:b.shape[0] - dy, :b.shape[1] - dx], b[dy:, dx:]
        diff = (a1 != a2) & (a1 >= 0) & (a2 >= 0)
        d[:b.shape[0] - dy, :b.shape[1] - dx] |= diff; d[dy:, dx:] |= diff
    return d


def tobler_reach(z, land, points, days=2.0):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    h, w = z.shape; idx = np.arange(z.size).reshape(z.shape); rows, cols, cost = [], [], []
    for dy, dx in [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]:
        y0, y1, x0, x1 = max(0, -dy), min(h, h - dy), max(0, -dx), min(w, w - dx)
        s, t = np.s_[y0:y1, x0:x1], np.s_[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        km = DX_KM * np.hypot(dy, dx); slope = (z[t] - z[s]) / (km * 1000)
        v = 6.0 * np.exp(-3.5 * np.abs(slope + 0.05)) * 0.6 * 8.0          # km per day, off path, 8 h march
        ok = land[s] & land[t]
        rows.append(idx[s][ok]); cols.append(idx[t][ok]); cost.append((km / v)[ok])
    g = coo_matrix((np.concatenate(cost), (np.concatenate(rows), np.concatenate(cols))), shape=(z.size, z.size)).tocsr()
    d = dijkstra(g, directed=True, indices=points, limit=days)
    return np.isfinite(d) & (d <= days)


def truth(name, ratio):
    z, land = window(name)
    tier, tops, h0, rivers = sketch(z, land, ratio)
    A, basins = route(z, land, DX_KM * 1000)
    rng = np.random.default_rng(7)
    inner = land & ndi.binary_erosion(land, np.ones((41, 41)), border_value=0)
    cand = np.flatnonzero(inner.ravel()); points = rng.choice(cand, size=min(30, len(cand)), replace=False)
    return dict(z=z, land=land, tier=tier, tops=tops, h0=h0, rivers=rivers, A=A, div=divides(basins, A, land),
                reach=tobler_reach(z, land, points), points=points)


def slope_of(z):
    gy, gx = np.gradient(z, DX_KM * 1000); return np.degrees(np.arctan(np.hypot(gy, gx)))


def score(T, zr):
    from scipy.stats import ks_2samp
    land, tier = T["land"], T["tier"]
    Ar, br = route(zr, land, DX_KM * 1000)
    dv = divides(br, Ar, land)
    dt = ndi.distance_transform_edt(~T["div"]) * DX_KM; dr = ndi.distance_transform_edt(~dv) * DX_KM
    m1 = float(0.5 * (dt[dv].mean() + dr[T["div"]].mean())) if dv.any() and T["div"].any() else 99.0
    st, sr = slope_of(T["z"]), slope_of(zr)
    m2 = float(np.mean([ks_2samp(st[land & (tier == k)], sr[land & (tier == k)]).statistic for k in range(1, 5) if (land & (tier == k)).sum() > 50]))
    far = ~ndi.binary_dilation(T["rivers"], np.ones((5, 5)))
    ct, cr = (T["A"] >= 500e6) & land & far, (Ar >= 500e6) & land & far
    near = lambda a, b: ndi.binary_dilation(b, iterations=int(round(5 / DX_KM)))[a].mean() if a.any() else 0.0
    rec, prec = near(ct, cr), near(cr, ct); m3 = float(0 if rec + prec == 0 else 2 * rec * prec / (rec + prec))
    rr = tobler_reach(zr, land, T["points"])
    iou = [float((a & b).sum() / max((a | b).sum(), 1)) for a, b in zip(T["reach"], rr)]
    edges = [0.0] + T["tops"]
    band = {}
    for k in range(1, 5):
        m = land & (tier == k); lo, hi = edges[k - 1], edges[k]; mg = 0.1 * (hi - lo)
        if m.any():
            band[k] = dict(true=float(((T["z"][m] >= lo - mg) & (T["z"][m] <= hi + mg)).mean()), rec=float(((zr[m] >= lo - mg) & (zr[m] <= hi + mg)).mean()))
    return dict(M1_divides_km=m1, M2_slope_ks=m2, M3_new_river_f1=m3, M4_isochrone_iou=float(np.mean(iou)), M5_tier_band=band)


def settings():
    keys = ("m", "noise_km", "noise_sigma", "river_boost_km2", "smooth_px")
    vals = ((0.35, 0.45, 0.55), (6.0, 12.0, 24.0), (0.2, 0.35, 0.6), (1000.0, 3000.0, 10000.0), (0.0, 0.7))
    return [dict(zip(keys, v)) for v in itertools.product(*vals)]


def run_group(group, chosen=None):
    import terrain_erosion as TE
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time(); ratio = map_river_ratio()
    names = list(json.loads(PLAN.read_text())["windows"][group])
    res = dict(plan=str(PLAN.relative_to(ROOT)), group=group, map_river_ratio=ratio, windows={})
    for name in names:
        T = truth(name, ratio)
        row = dict(tops=T["tops"], land_cells=int(T["land"].sum()), baseline=score(T, T["h0"]), settings=[])
        for s in ([chosen] if chosen else settings()):
            zr, _ = TE.evolve(T["h0"], T["land"], T["rivers"], DX_KM * 1000, dict(s, rounds=6, burn_m=4.0, lowpass_km=14.0))
            row["settings"].append(dict(s, **score(T, zr)))
        res["windows"][name] = row
        log(f"{name}: {len(row['settings'])} settings scored ({time.time() - t0:.0f}s); baseline {row['baseline']['M1_divides_km']:.1f} km, "
            f"KS {row['baseline']['M2_slope_ks']:.3f}, IoU {row['baseline']['M4_isochrone_iou']:.3f}")
    return res


def dev():
    res = run_group("development")
    names = list(res["windows"]); S = settings(); ranks = np.zeros(len(S))
    for name in names:
        rows = res["windows"][name]["settings"]
        for key, sign in (("M1_divides_km", 1), ("M2_slope_ks", 1), ("M4_isochrone_iou", -1)):
            v = np.array([sign * r[key] for r in rows]); ranks += v.argsort().argsort()
    best = int(np.argmin(ranks)); res["C_star"] = S[best]; res["mean_rank"] = float(ranks[best] / (3 * len(names)))
    (OUT / "dev.json").write_text(json.dumps(res, indent=1))
    log("C* =", S[best])
    for name in names:
        b = res["windows"][name]["baseline"]; c = res["windows"][name]["settings"][best]
        log(f"  {name}: divides {b['M1_divides_km']:.1f} -> {c['M1_divides_km']:.1f} km, slope KS {b['M2_slope_ks']:.3f} -> {c['M2_slope_ks']:.3f}, "
            f"IoU {b['M4_isochrone_iou']:.3f} -> {c['M4_isochrone_iou']:.3f}, new rivers F1 {c['M3_new_river_f1']:.2f}, bands {c['M5_tier_band']}")


def blind():
    cs = json.loads((OUT / "dev.json").read_text())["C_star"]
    res = run_group("blind", cs)
    wins = {}
    for name, row in res["windows"].items():
        b, c = row["baseline"], row["settings"][0]
        wins[name] = dict(M1=c["M1_divides_km"] < b["M1_divides_km"], M2=c["M2_slope_ks"] < b["M2_slope_ks"], M4=c["M4_isochrone_iou"] > b["M4_isochrone_iou"])
        log(f"  {name}: divides {b['M1_divides_km']:.1f} -> {c['M1_divides_km']:.1f} km, slope KS {b['M2_slope_ks']:.3f} -> {c['M2_slope_ks']:.3f}, "
            f"IoU {b['M4_isochrone_iou']:.3f} -> {c['M4_isochrone_iou']:.3f}, new rivers F1 {c['M3_new_river_f1']:.2f}")
    gates = {g: sum(w[k] for w in wins.values()) >= 3 for g, k in (("G1", "M1"), ("G2", "M2"), ("G3_reported", "M4"))}
    res.update(C_star=cs, wins=wins, gates=gates, adopt=bool(gates["G1"] and gates["G2"]))   # plan_B2 amendment_1
    (OUT / "blind.json").write_text(json.dumps(res, indent=1)); log("gates:", gates, "adopt:", res["adopt"])


if __name__ == "__main__":
    {"fetch": fetch, "dev": dev, "blind": blind}[sys.argv[1]]()
