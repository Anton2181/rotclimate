"""State strength at contested borders (calibration/polity_20261025/plan_strength_20261031.json).

    python -I scripts/polity_strength_check.py --out output/polity_strength_20261031

Fit: the Roman Empire against the Parthian Empire, AD 150 (Roman sources:
Hanson's towns and the Itiner-e roads of AD 150, as test T1; Parthian sources:
seats placed by the map's seat rule on the modelled people inside the
Cliopatria polygon). Tests: Han AD 2 against the Xiongnu and Tang AD 742
against the Turgesh, in the E3 window with E3's sources (walking). A land cell
goes to A when d_A / k_A < d_B / k_B with k_p = (F_p / sqrt(F_A F_B))^gamma,
F_p the modelled people within 2 year-round days of p's own sources.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from polity import control as C  # noqa: E402
from polity import earth as E  # noqa: E402
from polity import network as N  # noqa: E402
from polity import settle  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025/plan_strength_20261031.json"
GAMMAS = [0.0, 0.1, 0.2, 0.3, 0.5]


def cached_window(path, lat0, lon0, w, h, cell):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        g = E.window(lat0, lon0, w, h, cell)
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in g.items()})
    with np.load(path) as z:
        g = {k: z[k] for k in z.files}
    for k in ("cell_km", "lat0", "lon0"):
        g[k] = float(g[k])
    return g


def year_days(world, st, cl, sources_list, places, horse=False):
    """Year-round effective days from each source set, one monthly network at a time."""
    W = world["land"].shape[1]
    ports = [p for p in places if ndi.binary_dilation(st["water"], iterations=2)[p]]
    near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
    river_places = [p for p in places if near_river[p]]
    per = [[] for _ in sources_list]
    for m in range(12):
        net = N.month_network(world, st, cl, m, ports, river_places)
        for i, src in enumerate(sources_list):
            per[i].append(net.days(src))
        del net
    return [C.effective_days(np.stack(x)).reshape(world["land"].shape) for x in per]


def contest(d_a, d_b, F_a, F_b, mask_a, mask_b):
    """Balanced accuracy over the two polities' land for each gamma."""
    rows = {}
    for gamma in GAMMAS:
        mean = np.sqrt(F_a * F_b)
        k_a, k_b = (F_a / mean) ** gamma, (F_b / mean) ** gamma
        to_a = d_a / k_a < d_b / k_b
        right_a = (to_a & mask_a).sum() / max(mask_a.sum(), 1)
        right_b = (~to_a & mask_b).sum() / max(mask_b.sum(), 1)
        rows[f"{gamma:g}"] = dict(balanced_accuracy=float(0.5 * (right_a + right_b)), a_right=float(right_a),
                                  b_right=float(right_b), k_a=float(k_a), k_b=float(k_b))
    return rows


def base(world, d, cell_km):
    return float((world["density"] * cell_km ** 2 * (world["land"] & (d <= 2.0))).sum())


def rome_parthia(out):
    from polity_earth_check import apply_sea, snap, world_of
    apply_sea()
    g = cached_window(out / "rome_parthia.npz", 35.0, 42.0, 3600, 2400, 9.0)
    land = g["land"].astype(bool); W = land.shape[1]
    road = E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land
    towns = E.hanson_towns(150)
    r, c, ok = snap(g, np.array([t["lat"] for t in towns]), np.array([t["lon"] for t in towns]))
    roman_places = [(int(y), int(x)) for y, x, k in zip(r, c, ok) if k]
    rome = E.inside_polygons(g, E.cliopatria("Roman Empire", 150)) & land
    parthia = E.inside_polygons(g, E.cliopatria("Parthian Empire", 150)) & land & ~rome
    world = world_of(g, road)
    st = N.statics(world)
    water_km = ndi.distance_transform_edt(~(st["basin"] > 0) & land) * g["cell_km"]
    seats, _, _ = settle.place_towns(world["density"], land, water_km, np.zeros_like(land), world["elev"], g["cell_km"],
                                     [], allowed=parthia)
    cl = N.climate(world, st)
    rome_src = np.unique(np.r_[[y * W + x for y, x in roman_places], np.flatnonzero(road.ravel())])
    parthia_src = np.array([y * W + x for y, x in seats])
    d_r, d_p = year_days(world, st, cl, [rome_src, parthia_src], roman_places + list(seats))
    F_r, F_p = base(world, d_r, g["cell_km"]), base(world, d_p, g["cell_km"])
    return dict(roman_towns=len(roman_places), road_cells=int(road.sum()), parthian_seats=len(seats),
                roman_cells=int(rome.sum()), parthian_cells=int(parthia.sum()), F_rome=F_r, F_parthia=F_p,
                gammas=contest(d_r, d_p, F_r, F_p, rome, parthia))


def steppe(out):
    from polity_earth_check import apply_sea, snap, world_of
    apply_sea()
    g = cached_window(out / "steppe.npz", 41.0, 106.0, 4200, 2800, 9.0)
    world = world_of(g); land = world["land"]; W = land.shape[1]
    st = N.statics(world); cl = N.climate(world, st)
    res = {}
    for label, year, (name, sy) in [("Han AD 2 against the Xiongnu", "2AD", ("Xiongnu", 2)),
                                    ("Tang AD 742 against the Turgesh", "742AD", ("Türgesh", 742))]:
        t = time.time()
        seats = E.han_seats(year)
        r, c, ok = snap(g, np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
        places = [(int(a), int(b)) for a, b, k in zip(r, c, ok) if k]
        ids, _ = E.han_commanderies(g, year)
        farm = (ids >= 0) & land
        herd = E.inside_polygons(g, E.cliopatria(name, sy)) & land & ~farm
        camps = np.flatnonzero((herd & (g["density"] >= 0.5)).ravel())
        d_f, d_h = year_days(world, st, cl, [np.array([p[0] * W + p[1] for p in places]), camps], places)
        F_f, F_h = base(world, d_f, g["cell_km"]), base(world, d_h, g["cell_km"])
        res[label] = dict(seats=len(places), camps=int(len(camps)), farm_cells=int(farm.sum()), steppe_cells=int(herd.sum()),
                          F_farm=F_f, F_steppe=F_h, gammas=contest(d_f, d_h, F_f, F_h, farm, herd), seconds=round(time.time() - t))
        print(label, json.dumps(res[label]["gammas"]), flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_strength_20261031")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(PLAN.read_text())
    fit = rome_parthia(a.out)
    print("Rome-Parthia", json.dumps(fit["gammas"]), flush=True)
    best = max(GAMMAS, key=lambda gm: (round(fit["gammas"][f"{gm:g}"]["balanced_accuracy"], 6), -gm))
    tests = steppe(a.out)
    key = f"{best:g}"
    gains = [t["gammas"][key]["balanced_accuracy"] - t["gammas"]["0"]["balanced_accuracy"] for t in tests.values()]
    adopted = best > 0 and all(g_ >= 0 for g_ in gains) and float(np.mean(gains)) >= 0.005
    result = dict(plan=str(PLAN.relative_to(ROOT)), fit=fit, gamma_fitted=best, tests=tests,
                  test_gains=gains, adopted=bool(adopted), rule=plan["decision"])
    (a.out / "strength.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(dict(gamma=best, gains=gains, adopted=adopted), indent=1))


if __name__ == "__main__":
    main()
