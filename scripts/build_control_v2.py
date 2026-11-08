"""Control map v2 in the atlases (calibration/earth_control_20261106/plan_blind2.json passed for joint365):
food-supported reach from the joint-budget staffed sites plus the painted roads within 2 year-round days of
each polity's staffed sites (reach rule P2), held where the nearest polity's year-round days are <= 2.

    .venv/bin/python -I scripts/build_control_v2.py            # all atlases and climate modes

Writes output/control_v2_20261107/<atlas>_<mode>/control_v2.npz and the map image
atlases/<atlas>/data/[corrected/]settled_control_v2_joint365.webp; the publisher adds the option.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from atlas_set import active  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)
OUT = ROOT / "output/control_v2_20261107"
CASE = "joint365"
HELD_DAYS = 2.0


def build(name, mode):
    from PIL import Image
    from matplotlib.colors import to_rgb
    from polity import control as C, network as N
    from polity.administrative_world import audit_world
    t0 = time.time()
    data = ROOT / "atlases" / name / "data"
    folder = data / ("corrected" if mode == "corrected" else "")
    model = json.loads(gzip.decompress((ROOT / f"output/settlement_fertility_20261106/{name}_{mode}/settled_reach.json.gz").read_bytes()))
    case = next(c for c in model["cases"] if c["id"] == CASE)
    sites, actors = model["sites"], model["actors"]
    nodes = np.array([s["node"] for s in sites]); aidx = np.array([s["actor_index"] for s in sites])
    active = np.array(case["institutional_active"], bool)
    r, meta = audit_world(data.parent, mode)
    land = r["land"]; shape = land.shape
    world, st, cl = r["world"], r["statics"], r["climate"]
    nets = [N.month_network(world, st, cl, m, r["ports"], r["river_places"]) for m in range(12)]
    roads = np.flatnonzero(world["road"].ravel() & land.ravel())
    best = np.full(land.size, np.inf); who = np.full(land.size, -1, np.int16); per_actor = []
    for a in range(len(actors)):
        staffed = nodes[(aidx == a) & active]
        if not len(staffed):
            per_actor.append(dict(actor=actors[a]["name"], staffed=0, roads=0)); continue
        d1 = C.effective_days(np.stack([net.days(staffed) for net in nets]))
        kept = roads[d1[roads] <= HELD_DAYS]
        d2 = C.effective_days(np.stack([net.days(np.unique(np.r_[staffed, kept])) for net in nets]))[:land.size]
        upd = d2 < best
        best = np.where(upd, d2, best); who = np.where(upd, a, who)
        per_actor.append(dict(actor=actors[a]["name"], staffed=int(len(staffed)), roads=int(len(kept))))
        print(f"   {name} {mode} {actors[a]['name']}: {len(staffed)} staffed sites, {len(kept)} road cells kept ({time.time() - t0:.0f}s)", flush=True)
    held = land.ravel() & (best <= HELD_DAYS)
    out = OUT / f"{name}_{mode}"; out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "control_v2.npz", held=held.reshape(shape), actor=np.where(held, who, -1).reshape(shape).astype(np.int16),
                        days=np.where(np.isfinite(best), best, 999.0).reshape(shape).astype(np.float32))
    colors = np.array([to_rgb(a["color"]) for a in actors])
    rgb = np.zeros((land.size, 3)); rgb[:] = [.84, .89, .94]; rgb[land.ravel()] = [.89, .87, .81]
    h = np.flatnonzero(held); rgb[h] = np.array([.89, .87, .81]) * 0.2 + colors[who[h]] * 0.8
    im = Image.fromarray(np.rint(rgb.reshape(shape + (3,)) * 255).astype("u1")).resize((meta["width"], meta["height"]), Image.Resampling.NEAREST)
    im.save(folder / f"settled_control_v2_{CASE}.webp", lossless=True)
    km2 = float(np.mean(r["cell_km"]) ** 2) if np.ndim(r["cell_km"]) else float(r["cell_km"] ** 2)
    summary = dict(atlas=name, climate=mode, case=CASE, rule="P2: staffed sites + painted roads within 2 year-round days of them; held where nearest polity <= 2 days",
                   staffed=int(active.sum()), sites=int(len(sites)), held_land_share=float(held.sum() / land.sum()), held_km2=float(held.sum() * km2), actors=per_actor)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(f"{name} {mode}: held {summary['held_land_share']:.1%} of land ({time.time() - t0:.0f}s)", flush=True)
    return summary


def main():
    done = []
    for name in active(("free_fit", "earth_fit", "whittaker_fit")):
        meta = json.loads((ROOT / "atlases" / name / "data/atlas.json").read_text())
        for mode in ["raw"] + (["corrected"] if meta.get("corrected_climate") else []):
            done.append(build(name, mode))
    (OUT / "summary.json").write_text(json.dumps(done, indent=1))


if __name__ == "__main__":
    main()
