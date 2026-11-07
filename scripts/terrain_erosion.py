"""Workstream B of reports/GEOGRAPHY_CONTROL_PLAN_20261107.md: an eroded height map that keeps the painted tiers at
climate scale and carries the marked rivers.

Landscape evolution to steady state (stream-power law dz/dt = U - K A^m S^n + D lap z; Howard 1994, Whipple & Tucker
1999; implicit O(n) solver of Braun & Willett 2013 via fastscapelib; sinks resolved on a minimum spanning tree).
  * uplift U from the target large-scale elevation h0 (the tier ramps), with log-normal noise at a declared scale so
    ridges and valleys form (Perron, Kirchner & Dietrich 2009: their spacing is set by D / K);
  * the marked rivers are channels: their cells are burned below their surroundings at every step and carry extra
    drainage area (the catchment the drawing implies), so the routing follows them (Genevaux et al. 2013);
  * the sea is base level (fixed at 0);
  * faithful to the tiers at climate scale: between rounds the uplift is rescaled by lowpass(h0) / lowpass(z), and a
    last smooth additive correction makes lowpass(z) = lowpass(h0), followed by a sink-free re-route.

    .venv/bin/python -I scripts/terrain_erosion.py preview [factor]   # uncalibrated map preview (default factor 2)

The Earth calibration (posterize and reconstruct, plan B2) fits K, m, D, the noise and the river boost; until then
this is a preview only and nothing downstream uses it.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/terrain_erosion_20261107"
DEFAULTS = dict(m=0.45, rounds=6, noise_km=12.0, noise_sigma=0.35, river_boost_km2=3000.0, burn_m=4.0, lowpass_km=14.0,
                smooth_px=0.7, smooth_mix=0.5, seed=1)
log = lambda *a: print(*a, flush=True)  # noqa: E731


def evolve(h0, land, rivers, dx_m, prm=None):
    """Steady-state stream-power elevation (m) for target h0 on land; sea = 0. Returns (z, info).

    At steady state with n = 1 every channel's slope is S = k_sn A^-m (k_sn = (U / K), the channel steepness), so the
    elevation is that slope summed down each flow path to the sea (the chi integral; Perron & Royden 2013), solved
    level by level from the base levels upward. Routing and elevation are iterated until the drainage settles; k_sn is
    rescaled between rounds so the large-scale elevation matches h0 (the tiers at climate scale), with log-normal
    variation at noise_km (rock strength) seeding ridges and valleys."""
    import fastscapelib as fs
    p = dict(DEFAULTS, **(prm or {})); t0 = time.time()
    ny, nx = h0.shape; land = land.astype(bool); rivers = rivers.astype(bool) & land
    status = {(int(i), int(j)): fs.NodeStatus.FIXED_VALUE for i, j in zip(*np.nonzero(~land))}
    grid = fs.RasterGrid([ny, nx], [dx_m, dx_m], fs.NodeStatus.FIXED_VALUE, status)
    flow = fs.FlowGraph(grid, [fs.SingleFlowRouter(), fs.MSTSinkResolver()]); impl = flow.impl()
    rng = np.random.default_rng(p["seed"]); cells = dx_m / 1000.0
    def smooth_noise(km):
        n = ndi.gaussian_filter(rng.standard_normal(h0.shape), max(km / cells, 0.5)); return n / n.std()
    lp = lambda a: ndi.gaussian_filter(np.where(land, a, 0.0), p["lowpass_km"] / cells) / np.maximum(
        ndi.gaussian_filter(land.astype(float), p["lowpass_km"] / cells), 1e-6)
    target = lp(h0)
    rock = np.exp(p["noise_sigma"] * smooth_noise(p["noise_km"]))
    ksn = np.where(land, rock, 0.0)
    # initial surface: the target plus multi-scale roughness to seed the drainage pattern
    z = np.where(land, h0 * (1 + 0.15 * smooth_noise(p["noise_km"] / 2)) + 5 * smooth_noise(p["noise_km"]), 0.0)
    boost = np.where(rivers, p["river_boost_km2"] * 1e6, 0.0)
    for r in range(p["rounds"]):
        zr = np.where(rivers, z - p["burn_m"], z)
        flow.update_routes(zr)
        A = flow.accumulate(dx_m * dx_m).ravel() + boost.ravel()
        rec = impl.receivers[:, 0]; dist = impl.receivers_distance[:, 0]
        incr = ksn.ravel() * np.power(np.maximum(A, dx_m * dx_m), -p["m"]) * dist
        zz = np.zeros(A.size)
        order, lev = impl.bfs_indices, impl.bfs_levels
        for a, b in zip(lev[:-1], lev[1:]):
            nodes = order[a:b]; nodes = nodes[rec[nodes] != nodes]
            zz[nodes] = zz[rec[nodes]] + incr[nodes]
        zz = zz.reshape(h0.shape)
        scale = np.where(land, target / np.maximum(lp(zz), 1e-6), 1.0)
        scale = np.exp(ndi.gaussian_filter(np.log(np.clip(scale, 1e-3, 1e3)), p["lowpass_km"] / cells))
        ksn = np.where(land, ksn * scale, 0.0)
        z = np.where(land, zz * scale, 0.0)
        z = np.where(land, ndi.gaussian_filter(z, p["smooth_px"]) * (1 - p["smooth_mix"]) + z * p["smooth_mix"], 0.0) if p["smooth_px"] else z
        log(f"   round {r + 1}: mean |lowpass(z) - lowpass(h0)| {np.abs(lp(z) - target)[land].mean():.1f} m ({time.time() - t0:.0f}s)")
    z = np.where(land, np.maximum(z + (target - lp(z)), 0.5), 0.0)  # last smooth correction: climate-scale faithful
    zr = np.where(rivers, z - p["burn_m"], z); zf = flow.update_routes(zr)
    A = flow.accumulate(dx_m * dx_m)
    z = np.where(land, np.maximum(zf + (z - zr), 0.5), 0.0)       # sink-free surface (lakes filled), rivers not left burned
    return z, dict(params=p, drainage_area_m2=A, seconds=time.time() - t0)


def checks(z, h0, land, rivers, tier, tops, A, dx_m, lowpass_km=14.0):
    """Plan B3 acceptance checks (reported)."""
    lp = lambda a: ndi.gaussian_filter(np.where(land, a, 0.0), lowpass_km * 1000 / dx_m) / np.maximum(
        ndi.gaussian_filter(land.astype(float), lowpass_km * 1000 / dx_m), 1e-6)
    chan = A >= 200e6                                                  # channels: >= 200 km2 upstream
    near = ndi.binary_dilation(chan, np.ones((3, 3)))
    edges = [0.0] + list(tops)
    band = {}
    for k in range(1, 5):
        m = land & (tier == k)
        if m.any():
            lo, hi = edges[k - 1], edges[k]; margin = 0.1 * (hi - lo)
            band[k] = float(((z[m] >= lo - margin) & (z[m] <= hi + margin)).mean())
    gy, gx = np.gradient(z, dx_m); slope = np.degrees(np.arctan(np.hypot(gy, gx)))[land]
    return dict(rivers_on_channel=float(near[rivers & land].mean()), tier_band_share=band,
                climate_scale_mean_abs_m=float(np.abs(lp(z) - lp(h0))[land].mean()),
                slope_deg_pct={q: float(np.percentile(slope, q)) for q in (25, 50, 75, 90)},
                channel_density_km_per_km2=float(chan[land].sum() * dx_m / 1000 / (land.sum() * (dx_m / 1000) ** 2)))


def preview(factor=2):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    from rotclimate.geography import elevation_fullres, source_layers
    OUT.mkdir(parents=True, exist_ok=True)
    tops = json.loads((ROOT / "calibration/map_world_r43/params.json").read_text())["tier_tops"]
    L = source_layers(); h_full = elevation_fullres(tuple(tops))
    f = int(factor); H, W = (h_full.shape[0] // f) * f, (h_full.shape[1] // f) * f
    blk = lambda a, fn: fn(a[:H, :W].reshape(H // f, f, W // f, f), axis=(1, 3))
    h0 = blk(h_full, np.mean); land = blk(L["land"].astype(float), np.mean) > 0.5
    rivers = blk(L["rivers"].astype(bool), np.max) & land; tier = blk(L["tier"].astype(int), np.max)
    dx = 1.143 * 1609.344 * f                                          # source px = 1.143 mi
    log(f"map at factor {f}: {h0.shape}, {land.sum():,} land cells, {rivers.sum():,} river cells, dx {dx:.0f} m")
    z, info = evolve(h0, land, rivers, dx)
    c = checks(z, h0, land, rivers, tier, tops, info["drainage_area_m2"], dx)
    log(json.dumps(c, indent=1))
    np.savez_compressed(OUT / f"map_preview_f{f}.npz", z=z.astype(np.float32), h0=h0.astype(np.float32), land=land, rivers=rivers,
                        area=info["drainage_area_m2"].astype(np.float32))
    (OUT / f"map_preview_f{f}.json").write_text(json.dumps(dict(checks=c, params=info["params"], seconds=info["seconds"]), indent=1))
    ls = LightSource(azdeg=315, altdeg=40)
    fig, ax = plt.subplots(2, 1, figsize=(14, 13.5), constrained_layout=True)
    for a, e, title in ((ax[0], h0, "Today: tier ramps"), (ax[1], z, "Preview: eroded, rivers imposed, tiers kept at climate scale (uncalibrated)")):
        E = np.where(land, e, np.nan)
        rgb = ls.shade(np.nan_to_num(E), cmap=plt.get_cmap("terrain"), vert_exag=8, dx=dx, dy=dx, blend_mode="soft", vmin=-200, vmax=2800)
        rgb[~land] = [0.80, 0.87, 0.93, 1]
        a.imshow(rgb); a.set_title(title, fontsize=11); a.axis("off")
    yy, xx = np.nonzero(rivers); ax[1].scatter(xx, yy, s=0.15, c="#1f4e9c", lw=0)
    chan = info["drainage_area_m2"] >= 1000e6
    yy, xx = np.nonzero(chan & land & ~rivers); ax[1].scatter(xx, yy, s=0.1, c="#5fa8d3", lw=0)
    fig.savefig(OUT / f"map_preview_f{f}.png", dpi=110); log("wrote", OUT / f"map_preview_f{f}.png")


if __name__ == "__main__":
    {"preview": lambda: preview(*(sys.argv[2:3] or [2]))}[sys.argv[1]]()
