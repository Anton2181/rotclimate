"""Plan T1 (calibration/geography_control_20261107/plan_T1.json): the height map as a climate lever inside the tier
bands. L1 = band position per upland tier (ramp exponent gamma_k), L2 = where the tier-1 hills stand (amount unchanged).

    .venv/bin/python -I scripts/terrain_climate_t1.py screen        # lapse-only emulator on the v2.1 climate run
    .venv/bin/python -I scripts/terrain_climate_t1.py build NAME g2 g3 g4 w   # a candidate height map (plan_R1 pipeline)
    .venv/bin/python -I scripts/terrain_climate_t1.py confirm NAME ...        # full climate runs + adoption rule
"""
from __future__ import annotations

import itertools
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_T1.json"
OUT = ROOT / "output/terrain_climate_t1"
ERO = ROOT / "output/terrain_erosion_20261107"
V21_RUN = ROOT / "output/terrain_v21_climate_check/terrain_v21_result.pkl"
GAMMAS = (0.6, 0.8, 1.0, 1.25, 1.6)
WEIGHTS = (0.0, 0.5, 1.0)
DX = 1.143 * 1609.344
log = lambda *a: print(*a, flush=True)  # noqa: E731


def tops():
    return json.loads((ROOT / "calibration/map_world_r44_terrain/params.json").read_text())["tier_tops"]


def ramps_gamma(tier_tops, gammas):
    """rotclimate.geography.elevation_fullres (tier ramps) with s -> s^gamma_k inside the upland tiers k = 2, 3, 4."""
    from rotclimate.geography import _tier_ramps, source_layers
    tier = source_layers()["tier"]; t = [0.0] + list(tier_tops); h = np.zeros(tier.shape)
    for k, s in _tier_ramps().items():
        g = gammas.get(k, 1.0)
        h += np.where(tier == k, t[k - 1] + (t[k] - t[k - 1]) * np.power(np.clip(s, 0, 1), g), 0.0)
    h = ndi.gaussian_filter(h, 2.0)
    return np.where(source_layers()["land"], np.maximum(h, 1.0), 0.0)


def grid_index(g, f):
    """Map climate-grid cells to source blocks (the grid pads the map symmetrically)."""
    from rotclimate.geography import source_layers
    H, W = source_layers()["land"].shape
    by, bx = H // f, W // f; py, px = (g.ny - by) // 2, (g.nx - bx) // 2
    return by, bx, py, px


def to_grid(a_full, g, f):
    by, bx, py, px = grid_index(g, f)
    b = a_full[:by * f, :bx * f].reshape(by, f, bx, f).mean((1, 3))
    out = np.zeros((g.ny, g.nx)); out[py:py + by, px:px + bx] = b
    return out


