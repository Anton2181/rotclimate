"""Language areas from below, layer 2c: language density from terrain and land-quality variation.

Frozen plan: calibration/language_areas_20261101/plan_2c.json.

On 2 deg blocks of crop-capable land (the map's crop rules on WorldClim),
log(1 + Glottolog languages) is regressed on climate alone (C0) and on
climate plus elevation variation, land-quality variation and mean land
quality (C1), each continent predicted from the others.

    python -I scripts/language_density_earth.py --out output/language_areas_20261101/layer2c
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

import land_people_earth as lpe  # noqa: E402

PLAN = ROOT / "calibration" / "language_areas_20261101" / "plan_2c.json"
WINDOW = dict(lat=(-56.0, 72.0), lon=(-180.0, 180.0))
B = 24                         # 5 arc-min cells per 2 deg block
MACRO = ("Africa", "Eurasia", "Papunesia", "North America", "South America", "Australia")
CROP_KEYS = ("kcal_wheat", "kcal_barley", "kcal_millet", "kcal_rice", "kcal_dates")


def crop_world(cache: Path):
    f = cache / "earth.npz"
    lpe.WINDOW = WINDOW
    if not f.exists():
        cache.mkdir(parents=True, exist_ok=True)
        lpe.compute(cache)
    z = np.load(f)
    rs, cs = lpe.window_slices()
    elev = lpe.wc("elev")[rs, cs]
    land = z["land"]
    best = np.max(np.stack([np.nan_to_num(z[k]) for k in CROP_KEYS]), 0) * z["arable"]
    best = np.where(land, best, np.nan)
    ref = float(np.nanpercentile(best[land], 95))
    s = np.clip(best / ref, 0, 1)
    return dict(land=land, s=s, T=z["T_ann"], P=z["P_ann"], npp=z["npp"], elev=np.where(land, elev, np.nan), ref=ref)


def block_stats(W):
    land = W["land"]
    h, w = land.shape[0] // B, land.shape[1] // B

    def blk(a):
        return a[:h * B, :w * B].reshape(h, B, w, B).transpose(0, 2, 1, 3).reshape(h, w, B * B)
    lf = blk(land.astype(float)).mean(-1)
    with np.errstate(invalid="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore")
        st = dict(landfrac=lf, s_mean=np.nanmean(blk(W["s"]), -1), s_std=np.nanstd(blk(W["s"]), -1),
                  T=np.nanmean(blk(W["T"]), -1), P=np.nanmean(blk(W["P"]), -1), npp=np.nanmean(blk(W["npp"]), -1),
                  elev_std=np.nanstd(blk(W["elev"]), -1))
    lat = WINDOW["lat"][1] - (np.arange(h) + 0.5) * 2.0
    lon = WINDOW["lon"][0] + (np.arange(w) + 0.5) * 2.0
    return st, lat, lon


def glottolog():
    rows = [r for r in csv.DictReader(open(ROOT / "data/cache/glottolog/languages.csv", encoding="utf-8"))
            if r["Level"] == "language" and r["Latitude"] and r["Longitude"]]
    lat = np.array([float(r["Latitude"]) for r in rows]); lon = np.array([float(r["Longitude"]) for r in rows])
    macro = np.array([r["Macroarea"].split(";")[0] for r in rows])
    return lat, lon, macro


def features(X, names):
    return np.column_stack([X[n] for n in names])


def ols_cv(Xf, y, groups, macros):
    pred = np.full(len(y), np.nan)
    for m in macros:
        te = groups == m; tr = ~te
        mu, sd = Xf[tr].mean(0), Xf[tr].std(0) + 1e-12
        A = np.column_stack([np.ones(tr.sum()), (Xf[tr] - mu) / sd])
        coef, *_ = np.linalg.lstsq(A, y[tr], rcond=None)
        pred[te] = np.column_stack([np.ones(te.sum()), (Xf[te] - mu) / sd]) @ coef
    return pred


def ols_all(Xf, y):
    mu, sd = Xf.mean(0), Xf.std(0) + 1e-12
    coef, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(y)), (Xf - mu) / sd]), y, rcond=None)
    return coef, mu, sd


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="output/language_areas_20261101/layer2c")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    plan = json.loads(PLAN.read_text())
    W = crop_world(out / "crops5")
    print(f"crop rules on the world ({time.time() - t0:.0f}s)", flush=True)
    st, blat, blon = block_stats(W)
    keep = (st["landfrac"] >= 0.5) & (st["s_mean"] >= 0.05)
    by, bx = np.nonzero(keep)
    glat, glon, gmac = glottolog()
    iy = np.floor((WINDOW["lat"][1] - glat) / 2.0).astype(int); ix = np.floor((glon - WINDOW["lon"][0]) / 2.0).astype(int)
    n = np.zeros(keep.shape, int); ok = (iy >= 0) & (iy < keep.shape[0]) & (ix >= 0) & (ix < keep.shape[1])
    np.add.at(n, (iy[ok], ix[ok]), 1)
    # macroarea of each block: most of its languages, else the nearest language's
    tree = cKDTree(np.column_stack([glat, glon]))
    groups = []
    for y_, x_ in zip(by, bx):
        inside = ok & (iy == y_) & (ix == x_)
        if inside.any():
            vals, cnt = np.unique(gmac[inside], return_counts=True); groups.append(vals[cnt.argmax()])
        else:
            groups.append(gmac[tree.query([blat[y_], blon[x_]])[1]])
    groups = np.array(groups)
    y = np.log1p(n[by, bx].astype(float))
    X = dict(T=st["T"][by, bx], logP=np.log10(np.maximum(st["P"][by, bx], 1.0)), logNPP=np.log10(np.maximum(st["npp"][by, bx], 1.0)),
             rug=np.log10(1.0 + st["elev_std"][by, bx]), s_std=st["s_std"][by, bx], s_mean=st["s_mean"][by, bx])
    sets = {"C0": ["T", "logP", "logNPP"], "C1": ["T", "logP", "logNPP", "rug", "s_std", "s_mean"],
            "C0+rug": ["T", "logP", "logNPP", "rug"]}
    print(f"{len(y)} blocks; languages in them {int(n[by, bx].sum())}; macroareas "
          + ", ".join(f"{m} {int((groups == m).sum())}" for m in MACRO), flush=True)
    sst = float(np.sum((y - y.mean()) ** 2))
    res = {}
    for k, names in sets.items():
        Xf = features(X, names)
        p = ols_cv(Xf, y, groups, MACRO)
        coef, mu, sd = ols_all(Xf, y)
        res[k] = dict(heldout_r2=float(1 - np.sum((y - p) ** 2) / sst),
                      rmse={m: float(np.sqrt(np.mean((y[groups == m] - p[groups == m]) ** 2))) for m in MACRO},
                      coef_all={nm: float(c) for nm, c in zip(["intercept"] + names, coef)},
                      mu={nm: float(v) for nm, v in zip(names, mu)}, sd={nm: float(v) for nm, v in zip(names, sd)},
                      pred=p)
        print(f"{k}: held-out R2 {res[k]['heldout_r2']:.3f}; RMSE " + ", ".join(f"{m} {res[k]['rmse'][m]:.3f}" for m in MACRO)
              + "; coef " + ", ".join(f"{nm} {c:+.3f}" for nm, c in res[k]["coef_all"].items()), flush=True)
    wins = sum(res["C1"]["rmse"][m] < res["C0"]["rmse"][m] for m in MACRO)
    if res["C1"]["heldout_r2"] >= res["C0"]["heldout_r2"] + 0.05 and wins >= 4:
        verdict = "C1"
    elif res["C0"]["heldout_r2"] >= 0.20:
        verdict = "C0"
    else:
        verdict = "owner"
    summary = dict(plan=str(PLAN.relative_to(ROOT)), frozen=plan["frozen"], blocks=int(len(y)), verdict=verdict,
                   c1_beats_c0_macroareas=int(wins), s_ref_kcal=W["ref"],
                   models={k: {kk: vv for kk, vv in v.items() if kk != "pred"} for k, v in res.items()})
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    np.savez_compressed(out / "blocks.npz", lat=blat[by], lon=blon[bx], y=y, n=n[by, bx], group=groups,
                        **{f"x_{k}": v for k, v in X.items()}, **{f"pred_{k}": v["pred"] for k, v in res.items()})
    print(f"verdict: {verdict} (C1 beats C0 in {wins}/6) ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
