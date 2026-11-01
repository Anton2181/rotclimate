"""Language areas from below, layer 2d: farming hearths from the map alone
(calibration/language_areas_20261101/plan_2d.json).

Earth's nine homelands give a base rate per km2 of land; layer 2b's
productivity index (Miami NPP, 500 km disc mean; AUC 0.78) gives a likelihood
ratio by tercile of Earth's random discs. Applied to the map's own climate:
the expected number of independent hearths, the chance of none, and the
likeliest places.

    python -I scripts/farming_hearths_map.py atlases/earth_fit output/language_areas_20261101/layer2d
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
from scipy.signal import fftconvolve  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from farming_hearths_earth import RADIUS, chord_km, unit_xyz  # noqa: E402
from language_map_preview import packet  # noqa: E402

PLAN = ROOT / "calibration/language_areas_20261101/plan_2d.json"
PLAN_2B = ROOT / "calibration/language_areas_20261101/plan_2b.json"
RUN_2B = ROOT / "output/language_areas_20261101/layer2b"


def earth_calibration():
    """Base rate and tercile likelihood ratios, from layer 2b's own grid, discs and homelands."""
    F = np.load(RUN_2B / "forge_world.npz")
    lat, lon, npp = F["lat"], F["lon"], F["npp"]
    land_km2 = float(np.sum((111.2 ** 2) * np.cos(np.radians(lat))))
    plan = json.loads(PLAN_2B.read_text())
    homes = plan["targets"]["points (lat, lon), placed here at each homeland's centre of early domestication"]
    hp = np.array([p for pts in homes.values() for p in pts])
    xyz = unit_xyz(lat, lon); tree = cKDTree(xyz)
    far = np.ones(len(lat), bool)
    for p in hp:
        far &= np.linalg.norm(xyz - unit_xyz([p[0]], [p[1]]), axis=1) > chord_km(1000.0)
    rand = np.random.default_rng(0).choice(np.flatnonzero(far), 2000, replace=False)
    members = tree.query_ball_point(xyz[rand], chord_km(RADIUS))
    rd = np.array([npp[m].mean() for m in members])
    cuts = np.percentile(rd, [100 / 3, 200 / 3])
    hv = []
    for pts in homes.values():
        pts = np.array(pts)
        hv.append(max(npp[m].mean() for m in tree.query_ball_point(unit_xyz(pts[:, 0], pts[:, 1]), chord_km(RADIUS))))
    hv = np.array(hv)
    counts = np.array([np.sum(hv < cuts[0]), np.sum((hv >= cuts[0]) & (hv < cuts[1])), np.sum(hv >= cuts[1])])
    lr = ((counts + 0.5) / (len(hv) + 1.5)) / (1 / 3)
    return dict(base_per_km2=len(hv) / land_km2, land_km2=land_km2, cuts=cuts.tolist(), homeland_counts=counts.tolist(),
                lr=lr.tolist(), homeland_npp=dict(zip(homes, hv.tolist())), random_npp_pcts=np.percentile(rd, [5, 50, 95]).tolist())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("atlas", type=Path); ap.add_argument("out", type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cal = earth_calibration()
    data = a.atlas / "data"
    A = json.loads((data / "atlas.json").read_text())
    base = data / "corrected" if (data / "corrected" / "atlas.bin").exists() else data
    blob = (base / "atlas.bin").read_bytes()
    s = A["arrays"]["cls"]
    cls = np.frombuffer(blob, dtype=s["dtype"], count=int(np.prod(s["shape"])), offset=s["offset"]).reshape(s["shape"])
    land = cls != 255
    H, _ = packet(data, "harvest")
    npp = np.where(land, np.nan_to_num(H["npp"]), 0.0)
    h, w = land.shape
    cell_km = A["mi_per_px"] * 1.609344 * (A["width"] / w)
    r = int(round(RADIUS / cell_km))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disc = ((yy ** 2 + xx ** 2) <= r * r).astype(float)
    cnt = fftconvolve(land.astype(float), disc, mode="same")
    dm = np.where(land, fftconvolve(npp, disc, mode="same") / np.maximum(cnt, 1e-9), np.nan)
    tercile = np.where(dm < cal["cuts"][0], 0, np.where(dm < cal["cuts"][1], 1, 2))
    lr = np.where(land, np.array(cal["lr"])[tercile], 0.0)
    area = cell_km ** 2
    expected = float(cal["base_per_km2"] * (lr * area)[land].sum())
    land_km2 = float(land.sum() * area)
    # candidates: strongest disc means, at least 1,500 km apart
    # a candidate stands on a landmass of at least 50,000 km2 and its disc
    # holds at least 30 % of a full disc's land cells (not a speck or the edge)
    from scipy import ndimage as ndi
    comp, n = ndi.label(land)
    big = np.isin(comp, 1 + np.flatnonzero(ndi.sum(np.ones_like(comp), comp, np.arange(1, n + 1)) * area >= 5e4))
    ok = land & big & (cnt >= 0.3 * disc.sum())
    order = np.argsort(-np.where(ok, np.nan_to_num(dm, nan=-1), -1).ravel()); kept = []
    step = max(1, int(round(25 / cell_km)))
    for i in order:
        y, x = divmod(int(i), w)
        if not ok[y, x] or (y % step) or (x % step):
            continue
        if all(math.hypot(y - ky, x - kx) * cell_km >= 1500.0 for ky, kx in kept):
            kept.append((y, x))
        if len(kept) >= 3:
            break
    rd_cuts = cal["cuts"]
    cands = [dict(row=int(y), col=int(x), npp_disc=float(dm[y, x]), earth_tercile=int(tercile[y, x]) + 1,
                  above_earth_median=bool(dm[y, x] > cal["random_npp_pcts"][1])) for y, x in kept]
    lat = A["world"]["lat_north"] - (np.arange(h) + 0.5) / h * (A["world"]["lat_north"] - A["world"]["lat_south"])
    for c in cands:
        c["lat"] = float(lat[c["row"]])
    summary = dict(plan=str(PLAN.relative_to(ROOT)), atlas=str(a.atlas), earth=cal, map_land_km2=land_km2,
                   map_tercile_shares=[float(np.mean(tercile[land] == k)) for k in range(3)],
                   expected_hearths=expected, p_no_hearth=float(math.exp(-expected)),
                   expected_hearths_if_all_top_tercile=float(cal["base_per_km2"] * cal["lr"][2] * land_km2),
                   candidates=cands, beyond=A["world"]["beyond"], map_lat=[A["world"]["lat_south"], A["world"]["lat_north"]])
    (a.out / "hearths_map.json").write_text(json.dumps(summary, indent=1))
    np.save(a.out / "npp_disc.npy", dm.astype(np.float32))
    figure(a.out / "hearths_map.png", land, dm, cal, summary, cell_km)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("earth",)}, indent=1))
    print("earth:", json.dumps({k: v for k, v in cal.items() if k != "homeland_npp"}))


