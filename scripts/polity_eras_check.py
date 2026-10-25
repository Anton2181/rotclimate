"""More Earth checks of the polity model with data on disk: China over 1,800
years, and steppe polities against farming states.

    python3 -I scripts/polity_eras_check.py --stage e1   # how seats are spaced: people, area or both
    python3 -I scripts/polity_eras_check.py --stage e2   # the drawn extent's reach from seats, by era
    python3 -I scripts/polity_eras_check.py --stage e3   # riders against walkers at the steppe border

Plan (frozen before results): calibration/polity_20261025/plan_eras.json.
Writes calibration/polity_20261025/eras_{e1,e2,e3}.json.
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
from matplotlib.path import Path as Poly  # noqa: E402

from polity import control as C  # noqa: E402
from polity import earth as E  # noqa: E402
from polity import network as N  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025"
YEARS = ["2AD", "742AD", "1102AD", "1820AD"]


def log(*a):
    print(*a, flush=True)


def poisson_deviance(y, mu):
    y = np.asarray(y, float); mu = np.maximum(np.asarray(mu, float), 1e-9)
    t = np.where(y > 0, y * np.log(np.maximum(y, 1e-12) / mu), 0.0)
    return float(2 * np.sum(t - (y - mu)))


def prefectures(year):
    """Prefecture polygons of one year (Albers, as stored) with people and area,
    and the number of seats inside each."""
    import shapefile
    from han_census_check import albers_forward
    seats = E.han_seats(year)
    X, Y = albers_forward(np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
    pts = np.column_stack([X, Y])
    r = shapefile.Reader(str(E.CACHE / "han_ad2/shp/ResearchArea"), encoding="utf-8")
    rows = []
    taken = np.zeros(len(pts), bool)
    for shp, rec in zip(r.iterShapes(), r.iterRecords()):
        d = rec.as_dict()
        if d["YEAR"] != year:
            continue
        inside = np.zeros(len(pts), bool)
        parts = list(shp.parts) + [len(shp.points)]
        for k in range(len(parts) - 1):
            ring = np.asarray(shp.points[parts[k]:parts[k + 1]])
            inside ^= Poly(ring).contains_points(pts)
        inside &= ~taken; taken |= inside
        rows.append(dict(name=d["PrefNAM"], people=float(d["POP"] or 0), area=float(d["AREA"] or 0),
                         seats=int(inside.sum())))
    return rows, len(seats), int(taken.sum())


def stage_e1(a):
    out = {"eras": {}}
    data = {}
    for y in YEARS:
        rows, n_seats, n_in = prefectures(y)
        rows = [r for r in rows if r["seats"] >= 1 and r["people"] > 0 and r["area"] > 0]
        data[y] = rows
        out["eras"][y] = dict(prefectures=len(rows), seats=int(sum(r["seats"] for r in rows)), seats_total=n_seats,
                              seats_in_polygons=n_in, people_M=sum(r["people"] for r in rows) / 1e6,
                              area_Mkm2=sum(r["area"] for r in rows) / 1e6)
        log(y, out["eras"][y])

    def arrays(y):
        r = data[y]
        return (np.array([x["seats"] for x in r], float), np.array([x["people"] for x in r]),
                np.array([x["area"] for x in r]))

    def design(p, ar, beta):
        return np.exp(beta * np.log(p) + (1 - beta) * np.log(ar))
    ys, ps, ars = arrays("2AD")
    fits = {}
    for beta in np.round(np.arange(0, 1.0001, 0.05), 2):
        x = design(ps, ars, beta)
        c = ys.sum() / x.sum()
        fits[float(beta)] = dict(c=float(c), deviance=poisson_deviance(ys, c * x))
    best_beta = min(fits, key=lambda b: fits[b]["deviance"])
    out["fit_2AD"] = dict(by_beta=fits, best_beta=best_beta)
    log("AD 2 deviance by beta:", {b: round(v["deviance"]) for b, v in fits.items()}, "best", best_beta)
    rules = {"people (beta 1)": 1.0, "area (beta 0)": 0.0, f"mixed (beta {best_beta:g})": best_beta}
    test = {}
    for name, beta in rules.items():
        c = fits[beta]["c"]
        per = {}
        for y in YEARS[1:]:
            yy, pp, aa = arrays(y)
            x = design(pp, aa, beta)
            per[y] = dict(deviance=poisson_deviance(yy, c * x), predicted=float((c * x).sum()), actual=int(yy.sum()),
                          refit_c_ratio=float(yy.sum() / x.sum() / c))
        test[name] = dict(beta=beta, eras=per, summed=float(sum(v["deviance"] for v in per.values())))
        log(name, {y: (round(v["deviance"]), round(v["predicted"]), v["actual"]) for y, v in per.items()},
            "summed", round(test[name]["summed"]))
    winner = min(test, key=lambda k: test[k]["summed"])
    out["test"] = test; out["winner"] = winner; out["winner_beta"] = test[winner]["beta"]
    log("winner:", winner)
    (PLAN / "eras_e1.json").write_text(json.dumps(out, indent=1))


def year_days(nets, sources, offsets=None):
    return C.effective_days(np.stack([n.days(sources, offsets) for n in nets]))


def stage_e2(a):
    from polity_earth_check import apply_sea, balanced_accuracy, auc, load_window, monthly_nets, snap, world_of
    apply_sea()
    g = load_window("han"); world = world_of(g); land = world["land"]; W = land.shape[1]
    out = {}
    for y in YEARS:
        t = time.time()
        seats = E.han_seats(y)
        r, c, ok = snap(g, np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
        places = [(int(a_), int(b_)) for a_, b_, k in zip(r, c, ok) if k]
        ids, _ = E.han_commanderies(g, y)
        inside = (ids >= 0) & land
        st, cl, nets = monthly_nets(g, world, places)
        d = year_days(nets, [p[0] * W + p[1] for p in places]).reshape(land.shape)
        band = land & (d <= 15)
        grid = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
        bas = {f"{h:g}": balanced_accuracy(d, inside, band, h) for h in grid}
        best = max(bas, key=bas.get)
        out[y] = dict(seats=len(places), best_held=float(best), ba=bas[best], auc=auc(d, inside, band), by_held=bas)
        log(y, len(places), "seats: best", best, "days, BA", round(bas[best], 4), f"({time.time() - t:.0f}s)")
        del nets
        (PLAN / "eras_e2.json").write_text(json.dumps(out, indent=1))


def stage_e3(a):
    from polity_earth_check import apply_sea, balanced_accuracy, snap, world_of
    apply_sea()
    path = ROOT / "output/polity_earth/steppe.npz"
    if not path.exists():
        g = E.window(41.0, 106.0, 4200, 2800, 9.0)
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in g.items()})
    with np.load(path) as z:
        g = {k: z[k] for k in z.files}
    for k in ("cell_km", "lat0", "lon0"):
        g[k] = float(g[k])
    world = world_of(g); land = world["land"]; W = land.shape[1]
    st = N.statics(world); cl = N.climate(world, st)
    out = {}
    cases = [("Han AD 2 against the Xiongnu", "2AD", ("Xiongnu", 2)),
             ("Tang AD 742 against the Türgesh", "742AD", ("Türgesh", 742))]
    for label, year, (steppe, sy) in cases:
        t = time.time()
        seats = E.han_seats(year)
        r, c, ok = snap(g, np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
        places = [(int(a_), int(b_)) for a_, b_, k in zip(r, c, ok) if k]
        ids, _ = E.han_commanderies(g, year)
        farm = (ids >= 0) & land
        herd = E.inside_polygons(g, E.cliopatria(steppe, sy)) & land & ~farm
        camps = np.flatnonzero((herd & (g["density"] >= 0.5)).ravel())
        from scipy import ndimage as ndi
        ports = [p for p in places if ndi.binary_dilation(st["water"], iterations=2)[p]]
        near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
        river_places = [p for p in places if near_river[p]]
        d_farm, d_foot, d_ride = [], [], []
        for m in range(12):
            net = N.month_network(world, st, cl, m, ports, river_places)
            d_farm.append(net.days([p[0] * W + p[1] for p in places]))
            d_foot.append(net.days(camps))
            del net
            horse = N.month_network(world, st, cl, m, horse=True)
            d_ride.append(horse.days(camps))
            del horse
        df, dw, dr = (C.effective_days(np.stack(x)).reshape(land.shape) for x in (d_farm, d_foot, d_ride))
        union = farm | herd
        res = {}
        for name, ds in (("walking", dw), ("riding", dr)):
            pred_herd = ds < df
            tpr = (pred_herd & herd).sum() / max(herd.sum(), 1)
            tnr = (~pred_herd & farm).sum() / max(farm.sum(), 1)
            res[name] = dict(balanced_accuracy=float(0.5 * (tpr + tnr)), steppe_right=float(tpr), farm_right=float(tnr),
                             steppe_within_2_days=float((ds[herd] <= 2).mean()))
        out[label] = dict(farm_cells=int(farm.sum()), steppe_cells=int(herd.sum()), camps=int(len(camps)),
                          seats=len(places), **res, passed=bool(res["riding"]["balanced_accuracy"] >
                                                               res["walking"]["balanced_accuracy"]))
        log(label, json.dumps(out[label]), f"({time.time() - t:.0f}s)")
        np.savez_compressed(ROOT / f"output/polity_earth/steppe_{year}.npz", farm=farm, herd=herd, d_farm=df,
                            d_walk=dw, d_ride=dr)
        (PLAN / "eras_e3.json").write_text(json.dumps(out, indent=1))
    out["passed"] = all(v["passed"] for v in out.values() if isinstance(v, dict))
    (PLAN / "eras_e3.json").write_text(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=["e1", "e2", "e3"], required=True)
    a = ap.parse_args()
    {"e1": stage_e1, "e2": stage_e2, "e3": stage_e3}[a.stage](a)


if __name__ == "__main__":
    main()
