"""Figures for the Earth control round 2 (development) and the blind pools' inputs (no outcome).

    .venv/bin/python -I scripts/plot_earth_control_round2.py round2
    .venv/bin/python -I scripts/plot_earth_control_round2.py pools
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/earth_control_20261106"
SEA, LAND, MISS, OUTSIDE, HELD = [0.84, 0.89, 0.94], [0.93, 0.92, 0.88], [0.96, 0.78, 0.62], [0.55, 0.62, 0.85], [0.45, 0.62, 0.38]


def paint(land, inside, band, held):
    img = np.ones(land.shape + (3,)) * np.array(SEA)
    img[land] = LAND
    img[land & inside & ~held] = MISS
    img[land & ~inside & held] = OUTSIDE
    img[land & inside & held] = HELD
    img[land & ~band] = img[land & ~band] * 0.94
    return img


def round2():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    res = json.loads((OUT / "round2/results_round2.json").read_text())
    cols = [("legacy_0", None, "Transport only (legacy_0)"),
            ("fert_bare_fixed", "P0", "Bare fallow · round 1\n(fixed rural claim, every-month patrols)"),
            ("fert_bare_scaled", "P0", "Bare fallow · scaled rural claim\n(every-month patrols)"),
            ("fert_bare_scaled", "P2", "Bare fallow · scaled claim · P2\n(staffed towns + their roads)"),
            ("joint365_scaled", "P2", "Joint budget · P2")]
    fig, axes = plt.subplots(2, 5, figsize=(22, 8.8))
    for i, name in enumerate(("rome", "han")):
        z = dict(np.load(OUT / f"round2/{name}.npz"))
        land, inside, band = z["land"], z["inside"], z["band"]
        r = res["regions"][name]
        for j, (case, rule, title) in enumerate(cols):
            held = (land & (z["year_days"] <= 2.0)) if case == "legacy_0" else z[f"{case}__{rule}"]
            ba = r["legacy_0"]["ba"] if case == "legacy_0" else r[case][rule]["ba"]
            staffed = "" if case == "legacy_0" else f" · staffed {r[case]['staffed_share']:.0%}"
            ax = axes[i, j]; ax.imshow(paint(land, inside, band, held), interpolation="nearest"); ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(f"{'Rome AD 150' if name == 'rome' else 'Han AD 2'} · {title}\nbalanced accuracy {ba:.3f}{staffed}", fontsize=9.5)
    fig.legend(handles=[Patch(color=HELD, label="held, inside the historical extent"), Patch(color=MISS, label="claimed, not held"),
                        Patch(color=OUTSIDE, label="held, outside the extent")], loc="lower center", ncol=3, fontsize=10, frameon=False)
    fig.suptitle("Earth control round 2 (development data): the scaled rural claim feeds the towns again, and roads maintained from staffed towns "
                 "close the gaps (Rome 0.835 vs transport-only 0.820)", fontsize=11.5)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95)); fig.savefig(OUT / "round2/earth_control_round2.png", dpi=90)
    print("figure", OUT / "round2/earth_control_round2.png")


def pools():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import polity_earth_check as P
    import earth_control_blind as B
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.6))
    for ax, pool, title in zip(axes, ("B1", "B2"), ("B1 · Hellenistic settlements (Pleiades) · states in 200 BC", "B2 · Neo-Assyrian settlements · states in 700 BC")):
        g = dict(np.load(B.OUT / f"{pool}_window.npz"))
        for k in ("cell_km", "lat0", "lon0"):
            g[k] = float(g[k])
        land = g["land"].astype(bool)
        inside, n = B.target(g, B.POOLS[pool]["year"]); inside &= land
        pts = B.pleiades(B.POOLS[pool]["tags"])
        r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
        img = np.ones(land.shape + (3,)) * np.array(SEA); img[land] = LAND; img[inside] = [0.80, 0.86, 0.74]
        ax.imshow(img, interpolation="nearest"); ax.scatter(c[ok], r[ok], s=2.5, c="#5a3d1e", linewidths=0)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_title(f"{title}\n{int(ok.sum())} settlements · {n} state polygons (green)", fontsize=10)
    fig.suptitle("Blind Earth control pools (inputs only; frozen in plan_blind.json before any outcome)", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(B.OUT / "blind_pools_inputs.png", dpi=95)
    print("figure", B.OUT / "blind_pools_inputs.png")


if __name__ == "__main__":
    {"round2": round2, "pools": pools}[sys.argv[1]]()
