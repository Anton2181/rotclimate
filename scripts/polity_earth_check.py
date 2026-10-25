"""Polity v2 on Earth: fits on Han China (AD 2) and on Mediterranean sailing
records, tests on the Roman empire (AD 150).

    python3 -I scripts/polity_earth_check.py --stage windows   # build and cache the two Earth windows
    python3 -I scripts/polity_earth_check.py --stage sea       # F5 closure, F6 storminess, river speeds; T5-T7
    python3 -I scripts/polity_earth_check.py --stage fits      # F1-F4, F7 on Han
    python3 -I scripts/polity_earth_check.py --stage tests     # T1-T4, T8 on Rome and points (run once)

Plan (frozen before any result): calibration/polity_20261025/plan.json.
Writes calibration/polity_20261025/{sea,fits,tests}.json; windows are cached
in output/polity_earth/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from polity import control as C  # noqa: E402
from polity import earth as E  # noqa: E402
from polity import network as N  # noqa: E402
from polity import seasons as S  # noqa: E402
from polity import transport as X  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025"
CACHEDIR = ROOT / "output/polity_earth"
VEGETIUS = ["closed", "closed", "uncertain", "uncertain", "uncertain", "open", "open", "open",
            "uncertain", "uncertain", "closed", "closed"]
CAPITAL_HAN = (34.30, 108.90)
# Casson (1951) Table 1: (from, to, days low, days high), sailing season
CASSON = [("Alexandria", "Byzantium", 17, 20), ("Alexandria", "Crete east", 11, 14), ("Alexandria", "Cyprus", 6.5, 6.5),
          ("Alexandria", "Cyrene", 7, 9), ("Alexandria", "Massilia", 58, 78), ("Alexandria", "Myra", 5.5, 7),
          ("Alexandria", "Naples", 50, 70), ("Alexandria", "Rhodes", 7.5, 10), ("Alexandria", "Rome", 53, 73),
          ("Ascalon", "Thessalonica", 13, 19), ("Berytus", "Rhodes", 7, 9), ("Byzantium", "Alexandria", 9, 9),
          ("Byzantium", "Gaza", 10, 10), ("Byzantium", "Rhodes", 5, 5), ("Caesarea", "Rhodes", 10, 10),
          ("Carthage", "Gibraltar", 7, 7), ("Carthage", "Rome", 2, 4), ("Corinth", "Naples", 4.5, 7),
          ("Crete east", "Alexandria", 3, 4), ("Crete west", "Cyrene", 1.5, 2), ("Cyprus", "Alexandria", 2, 2.5),
          ("Cyprus", "Rhodes", 4, 5), ("Cyrene", "Alexandria", 4.5, 4.5), ("Cyrene", "Crete west", 2, 2),
          ("Epidamnus", "Rome", 5, 5), ("Gaza", "Byzantium", 20, 20), ("Gaza", "Rhodes", 10, 12),
          ("Gibraltar", "Carthage", 6, 8), ("Gibraltar", "Rome", 7, 10), ("Massilia", "Alexandria", 20, 30),
          ("Massilia", "Rome", 2, 3), ("Myra", "Alexandria", 2.5, 3.5), ("Naples", "Alexandria", 9, 11),
          ("Naples", "Corinth", 5.5, 8), ("Naples", "Rome", 3, 3), ("Narbo", "Rome", 2.5, 3.5), ("Narbo", "Utica", 5, 5),
          ("Rhodes", "Alexandria", 3.5, 3.5), ("Rhodes", "Berytus", 3, 4), ("Rhodes", "Byzantium", 10, 10),
          ("Rhodes", "Caesarea", 3, 4), ("Rhodes", "Cyprus", 1.5, 2.5), ("Rhodes", "Gaza", 3, 4), ("Rhodes", "Rome", 45, 63),
          ("Rhodes", "Tyre", 4, 4), ("Rome", "Alexandria", 10, 13), ("Rome", "Carthage", 2, 4), ("Rome", "Epidamnus", 4.5, 6.5),
          ("Rome", "Gibraltar", 7, 7), ("Rome", "Massilia", 4.5, 6), ("Rome", "Naples", 1, 1.5), ("Rome", "Narbo", 3, 3),
          ("Rome", "Rhodes", 7, 11), ("Rome", "Tarraco", 4, 4), ("Tarraco", "Rome", 3.5, 5), ("Thessalonica", "Ascalon", 12, 12),
          ("Tyre", "Rhodes", 9, 11)]
PORTS = {"Alexandria": (31.20, 29.88), "Byzantium": (41.05, 29.02), "Crete east": (35.28, 26.30),
         "Crete west": (35.28, 23.55), "Cyprus": (34.75, 32.40), "Cyrene": (32.90, 21.97), "Massilia": (43.29, 5.36),
         "Myra": (36.22, 29.95), "Naples": (40.82, 14.10), "Rhodes": (36.45, 28.23), "Rome": (41.74, 12.25),
         "Ascalon": (31.66, 34.54), "Thessalonica": (40.62, 22.94), "Berytus": (33.90, 35.50), "Gaza": (31.53, 34.43),
         "Caesarea": (32.50, 34.89), "Carthage": (36.85, 10.33), "Gibraltar": (36.13, -5.35), "Corinth": (37.93, 22.89),
         "Epidamnus": (41.31, 19.44), "Narbo": (43.10, 3.10), "Utica": (37.06, 10.06), "Tyre": (33.27, 35.19),
         "Tarraco": (41.11, 1.25), "Messana": (38.19, 15.56)}
# Pliny NH 19.3-4 via Casson's first table: record runs before fair winds
PLINY = [("Rome", "Carthage", 2), ("Messana", "Alexandria", 6.5), ("Rome", "Gibraltar", 7), ("Rome", "Tarraco", 4),
         ("Rome", "Narbo", 3), ("Naples", "Alexandria", 9)]
WINDOWS = {k: v for k, v in json.loads((PLAN / "plan.json").read_text())["earth_windows"].items() if k != "note"}


def log(*a):
    print(*a, flush=True)


def load_window(name):
    path = CACHEDIR / f"{name}.npz"
    with np.load(path) as z:
        g = {k: z[k] for k in z.files}
    for k in ("cell_km", "lat0", "lon0"):
        g[k] = float(g[k])
    return g


def world_of(g, road=None):
    """The window as a polity.network world; narrow straits carved as ferried water."""
    strait = E.straits(g)
    w = dict(elev=g["elev"], land=g["land"].astype(bool) & ~strait, biome=g["biome"],
             swamp=np.zeros(g["land"].shape, bool),
             density=g["density"], cell_km=g["cell_km"], lat=g["lat"], tilt=23.44, T=g["tavg"], Tmax=g["tmax"],
             Tmin=g["tmin"], P=g["prec"], u=g["u"], v=g["v"], wind=g["wind"], sigma=g["sigma"],
             river=g["river"].astype(bool), road=np.zeros(g["land"].shape, bool) if road is None else road,
             ferry=strait, tracks=None)
    return w


def snap(g, lat, lon, to="land"):
    """(row, col) of points snapped to the nearest land (or water) cell."""
    r, c, ok = E.to_cells(g, lat, lon)
    mask = g["land"].astype(bool) if to == "land" else ~g["land"].astype(bool)
    _, (iy, ix) = ndi.distance_transform_edt(~mask, return_indices=True)
    r = np.clip(r, 0, mask.shape[0] - 1); c = np.clip(c, 0, mask.shape[1] - 1)
    return iy[r, c], ix[r, c], ok


def balanced_accuracy(days, inside, band, threshold):
    pred = days <= threshold
    tpr = (pred & inside & band).sum() / max((inside & band).sum(), 1)
    tnr = (~pred & ~inside & band).sum() / max((~inside & band).sum(), 1)
    return 0.5 * (tpr + tnr)


def auc(days, inside, band):
    from scipy.stats import rankdata
    x = -np.nan_to_num(days[band], posinf=1e9); y = inside[band]
    r = rankdata(x); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / max(n1 * n0, 1))


def poisson_deviance(y, mu):
    y = np.asarray(y, float); mu = np.maximum(np.asarray(mu, float), 0.5)
    t = np.where(y > 0, y * np.log(np.maximum(y, 1e-12) / mu), 0.0)
    return float(2 * np.sum(t - (y - mu)))


def spearman(a, b):
    from scipy.stats import spearmanr
    return float(spearmanr(a, b).statistic)


# ------------------------------------------------------------------ stages
def stage_windows(a):
    CACHEDIR.mkdir(parents=True, exist_ok=True)
    for name, w in WINDOWS.items():
        t = time.time()
        g = E.window(w["lat0"], w["lon0"], w["width_km"], w["height_km"], w["cell_km"])
        np.savez_compressed(CACHEDIR / f"{name}.npz", **{k: np.asarray(v) for k, v in g.items()})
        log(name, g["lat"].shape, f"land {g['land'].mean():.2f}", f"{time.time() - t:.0f}s")


def mediterranean(g):
    lat, lon = g["lat"], g["lon"]
    water = ~g["land"].astype(bool)
    med = water & (lon > -5.6) & (lon < 36.5) & (lat > 30) & (lat < 46.5)
    med &= ~((lon > 26.5) & (lat > 40.8))          # Black Sea and the Straits' north
    return med


def stage_sea(a):
    out = {}
    # F6: storminess of the open ocean by latitude and month (for the map's vector-mean winds)
    from rotclimate.earth import _wc
    u, la, lo = E._ncep("uwnd"); v, _, _ = E._ncep("vwnd"); ws, _, _ = E._ncep("wspd")
    sig = np.sqrt(np.maximum(ws ** 2 - u ** 2 - v ** 2, 0))
    LA, LO = np.meshgrid(la, lo, indexing="ij")
    land = np.isfinite(E.sample_global(_wc("elev"), LA, np.where(LO > 180, LO - 360, LO)))
    bins = np.arange(15, 55, 5.0)
    table = []
    for b0 in bins[:-1]:
        sel = ~land & (LA >= b0) & (LA < b0 + 5)
        table.append([float(np.median(sig[m][sel])) for m in range(12)])
    out["F6_sigma_table"] = dict(lat_centres=(bins[:-1] + 2.5).tolist(), sigma=table)
    log("F6 sigma by latitude (rows) and month:", np.round(table, 1).tolist())
    # F5: Vegetius' season in the Mediterranean
    g = load_window("rome")
    med = mediterranean(g)
    msig = [float(g["sigma"][m][med].mean()) for m in range(12)]
    mws = [float(g["wind"][m][med].mean()) for m in range(12)]
    cands = sorted(set(np.round(msig, 3)))
    mids = [cands[0] - 0.1] + [(x + y) / 2 for x, y in zip(cands[:-1], cands[1:])] + [cands[-1] + 0.1]
    best = None
    for su in mids:
        for sc in mids:
            if sc < su:
                continue
            cls = ["closed" if s >= sc else "uncertain" if s >= su else "open" for s in msig]
            hits = sum(x == y for x, y in zip(cls, VEGETIUS))
            if best is None or hits > best[0]:
                best = (hits, su, sc, cls)
    out["F5_closure"] = dict(med_sigma=msig, med_wind=mws, uncertain_sigma=best[1], closed_sigma=best[2],
                             months_right=best[0], classes=best[3], vegetius=VEGETIUS)
    log("F5 Mediterranean sigma", np.round(msig, 2).tolist(), "-> uncertain", round(best[1], 3), "closed",
        round(best[2], 3), f"{best[0]}/12", best[3])
    N.SEA_UNCERTAIN_SIGMA, N.SEA_CLOSED_SIGMA = best[1], best[2]
    # river speeds: ORBIS' static network holds its river edges in one direction only, upstream (towed,
    # 10-31 km/day) except the Nile, sailed upstream before the north wind (70-110 km/day). Upstream is
    # their median off the Nile; downstream, which the file lacks, is set to a ~1 m/s current plus oars
    # (~3.5 km/h) for 10 hours, 70 km/day (a deviation from the plan, reported).
    sites, edges = E.orbis_edges()
    up, nile = [], []
    for e in edges:
        if e["kind"] != "upstream" or e["days"] <= 0:
            continue
        line = np.asarray(e["line"])
        km = float(np.sum(6371 * np.radians(np.hypot(np.diff(line[:, 0]),
                                                      np.diff(line[:, 1]) * np.cos(np.radians(line[:-1, 0]))))))
        on_nile = 24 <= line[:, 0].mean() <= 31.6 and 29 <= line[:, 1].mean() <= 33.5
        (nile if on_nile else up).append(km / e["days"])
    out["river_speeds"] = dict(up_km_day=float(np.median(up)), down_km_day=70.0, n_up=len(up),
                               nile_upstream_under_sail_km_day=float(np.median(nile)) if nile else None,
                               note="downstream not in the ORBIS file; 70 km/day = 1 m/s current + 3.5 km/h oars x 10 h")
    X.RIVER_DOWN_KM_DAY, X.RIVER_UP_KM_DAY = out["river_speeds"]["down_km_day"], out["river_speeds"]["up_km_day"]
    log("rivers (ORBIS):", out["river_speeds"])
    # T5: the Arabian Sea off the Konkan coast
    pt = {k: [float(ndi.map_coordinates(a_[m], [[(la[0] - 16.0) / 2.5], [71.0 / 2.5]], order=1)[0]) for m in range(12)]
          for k, a_ in (("sigma", sig), ("wind", ws))}
    cls = []
    for m in range(12):
        f = float(C.sea_season(np.array(pt["sigma"][m]), np.array(pt["wind"][m]), best[1], best[2]))
        cls.append("closed" if f <= C.CLOSED else "uncertain" if f <= C.UNCERTAIN else "open")
    ok = all(c != "open" for c in cls[5:8]) and all(c == "open" for c in (cls[11], cls[0], cls[1]))
    out["T5_monsoon_sea"] = dict(sigma=pt["sigma"], wind=pt["wind"], classes=cls, passed=bool(ok))
    log("T5 Konkan coast:", cls, "pass" if ok else "FAIL")
    # T6 / T7: sailing days in the Rome window
    world = world_of(g)
    st = N.statics(world); cl = N.climate(world, st)
    cells = {k: snap(g, np.array([la_]), np.array([lo_]), "water")[:2] for k, (la_, lo_) in PORTS.items()}
    idx = {k: int(r[0]) * g["land"].shape[1] + int(c[0]) for k, (r, c) in cells.items()}
    nets = {}
    def sea_net(m):
        if m not in nets:
            nets[m] = C.Network(st["land"].size, [X.sea_edges(st["water"], world["u"][m], world["v"][m], world["wind"][m],
                                                               cl["steadiness"][m], cl["sea"][m], world["cell_km"],
                                                               st["coast_km"])])
        return nets[m]
    season = [4, 5, 6, 7, 8]
    sources = sorted({r[0] for r in CASSON} | {r[0] for r in PLINY})
    model = {}
    for m in season:
        net = sea_net(m)
        for s_ in sources:
            d = net.days([idx[s_]])
            for t_ in PORTS:
                model.setdefault((s_, t_), []).append(float(d[idx[t_]]))
    rows = []
    for s_, t_, lo_, hi_ in CASSON:
        md = float(np.mean(model[(s_, t_)]))
        rows.append(dict(route=f"{s_}-{t_}", casson=(lo_ + hi_) / 2, model=md, ratio=md / ((lo_ + hi_) / 2)))
    cas = np.array([r["casson"] for r in rows]); mod = np.array([r["model"] for r in rows])
    rho = spearman(mod, cas); med = float(np.median(mod / cas))
    out["T6_casson"] = dict(routes=rows, spearman=rho, median_ratio=med, median_abs_log_ratio=float(np.median(np.abs(np.log(mod / cas)))),
                            passed=bool(rho >= 0.6 and 0.67 <= med <= 1.5))
    log(f"T6 Casson: Spearman {rho:.2f}, median ratio {med:.2f}", "pass" if out["T6_casson"]["passed"] else "FAIL")
    for r in rows:
        log(f"   {r['route']:<26} Casson {r['casson']:5.1f}  model {r['model']:6.1f}")
    out["pliny"] = [dict(route=f"{s_}-{t_}", pliny=dd, model_july=float(model[(s_, t_)][2]),
                         model_season=float(np.mean(model[(s_, t_)]))) for s_, t_, dd in PLINY]
    log("Pliny records vs model (July):", [(p["route"], p["pliny"], round(p["model_july"], 1)) for p in out["pliny"]])
    # T7: ORBIS sea edges in July
    net = sea_net(6)
    o_rows = []
    by_src = {}
    for e in edges:
        if e["kind"] not in ("coastal", "overseas"):
            continue
        s, t = sites.get(e["source"]), sites.get(e["target"])
        if not s or not t:
            continue
        rs, cs, oks = snap(g, np.array([s["lat"]]), np.array([s["lon"]]), "water")
        rt, ct, okt = snap(g, np.array([t["lat"]]), np.array([t["lon"]]), "water")
        if not (oks[0] and okt[0]):
            continue
        by_src.setdefault(int(rs[0]) * g["land"].shape[1] + int(cs[0]), []).append(
            (int(rt[0]) * g["land"].shape[1] + int(ct[0]), e))
    for src, lst in by_src.items():
        d = net.days([src])
        for dst, e in lst:
            if np.isfinite(d[dst]) and d[dst] > 0:
                o_rows.append((e["kind"], e["days"], float(d[dst])))
    ok_ = np.array([(r[1], r[2]) for r in o_rows])
    out["T7_orbis"] = dict(n=len(o_rows), spearman=spearman(ok_[:, 1], ok_[:, 0]),
                           median_ratio=float(np.median(ok_[:, 1] / ok_[:, 0])),
                           by_kind={k: dict(n=int(sum(1 for r in o_rows if r[0] == k)),
                                            median_ratio=float(np.median([r[2] / r[1] for r in o_rows if r[0] == k])))
                                    for k in ("coastal", "overseas")})
    log("T7 ORBIS July:", out["T7_orbis"])
    (PLAN / "sea.json").write_text(json.dumps(out, indent=1))


def stage_sea_table(a):
    """F5 on the F6 table (a deviation from the plan, reported): the map's storminess comes from the open-ocean
    table, stormier than the Mediterranean at the same latitude, so the thresholds for the map are refitted the
    same way on the table's row at the Mediterranean's latitude (37.5 N)."""
    s = json.loads((PLAN / "sea.json").read_text())
    t = s["F6_sigma_table"]; row = t["sigma"][t["lat_centres"].index(37.5)]
    vals = sorted(row)
    mids = [vals[0] - 0.1] + [(x + y) / 2 for x, y in zip(vals[:-1], vals[1:])] + [vals[-1] + 0.1]
    best = None
    for su in mids:
        for sc in mids:
            if sc < su:
                continue
            cls = ["closed" if v >= sc else "uncertain" if v >= su else "open" for v in row]
            hits = sum(x == y for x, y in zip(cls, VEGETIUS))
            if best is None or hits > best[0]:
                best = (hits, su, sc, cls)
    s["F5_on_F6_table"] = dict(row_37_5N=row, uncertain_sigma=best[1], closed_sigma=best[2], months_right=best[0],
                               classes=best[3])
    log("F5 on the F6 table:", s["F5_on_F6_table"])
    (PLAN / "sea.json").write_text(json.dumps(s, indent=1))


def apply_sea():
    s = json.loads((PLAN / "sea.json").read_text())
    N.SEA_UNCERTAIN_SIGMA = s["F5_closure"]["uncertain_sigma"]; N.SEA_CLOSED_SIGMA = s["F5_closure"]["closed_sigma"]
    X.RIVER_DOWN_KM_DAY = s["river_speeds"]["down_km_day"]; X.RIVER_UP_KM_DAY = s["river_speeds"]["up_km_day"]
    return s


def monthly_nets(g, world, places, months=range(12)):
    st = N.statics(world); cl = N.climate(world, st)
    ports = X.ports_of(places, st["water"])
    near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
    river_places = [(y, x) for y, x in places if near_river[y, x]]
    nets = []
    for m in months:
        t = time.time()
        nets.append(N.month_network(world, st, cl, m, ports, river_places))
        log(f"   month {m + 1}: {nets[-1].base.nnz:,} edges, {time.time() - t:.0f}s")
    return st, cl, nets


def year_days(nets, sources, offsets=None):
    return C.effective_days(np.stack([n.days(sources, offsets) for n in nets]))


def stage_fits(a):
    apply_sea()
    out = {}
    g = load_window("han")
    world = world_of(g)
    land = world["land"]; W = land.shape[1]
    seats = E.han_seats()
    r, c, ok = snap(g, np.array([s["lat"] for s in seats]), np.array([s["lon"] for s in seats]))
    seats = [dict(s, row=int(y), col=int(x)) for s, y, x, k in zip(seats, r, c, ok) if k]
    log(len(seats), "Han seats in the window")
    ids, rows = E.han_commanderies(g)
    inside = ids >= 0
    places = [(s["row"], s["col"]) for s in seats]
    st, cl, nets = monthly_nets(g, world, places)
    flat = np.array([s["row"] * W + s["col"] for s in seats])
    county = np.array([s["type"] == "County Seat" for s in seats])
    cr, cc, _ = snap(g, np.array([CAPITAL_HAN[0]]), np.array([CAPITAL_HAN[1]]))
    capital = year_days(nets, [int(cr[0]) * W + int(cc[0])]).reshape(land.shape)
    cap_at = capital.ravel()[flat]
    base = year_days(nets, flat).reshape(land.shape)
    band = land & (base <= 15)
    grid_h = json.loads((PLAN / "plan.json").read_text())["fits"]["F1_held_days"]["grid"]
    res = []
    for o in (0.0, 0.25, 0.5, 1.0):
        for lam in (0.0, 0.01, 0.02, 0.04):
            off = o * county + lam * np.nan_to_num(cap_at, posinf=60)
            d = base if (o == 0 and lam == 0) else year_days(nets, flat, off).reshape(land.shape)
            bas = {h: balanced_accuracy(d, inside, band, h) for h in grid_h}
            hb = max(bas, key=bas.get)
            res.append(dict(o_county=o, lam=lam, best_held=hb, ba=bas[hb], auc=auc(d, inside, band), by_held=bas))
            log(f"   o {o:4.2f} lambda {lam:4.2f}: held {hb} BA {bas[hb]:.4f} AUC {res[-1]['auc']:.4f}")
    r0 = res[0]
    best = max(res, key=lambda x: x["ba"])
    adopt = best if best["ba"] - r0["ba"] >= 0.005 else r0
    out["F1_held_days"] = dict(held_days=r0["best_held"], ba=r0["ba"], auc=r0["auc"], by_held=r0["by_held"])
    out["F2_ranks"] = dict(grid=res, best=dict(o_county=best["o_county"], lam=best["lam"], ba=best["ba"]),
                           adopted=dict(o_county=adopt["o_county"], lam=adopt["lam"], held_days=adopt["best_held"]))
    log("F1:", out["F1_held_days"]["held_days"], round(r0["ba"], 4), " F2 adopted:", out["F2_ranks"]["adopted"])
    # context: share of Han people within x days of a seat
    km2 = world["cell_km"] ** 2
    people = np.where(inside, world["density"], 0) * km2
    out["people_within_days"] = {str(x): float(people[base <= x].sum() / max(people.sum(), 1)) for x in (0.5, 1, 1.5, 2, 3)}
    log("people within days:", out["people_within_days"])
    # F3: seat counts per commandery
    from polity.settle import place_towns
    water_km = ndi.distance_transform_edt(~((st["basin"] > 0) | st["water"])) * world["cell_km"]
    coverage = np.array([g["covered"][ids == k].mean() if (ids == k).any() else 0 for k in range(len(rows))])
    ncells = np.bincount(ids[ids >= 0], minlength=len(rows))
    use = (coverage >= 0.9) & (ncells >= 4)
    actual = np.bincount([ids[s["row"], s["col"]] for s in seats if ids[s["row"], s["col"]] >= 0], minlength=len(rows))
    f3 = []
    for sp in (25000, 32000, 40000, 50000, 63000):
        for mr in (40, 60, 90):
            towns, _, _ = place_towns(world["density"], land, water_km, np.zeros(land.shape, bool), world["elev"],
                                      world["cell_km"], [], allowed=inside, seat_people=sp, max_radius_km=mr)
            pred = np.bincount([ids[y, x] for y, x in towns if ids[y, x] >= 0], minlength=len(rows))
            f3.append(dict(seat_people=sp, max_radius_km=mr, deviance=poisson_deviance(actual[use], pred[use]),
                           placed=int(pred[use].sum()), actual=int(actual[use].sum())))
            log(f"   F3 {sp} / {mr} km: deviance {f3[-1]['deviance']:.0f}, placed {f3[-1]['placed']} vs {f3[-1]['actual']}")
    b3 = min(f3, key=lambda x: x["deviance"])
    out["F3_seats"] = dict(grid=f3, best=b3, commanderies=int(use.sum()))
    # F4: refuge terrain
    model_people = np.bincount(ids[ids >= 0], weights=(world["density"] * km2)[ids >= 0], minlength=len(rows))
    relief = np.bincount(ids[ids >= 0], weights=g["relief"][ids >= 0], minlength=len(rows)) / np.maximum(ncells, 1) / 1000
    census = np.array([r_["people"] for r_ in rows])
    u4 = use & (model_people > 0) & (census > 0)
    y = np.log(census[u4] / model_people[u4]); x = relief[u4]
    A = np.column_stack([np.ones_like(x), x]); coef, res_, _, _ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef; s2 = resid @ resid / max(len(y) - 2, 1)
    se = np.sqrt(s2 * np.linalg.inv(A.T @ A)[1, 1])
    k = float(coef[1]); lo_, hi_ = k - 1.98 * se, k + 1.98 * se
    out["F4_refuge"] = dict(k_per_km=k, ci95=[float(lo_), float(hi_)], n=int(u4.sum()), intercept=float(coef[0]),
                            adopted=bool(hi_ < 0), spearman=spearman(x, y))
    log("F4 refuge:", out["F4_refuge"])
    # F7: pastoral share of AD 2 polities (both windows)
    shares = {}
    for wname in ("han", "rome"):
        gw = g if wname == "han" else load_window("rome")
        for name, polys in E.cliopatria_polities(2).items():
            m = E.inside_polygons(gw, polys) & gw["land"].astype(bool) & gw["covered"].astype(bool)
            if m.sum() < 50:
                continue
            ppl = gw["density"][m]
            if ppl.sum() <= 0:
                continue
            sh = float((gw["herders"][m] * ppl).sum() / ppl.sum())
            if name not in shares or m.sum() > shares[name]["cells"]:
                shares[name] = dict(share=sh, cells=int(m.sum()), window=wname)
    lab = json.loads((PLAN / "plan.json").read_text())["fits"]["F7_pastoral"]["labels_fit"]
    best7 = None
    for th in (0.3, 0.4, 0.5, 0.6, 0.7):
        hits = sum(shares[n]["share"] > th for n in lab["mobile"] if n in shares) + \
            sum(shares[n]["share"] <= th for n in lab["settled"] if n in shares)
        margin = min([shares[n]["share"] - th for n in lab["mobile"] if n in shares] +
                     [th - shares[n]["share"] for n in lab["settled"] if n in shares])
        if best7 is None or (hits, margin) > (best7[0], best7[1]):
            best7 = (hits, margin, th)
    out["F7_pastoral"] = dict(shares=shares, threshold=best7[2], right=best7[0])
    log("F7 pastoral shares:", {n: round(v["share"], 2) for n, v in shares.items()}, "threshold", best7[2])
    (PLAN / "fits.json").write_text(json.dumps(out, indent=1))


def stage_tests(a):
    apply_sea()
    fits = json.loads((PLAN / "fits.json").read_text())
    out = {}
    g = load_window("rome")
    land = g["land"].astype(bool); W = land.shape[1]
    roads = E.itinere_roads(150)
    road = E.draw_lines(g, [l for _, l in roads]) & land
    towns = E.hanson_towns(150)
    r, c, ok = snap(g, np.array([t["lat"] for t in towns]), np.array([t["lon"] for t in towns]))
    towns = [dict(t, row=int(y), col=int(x)) for t, y, x, k in zip(towns, r, c, ok) if k]
    log(len(towns), "Roman towns,", int(road.sum()), "road cells")
    inside = E.inside_polygons(g, E.cliopatria("Roman Empire", 150)) & land
    world = world_of(g, road)
    # v1: walking only, snow-free season, held 2 days
    st = N.statics(world)
    eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
    v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], st["paths"])
    flat_t = np.array([t["row"] * W + t["col"] for t in towns])
    srcs = np.unique(np.r_[flat_t, np.flatnonzero(road.ravel())])
    from scipy.sparse.csgraph import dijkstra
    d1 = dijkstra(v1, directed=True, indices=srcs, min_only=True).reshape(land.shape)
    band = land & (d1 <= 15)
    ba1 = balanced_accuracy(d1, inside, band, 2.0); au1 = auc(d1, inside, band)
    # v2
    adopted = fits["F2_ranks"]["adopted"]
    places = [(t["row"], t["col"]) for t in towns]
    st, cl, nets = monthly_nets(g, world, places)
    ranks = [str(t.get("rank")) for t in towns]
    high = np.array([rk in ("1", "2", "1.0", "2.0") for rk in ranks])
    log("Hanson ranks:", {k: ranks.count(k) for k in sorted(set(ranks))})
    off_t = adopted["o_county"] * (~high)
    if adopted["lam"] > 0:
        rr, rc_, _ = snap(g, np.array([41.89]), np.array([12.49]))
        cap = year_days(nets, [int(rr[0]) * W + int(rc_[0])]).ravel()
        off_t = off_t + adopted["lam"] * np.nan_to_num(cap[flat_t], posinf=60)
    road_cells = np.flatnonzero(road.ravel())
    src2 = np.r_[flat_t, road_cells]
    off2 = np.r_[off_t, np.full(len(road_cells), adopted["o_county"])]
    d2 = year_days(nets, src2, off2).reshape(land.shape)
    if fits["F4_refuge"]["adopted"]:
        d2 = d2 - C.CONTROL_DAYS * fits["F4_refuge"]["k_per_km"] * g["relief"] / 1000
    held = adopted["held_days"]
    ba2 = balanced_accuracy(d2, inside, band, held); au2 = auc(d2, inside, band)
    out["T1_roman_extent"] = dict(v1=dict(ba=ba1, auc=au1, held=2.0), v2=dict(ba=ba2, auc=au2, held=held),
                                  passed=bool(ba2 >= ba1), cells=int(band.sum()))
    log("T1 Roman extent:", out["T1_roman_extent"])
    # post hoc (after seeing T1): which part of v2 does it
    d2_raw = year_days(nets, src2, off2).reshape(land.shape)
    foot_nets = [N.month_network(world, st, cl, m, boats=False) for m in range(12)]
    d2_foot = year_days(foot_nets, src2, off2).reshape(land.shape)
    del foot_nets
    diag = {}
    for name_, d_ in (("v1 days", d1), ("v2 days, no refuge", d2_raw), ("v2 days, with refuge", d2),
                      ("v2 seasons on foot, no boats, no refuge", d2_foot)):
        diag[name_] = {f"held {h:g}": balanced_accuracy(d_, inside, band, h) for h in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)}
        diag[name_]["auc"] = auc(d_, inside, band)
    out["T1_roman_extent"]["post_hoc"] = diag
    log("T1 post hoc:", json.dumps(diag))
    (PLAN / "tests.json").write_text(json.dumps(out, indent=1))
    # T2 / T3: towns per block of 22 x 22 cells (~200 km)
    B = 22; ny, nx = land.shape[0] // B, land.shape[1] // B
    def blocks(a_):
        return a_[:ny * B, :nx * B].reshape(ny, B, nx, B).sum((1, 3))
    km2 = g["cell_km"] ** 2
    cnt = np.zeros((ny, nx)); area = np.zeros((ny, nx))
    for t in towns:
        i, j = t["row"] // B, t["col"] // B
        if i < ny and j < nx:
            cnt[i, j] += 1; area[i, j] += t["area_ha"]
    lb = blocks(land.astype(float)); ib = blocks(inside.astype(float))
    okb = (lb >= 0.3 * B * B) & (ib >= 0.5 * lb) & (blocks(g["covered"].astype(float) * land) >= 0.9 * lb)
    ppl = blocks(g["density"] * km2)
    k4 = fits["F4_refuge"]["k_per_km"]
    ppl_r = blocks(g["density"] * km2 * np.exp(k4 * g["relief"] / 1000))
    s_without = spearman(ppl[okb] / lb[okb], area[okb] / lb[okb]); s_with = spearman(ppl_r[okb] / lb[okb], area[okb] / lb[okb])
    out["T2_roman_towns_refuge"] = dict(without=s_without, with_refuge=s_with, blocks=int(okb.sum()),
                                        passed=bool(s_with >= s_without))
    log("T2 refuge:", out["T2_roman_towns_refuge"])
    (PLAN / "tests.json").write_text(json.dumps(out, indent=1))
    from polity.settle import place_towns
    water_km = ndi.distance_transform_edt(~((st["basin"] > 0) | st["water"])) * g["cell_km"]
    b3 = fits["F3_seats"]["best"]
    dev = {}
    for key, sp, mr in (("v1", 40000, 60), ("fit", b3["seat_people"], b3["max_radius_km"])):
        pt, _, _ = place_towns(g["density"], land, water_km, road, g["elev"], g["cell_km"], [], allowed=inside,
                               seat_people=sp, max_radius_km=mr)
        pc = np.zeros((ny, nx))
        for y, x in pt:
            if y // B < ny and x // B < nx:
                pc[y // B, x // B] += 1
        dev[key] = dict(deviance=poisson_deviance(cnt[okb], pc[okb]), placed=int(pc[okb].sum()), actual=int(cnt[okb].sum()))
    out["T3_roman_town_counts"] = dict(**dev, passed=bool(dev["fit"]["deviance"] <= dev["v1"]["deviance"]))
    log("T3 town counts:", out["T3_roman_town_counts"])
    # T4: polity types in AD 117 and 150
    th = fits["F7_pastoral"]["threshold"]
    plan = json.loads((PLAN / "plan.json").read_text())["tests_run_once"]["T4_polity_types"]
    gh = load_window("han")
    shares = {}
    for year in (117, 150):
        for gw in (gh, g):
            for name, polys in E.cliopatria_polities(year).items():
                m = E.inside_polygons(gw, polys) & gw["land"].astype(bool) & gw["covered"].astype(bool)
                if m.sum() < 50 or gw["density"][m].sum() <= 0:
                    continue
                sh = float((gw["herders"][m] * gw["density"][m]).sum() / gw["density"][m].sum())
                key = f"{name} ({year})"
                if key not in shares or m.sum() > shares[key]["cells"]:
                    # post hoc: the area-weighted share too
                    shares[key] = dict(share=sh, cells=int(m.sum()), area_share_post_hoc=float(gw["herders"][m].mean()))
    scored = []
    for key, v in shares.items():
        name = key.rsplit(" (", 1)[0]
        truth = "mobile" if name in plan["mobile"] else "settled" if name in plan["settled"] else None
        if truth:
            pred = "mobile" if v["share"] > th else "settled"
            scored.append(dict(polity=key, share=v["share"], truth=truth, pred=pred))
    acc = float(np.mean([s_["truth"] == s_["pred"] for s_ in scored])) if scored else float("nan")
    out["T4_polity_types"] = dict(threshold=th, scored=scored, accuracy=acc, passed=bool(acc >= 0.8),
                                  unscored={k: round(v["share"], 3) for k, v in shares.items()
                                            if k.rsplit(" (", 1)[0] not in plan["mobile"] + plan["settled"]})
    log("T4 polity types:", acc, [(s_["polity"], round(s_["share"], 2), s_["pred"]) for s_ in scored])
    log("T4 post hoc, area-weighted herders:", {k: (round(v["share"], 2), round(v["area_share_post_hoc"], 2), v["cells"])
                                                for k, v in shares.items()})
    out["T4_polity_types"]["post_hoc_area_share"] = {k: v["area_share_post_hoc"] for k, v in shares.items()}
    (PLAN / "tests.json").write_text(json.dumps(out, indent=1))
    out["T8_seasons"] = seasons_check()
    (PLAN / "tests.json").write_text(json.dumps(out, indent=1))


def point_climate(lat, lon):
    from rotclimate.earth import _wc
    la, lo = np.array([lat]), np.array([lon])
    f = {v: np.stack([E.sample_global(_wc(v, m + 1), la, lo, order=1) for m in range(12)]) for v in ("tavg", "tmax", "tmin", "prec")}
    return S.fields(f["tavg"], f["tmax"], f["tmin"], f["prec"], la)


def seasons_check():
    from rotclimate.earth import _wc
    out = {}
    for name, (la, lo) in {"Moscow": (55.75, 37.62), "Kyiv": (50.45, 30.52), "Beijing": (39.90, 116.40),
                           "Rome": (41.90, 12.50), "Patna": (25.60, 85.10)}.items():
        f = point_climate(la, lo)
        cost = [float((np.maximum(1 + 1.5 * f["snow"][m], 1 + 0.8 * f["mud"][m]) * f["heat"][m])[0]) for m in range(12)]
        out[name] = dict(snow_months=int(f["snow"][:, 0].sum()),
                         mud=[round(float(x), 2) for x in f["mud"][:, 0]],
                         cost=[round(c_, 2) for c_ in cost],
                         worst=[S.MONTHS[m] for m in np.argsort(cost)[::-1][:3]])
        log(name, out[name])
    plan = json.loads((PLAN / "plan.json").read_text())["tests_run_once"]["T8_seasons"]
    out["snow_ok"] = {k: plan["snow_months"][k][0] <= out[k]["snow_months"] <= plan["snow_months"][k][1]
                      for k in plan["snow_months"]}
    out["mud_ok_Kyiv"] = {m: out["Kyiv"]["mud"][S.MONTHS.index(m)] >= 0.5 for m in plan["mud_months_expected"]["Kyiv"]}
    out["monsoon_ok_Patna"] = sorted(out["Patna"]["worst"]) == sorted(plan["monsoon_worst_months"]["Patna"])
    # floods: basin-box runoff peaks
    for name, (la0, la1, lo0, lo1) in {"Nile (Ethiopian highlands)": (7, 14, 35, 40),
                                       "Danube (Alps to the Iron Gates)": (44, 49, 9, 23)}.items():
        la = np.arange(la0, la1, 0.25); lo = np.arange(lo0, lo1, 0.25)
        LA, LO = np.meshgrid(la, lo, indexing="ij")
        f = {v: np.stack([E.sample_global(_wc(v, m + 1), LA, LO) for m in range(12)]) for v in ("tavg", "tmax", "tmin", "prec")}
        ok = np.isfinite(f["tavg"][0])
        ff = S.fields(*(np.nan_to_num(f[v]) for v in ("tavg", "tmax", "tmin", "prec")), LA)
        q = [float(ff["runoff"][m][ok].mean()) for m in range(12)]
        q = np.array(q) / max(np.mean(q), 1e-9)
        out[name] = dict(flow_index=np.round(q, 2).tolist(), peak=[S.MONTHS[m] for m in np.argsort(q)[::-1][:3]])
        log(name, out[name])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=["windows", "sea", "sea_table", "fits", "tests"], required=True)
    a = ap.parse_args()
    {"windows": stage_windows, "sea": stage_sea, "sea_table": stage_sea_table, "fits": stage_fits,
     "tests": stage_tests}[a.stage](a)


if __name__ == "__main__":
    main()
