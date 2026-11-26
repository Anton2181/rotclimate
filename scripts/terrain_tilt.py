"""Height map calibration under natural physics (owner, 27 Nov 2026): rivers follow unchanging physics (Priority-Flood
steepest descent); the height map is calibrated. Relative river rule: a new (undrawn) river must be smaller than the
drawn river systems in its own region (within R km of its outlet; drawn river system = a connected drawn river with
its tributaries, size = catchment at its mouth). Tier rules as v2.2.

Calibration lever: a regional tilt added to the tier ramps before erosion, rising with distance from the nearest drawn
river or coast (alpha m per km), clipped to each cell's painted tier band, so water is guided towards the drawn
rivers. Everything downstream is the unchanged v2.2 pipeline (terrain_erosion.compose with physics routing,
terrain_rivers.condition with lakes).

    .venv/bin/python -I scripts/terrain_tilt.py scan 0 2 5 10      # build + evaluate per alpha (no files written)
    .venv/bin/python -I scripts/terrain_tilt.py build ALPHA         # write map_height_v23.npz + .json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
ERO = ROOT / "output/terrain_erosion_20261107"
NB = np.array([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)], np.int64)
R_KM = 300.0
log = lambda *a: print(*a, flush=True)  # noqa: E731


def setup():
    import terrain_rivers as TR
    from rotclimate.geography import elevation_fullres, source_layers
    scan = json.loads((TR.OUT / "map_form_scan3.json").read_text()); form = scan["chosen"]
    plan = json.loads((ROOT / "calibration/geography_control_20261107/plan_B2.json").read_text())
    cs = plan["development_result"]["C_star"]
    tops = json.loads((ROOT / "calibration/map_world_r44_terrain/params.json").read_text())["tier_tops"]
    L = source_layers(); h0 = elevation_fullres(tuple(tops)); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    tier = L["tier"].astype(int); dx = 1.143 * 1609.344
    hf = dict(json.loads((ERO / "hill_fit.json").read_text())["best"], height_m=scan["hill_height_m"])
    return dict(TR=TR, form=form, cs=cs, tops=tops, L=L, h0=h0, land=land, rivers=rivers, tier=tier, dx=dx, hf=hf)


def tilted(S, alpha):
    h0, land, rivers, tier, tops = S["h0"], S["land"], S["rivers"], S["tier"], S["tops"]
    outlet = ~land | rivers
    dkm = ndi.distance_transform_edt(~outlet) * (S["dx"] / 1000.0)
    lo = np.array([0.0] + list(tops))[np.clip(tier - 1, 0, 4)]; hi = np.array([0.0] + list(tops))[np.clip(tier, 0, 4)]
    h = h0 + alpha * dkm
    return np.where(land, np.clip(h, np.maximum(lo, 1.0), np.maximum(hi, 2.0)), 0.0)


def build_z(S, alpha):
    TE = __import__("terrain_erosion"); TR = S["TR"]
    h = tilted(S, alpha)
    z0, info = TE.compose(h, S["land"], S["rivers"], S["dx"], S["cs"], S["hf"], hill_weight=TR.tier1_weight(S["tier"]))
    lake = S["L"]["lake"].astype(bool) & ~S["land"]
    z, rec, level = TR.condition(z0, S["land"], S["rivers"], ramp=S["h0"], lake=lake, **S["form"])
    return np.where(S["land"], z, 0.0).astype(np.float32), level.astype(np.float32), lake


def evaluate(S, z, level, lake):
    TE = __import__("terrain_erosion"); TR = S["TR"]
    from rotclimate.routing import _accumulate, _flood
    from scipy.spatial import cKDTree
    land, rivers, h0, tier, tops, dx = S["land"], S["rivers"], S["h0"], S["tier"], S["tops"], S["dx"]
    H, W = land.shape; px = (dx / 1000.0) ** 2; pxkm = dx / 1000.0
    through = ~land & (level > 0)
    rv, order = _flood(np.where(land, z.astype(float), np.where(through, level, -1e9)), land | through, NB)
    A = (_accumulate(order, rv, land.ravel().astype(float)) * px).reshape(H, W)
    comp, nc = ndi.label(rivers, structure=np.ones((3, 3)))
    csize = ndi.maximum(A, comp, np.arange(1, nc + 1))                       # each drawn river system at its mouth
    und = land & ~rivers; undf = und.ravel()
    ends = np.flatnonzero(undf & ~((rv >= 0) & undf[np.maximum(rv, 0)]))
    endA = A.ravel()[ends]; ey, ex = np.divmod(ends, W)
    dy, dxx = np.nonzero(rivers); ds = csize[comp[dy, dxx] - 1]
    tree = cKDTree(np.c_[dy, dxx]); idx = np.flatnonzero(endA > 100)
    viol = []
    for k, lst in zip(idx, tree.query_ball_point(np.c_[ey[idx], ex[idx]], R_KM / pxkm)):
        if lst and endA[k] >= ds[lst].min():
            viol.append((float(endA[k]), float(ds[lst].min()), int(ey[k]), int(ex[k])))
    viol.sort(reverse=True)
    strict = TR.strict_check(z, land, rivers, lake=lake, level=level)
    v22 = np.load(ERO / "map_height_v22.npz")
    c = TE.checks(z.astype(float), h0, land, rivers, tier, tops, A * 1e6, dx)
    c2 = TE.checks(np.asarray(v22["z"], float), h0, land, rivers, tier, tops, np.asarray(v22["area"], float), dx)
    slope = float(np.median(TE.slopes_9km(z.astype(float), land, dx, tier, 1)))
    gates = dict(owner_rivers=strict["passes"],
                 tier_bands_2_4=all(c["tier_band_share"][k] >= c2["tier_band_share"][k] - 0.02 for k in (2, 3, 4)),
                 climate_scale=c["climate_scale_mean_abs_m"] <= c2["climate_scale_mean_abs_m"] + 5.0,
                 lowland_slope=abs(slope / 0.167 - 1) <= 0.10, relative_rule=not viol)
    return dict(gates=gates, violations=len(viol), worst=viol[:6], largest_undrawn_km2=float(A[und].max()),
                tier_bands=c["tier_band_share"], climate_scale=c["climate_scale_mean_abs_m"], tier1_slope=slope)


def scan(alphas):
    S = setup()
    for a in alphas:
        z, level, lake = build_z(S, float(a))
        r = evaluate(S, z, level, lake)
        log(f"alpha {a}: " + json.dumps(r, default=float))


def build(alpha):
    S = setup(); z, level, lake = build_z(S, float(alpha)); r = evaluate(S, z, level, lake)
    np.savez_compressed(ERO / "map_height_v23.npz", z=z, tier_tops=np.asarray(S["tops"], float), lake_level=level)
    (ERO / "map_height_v23.json").write_text(json.dumps(dict(alpha_m_per_km=float(alpha), R_km=R_KM, **r), indent=1, default=float))
    log(json.dumps(r, indent=1, default=float))


if __name__ == "__main__":
    {"scan": lambda: scan(sys.argv[2:]), "build": lambda: build(sys.argv[2])}[sys.argv[1]]()
