"""Plan R2 (calibration/geography_control_20261107/plan_R2.json): drawn rivers as trunk valleys. The erosion solve in
correct units so the river boost acts; the boost fitted on Earth by how much land drains into the drawn rivers.

    .venv/bin/python -I scripts/terrain_rivers_r2.py boost      # D1-D4 selection, B1-B4 check
    .venv/bin/python -I scripts/terrain_rivers_r2.py form       # plan_R1 valley form re-selected on the new composition
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_R2.json"
OUT = ROOT / "output/terrain_rivers_r2"
log = lambda *a: print(*a, flush=True)  # noqa: E731


def capture(z, land, rivers):
    """Share of land whose Priority-Flood path reaches a drawn-river cell."""
    from rotclimate import routing as R
    recv, order = R._flood(np.where(land, z, -1e9), land, R.NB)
    reach = rivers.ravel().copy()
    for c in order:                                                   # outlets first: downstream cells known first
        r = recv[c]
        if r >= 0 and reach[r]:
            reach[c] = True
    return float(reach.reshape(land.shape)[land].mean())


def setup():
    import terrain_earth_b2 as B2
    cs = json.loads(B2.PLAN.read_text())["development_result"]["C_star"]
    scan = json.loads((ROOT / "output/terrain_rivers_20261107/map_form_scan3.json").read_text())
    hf = dict(json.loads((ROOT / "output/terrain_erosion_20261107/hill_fit.json").read_text())["best"], height_m=scan["hill_height_m"])
    return B2, cs, scan, hf


def boost():
    import terrain_erosion as TE
    import terrain_rivers as TR
    B2, cs, scan, hf = setup()
    OUT.mkdir(parents=True, exist_ok=True); plan = json.loads(PLAN.read_text()); grid = plan["earth_fit"]["boost_grid_km2"]
    ratio = B2.map_river_ratio(); res = {}
    for group in ("development", "blind"):
        for name in json.loads(B2.PLAN.read_text())["windows"][group]:
            t0 = time.time(); T = B2.truth(name, ratio); land = T["land"]; riv = TR.connected(land, T["rivers"]); T["rivers"] = riv
            row = dict(group=group, truth_capture=capture(T["z"], land, riv), boosts={})
            for b in grid:
                z0, _ = TE.compose(T["h0"], land, riv, B2.DX_KM * 1000, cs, hf, hill_weight=TR.tier1_weight(T["tier"]),
                                   extra=dict(area_m2=True, river_boost_km2=float(b)))
                zc, _ = TR.condition(z0, land, riv, ramp=T["h0"], **scan["chosen"])
                sc = B2.score(T, zc)
                row["boosts"][str(b)] = dict(capture=capture(zc, land, riv), divides_km=sc["M1_divides_km"], slope_ks=sc["M2_slope_ks"])
            res[name] = row
            log(f"{name}: truth {row['truth_capture']:.2f}; " + ", ".join(f"{b}: cap {v['capture']:.2f} div {v['divides_km']:.1f} ks {v['slope_ks']:.3f}"
                                                                  for b, v in row["boosts"].items()) + f" ({time.time() - t0:.0f}s)")
    dev = [n for n in res if res[n]["group"] == "development"]
    m = lambda b, k: float(np.mean([res[n]["boosts"][str(b)][k] for n in dev]))
    err = {b: float(np.mean([abs(res[n]["boosts"][str(b)]["capture"] - res[n]["truth_capture"]) for n in dev])) for b in grid}
    ok = [b for b in grid if m(b, "divides_km") <= 1.10 * m(0, "divides_km") and m(b, "slope_ks") <= 1.10 * m(0, "slope_ks")]
    chosen = min(ok, key=lambda b: err[b])
    chk = [n for n in res if res[n]["group"] == "blind"]
    err_chk = {b: float(np.mean([abs(res[n]["boosts"][str(b)]["capture"] - res[n]["truth_capture"]) for n in chk])) for b in grid}
    out = dict(plan=str(PLAN.relative_to(ROOT)), windows=res, dev_capture_error=err, dev_divides={b: m(b, "divides_km") for b in grid},
               dev_slope_ks={b: m(b, "slope_ks") for b in grid}, admissible=ok, chosen_boost_km2=chosen, check_capture_error=err_chk)
    (OUT / "boost.json").write_text(json.dumps(out, indent=1))
    log("dev capture error", {b: round(v, 3) for b, v in err.items()}, "admissible", ok, "chosen", chosen)
    log("check capture error", {b: round(v, 3) for b, v in err_chk.items()})


if __name__ == "__main__":
    {"boost": boost}[sys.argv[1]]()