def zones(r, dz=None):
    from rotclimate.koppen import climate_indices, monthly_stats, classify
    from rotclimate.score import memberships, terrain_slope, best_zone
    g, p = r.grid, r.params; T = np.asarray(r.T, float)
    if dz is not None:
        T = T - (p.lapse_rate / 1000.0) * dz[None]
    st = monthly_stats(T, r.P, r.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    ix = climate_indices(st["Tm"], st["Pm"], st["summer"])
    return best_zone(memberships(ix, slope=terrain_slope(g)), koppen=classify(st["Tm"], st["Pm"], st["summer"]))


def halves(g):
    painted = g.inmap & g.land & (g.target > 0)
    cols = np.nonzero(g.inmap.any(0))[0]; mid = (cols.min() + cols.max()) // 2
    west = painted.copy(); west[:, mid:] = False
    return painted, west, painted & ~west


def score(pred, g):
    painted, west, east = halves(g)
    ok = pred == g.target
    return dict(all=float(ok[painted].mean()), west=float(ok[west].mean()), east=float(ok[east].mean()))


def preference(r):
    """L2: +1 where raising a tier-1 climate cell 300 m turns a wrong painted cell right, -1 where it turns a right one
    wrong (lapse-only on the v2.1 run); full resolution, smoothed at the hills' 80 km scale and standardised."""
    from rotclimate.geography import source_layers, _block
    g = r.grid; f = r.params.downsample; L = source_layers()
    tier1 = to_grid((L["tier"] == 1).astype(float), g, f) > 0.5
    base = zones(r); up = zones(r, np.where(tier1, 300.0, 0.0))
    painted = g.inmap & g.land & (g.target > 0) & tier1
    pref = np.zeros((g.ny, g.nx))
    pref[painted & (base != g.target) & (up == g.target)] = 1.0
    pref[painted & (base == g.target) & (up != g.target)] = -1.0
    by, bx, py, px = grid_index(g, f)
    full = np.kron(pref[py:py + by, px:px + bx], np.ones((f, f)))
    H, W = L["land"].shape; P = np.zeros((H, W)); P[:full.shape[0], :full.shape[1]] = full
    P = ndi.gaussian_filter(P, 80.0 / (DX / 1000.0))
    return (P - P.mean()) / (P.std() + 1e-12)


def steered_field(pref, w, land):
    """Mix the default hilliness with the preference and rank-match back to the default's distribution on land."""
    import terrain_erosion as TE
    n = TE.hill_noise(land.shape, DX)
    if w == 0:
        return n
    mix = (1 - w) * n + w * pref
    out = n.copy(); idx = np.flatnonzero(land.ravel())
    order = np.argsort(mix.ravel()[idx]); out.ravel()[idx[order]] = np.sort(n.ravel()[idx])
    return out


def screen():
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with open(V21_RUN, "rb") as fh:
        r = pickle.load(fh)
    g, f = r.grid, r.params.downsample
    base_full = ramps_gamma(tops(), {})
    s0 = score(zones(r), g); log("v2.1 run, strict (lapse emulator baseline):", s0)
    rows = []
    for g2, g3, g4 in itertools.product(GAMMAS, GAMMAS, GAMMAS):
        dz = to_grid(ramps_gamma(tops(), {2: g2, 3: g3, 4: g4}) - base_full, g, f)
        s = score(zones(r, dz), g); rows.append(dict(g2=g2, g3=g3, g4=g4, **s))
    rows.sort(key=lambda d: -d["all"])
    log("L1 best:", rows[:5], f"({time.time() - t0:.0f}s)")
    # L2: the hills' block-mean effect for each weight (hill layer rebuilt with the steered field)
    import terrain_erosion as TE
    from rotclimate.geography import source_layers
    from terrain_rivers import tier1_weight
    L = source_layers(); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    hfit = json.loads((ROOT / "output/terrain_rivers_20261107/map_form_scan3.json").read_text())["hill_height_m"]
    hf = dict(json.loads((ERO / "hill_fit.json").read_text())["best"], height_m=hfit)
    cs = json.loads((ROOT / "calibration/geography_control_20261107/plan_B2.json").read_text())["development_result"]["C_star"]
    prm = dict(cs, rounds=6, burn_m=4.0, lowpass_km=14.0); w1 = tier1_weight(L["tier"].astype(int))
    pref = preference(r); hill_rows = []; hill0 = None
    for w in WEIGHTS:
        hl = TE.hills(land, rivers, DX, hf["height_m"], sigma=hf["sigma"], prm=prm, field=steered_field(pref, w, land))
        hl = np.where(hl > 0, hf["cap_m"] * np.tanh(hl / hf["cap_m"]), hl) * w1
        if hill0 is None:
            hill0 = hl
        s = score(zones(r, to_grid(np.where(land, hl - hill0, 0.0), g, f)), g); hill_rows.append(dict(w=w, **s))
        log("L2", hill_rows[-1])
    out = dict(plan=str(PLAN.relative_to(ROOT)), baseline=s0, L1=rows, L2=hill_rows, seconds=time.time() - t0)
    (OUT / "screen.json").write_text(json.dumps(out, indent=1))
    np.save(OUT / "preference.npy", pref.astype(np.float32))


def build(name, g2, g3, g4, w):
    """A candidate height map through the plan_R1 pipeline (composition, conditioning with the adopted form)."""
    import terrain_erosion as TE
    import terrain_rivers as TR
    from rotclimate.geography import source_layers
    L = source_layers(); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land; tier = L["tier"].astype(int)
    tt = tops(); h0 = ramps_gamma(tt, {2: g2, 3: g3, 4: g4})
    scan = json.loads((ROOT / "output/terrain_rivers_20261107/map_form_scan3.json").read_text())
    hf = dict(json.loads((ERO / "hill_fit.json").read_text())["best"], height_m=scan["hill_height_m"])
    cs = json.loads((ROOT / "calibration/geography_control_20261107/plan_B2.json").read_text())["development_result"]["C_star"]
    field = steered_field(np.load(OUT / "preference.npy").astype(float), w, land) if w else None
    z0, _ = TE.compose(h0, land, rivers, DX, cs, hf, hill_weight=TR.tier1_weight(tier), hill_field=field)
    z, rec = TR.condition(z0, land, rivers, ramp=h0, **scan["chosen"])
    z32 = np.where(land, z, 0.0).astype(np.float32)
    strict = TR.strict_check(z32, land, rivers)
    v21 = np.load(ERO / "map_height_v21.npz")["z"].astype(float)
    base_h0 = ramps_gamma(tt, {})
    c21 = TE.checks(v21, base_h0, land, rivers, tier, tt, np.zeros(v21.shape), DX)
    c = TE.checks(z32.astype(float), base_h0, land, rivers, tier, tt, np.zeros(v21.shape), DX)
    from scipy.stats import ks_2samp
    ref9 = np.load(ERO / "earth_lowland_slopes.npz")["s9"]
    s9, s9b = TE.slopes_9km(z32.astype(float), land, DX, tier, 1), TE.slopes_9km(v21, land, DX, tier, 1)
    rec2 = dict(name=name, gammas=[g2, g3, g4], w=w, strict=strict, tier_bands=c["tier_band_share"], tier_bands_v21=c21["tier_band_share"],
                tier1_slope_median=float(np.median(s9)), slope_ks=float(ks_2samp(s9, ref9).statistic),
                slope_ks_v21=float(ks_2samp(s9b, ref9).statistic))
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / f"map_height_{name}.npz", z=z32, tier_tops=np.asarray(tt, float))
    (OUT / f"map_height_{name}.json").write_text(json.dumps(rec2, indent=1, default=float))
    log(json.dumps(rec2, indent=1, default=float))


