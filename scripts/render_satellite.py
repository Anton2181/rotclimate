"""A satellite-style picture of the world from its simulated climate.

Drawn at the resolution of the original terrain drawing (4401 x 2037,
data/source/original/terrain.png), not the 2000 x 926 working layers.

Land colour comes from what the climate would grow: vegetation cover from the
aridity (annual rain against a Holdridge potential evaporation), its kind from
the temperatures (boreal, broadleaf, tropical forest, steppe, savanna), bare
ground from heat and dryness (hot sand, cold desert, tundra), snow from the
simulated snowpack and ice where even the warmest month freezes. The season
shown browns the grass in its dry months and the leaves in its cold ones. The
relief is hillshaded from the tier terrain with a ridged fractal where the
ground is high, so ranges read as ranges. The sea shades from shelf to deep
water with distance from the coast, warmer seas a little more turquoise, with
sea ice where it freezes.

    python -I scripts/render_satellite.py --params calibration/earth/free_e3new_retro.json \
        --downsample 8 --out output/satellite
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from rotclimate.config import Params  # noqa: E402
from rotclimate.koppen import monthly_weights  # noqa: E402

ORIG = ROOT / "data" / "source" / "original"
MAP_KM = 3680.0                          # map width (2287 mi)


def load(path):
    d = json.loads(Path(path).read_text())
    d = d.get("params", d)
    return Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__})


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def smooth(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = np.asarray(t, np.float32)[..., None]
    return a * (1 - t) + b * t


def fractal(shape, seed, scales, weights, ridged=False):
    """Sum of smoothed white-noise octaves (scales in pixels), roughly -1..1."""
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    for s, w in zip(scales, weights):
        n = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), s, mode="wrap")
        n /= n.std() + 1e-12
        if ridged:
            n = 1.0 - 2.0 * np.abs(np.tanh(n))
        out += w * n
    return out / sum(weights)


def ridged_multifractal(shape, seed, scales, amps, gain=2.2):
    """Musgrave's ridged multifractal, normalised to mean 0 and std 1: sharp
    ridge lines, and the finer octaves only where the coarser ones already
    rise, so valleys stay smooth. scales in pixels, coarse to fine."""
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    weight = np.ones(shape, np.float32)
    for s, amp in zip(scales, amps):
        n = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), s, mode="wrap")
        n /= n.std() + 1e-12
        sig = (1.0 - np.abs(np.tanh(0.9 * n))) ** 2 * weight
        weight = np.clip(sig * gain, 0.0, 1.0)
        out += amp * sig
    return (out - out.mean()) / (out.std() + 1e-12)


# palette, chosen against Blue Marble / Sentinel-2 true-colour composites
C = {k: hexrgb(v) for k, v in dict(
    boreal="#22392a", broadleaf="#2f5326", rainforest="#1d4319", steppe="#8b8455", savanna="#7d7a3e",
    tundra="#7d7a64", sand_hot="#d9b583", sand_red="#c48d5a", cold_desert="#a69a82", rock="#8c8478",
    rock_dark="#5e5a52",
    snow="#eef1f4", ice="#f6f8fb", dry_grass="#a8935e", dormant="#5f5a3e", shelf="#2f8a9a",
    shelf_warm="#3aa3a6", deep="#0a1f3d", mid="#123a66", lake="#163a5a", river="#2b4a5c",
    seaice="#dfe7ee").items()}


def original_terrain():
    """Land, tier (1-4), lakes and rivers at the original drawing's resolution."""
    im = Image.open(ORIG / "terrain.png")                # palette: 4 tier colours, index 4 = water
    idx = np.array(im)
    land = idx < 4
    tier = np.where(land, idx + 1, 0).astype(np.int8)
    water = ~land
    lab, _ = ndi.label(water)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    lake = water & ~np.isin(lab, border[border > 0])
    rivers = np.array(Image.open(ORIG / "rivers.png"))[..., 3].astype(np.float32) / 255.0
    return land, tier, lake, rivers


