"""Why the western Mediterranean sails too slowly (diagnostic; reports/POLITY_SEASONS_20261031.md, "not addressed").

    python -I scripts/polity_sea_west.py --out output/polity_sea_west_20261031

Casson's (1951) western passages come out 2-4x too slow in test T6 and the
long passages upwind to Rome ~2.5x too fast. For each route, in June and
July, the fastest sea path of the model's sailing network is traced and its
days split into what sets them: path length against the great circle, the
wind factor (mean scalar wind / 6 m/s, at least 0.25), the point of sailing
(polar, blended with its mean by the wind's steadiness), the coastal factor
(0.7 within 20 km of land) and the season factor. Diagnostic only: Casson's
times were seen in T6, so nothing here is fitted or adopted.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy.sparse import csr_matrix  # noqa: E402
from scipy.sparse.csgraph import dijkstra  # noqa: E402

import polity_earth_check as P  # noqa: E402
from polity import earth as E  # noqa: E402
from polity import network as N  # noqa: E402
from polity import transport as X  # noqa: E402

ROUTES = [("Rome", "Narbo"), ("Narbo", "Rome"), ("Rome", "Massilia"), ("Massilia", "Rome"), ("Rome", "Carthage"),
          ("Carthage", "Rome"), ("Rome", "Tarraco"), ("Tarraco", "Rome"), ("Rome", "Gibraltar"), ("Gibraltar", "Rome"),
          ("Rome", "Naples"), ("Rome", "Alexandria"), ("Alexandria", "Rome"), ("Rhodes", "Rome"), ("Alexandria", "Massilia"),
          ("Alexandria", "Naples"), ("Byzantium", "Alexandria"), ("Alexandria", "Byzantium")]


def great_circle(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (*a, *b))
    return 6371 * 2 * np.arcsin(np.sqrt(np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_sea_west_20261031")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    P.apply_sea()
    path = P.CACHEDIR / "rome.npz"
    if not path.exists():
        P.CACHEDIR.mkdir(parents=True, exist_ok=True)
        w = P.WINDOWS["rome"]
        g = E.window(w["lat0"], w["lon0"], w["width_km"], w["height_km"], w["cell_km"])
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in g.items()})
    g = P.load_window("rome")
    world = P.world_of(g); st = N.statics(world); cl = N.climate(world, st)
    water = st["water"]; h, w = water.shape; ck = world["cell_km"]
    cells = {k: P.snap(g, np.array([la]), np.array([lo]), "water")[:2] for k, (la, lo) in P.PORTS.items()}
    idx = {k: int(r[0]) * w + int(c[0]) for k, (r, c) in cells.items()}
    casson = {(s, t): (lo + hi) / 2 for s, t, lo, hi in P.CASSON}
    coastal = st["coast_km"] <= X.COAST_KM
    out = dict(note=__doc__.split("\n\n")[1].replace("\n", " "), months={}, routes=[])
    for m in (5, 6):
        u, v, wind = world["u"][m], world["v"][m], world["wind"][m]
        steady, season = cl["steadiness"][m], cl["sea"][m]
        src, dst, days = X.sea_edges(water, u, v, wind, steady, season, ck, st["coast_km"])
        G = csr_matrix((days, (src, dst)), shape=(h * w, h * w))
        speed = np.hypot(u, v)
        ex = np.where(speed > 1e-6, u / np.maximum(speed, 1e-6), 0.0); ny = np.where(speed > 1e-6, v / np.maximum(speed, 1e-6), 0.0)
        med = P.mediterranean(g)
        out["months"][m + 1] = dict(med_wind_mean=float(wind[med].mean()), med_vector_mean=float(speed[med].mean()),
                                    med_steadiness=float(steady[med].mean()),
                                    west_wind=float(wind[med & (g["lon"] < 16)].mean()), east_wind=float(wind[med & (g["lon"] >= 16)].mean()),
                                    west_steadiness=float(steady[med & (g["lon"] < 16)].mean()),
                                    east_steadiness=float(steady[med & (g["lon"] >= 16)].mean()))
        for s_, t_ in ROUTES:
            d, pred = dijkstra(G, directed=True, indices=idx[s_], return_predecessors=True)
            node, seq = idx[t_], []
            while node != idx[s_] and node >= 0:
                seq.append(node); node = pred[node]
            seq = [idx[s_]] + seq[::-1]
            ys, xs = np.unravel_index(np.array(seq), (h, w))
            steps = np.hypot(np.diff(ys), np.diff(xs)) * ck
            km = float(steps.sum())
            dy, dx = np.diff(ys), np.diff(xs)
            mid = lambda f: 0.5 * (f[ys[:-1], xs[:-1]] + f[ys[1:], xs[1:]])
            cos_t = (dx * mid(ex) - dy * mid(ny)) / np.maximum(np.hypot(dx, dy), 1e-9)
            theta = np.degrees(np.arccos(np.clip(cos_t, -1, 1)))
            s = np.clip(mid(steady), 0, 1)
            hh = s * X.polar(theta) + (1 - s) * X.POLAR_MEAN
            gg = np.clip(mid(wind) / X.FULL_WIND, X.LIGHT_AIRS, 1.0)
            cc = np.where(coastal[ys[:-1], xs[:-1]] & coastal[ys[1:], xs[1:]], X.COAST_FACTOR, 1.0)
            ss = np.minimum(season[ys[:-1], xs[:-1]], season[ys[1:], xs[1:]])
            wt = steps / max(km, 1e-9)
            gc = great_circle(P.PORTS[s_], P.PORTS[t_])
            row = dict(route=f"{s_}-{t_}", month=m + 1, casson=casson.get((s_, t_)), model_days=float(d[idx[t_]]),
                       path_km=km, great_circle_km=float(gc), detour=km / gc,
                       km_day_made=km / max(float(d[idx[t_]]), 1e-9), fair_km_day=X.SAIL_FAIR_KNOTS * X.KNOT_KM_H * 24,
                       wind_factor=float((wt * gg).sum()), polar=float((wt * hh).sum()), coastal_factor=float((wt * cc).sum()),
                       coastal_share=float((wt * (cc < 1)).sum()), season_factor=float((wt * ss).sum()),
                       mean_wind=float((wt * mid(wind)).sum()), downwind_share=float((wt * (theta < 60)).sum()),
                       upwind_share=float((wt * (theta > 120)).sum()), steadiness=float((wt * s).sum()))
            out["routes"].append(row)
            if m == 6:
                c = f"{row['casson']:5.1f}" if row["casson"] else "    -"
                print(f"{row['route']:<22} Casson {c} model {row['model_days']:5.1f} d | {km:5.0f} km (x{row['detour']:.2f}) "
                      f"{row['km_day_made']:4.0f} km/d | wind {row['mean_wind']:.1f} m/s g {row['wind_factor']:.2f} polar {row['polar']:.2f} "
                      f"coast {row['coastal_share']:.2f} season {row['season_factor']:.2f} up {row['upwind_share']:.2f}", flush=True)
    print(json.dumps(out["months"], indent=1))
    (a.out / "sea_west.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
