"""Language areas from below, layer 2: how farming spreads, tested on Earth.

Frozen plan: calibration/language_areas_20261101/plan_2.json.

Four models of when farming reached 727 dated early-farming sites of the Near
East and Europe (Pinhasi, Fort & Ammerman 2005, Supporting Information 1):
  M0  great-circle distance from the origin;
  M1  the paper's own shortest-path distance;
  M2  travel time over terrain (Tobler) with sea crossings at kappa x flat land;
  M3  M2 slowed where wheat and barley do badly, by max(s, 0.05)^beta, s from
      scripts/land_people.py's crop rules on WorldClim (the map's own rules).
Each is a straight line, date = a - b x distance, with the origin (of the
paper's 37 candidates) and parameters fitted on six of seven regional blocks
and scored on the seventh.

Inputs (data/cache is not committed): data/cache/pinhasi2005/st001.xls,
WorldClim 2.1 5 arc-min zips and Natural Earth rivers (as land_people_earth).

    python -I scripts/farming_spread_earth.py --out output/language_areas_20261101/layer2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import land_people_earth as lpe  # noqa: E402

PLAN = ROOT / "calibration" / "language_areas_20261101" / "plan_2.json"
SITES = ROOT / "data" / "cache" / "pinhasi2005" / "st001.xls"
WINDOW = dict(lat=(24.0, 62.0), lon=(-12.0, 56.0))
COARSE = 3                       # 5 arc-min cells per 0.25 deg cell
R_KM = 6371.0
FLAT = 6.0 * np.exp(-3.5 * 0.05)  # Tobler on the flat, km/h
S_MIN = 0.05
KAPPAS = (1.0, 1.5, 2.0, 3.0, 5.0, 10.0)
BETAS = (0.25, 0.5, 0.75, 1.0, 1.5)
REGIONS = ("Near East", "Anatolia", "Europe", "Iberia")
BLOCKS = {
    "Near East & Anatolia": {"Turkey@Anatolia", "Israel", "Jordan", "Syria", "Iraq", "Iran", "Lebanon", "Egypt", "Cyprus"},
    "Southeast Europe": {"Greece", "Thrace", "Turkey@Europe", "Republic of Macedon", "Bulgaria", "Romania", "Serbia",
                         "Yugoslavia", "Croatia", "Bosnia-Herzegovina", "Bosnia?", "Hungary"},
    "Italy": {"Italy"},
    "Iberia & France": {"Spain", "Portugal", "Andora", "France"},
    "Central Europe": {"Austria", "Switzerland", "Germany", "Czech", "Czech Republic", "Slovakia", "Solvakia", "Poland",
                       "Lithuania", "Belgium", "Netherlands"},
    "Britain & Ireland": {"Great Britain", "Ireland"},
    "Denmark & Sweden": {"Denmark", "Sweden"},
}


# ---------------------------------------------------------------- data
def read_sites():
    import xlrd
    sh = xlrd.open_workbook(str(SITES)).sheet_by_index(0)
    hdr = sh.row_values(1)
    rows = [sh.row_values(r) for r in range(2, sh.nrows)]
    origin_names = hdr[14:51]
    coords = {}
    for r in rows:
        if r[3] in ("Anatolia/Syria point", "Spain/France point") or r[0] == "centre":
            coords[r[3].replace(" point", " Point")] = (float(r[1]), float(r[2]))
    alias = {"Çatal Höyuk": "Çatal Höyük", "AliKosh": "Ali Kosh", "Amm. & CS": "Ammerman & CS"}
    origins = [(n, coords[alias.get(n, n)]) for n in origin_names]
    sites = []
    for r in rows:
        if r[0] != "SITE" or r[4] not in REGIONS or r[11] == "":
            continue
        key = f"{r[5]}@{r[4]}" if r[5] == "Turkey" else r[5]
        block = next(b for b, members in BLOCKS.items() if key in members)
        m1 = [float(r[14 + i]) if r[14 + i] != "" else np.nan for i in range(len(origin_names))]
        sites.append(dict(name=r[3], country=r[5], lat=float(r[1]), lon=float(r[2]), date=float(r[11]),
                          block=block, m1=m1))
    return sites, origins


def great_circle(lat1, lon1, lat2, lon2):
    a, b, c, d = map(np.radians, (lat1, lon1, lat2, lon2))
    return R_KM * np.arccos(np.clip(np.sin(a) * np.sin(c) + np.cos(a) * np.cos(c) * np.cos(b - d), -1, 1))


def crop_field(cache: Path):
    """s and elevation on the 0.25 deg grid; the 5 arc-min crop run is cached."""
    f = cache / "earth.npz"
    if not f.exists():
        lpe.WINDOW = WINDOW
        cache.mkdir(parents=True, exist_ok=True)
        lpe.compute(cache)
    z = np.load(f)
    lpe.WINDOW = WINDOW
    rs, cs = lpe.window_slices()
    elev = lpe.wc("elev")[rs, cs]
    land5 = z["land"]
    s5 = np.where(land5, np.fmax(z["kcal_wheat"], z["kcal_barley"]) * z["arable"], np.nan)
    ref = float(np.nanpercentile(s5[land5], 95))
    s5 = np.clip(s5 / ref, 0, 1)
    h, w = land5.shape[0] // COARSE, land5.shape[1] // COARSE

    def blocks(a):
        return a[:h * COARSE, :w * COARSE].reshape(h, COARSE, w, COARSE)
    lf = blocks(land5.astype(float)).mean((1, 3))
    land = lf >= 0.5
    with np.errstate(invalid="ignore"):
        s = np.nanmean(blocks(s5), axis=(1, 3))
        e = np.nanmean(blocks(np.where(land5, elev, np.nan)), axis=(1, 3))
    s = np.where(land, np.nan_to_num(s), 0.0)
    e = np.where(land, np.nan_to_num(e), 0.0)
    step = COARSE / lpe.RES
    lat = WINDOW["lat"][1] - (np.arange(h) + 0.5) * step
    lon = WINDOW["lon"][0] + (np.arange(w) + 0.5) * step
    return dict(s=s, elev=e, land=land, lat=lat, lon=lon, step=step, ref=ref)


# ---------------------------------------------------------------- graph
def graph(g, kappa, beta=None):
    s, elev, land, lat, step = g["s"], g["elev"], g["land"], g["lat"], g["step"]
    h, w = land.shape
    idx = np.arange(h * w).reshape(h, w)
    f = np.maximum(s, S_MIN) ** beta if beta is not None else np.ones_like(s)
    rows, cols, cost = [], [], []
    dy_km = R_KM * np.radians(step)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        ys = np.arange(0, h - dy)
        xa = np.arange(max(0, -dx), w - max(0, dx))
        a = idx[np.ix_(ys, xa)]
        b = idx[np.ix_(ys + dy, xa + dx)]
        la = np.radians(lat[ys] - 0.5 * dy * step)[:, None]
        dist = np.sqrt((R_KM * np.radians(step) * np.cos(la) * abs(dx)) ** 2 + (dy_km * dy) ** 2) * np.ones(a.shape)
        ea, eb = elev[np.ix_(ys, xa)], elev[np.ix_(ys + dy, xa + dx)]
        both = land[np.ix_(ys, xa)] & land[np.ix_(ys + dy, xa + dx)]
        fab = 0.5 * (f[np.ix_(ys, xa)] + f[np.ix_(ys + dy, xa + dx)])
        slope = (eb - ea) / 1000.0 / np.maximum(dist, 1e-6)
        sea = kappa * dist / FLAT
        t_ab = np.where(both, dist / (6.0 * np.exp(-3.5 * np.abs(slope + 0.05))) / fab, sea)
        t_ba = np.where(both, dist / (6.0 * np.exp(-3.5 * np.abs(-slope + 0.05))) / fab, sea)
        rows += [a.ravel(), b.ravel()]
        cols += [b.ravel(), a.ravel()]
        cost += [t_ab.ravel(), t_ba.ravel()]
    n = h * w
    return coo_matrix((np.concatenate(cost), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()


def cell_of(g, lat, lon, land_only=True):
    h, w = g["land"].shape
    y = int(np.floor((WINDOW["lat"][1] - lat) / g["step"]))
    x = int(np.floor((lon - WINDOW["lon"][0]) / g["step"]))
    if not (0 <= y < h and 0 <= x < w):
        return None
    if land_only and not g["land"][y, x]:
        ys, xs = np.nonzero(g["land"])
        k = np.argmin((ys - y) ** 2 + ((xs - x) * np.cos(np.radians(lat))) ** 2)
        y, x = ys[k], xs[k]
    return y * w + x


# ---------------------------------------------------------------- fit
def line_fit(d, t):
    A = np.stack([np.ones_like(d), d], 1)
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    return coef


def select(D, t, train):
    """D: (settings, origins, sites) distances. Best (setting, origin, coef) on train."""
    best = (np.inf, None)
    for i in range(D.shape[0]):
        for j in range(D.shape[1]):
            d = D[i, j]
            ok = train & np.isfinite(d)
            if ok.sum() < train.sum() * 0.99:
                continue
            c = line_fit(d[ok], t[ok])
            rmse = float(np.sqrt(np.mean((t[ok] - (c[0] + c[1] * d[ok])) ** 2)))
            if rmse < best[0]:
                best = (rmse, (i, j, c))
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="output/language_areas_20261101/layer2")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    plan = json.loads(PLAN.read_text())
    sites, origins = read_sites()
    g = crop_field(out / "crops5")
    # a site whose coordinates fall outside the climate window cannot be
    # placed on the graph; it is left out of every model alike
    outside = [x["name"] for x in sites if cell_of(g, x["lat"], x["lon"]) is None]
    sites = [x for x in sites if cell_of(g, x["lat"], x["lon"]) is not None]
    print(f"{len(sites)} sites ({len(outside)} outside the window: {outside}), {len(origins)} origins", flush=True)
    t = np.array([s["date"] for s in sites])
    blocks = np.array([s["block"] for s in sites])
    slat = np.array([s["lat"] for s in sites]); slon = np.array([s["lon"] for s in sites])

    print(f"crop field {g['land'].shape} ({time.time() - t0:.0f}s)", flush=True)
    site_cells = np.array([cell_of(g, la, lo) for la, lo in zip(slat, slon)])
    org_cells = [cell_of(g, la, lo, land_only=False) for _, (la, lo) in origins]

    D = {}
    D["M0"] = np.array([[great_circle(slat, slon, la, lo) for _, (la, lo) in origins]])
    D["M1"] = np.array([np.array([s["m1"] for s in sites]).T])
    srcs = [c for c in org_cells if c is not None]
    use = [i for i, c in enumerate(org_cells) if c is not None]

    def travel(kappa, beta):
        G = graph(g, kappa, beta)
        dist = dijkstra(G, directed=True, indices=srcs, min_only=False)
        full = np.full((len(origins), len(sites)), np.nan)
        full[use] = dist[:, site_cells] * FLAT       # in flat-land km
        return full
    D["M2"] = np.array([travel(k, None) for k in KAPPAS])
    settings = {"M0": [{}], "M1": [{}], "M2": [dict(kappa=k) for k in KAPPAS]}
    m3, s3 = [], []
    for k in KAPPAS:
        for b in BETAS:
            m3.append(travel(k, b)); s3.append(dict(kappa=k, beta=b))
    D["M3"] = np.array(m3); settings["M3"] = s3
    print(f"travel times ({time.time() - t0:.0f}s)", flush=True)

    names = list(BLOCKS)
    res = {}
    for m in ("M0", "M1", "M2", "M3"):
        pred = np.full(len(sites), np.nan)
        per = {}
        for b in names:
            test = blocks == b
            rmse_tr, (i, j, c) = select(D[m], t, ~test)
            pred[test] = c[0] + c[1] * D[m][i, j][test]
            per[b] = dict(rmse=float(np.sqrt(np.nanmean((t[test] - pred[test]) ** 2))), n=int(test.sum()),
                          origin=origins[j][0], setting=settings[m][i], km_per_year=float(-1 / c[1]) if c[1] < 0 else None)
        ok = np.isfinite(pred)
        rmse_all, (i, j, c) = select(D[m], t, np.ones(len(sites), bool))
        res[m] = dict(heldout_rmse=float(np.sqrt(np.mean((t[ok] - pred[ok]) ** 2))),
                      heldout_r=float(np.corrcoef(t[ok], pred[ok])[0, 1]), n_pred=int(ok.sum()), blocks=per,
                      all_sites=dict(rmse=rmse_all, origin=origins[j][0], setting=settings[m][i],
                                     km_per_year=float(-1 / c[1]) if c[1] < 0 else None,
                                     r=float(-np.corrcoef(D[m][i, j][np.isfinite(D[m][i, j])],
                                                          t[np.isfinite(D[m][i, j])])[0, 1])),
                      pred=pred.tolist())
        print(f"{m}: held-out RMSE {res[m]['heldout_rmse']:.0f} y, r {res[m]['heldout_r']:.3f}; all sites "
              f"{rmse_all:.0f} y from {origins[j][0]} {settings[m][i]} {res[m]['all_sites']['km_per_year']:.2f} km/y",
              flush=True)
        for b in names:
            print(f"   {b:22s} n={per[b]['n']:3d} {per[b]['rmse']:6.0f}  {per[b]['origin']} {per[b]['setting']}")

    base = min(res[m]["heldout_rmse"] for m in ("M0", "M1", "M2"))
    m3_wins = sum(res["M3"]["blocks"][b]["rmse"] < res["M2"]["blocks"][b]["rmse"] for b in names)
    m2_wins = sum(res["M2"]["blocks"][b]["rmse"] < res["M0"]["blocks"][b]["rmse"] for b in names)
    if res["M3"]["heldout_rmse"] <= 0.95 * base and m3_wins >= 4:
        verdict = "M3"
    elif res["M2"]["heldout_rmse"] <= 0.95 * min(res["M0"]["heldout_rmse"], res["M1"]["heldout_rmse"]) and m2_wins >= 4:
        verdict = "M2"
    else:
        verdict = "distance"
    summary = dict(plan=str(PLAN.relative_to(ROOT)), frozen=plan["frozen"], n_sites=len(sites), left_out=outside,
                   verdict=verdict,
                   m3_beats_m2_blocks=m3_wins, m2_beats_m0_blocks=m2_wins, suit_ref_kcal=g["ref"],
                   models={m: {k: v for k, v in r.items() if k != "pred"} for m, r in res.items()})
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    np.savez_compressed(out / "fields.npz", s=g["s"], land=g["land"], elev=g["elev"], lat=g["lat"], lon=g["lon"],
                        site_lat=slat, site_lon=slon, date=t, block=blocks,
                        **{f"pred_{m}": np.array(r["pred"]) for m, r in res.items()})
    # arrival-time surfaces from the all-sites fits, for the figure
    for m in ("M2", "M3"):
        rmse_all, (i, j, c) = select(D[m], t, np.ones(len(sites), bool)); _ = rmse_all
        st = settings[m][i]
        G = graph(g, st["kappa"], st.get("beta"))
        dist = dijkstra(G, directed=True, indices=[org_cells[j]]) * FLAT
        np.save(out / f"arrival_{m}.npy", (c[0] + c[1] * dist.reshape(g["land"].shape)).astype(np.float32))
    print(f"verdict: {verdict} (M3 beats M2 in {m3_wins}/7, M2 beats M0 in {m2_wins}/7) ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