def elevation(tier, land, tops, px_scale, a_rise=8.0):
    """Continuous elevation (m) from the tier map, as geography.elevation_fullres
    but at this resolution (its pixel constants scaled by px_scale). `a_rise`
    sets how far (working-layer pixels) the highest tier takes to climb to
    its summit level."""
    tops = [0.0] + list(tops)
    h = np.zeros(tier.shape, np.float32)
    for k in range(1, 5):
        inside = tier == k
        if not inside.any():
            continue
        d_lo = ndi.distance_transform_edt(tier >= k)
        higher = tier > k
        if higher.any():
            d_hi = ndi.distance_transform_edt(~higher)
            s = d_lo / (d_lo + d_hi + 1e-9)
            if k == 1:
                s = np.minimum(s, 1 - np.exp(-d_lo / (60.0 * px_scale)))
        else:
            s = 1 - np.exp(-d_lo / (a_rise * px_scale))
        h += np.where(inside, tops[k - 1] + (tops[k] - tops[k - 1]) * s, 0.0).astype(np.float32)
    h = ndi.gaussian_filter(h, 2.0 * px_scale)
    return np.where(land, np.maximum(h, 1.0), 0.0).astype(np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", required=True)
    ap.add_argument("--downsample", type=int, default=8)
    ap.add_argument("--set", default='{"solver_rtol": 1e-6, "solver_require_convergence": false}')
    ap.add_argument("--out", required=True)
    ap.add_argument("--reuse", action="store_true", help="reuse <out>/climate_cache.npz instead of simulating")
    ap.add_argument("--relief", type=float, default=1.0, help="scale of the synthetic mountain relief")
    ap.add_argument("--vexag", type=float, default=0.6, help="hillshade vertical exaggeration")
    ap.add_argument("--rise", type=float, default=22.0, help="how gradually the highest tier climbs (pixels)")
    ap.add_argument("--erosion-steps", type=int, default=200, help="uplift-erosion steps that carve the valleys")
    ap.add_argument("--crop", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"),
                    help="render only this window of the original drawing (for quick look development)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    from rotclimate.model import ClimateModel

    p = load(a.params).replace(downsample=a.downsample, **json.loads(a.set))
    cache = out / "climate_cache.npz"
    if a.reuse and cache.exists():
        z = np.load(cache)
        Tm_c, Pm_c, Sm_c, gland = z["Tm"], z["Pm"], z["Sm"], z["land"]
        gpad, gf = int(z["pad"]), int(z["f"])
    else:
        res = ClimateModel(p).run()
        Wm = monthly_weights(res.days, p.year_days)
        n = len(res.days)
        Tm_c = (Wm @ res.Tsl.reshape(n, -1)).reshape((12,) + res.Tsl.shape[1:])
        Pm_c = (Wm @ res.P.reshape(n, -1)).reshape((12,) + res.P.shape[1:]) * p.year_days / 12.0
        Sm_c = (Wm @ res.snow.reshape(n, -1)).reshape((12,) + res.snow.shape[1:])
        gland, gpad, gf = res.grid.land, res.grid.pad, res.grid.f
        np.savez_compressed(cache, Tm=Tm_c, Pm=Pm_c, Sm=Sm_c, land=gland, pad=gpad, f=gf)
    print(f"climate ready ({time.time() - t0:.0f}s)", flush=True)

    land, tier, lake, rivers = original_terrain()
    H, W = land.shape
    px_scale = W / 2000.0                                   # original pixels per working-layer pixel
    km_px = MAP_KM / W
    elev = elevation(tier, land, p.tier_tops, px_scale, a_rise=a.rise)
    # the drawing's tiers are hex clusters: warp the elevation with smooth
    # noise so ridges and tier edges come out organic (coasts stay as drawn)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wy = fractal((H, W), 31, (5, 14, 35), (0.4, 0.8, 1.0)) * 9.0 * px_scale
    wx = fractal((H, W), 32, (5, 14, 35), (0.4, 0.8, 1.0)) * 9.0 * px_scale
    elev = np.where(land, np.maximum(ndi.map_coordinates(elev, [yy + wy, xx + wx], order=1, mode="nearest"), 1.0),
                    0.0).astype(np.float32)
    del yy, xx, wy, wx
    oy = ox = 0
    if a.crop:
        x0, y0, x1, y1 = a.crop
        land, tier, lake, rivers, elev = (v[y0:y1, x0:x1] for v in (land, tier, lake, rivers, elev))
        oy, ox = y0, x0
        H, W = land.shape
    # model grid -> original pixels (the working layers are block-averaged by g.f)
    yy, xx = np.mgrid[oy:oy + H, ox:ox + W].astype(np.float32)
    cy = (yy + 0.5) / px_scale / gf - 0.5 + gpad
    cx = (xx + 0.5) / px_scale / gf - 0.5 + gpad
    del yy, xx
    _, (fy, fx) = ndi.distance_transform_edt(~gland, return_indices=True)

    def up(a, land_fill=True):
        a = np.asarray(a, np.float64)
        sea = ndi.map_coordinates(a, [cy, cx], order=1, mode="nearest").astype(np.float32)
        if not land_fill:
            return sea
        lnd = ndi.map_coordinates(a[fy, fx], [cy, cx], order=1, mode="nearest").astype(np.float32)
        return np.where(land, lnd, sea)

    # month by month at full resolution
    lapse = p.lapse_rate * elev / 1000.0
    land_mean = np.array([float(Tm_c[k][gland].mean()) for k in range(12)])
    hot, cold = int(land_mean.argmax()), int(land_mean.argmin())
    seasons = {"summer": [(hot - 1) % 12, hot, (hot + 1) % 12],
               "winter": [(cold - 1) % 12, cold, (cold + 1) % 12]}
    Tann = np.zeros((H, W), np.float32); Pann = np.zeros_like(Tann); BT = np.zeros_like(Tann)
    Tcold = np.full((H, W), 99.0, np.float32); Thot = np.full((H, W), -99.0, np.float32)
    sT = {k: np.zeros_like(Tann) for k in seasons}; sP = {k: np.zeros_like(Tann) for k in seasons}
    sS = {k: np.zeros_like(Tann) for k in seasons}; sSST = {k: np.zeros_like(Tann) for k in seasons}
    for m in range(12):
        T = np.where(land, up(Tm_c[m]) - lapse, up(Tm_c[m], land_fill=False))
        P = np.maximum(up(Pm_c[m]), 0.0)
        Tann += T / 12; Pann += P; BT += np.clip(T, 0, 30) / 12
        Tcold = np.minimum(Tcold, T); Thot = np.maximum(Thot, T)
        for k, months in seasons.items():
            if m in months:
                sT[k] += T / 3; sP[k] += P / 3; sS[k] += np.maximum(up(Sm_c[m]), 0) / 3
                sSST[k] += up(Tm_c[m], land_fill=False) / 3
    print(f"climate at {W} x {H} ({time.time() - t0:.0f}s)", flush=True)

    # relief: valleys carved by growing the ranges against river erosion at a
    # quarter of the resolution (so the drainage branches the way real
    # drainage does), plus fine ridges for texture, stronger the higher the ground
    relief = smooth(elev, 150.0, 2000.0)
    from terrain_erosion import uplift_landscape
    f = 4
    coarse = ndi.zoom(elev, 1 / f, order=1)
    cdom = ndi.zoom((land | lake).astype(np.float32), 1 / f, order=1) > 0.5
    t1 = time.time()
    grown = uplift_landscape(coarse, cdom, km_px * 1000.0 * f, steps=a.erosion_steps, K=3e-3, jitter=0.35, seed=7)
    valleys = grown - ndi.gaussian_filter(grown, 4.0)
    valleys /= valleys[ndi.zoom(relief, 1 / f, order=1)[:valleys.shape[0], :valleys.shape[1]] > 0.8].std() + 1e-9
    valleys = ndi.zoom(valleys, (H / valleys.shape[0], W / valleys.shape[1]), order=3).astype(np.float32)
    print(f"valleys carved ({time.time() - t1:.0f}s)", flush=True)
    fine = ridged_multifractal((H, W), 11, tuple(s * px_scale / 2.2 for s in (3.5, 1.6)), (1.0, 0.6))
    elev_d = elev + a.relief * relief * (120.0 + 0.22 * elev) * (valleys + 0.15 * fine) \
        + 25.0 * fractal((H, W), 12, (2, 6, 18), (0.4, 0.7, 1.0))
    elev_d = np.where(land, np.maximum(elev_d, 1.0), 0.0).astype(np.float32)
    del valleys, fine, grown, coarse
    relief_T = p.lapse_rate * (elev_d - elev) / 1000.0          # the detailed relief's own lapse
    from matplotlib.colors import LightSource

    dx = km_px * 1000.0
    shade = LightSource(azdeg=315, altdeg=35).hillshade(elev_d, vert_exag=a.vexag, dx=dx, dy=dx).astype(np.float32)
    gy, gx = np.gradient(elev_d, dx)
    slope = np.hypot(gx, gy).astype(np.float32)
    del gx, gy
    # valleys sit in shadow longer than ridges (a cheap ambient occlusion)
    hollow = np.clip((ndi.gaussian_filter(elev_d, 4.0 * px_scale) - elev_d) / 400.0, -1.0, 1.0)

    # what grows
    pet = np.maximum(58.93 * BT, 60.0)                       # Holdridge potential evaporation, mm/yr
    # local soils and slopes: the same climate grows patchier cover
    ai = Pann / pet * np.exp(0.35 * fractal((H, W), 21, (4, 12, 35, 90, 200), (0.3, 0.5, 0.8, 1.0, 0.8)))
    near_river = ndi.gaussian_filter(np.maximum(rivers, lake.astype(np.float32)), 6.0 * px_scale)
    near_river = np.clip(near_river / (near_river.max() + 1e-9) * 6.0, 0, 1)
    cover = smooth(ai, 0.08, 0.9) ** 0.85
    cover = cover + (1 - cover) * 0.55 * near_river * smooth(Tann, 2.0, 10.0)   # green river valleys
    Thot_loc = Thot - relief_T
    trees = smooth(Thot_loc, 7.0, 12.0)                      # tree line: warmest month about 10 C
    tropical = smooth(Tcold, 14.0, 20.0)
    coldness = 1.0 - smooth(Tcold, -12.0, -2.0)
    woodiness = smooth(ai, 0.45, 1.1) * trees
    forest = mix(mix(C["broadleaf"], C["boreal"], np.maximum(coldness, 1.0 - smooth(Thot_loc, 11.0, 16.0))),
                 C["rainforest"], tropical)
    open_veg = mix(mix(C["steppe"], C["savanna"], tropical), C["tundra"], 1.0 - smooth(Thot_loc, 4.0, 11.0))
    veg = mix(open_veg, forest, woodiness)
    sandtex = 0.5 + 0.5 * fractal((H, W), 3, (3, 10, 30), (0.3, 0.5, 1.0))
    bare = mix(C["cold_desert"], C["sand_hot"], smooth(Tann, 8.0, 20.0))
    bare = mix(bare, C["sand_red"], smooth(Thot, 33.0, 40.0) * sandtex)
    base = mix(bare, veg, cover)
    # bare rock and scree: steep ground where nothing roots, and the
    # high ground above the alpine meadows
    rocky = np.maximum(smooth(slope, 0.12, 0.35) * (1.0 - 0.75 * woodiness),
                       1.0 - smooth(Thot_loc, 0.0, 6.0))
    rock = mix(C["rock"], C["rock_dark"], 0.5 + 0.5 * sandtex - 0.25)
    base = mix(base, rock, 0.85 * rocky)
    del bare, veg, forest, open_veg, rock
    # snow and ice follow the detailed relief (ridges hold snow, valleys melt)
    dist_km = (ndi.distance_transform_edt(~land) * km_px).astype(np.float32)
    grain = fractal((H, W), 5, (1.2, 4, 11), (0.5, 0.7, 1.0))
    seagrain = fractal((H, W), 7, (6, 25), (0.6, 1.0))
    shelfvar = fractal((H, W), 8, (8, 30, 80), (0.4, 0.8, 1.0))
    riv = ndi.gaussian_filter(rivers, 1.0)

    for name in seasons:
        T, P, S = sT[name], sP[name], sS[name]
        wet_now = P / np.maximum(np.clip(T, 0, None) * 5.0 + 15.0, 15.0)          # mm/month vs demand
        dryness = (1.0 - smooth(wet_now, 0.4, 1.6)) * (1.0 - woodiness * 0.6) * cover
        col = mix(base, C["dry_grass"], 0.75 * dryness * smooth(T, 5.0, 15.0))
        dormant = (1.0 - smooth(T, -2.0, 8.0)) * (1.0 - coldness * 0.7) * cover * (1 - tropical)
        col = mix(col, C["dormant"], 0.55 * dormant)
        Tloc = T - relief_T
        # lying snow where the season is below freezing at this spot (the
        # detailed relief), more of it where the model's snowpack is deep
        # (smoothed: its grid cells must not show)
        snowy = ndi.gaussian_filter(smooth(S, 2.0, 30.0), 25.0 * px_scale)
        snow = smooth(-Tloc, -1.0, 4.0) * (0.35 + 0.65 * snowy) * smooth(P, 3.0, 20.0)
        snow = snow * (1.0 - 0.55 * woodiness)         # forest canopy hides the snow beneath it
        col = mix(col, C["snow"], np.clip(snow, 0, 0.95))
        col = mix(col, C["ice"], smooth(-(Thot - relief_T), 0.5, 3.5))
        col = col * (1.0 + 0.045 * grain[..., None])
        col = col * (0.5 + 0.75 * shade[..., None]) * (1.0 - 0.18 * np.clip(hollow, 0, 1)[..., None])
        sst = sSST[name]
        shelf = mix(C["shelf"], C["shelf_warm"], smooth(sst, 12.0, 27.0))
        reach = dist_km * np.exp(-0.5 * shelfvar)                  # shelves of uneven width
        sea = mix(C["mid"], C["deep"], smooth(dist_km, 15.0, 160.0))
        sea = mix(sea, shelf, 0.55 * (1.0 - smooth(reach, 1.5, 18.0)))
        sea = sea * (1.0 + 0.03 * seagrain[..., None])
        sea = mix(sea, C["seaice"], 0.9 * smooth(-sst, 0.5, 2.5))
        img = np.where(land[..., None], col, sea)
        img = np.where(lake[..., None], mix(C["lake"], C["seaice"], smooth(-T, 1.0, 4.0)), img)
        img = mix(img, C["river"], np.clip(riv * 0.5, 0, 0.5) * land)
        img8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        big = Image.fromarray(img8)
        big.save(out / f"satellite_{name}.webp", quality=90, method=6)
        big.resize((1600, round(1600 * H / W)), Image.LANCZOS).save(out / f"satellite_{name}_preview.png")
        print(f"{name}: months {seasons[name]} written ({time.time() - t0:.0f}s)", flush=True)
    (out / "satellite.json").write_text(json.dumps(dict(params=str(a.params), downsample=a.downsample,
                                                        seasons=seasons, width=W, height=H), indent=1))


if __name__ == "__main__":
    main()