def figure(path, land, dm, cal, summ, cell_km):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    h, w = land.shape
    fig, ax = plt.subplots(figsize=(13, 7.0), constrained_layout=True)
    sea = np.array([0.84, 0.89, 0.94])
    ax.imshow(np.where(land, np.nan, 1.0), cmap=ListedColormap([sea]), interpolation="nearest")
    im = ax.imshow(np.where(land, dm, np.nan), cmap="YlGn", vmin=cal["cuts"][0], vmax=np.nanpercentile(dm[land], 99), interpolation="nearest")
    ax.contour(np.where(land, dm, np.nan), levels=[cal["cuts"][1]], colors="#7a5a1a", linewidths=1.0, linestyles="--")
    cb = fig.colorbar(im, ax=ax, shrink=0.6)
    cb.set_label("productivity within 500 km (Miami NPP, g/m²/yr)\ndashed: Earth's top-third threshold (above it: 7 of the 9 homelands)")
    for i, c in enumerate(summ["candidates"], 1):
        ax.plot(c["col"], c["row"], marker="*", ms=20, mfc="#c22f2f", mec="white", mew=1.2)
        ax.annotate(f"{i}", (c["col"], c["row"]), xytext=(9, 9), textcoords="offset points", fontsize=12, weight="bold", color="#5a1010")
    b = summ["beyond"]
    for side, (x, y, ha, va) in {"north": (w / 2 + 260, -14, "center", "bottom"), "south": (w / 2, h + 12, "center", "top"),
                                 "west": (-12, h / 2, "right", "center"), "east": (w + 12, h / 2, "left", "center")}.items():
        name = {"north": "north-west", "south": "south-west"}.get(side, side)   # the atlas's sectors
        ax.text(x, y, f"{name}: {100 * b[side]:.0f} % land beyond", ha=ha, va=va, fontsize=9, color="#333")
    ax.set_xlim(-170, w + 170); ax.set_ylim(h + 60, -60); ax.set_xticks([]); ax.set_yticks([])
    top = 100 * summ["map_tercile_shares"][2]
    ax.set_title(f"Can the map say where farming began? Expected independent hearths here: {summ['expected_hearths']:.2f}, "
                 f"so a {100 * summ['p_no_hearth']:.0f} % chance farming came from beyond the edge.\n"
                 f"(Earth: 9 homelands on {cal['land_km2'] / 1e6:.0f} M km² of land, weighted by productivity, the best tested predictor, AUC 0.78.) "
                 f"{top:.0f} % of the land is in Earth's top third, so places differ little;\nstars: the most productive places on large landmasses, "
                 f"at least 1,500 km apart, if a hearth formed here.", fontsize=10)
    fig.savefig(path, dpi=90)


if __name__ == "__main__":
    main()
