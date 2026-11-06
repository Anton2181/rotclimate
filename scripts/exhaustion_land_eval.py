"""Single evaluation of the frozen soil-fertility state on Exhaustion Land Phase II
(calibration/soil_fertility_20261106/plan.json, amendment_evaporation.json,
selection output/soil_fertility_20261106/selection.json).

Order of work, enforced here:
  1. check the selection's producer hashes (no code change since the fit);
  2. build every plot's 1856-1935 history from MANAGEMENT columns only;
  3. predict and write predictions.json (with its hash) BEFORE any Phase II yield is read;
  4. read the Phase II grain yields once and score M1, M2, M3.

Declared history details (plan text plus these): Phase I wheat 1856-1875 with fallows as
recorded; ammonium/nitrate N in March for wheat and April for potatoes; FYM (35 t, 3.0 t C,
225 kg N) in March before potatoes; 1923-1934 (no records): spring barley each year;
red clover residues each clover year in October and the ploughed-in stand in November
1911; cowpeas 1905 (failed) as bare ground.

    python -I scripts/exhaustion_land_eval.py --out output/soil_fertility_20261106
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import openpyxl  # noqa: E402

import soil_fertility_common as C  # noqa: E402
from harvest.soil_fertility import Params  # noqa: E402

DATA = ROOT / "data/cache/era_exhaustion_20261106"
SOURCES = ROOT / "calibration/soil_fertility_20261106/sources.json"
CLOVER_RESIDUE = (1.5, 15.0)          # t C/ha/yr, C:N  (plan)
CLOVER_PLOUGHED = (2.0, 15.0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_frozen(selection):
    bad = {p: h for p, h in selection["producers"].items() if sha(ROOT / p) != h}
    if bad:
        raise SystemExit(f"producer changed since the frozen selection: {sorted(bad)}")
    src = json.loads(SOURCES.read_text())
    for k in ("exhaustion_land_phase1", "exhaustion_land_phase2"):
        assert sha(ROOT / src[k]["file"]) == src[k]["sha256"], k


def crop_kind(name):
    n = (name or "").strip().lower()
    return {"winter wheat": "wheat", "spring barley": "barley", "oats": "oats", "potatoes": "potato",
            "fallow": "fallow", "red clover": "clover", "cow peas": "cowpea", "cowpea": "cowpea"}.get(n, n)


def histories():
    """Per plot: calendar (harvest year -> crop kind) and events, management columns only."""
    wb1 = openpyxl.load_workbook(DATA / "01-EX4-YLD5601.xlsx", read_only=True, data_only=True)
    rows = list(wb1["crop_data"].iter_rows(values_only=True))
    h = rows[0]; ix = {k: i for i, k in enumerate(h) if k}
    cal = {p: {} for p in range(1, 11)}
    ev = {p: {} for p in range(1, 11)}
    for r in rows[1:]:
        if r[0] is None:
            continue
        y, p = int(r[ix["harvest_year"]]), int(r[ix["plot"]])
        kind = crop_kind(r[ix["crop"]])
        cal[p][y] = kind
        fym = str(r[ix["fym_factor_level"]]).strip()
        n = r[ix["fertilizer_n_amount"]]
        n = float(n) if isinstance(n, (int, float)) else 0.0
        if fym == "FYM":
            ev[p].setdefault((y, 3), []).append(("fym", 35 * C.FYM_C_PER_T, 225.0))
        if n > 0:
            ev[p].setdefault((y, 3 if kind == "wheat" else 4), []).append(("fert", n))
    wb2 = openpyxl.load_workbook(DATA / "01-EX4-YLD0239.xlsx", read_only=True, data_only=True)
    rows = list(wb2["crop_data"].iter_rows(values_only=True))
    h = rows[0]; ix = {k: i for i, k in enumerate(h) if k}
    for r in rows[1:]:
        if r[0] is None:
            continue
        y, p = int(r[ix["harvest_year"]]), int(r[ix["plot"]])
        cal[p][y] = crop_kind(r[ix["crop"]])
    for p in cal:
        for y in range(1923, 1935):
            cal[p].setdefault(y, "barley")
        clover = sorted(y for y, k in cal[p].items() if k == "clover")
        for y in clover:
            ev[p].setdefault((y, 10), []).append(("residue",) + CLOVER_RESIDUE)
        if clover:
            ev[p].setdefault((clover[-1], 11), []).append(("residue",) + CLOVER_PLOUGHED)
        for y, k in list(cal[p].items()):
            if k == "cowpea":
                cal[p][y] = "fallow"
    return cal, ev


def predict(params):
    cal, ev = histories()
    drain_cache = {}
    out = {}
    for p in range(1, 11):
        key = tuple(sorted(cal[p].items()))
        if key not in drain_cache:
            drain_cache[key] = C.monthly_drainage("rothamsted", 1855, 1935, cal[p])[0]
        res = C.run("rothamsted", 1855, 1935, cal[p], ev[p], params, drainage=drain_cache[key])
        out[p] = {s["harvest"][0]: dict(grain=s["grain_t_ha"], crop=cal[p][s["harvest"][0]], potential=s["potential_t_ha"],
                                         organic_n=s["organic_n"], soc_active=s["soc_active"])
                  for s in res["seasons"] if s["harvest"][0] >= 1902}
        out[p]["_ledger_residual"] = res["residual"]
    return out, cal


def observed():
    wb = openpyxl.load_workbook(DATA / "01-EX4-YLD0239.xlsx", read_only=True, data_only=True)
    rows = list(wb["crop_data"].iter_rows(values_only=True))
    h = rows[0]; ix = {k: i for i, k in enumerate(h) if k}
    obs = {}
    for r in rows[1:]:
        if r[0] is None:
            continue
        kind = crop_kind(r[ix["crop"]])
        g = r[ix["grain_yield"]]
        if kind in ("wheat", "barley", "oats") and isinstance(g, (int, float)) and math.isfinite(g):
            obs[(int(r[ix["plot"]]), int(r[ix["harvest_year"]]))] = (float(g), kind)
    return obs


def lg(x):
    return math.log10(max(x, 0.05))


def score(pred, obs):
    def ratios(plots, years=None):
        o, p, keys = [], [], []
        for (pl, y), (g, _) in sorted(obs.items()):
            if pl not in plots or (years and y not in years) or (1, y) not in obs:
                continue
            o.append(lg(g) - lg(obs[(1, y)][0]))
            p.append(lg(pred[pl][y]["grain"]) - lg(pred[1][y]["grain"]))
            keys.append([pl, y])
        o, p = np.array(o), np.array(p)
        r = float(np.corrcoef(p, o)[0, 1]) if len(o) > 2 and np.ptp(p) > 1e-12 else None
        return dict(n=len(o), MAE_model=float(np.mean(np.abs(o - p))), MAE_null=float(np.mean(np.abs(o))),
                    Pearson_r=r, observed_mean_log10_ratio=float(o.mean()), predicted_mean_log10_ratio=float(p.mean()),
                    keys=keys, observed=o.tolist(), predicted=p.tolist())
    late = set(range(1912, 1923)) | {1935}
    m1 = ratios({2, 3, 4})
    m2 = ratios({5, 6}, late)
    m2b = ratios({7, 8, 9, 10}, late)
    m2c = ratios({5, 6, 7, 8, 9, 10}, set(range(1902, 1905)))
    lv = []
    for (pl, y), (g, kind) in sorted(obs.items()):
        a = C.a0(y, "wheat" if kind == "wheat" else "barley")
        if a is None:
            continue
        lv.append((g, pred[pl][y]["grain"], a, pl, y))
    g = np.array([x[0] for x in lv]); pm = np.array([x[1] for x in lv]); a0 = np.array([x[2] for x in lv])
    err = lambda q: float(np.mean(np.abs(np.log10(np.maximum(g, .05) / np.maximum(q, .05)))))   # noqa: E731
    m3 = dict(n=len(lv), MAE_model=err(pm), MAE_A0=err(a0), Pearson_r_model=float(np.corrcoef(pm, g)[0, 1]),
              Pearson_r_A0=float(np.corrcoef(a0, g)[0, 1]) if np.ptp(a0) > 0 else None,
              within_factor2_model=float(np.mean(np.abs(np.log10(np.maximum(g, .05) / np.maximum(pm, .05))) <= math.log10(2))),
              observed_mean=float(g.mean()), predicted_mean=float(pm.mean()), A0_mean=float(a0.mean()))
    q = dict(M1=bool(m1["MAE_model"] <= 0.95 * m1["MAE_null"] and (m1["Pearson_r"] or 0) > 0),
             M2=bool(m2["MAE_model"] <= 0.95 * m2["MAE_null"]), M3=bool(m3["MAE_model"] <= m3["MAE_A0"]))
    q["qualifies"] = all(q.values())
    return dict(M1_manure_memory=m1, M2_legume_memory=m2, M2_reported_PK_plots=m2b, reported_mineral_N_residue_1902_04=m2c,
                M3_level=m3, qualification=q)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/soil_fertility_20261106")
    a = ap.parse_args()
    selection = json.loads((a.out / "selection.json").read_text())
    check_frozen(selection)
    params = Params(**selection["parameters"])
    pred, cal = predict(params)
    ptxt = json.dumps({str(k): {str(y): v for y, v in d.items()} for k, d in pred.items()}, indent=1, sort_keys=True)
    (a.out / "predictions.json").write_text(ptxt)
    phash = hashlib.sha256(ptxt.encode()).hexdigest()
    print("predictions written", phash[:16], flush=True)
    obs = observed()                                       # the single read of Phase II yields
    result = score(pred, obs)
    result.update(selection=str((a.out / "selection.json").relative_to(ROOT)), predictions_sha256=phash,
                  parameters=selection["parameters"])
    (a.out / "evaluation.json").write_text(json.dumps(result, indent=1))
    for k in ("M1_manure_memory", "M2_legume_memory", "M2_reported_PK_plots", "reported_mineral_N_residue_1902_04"):
        m = result[k]
        print(f"{k:36s} n {m['n']:3d} MAE model {m['MAE_model']:.3f} null {m['MAE_null']:.3f} r {m['Pearson_r'] if m['Pearson_r'] is None else round(m['Pearson_r'], 2)} "
              f"obs mean {m['observed_mean_log10_ratio']:+.3f} pred {m['predicted_mean_log10_ratio']:+.3f}")
    m = result["M3_level"]
    print(f"M3 n {m['n']} MAE model {m['MAE_model']:.3f} A0 {m['MAE_A0']:.3f} r {m['Pearson_r_model']:+.2f} (A0 {m['Pearson_r_A0']}) "
          f"obs {m['observed_mean']:.2f} pred {m['predicted_mean']:.2f} A0 {m['A0_mean']:.2f}")
    print(result["qualification"])


if __name__ == "__main__":
    main()
