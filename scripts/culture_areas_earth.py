"""Do culture areas emerge as contact basins? (calibration/culture_areas_20261101/plan.json)

    python -I scripts/culture_areas_earth.py --out output/culture_areas_20261101
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
from scipy.cluster.hierarchy import fcluster, linkage  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.csgraph import dijkstra  # noqa: E402
from scipy.spatial.distance import squareform  # noqa: E402
from sklearn.metrics import adjusted_rand_score  # noqa: E402

PLAN = ROOT / "calibration/culture_areas_20261101/plan.json"
EA = ROOT / "data/cache/dplace_ea"
R_KM = 6371.0


def societies():
    rows = list(csv.DictReader(open(EA / "societies.csv")))
    sub = {}
    for r in csv.DictReader(open(EA / "data.csv")):
        if r["Var_ID"] in ("EA001", "EA002", "EA003", "EA004", "EA005"):
            m = re.findall(r"(\d+)", r["Value"])
            if m:
                v = np.mean([float(x) for x in m[:2]]) if len(m) >= 2 else float(m[0])
                sub.setdefault(r["Soc_ID"], {})[r["Var_ID"]] = v
    out = []
    for r in rows:
        s = sub.get(r["ID"], {})
        vec = [s.get(k, np.nan) for k in ("EA001", "EA002", "EA003", "EA004", "EA005")]
        out.append(dict(id=r["ID"], area=r["ID"][:2], macro=r["ID"][0], lat=float(r["Latitude"]), lon=float(r["Longitude"]), sub=vec))
    return out


def elevation_grid(step_deg=0.5):
    from rotclimate.earth import _wc
    e = _wc("elev").astype(float)
    land = np.isfinite(e)
    f = int(round(step_deg * 12))
    h, w = e.shape[0] // f, e.shape[1] // f
    blk = e[:h * f, :w * f].reshape(h, f, w, f)
    lf = np.isfinite(blk).mean((1, 3))
    em = np.nanmean(np.where(np.isfinite(blk), blk, np.nan), axis=(1, 3))
    land_c = lf >= 0.5
    em = np.where(land_c, np.nan_to_num(em), 0.0)
    return em, land_c, step_deg


def graph(elev, land, step):
    h, w = elev.shape
    lat = 90 - (np.arange(h) + 0.5) * step
    dy_km = R_KM * np.radians(step)
    flat = 6.0 * np.exp(-3.5 * 0.05)                      # Tobler on the flat, km/h
    rows, cols, cost = [], [], []
    idx = np.arange(h * w).reshape(h, w)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        y0, y1 = 0, h - dy
        src_y = np.arange(y0, y1)
        a = idx[src_y][:, :]
        b = idx[src_y + dy][:, :]
        b = np.roll(b, -dx, axis=1)                        # longitudes wrap
        la = np.radians(lat[src_y] - 0.5 * dy * step)[:, None]
        dx_km = R_KM * np.radians(step) * np.cos(la) * abs(dx)
        dist = np.sqrt(dx_km ** 2 + (dy_km * dy) ** 2) * np.ones((len(src_y), w))
        ea, eb = elev[src_y], np.roll(elev[src_y + dy], -dx, axis=1)
        la_, lb_ = land[src_y], np.roll(land[src_y + dy], -dx, axis=1)
        slope = (eb - ea) / 1000.0 / np.maximum(dist, 1e-6)
        both = la_ & lb_
        t_ab = np.where(both, dist / (6.0 * np.exp(-3.5 * np.abs(slope + 0.05))), 3.0 * dist / flat)
        t_ba = np.where(both, dist / (6.0 * np.exp(-3.5 * np.abs(-slope + 0.05))), 3.0 * dist / flat)
        rows += [a.ravel(), b.ravel()]; cols += [b.ravel(), a.ravel()]; cost += [t_ab.ravel(), t_ba.ravel()]
    return coo_matrix((np.concatenate(cost), (np.concatenate(rows), np.concatenate(cols))), shape=(h * w, h * w)).tocsr()


def snap(soc, land, step):
    h, w = land.shape
    ys, xs = np.nonzero(land)
    out = []
    for s in soc:
        y = int(np.clip((90 - s["lat"]) / step, 0, h - 1)); x = int(np.clip((s["lon"] + 180) / step, 0, w - 1))
        if not land[y, x]:
            k = np.argmin((ys - y) ** 2 + ((xs - x + w / 2) % w - w / 2) ** 2)
            y, x = ys[k], xs[k]
        out.append(y * w + x)
    return np.array(out)


def great_circle(soc):
    la = np.radians([s["lat"] for s in soc]); lo = np.radians([s["lon"] for s in soc])
    c = np.sin(la)[:, None] * np.sin(la)[None] + np.cos(la)[:, None] * np.cos(la)[None] * np.cos(lo[:, None] - lo[None])
    return R_KM * np.arccos(np.clip(c, -1, 1))


def cluster(D, k):
    D = 0.5 * (D + D.T); np.fill_diagonal(D, 0)
    return fcluster(linkage(squareform(D, checks=False), "average"), k, "maxclust")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/culture_areas_20261101")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    soc = societies(); n = len(soc); k = len(set(s["area"] for s in soc))
    labels = np.array([s["area"] for s in soc]); macro = np.array([s["macro"] for s in soc])
    elev, land, step = elevation_grid()
    G = graph(elev, land, step)
    nodes = snap(soc, land, step)
    T = np.zeros((n, n))
    for i in range(0, n, 64):
        d = dijkstra(G, directed=True, indices=nodes[i:i + 64])
        T[i:i + 64] = d[:, nodes]
        print(f"  travel times {min(i + 64, n)}/{n}", flush=True)
    T = np.where(np.isfinite(T), T, np.nanmax(T[np.isfinite(T)]) * 2)
    S = np.array([s["sub"] for s in soc], float)
    S = np.where(np.isfinite(S), S, np.nanmean(S, 0)); S = S / np.maximum(S.sum(1, keepdims=True), 1e-9)
    Dsub = np.abs(S[:, None, :] - S[None, :, :]).sum(-1) / 2
    mats = dict(A_location=great_circle(soc), B_contact=T, C_contact_lifeway=T * (1 + 1.0 * Dsub))
    res = {}
    labs = {}
    for name, D in mats.items():
        lab = cluster(D, k); labs[name] = lab
        res[name] = dict(world=float(adjusted_rand_score(labels, lab)),
                         by_macro={m: float(adjusted_rand_score(labels[macro == m], lab[macro == m])) for m in sorted(set(macro))})
        print(name, round(res[name]["world"], 3), {m: round(v, 3) for m, v in res[name]["by_macro"].items()}, flush=True)
    rng = np.random.default_rng(1101); diffs = {"B-A": [], "C-A": []}
    for b in range(1000):
        ix = np.unique(rng.integers(0, n, n))
        ari = {nm: adjusted_rand_score(labels[ix], cluster(D[np.ix_(ix, ix)], k)) for nm, D in mats.items()}
        diffs["B-A"].append(ari["B_contact"] - ari["A_location"]); diffs["C-A"].append(ari["C_contact_lifeway"] - ari["A_location"])
        if b % 200 == 0:
            print("  bootstrap", b, flush=True)
    ci = {kk: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for kk, v in diffs.items()}
    gain = {"B-A": res["B_contact"]["world"] - res["A_location"]["world"], "C-A": res["C_contact_lifeway"]["world"] - res["A_location"]["world"]}
    adopted = any(gain[kk] >= 0.05 and ci[kk][0] > 0 for kk in gain)
    out = dict(plan=str(PLAN.relative_to(ROOT)), societies=n, areas=k, results=res, gain=gain, bootstrap_95=ci, adopted=bool(adopted),
               rule=json.loads(PLAN.read_text())["adopt_if"])
    (a.out / "culture_areas.json").write_text(json.dumps(out, indent=1))
    np.savez_compressed(a.out / "clusters.npz", lat=[s["lat"] for s in soc], lon=[s["lon"] for s in soc], murdock=labels, **labs)
    print(json.dumps(dict(gain=gain, bootstrap_95=ci, adopted=adopted), indent=1))


if __name__ == "__main__":
    main()
