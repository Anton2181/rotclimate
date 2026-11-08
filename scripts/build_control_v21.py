"""Control map v2.1 in the atlases (calibration/geography_control_20261107/plan_A.json; Earth result in
output/geography_control_20261107/blind.json). The rule the blind test adopted: 'F' = control v2's held land and owner
(scripts/build_control_v2.py), with unheld pockets bounded only by one polity's held land and the sea as its territory:
governable pockets are held, the rest are 'unadministered upland / forest'. (Branch 'C_star', the summed influence of
staffed towns, failed the blind gate on the late-antique pool and is kept here only for the record.)

Cartography (plan A4): hillshade underneath, borders drawn as lines, a minimum mapping unit of 3 cells.

    .venv/bin/python -I scripts/build_control_v21.py            # all atlases and climate modes

Writes output/control_v21_20261107/<atlas>_<mode>/{control_v21.npz, summary.json} and the image
atlases/<atlas>/data/[corrected/]settled_control_v21_joint365.webp; the publisher adds the option.
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from atlas_set import active  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)
OUT = ROOT / "output/control_v21_20261107"
CASE = "joint365"
MMU = 3                                    # minimum mapping unit, cells


def rule():
    cs = json.loads((ROOT / "output/geography_control_20261107/dev.json").read_text())["C_star"]
    return float(cs["tau"]), float(cs["r0"])


def build(name, mode):
    from PIL import Image
    from matplotlib.colors import LightSource, to_rgb
    from polity import network as N
    from polity.administrative_world import audit_world
    import geography_control_a as A
    t0 = time.time(); tau, r0 = rule(); theta = np.exp(-r0 / tau)
    adopt = json.loads((ROOT / "output/geography_control_20261107/blind.json").read_text())["adopt"]
    data = ROOT / "atlases" / name / "data"; folder = data / ("corrected" if mode == "corrected" else "")
    model = json.loads(gzip.decompress((ROOT / f"output/settlement_fertility_20261106/{name}_{mode}/settled_reach.json.gz").read_bytes()))
    case = next(c for c in model["cases"] if c["id"] == CASE)
    sites, actors = model["sites"], model["actors"]
    nodes = np.array([s["node"] for s in sites]); aidx = np.array([s["actor_index"] for s in sites])
    active = np.array(case["institutional_active"], bool)
    r, meta = audit_world(data.parent, mode)
    land = r["land"]; shape = land.shape; world, st, cl = r["world"], r["statics"], r["climate"]
    staffed_n = [int(((aidx == a) & active).sum()) for a in range(len(actors))]
    if adopt == "C_star":
        nets = [N.month_network(world, st, cl, m, r["ports"], r["river_places"]) for m in range(12)]
        G = np.zeros((len(actors), land.size), np.float32)
        for a in range(len(actors)):
            staffed = nodes[(aidx == a) & active]
            if len(staffed):
                G[a] = A.grip(nets, staffed, {"equal": np.ones(len(staffed))}, taus=(tau,), n_cells=land.size)[tau]["equal"]
        best = G.max(0); owner = np.where(best > 0, G.argmax(0), -1)
        held = (land.ravel() & (best >= theta)).reshape(shape); own = np.where(held, owner.reshape(shape), -1)
        strength = np.clip(np.log(np.maximum(best, 1e-9) / theta) / np.log(8.0), 0, 1).reshape(shape)
    else:
        v = np.load(ROOT / f"output/control_v2_20261107/{name}_{mode}/control_v2.npz")
        held = v["held"] & land; own = np.where(held, v["actor"], -1).astype(int)
        strength = np.clip(1.0 - v["days"] / 2.0, 0, 1)            # deeper inside the 2-day line: stronger tint
        best = strength.ravel()
    # minimum mapping unit: drop held specks below MMU cells; fill unheld specks below MMU cells inside one polity
    lab, n = ndi.label(held, structure=np.ones((3, 3)))
    if n:
        size = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)); held &= ~np.isin(lab, np.flatnonzero(size < MMU) + 1)
    own = np.where(held, own, -1)
    # pockets bounded by one polity's held land (and the sea): territory of that polity
    elev = np.asarray(world["elev"], float); km = float(np.mean(r["cell_km"]))
    gy, gx = np.gradient(elev, km * 1000); slope = np.degrees(np.arctan(np.hypot(gy, gx)))
    forest = np.isin(np.asarray(world["biome"]), A.FOREST).astype(float); density = np.asarray(world["density"], float)
    territory = own.copy(); unadmin = np.zeros(shape, bool); holes = np.zeros(shape, bool)
    from population.export import decode_harvest
    import geography_control_a3 as A3m
    A3_AI, A3_EMPTY = A3m.AI_DESERT, A3m.EMPTY_DENSITY
    ai = np.nan_to_num(np.asarray(decode_harvest(folder)[1]["aridity"], float))
    for a in range(len(actors)):
        mine = own == a
        if not mine.any():
            continue
        others = (own >= 0) & ~mine
        pk, plab, ok = A.pockets(mine, land, other=others)
        if not pk.any():
            continue
        # plan_A3 (owner: holes such as deserts): desert or empty pockets stay holes
        hole = np.zeros(shape, bool)
        for k in np.flatnonzero(ok):
            m = plab == k
            if np.median(ai[m]) < A3_AI or np.median(density[m]) < A3_EMPTY:
                hole |= m
        pk = pk & ~hole; holes |= hole
        if not pk.any():
            continue
        gov = A.governable(plab, ok, mine, slope, forest, density)
        small = pk & ~gov
        sl, sn = ndi.label(small, structure=np.ones((3, 3)))
        if sn:                                             # tiny pockets are filled whatever their terrain
            ss = ndi.sum(np.ones_like(sl), sl, index=np.arange(1, sn + 1)); gov |= np.isin(sl, np.flatnonzero(ss < MMU) + 1)
        territory[pk] = a; held |= gov & pk; unadmin |= pk & ~gov
    own = np.where(held, territory, -1)
    out = OUT / f"{name}_{mode}"; out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "control_v21.npz", held=held, owner=own.astype(np.int16), territory=territory.astype(np.int16),
                        unadministered=unadmin, strength=strength.astype(np.float32))
    # cartography: hillshade, actor fill by grip, hatched unadministered pockets, border lines
    colors = np.array([to_rgb(a["color"]) for a in actors])
    W, H = meta["width"], meta["height"]
    def up(a, resample=Image.Resampling.NEAREST):
        return np.asarray(Image.fromarray(a).resize((W, H), resample))
    ap = ROOT / "atlases" / name / "params.json"
    tf = json.loads(ap.read_text()).get("terrain_file", "") if ap.exists() else ""
    hv2 = ROOT / tf if tf else None
    if hv2 is not None and hv2.exists():                   # the eroded height map the atlas was built on
        # relief shading at the source resolution (1.84 km), resized to the image if needed
        zv = np.load(hv2)["z"].astype(float)
        dxs = 1.143 * 1609.344
        shade_src = LightSource(azdeg=315, altdeg=45).hillshade(zv, vert_exag=6, dx=dxs, dy=dxs)
        shade_up = np.asarray(Image.fromarray((np.clip(shade_src, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.Resampling.BILINEAR)) / 255.0
    else:
        shade = LightSource(azdeg=315, altdeg=45).hillshade(np.where(land, elev, 0.0), vert_exag=25, dx=km * 1000, dy=km * 1000)
        shade_up = up((np.clip(shade, 0, 1) * 255).astype(np.uint8), Image.Resampling.BILINEAR) / 255.0
    land_up = up(land.astype(np.uint8)) > 0
    terr_up = up((territory + 1).astype(np.uint8)) .astype(int) - 1
    held_up = up(held.astype(np.uint8)) > 0
    un_up = up(unadmin.astype(np.uint8)) > 0
    rgb = np.empty((H, W, 3)); rgb[:] = [.84, .89, .94]
    base = np.array([.90, .88, .83]); relief = (0.80 + 0.30 * (shade_up - 0.5))[..., None]
    rgb[land_up] = (base * relief[land_up]).clip(0, 1)
    hu = held_up & (terr_up >= 0)
    alpha = 0.72                                        # flat fill: a grip tint by town re-draws every town as a dot
    rgb[hu] = rgb[hu] * (1 - alpha) + colors[terr_up[hu]] * alpha * relief[hu]
    uu = un_up & (terr_up >= 0)
    yy, xx = np.nonzero(uu); hatch = ((yy + xx) % 7) < 2
    tint = rgb[uu] * 0.75 + colors[terr_up[uu]] * 0.25
    tint[hatch] = tint[hatch] * 0.55 + colors[terr_up[uu]][hatch] * 0.45
    rgb[uu] = tint
    # the owner's painted claims (polity/fields.polity_fills), each assigned to the actor most of its sites belong to:
    # claimed land that no polity holds is tinted lightly in the claimant's colour, with the claim's edge as a fine line
    from polity.fields import polity_fills
    cids, _ = polity_fills(shape)
    site_claim = cids.ravel()[nodes]; claim_actor = {}
    for c in np.unique(site_claim[site_claim > 0]):
        a_ = aidx[(site_claim == c) & (aidx >= 0)]
        if len(a_):
            claim_actor[int(c)] = int(np.bincount(a_).argmax())
    claimant = np.full(shape, -1, int)
    for c, a_ in claim_actor.items():
        claimant[cids == c] = a_
    cl_up = up((claimant + 1).astype(np.uint8)).astype(int) - 1
    cu = land_up & (terr_up < 0) & (cl_up >= 0)
    rgb[cu] = rgb[cu] * 0.80 + colors[cl_up[cu]] * 0.20
    ce = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a, b = cl_up[:H - dy, :W - dx], cl_up[dy:, dx:]
        diff = (a != b) & ((a >= 0) | (b >= 0))
        ce[:H - dy, :W - dx] |= diff; ce[dy:, dx:] |= diff
    ce &= land_up & (terr_up < 0)
    rgb[ce] = rgb[ce] * 0.55 + colors[np.maximum(cl_up[ce], 0)] * 0.45
    # borders: where the territory owner changes (between polities, and territory against unheld land)
    t = np.where(land_up, terr_up, -2)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a, b = t[:H - dy, :W - dx], t[dy:, dx:]
        diff = (a != b) & ((a >= 0) | (b >= 0)) & (a != -2) & (b != -2)
        edge[:H - dy, :W - dx] |= diff; edge[dy:, dx:] |= diff
    rgb[edge] = rgb[edge] * 0.35 + np.array([.18, .17, .16]) * 0.65
    Image.fromarray(np.rint(rgb * 255).astype(np.uint8)).save(folder / f"settled_control_v21_{CASE}.webp", lossless=True)
    km2 = km ** 2
    summary = dict(atlas=name, climate=mode, case=CASE, adopted=adopt,
                   rule=("summed influence of staffed towns (plan_A C*)" if adopt == "C_star" else "control v2 (P2)") + "; pockets bounded by one polity are its territory",
                   staffed=int(active.sum()), sites=int(len(sites)), held_land_share=float(held.sum() / land.sum()),
                   territory_land_share=float((territory >= 0).sum() / land.sum()), unadministered_share=float(unadmin.sum() / land.sum()),
                   desert_hole_share=float(holes.sum() / land.sum()),
                   claimed_unheld_share=float((land & (territory < 0) & (claimant >= 0)).sum() / land.sum()),
                   held_km2=float(held.sum() * km2), actors=[dict(actor=a["name"], staffed=n) for a, n in zip(actors, staffed_n)])
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(f"{name} {mode}: held {summary['held_land_share']:.1%}, territory {summary['territory_land_share']:.1%}, "
          f"unadministered {summary['unadministered_share']:.1%} ({time.time() - t0:.0f}s)", flush=True)
    return summary


def main():
    done = []
    names = sys.argv[1:] or active(["free_fit", "earth_fit", "whittaker_fit"])
    for name in names:
        meta = json.loads((ROOT / "atlases" / name / "data/atlas.json").read_text())
        for mode in ["raw"] + (["corrected"] if meta.get("corrected_climate") else []):
            done.append(build(name, mode))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(done, indent=1))


if __name__ == "__main__":
    main()
