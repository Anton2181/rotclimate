"""A1: steppe polities' reach from the model's herding land (calibration/polity_20261025/addendum_herding_a1_20261101.json).

    python -I scripts/polity_herding_a1.py --out output/polity_strength_20261031
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from polity import earth as E  # noqa: E402
from polity import network as N  # noqa: E402
from polity_strength_check import CITIES, base, cached_window, contest, named_sources, year_days  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025/addendum_herding_a1_20261101.json"


def main():
    from polity_earth_check import apply_sea, snap, world_of
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_strength_20261031")
    a = ap.parse_args()
    apply_sea()
    add = json.loads(CITIES.read_text())
    g = cached_window(a.out / "steppe.npz", 41.0, 106.0, 4200, 2800, 9.0)
    world = world_of(g); land = world["land"]; W = land.shape[1]
    st = N.statics(world); cl = N.climate(world, st)
    herding = land & (g["herders"] >= 0.5) & (g["density"] >= 0.5)
    res = dict(addendum=str(PLAN.relative_to(ROOT)), herding_cells=int(herding.sum()), tests={})
    for label, year, (name, sy), centres in [("Han AD 2 against the Xiongnu", "2AD", ("Xiongnu", 2), add["xiongnu_sources"]),
                                             ("Tang AD 742 against the Turgesh", "742AD", ("Türgesh", 742), None)]:
        seats = E.han_seats(year)
        r, c, ok = snap(g, np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
        places = [(int(y), int(x)) for y, x, k in zip(r, c, ok) if k]
        ids, _ = E.han_commanderies(g, year)
        farm = (ids >= 0) & land
        poly = E.inside_polygons(g, E.cliopatria(name, sy)) & land & ~farm
        src = np.flatnonzero(herding.ravel())
        if centres:
            src = np.unique(np.r_[src, named_sources(g, centres)[0]])
        seen = np.flatnonzero((poly & (g["density"] >= 0.5)).ravel())
        d_f, d_h, d_s = year_days(world, st, cl, [np.array([p[0] * W + p[1] for p in places]), src, seen], places)
        F_f, F_h, F_s = (base(world, d, g["cell_km"]) for d in (d_f, d_h, d_s))
        rule = contest(d_f, d_h, F_f, F_h, farm, poly)["0"]
        ref = contest(d_f, d_s, F_f, F_s, farm, poly)["0"]
        res["tests"][label] = dict(herding_sources=int(len(src)), herding_inside_farm=int((herding & farm).sum()),
                                   herding_inside_polygon_share=float((herding & poly).sum() / max(poly.sum(), 1)),
                                   rule=rule, seen_polygon_camps=ref)
        print(label, f"rule {rule['balanced_accuracy']:.3f} (farm right {rule['a_right']:.3f}, steppe right {rule['b_right']:.3f}); "
              f"seen camps {ref['balanced_accuracy']:.3f}", flush=True)
    t = res["tests"].values()
    res["adopted"] = bool(all(x["rule"]["balanced_accuracy"] >= 0.90 and x["rule"]["balanced_accuracy"] >= x["seen_polygon_camps"]["balanced_accuracy"] - 0.03 for x in t))
    (a.out / "herding_a1.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("adopted:", res["adopted"])


if __name__ == "__main__":
    main()