def confirm(name):
    """Full climate run of a candidate and the plan_T1 adoption rule against the v2.1 run."""
    from build_atlas_variant import load
    from rotclimate.model import run_ensemble
    from add_corrected_layers import corrected_fields
    t0 = time.time(); terrain = str((OUT / f"map_height_{name}.npz").relative_to(ROOT))
    with open(V21_RUN, "rb") as fh:
        base = pickle.load(fh)
    p = load(ROOT / "calibration/map_world_r44/params.json").replace(downsample=8, terrain_file=terrain)
    new = run_ensemble(p, [1, 2, 3], workers=3)
    log(f"{name}: simulated in {time.time() - t0:.0f} s")
    with open(OUT / f"{name}_result.pkl", "wb") as fh:
        pickle.dump(new, fh)
    cal = ROOT / "calibration/earth_correction_r44_20261107"
    res = dict(plan=str(PLAN.relative_to(ROOT)), candidate=name, terrain_file=terrain)
    for tag, r in (("v21", base), (name, new)):
        dT, ratio, fit, change, _ = corrected_fields(r, cal)
        from rotclimate.koppen import climate_indices, monthly_stats, classify
        from rotclimate.score import memberships, terrain_slope, best_zone
        pp = r.params; st = monthly_stats(r.T, r.P, r.days, pp.year_days, summer_solstice=pp.winter_solstice_day + pp.year_days / 2)
        Tc = st["Tm"] + dT; Pc = np.maximum(st["Pm"], 0.0) * ratio          # the corrected monthly climate
        ix = climate_indices(Tc, Pc, st["summer"])
        pred = best_zone(memberships(ix, slope=terrain_slope(r.grid)), koppen=classify(Tc, Pc, st["summer"]))
        res[tag] = dict(raw=score(zones(r), r.grid), fit=fit, corrected_halves=score(pred, r.grid))
    cs = lambda tag: res[tag]["fit"]["corrected"]["strict_accuracy"]
    rw = lambda tag: res[tag]["fit"]["raw"]["strict_accuracy"]
    d_corr, d_raw = 100 * (cs(name) - cs("v21")), 100 * (rw(name) - rw("v21"))
    hv = {h: 100 * (res[name]["corrected_halves"][h] - res["v21"]["corrected_halves"][h]) for h in ("west", "east")} if "corrected_halves" in res[name] else {}
    meta = json.loads((OUT / f"map_height_{name}.json").read_text())
    gates = dict(gain=d_corr >= 0.5, no_half_worse=all(v >= -0.3 for v in hv.values()) if hv else False,
                 tiers=all(meta["tier_bands"][k] >= meta["tier_bands_v21"][k] - 0.02 for k in ("2", "3", "4")),
                 slope=abs(meta["tier1_slope_median"] / 0.167 - 1) <= 0.10 and meta["slope_ks"] <= meta["slope_ks_v21"] + 0.02,
                 rivers=meta["strict"]["passes"])
    res.update(delta_points=dict(raw=d_raw, corrected=d_corr, corrected_halves=hv), gates=gates, adopt=bool(all(gates.values())))
    (OUT / f"confirm_{name}.json").write_text(json.dumps(res, indent=1, default=float))
    log(json.dumps(dict(delta=res["delta_points"], gates=gates, adopt=res["adopt"]), indent=1, default=float))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "screen":
        screen()
    elif cmd == "build":
        build(sys.argv[2], *map(float, sys.argv[3:7]))
    elif cmd == "confirm":
        confirm(sys.argv[2])
