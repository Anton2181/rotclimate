"""Soil-fertility round 2 (calibration/soil_fertility_20261106/plan_round2.json).

    python -I scripts/soil_fertility_round2.py fit --workers 4      # development fit -> selection.json
    python -I scripts/soil_fertility_round2.py evaluate             # single Broadbalk 1926-1967 evaluation

Development uses spent data only; the evaluation writes its predictions before it reads
any 1926-1967 grain value.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import openpyxl  # noqa: E402

import soil_fertility_common as C  # noqa: E402
from harvest.soil_fertility import Params, Season, inert, simulate  # noqa: E402

OUT = ROOT / "output/soil_fertility_round2_20261106"
CACHE = C.CACHE
EXH = ROOT / "data/cache/era_exhaustion_20261106"
R2 = ROOT / "data/cache/era_round2_20261106"
BB_START, HOOS_START = 28.8, 33.8          # t C/ha total (e-RA 1843 estimate; RothC Hoosfield 1852)
CLOVER_YEARLY, CLOVER_PLOUGHED = (0.8, 20.0), (2.0, 19.0)
RAPE_CAKE_CN = 8.0
BOUNDS = dict(input_n=(0.0, 60.0), uptake_rate=(0.05, 0.9), kappa=(1.0, 5.0), fym_hum=(0.02, 0.6), prior_manure=(0.0, 3.0))
PRODUCERS = ("harvest/soil_fertility.py", "scripts/soil_fertility_common.py", "scripts/soil_fertility_round2.py",
             "harvest/soil_water_dual.py", "calibration/soil_fertility_20261106/plan_round2.json",
             "calibration/soil_fertility_20261106/amendment_evaporation.json",
             "calibration/soil_fertility_20261106/amendment_round2.json")
SOC = {"3": {1865: 27.072, 1881: 26.784, 1893: 22.464, 1914: 24.192},       # e-RA 01-BKSOC1843, t C/ha 0-23 cm
       "2.2": {1865: 50.71, 1881: 53.038, 1893: 58.098, 1914: 71.176},
       "2.1": {1893: 44.64, 1914: 58.594}}
RWF = ((1857, 1866, 0.6), (1867, 1925, 0.14))                                 # e-RA rwf3 page aggregates


def params_from(v, names):
    d = dict(zip(names, v))
    return Params(thermal_uptake=True, wet_deposition=True, demand_curve=True, **d)


def fym_events(first_harvest, last_harvest, month=10, tonnes=35.0, n=225.0, skip=()):
    return {(y - 1, month): [("fym", tonnes * C.FYM_C_PER_T, n)] for y in range(first_harvest, last_harvest + 1) if y not in skip}


# --- development data ---------------------------------------------------------------------

def broadbalk_obs():
    z = zipfile.ZipFile(CACHE / "broadbalk_0.zip")
    rows = list(csv.DictReader(io.StringIO(z.read("crop_data.csv").decode("utf-8-sig"))))
    acc = {}
    for r in rows:
        p = {"2": "2.2"}.get(r["plot"], r["plot"])
        if p not in ("3", "2.2", "2.1"):
            continue
        try:
            g, a, y = float(r["grain"]), float(r["area_ha"]), int(r["harvest_year"])
        except ValueError:
            continue
        s = acc.setdefault((p, y), [0.0, 0.0]); s[0] += g * a; s[1] += a
    return {k: v[0] / v[1] for k, v in acc.items()}


def broadbalk_group():
    obs = broadbalk_obs()
    cal = {y: "wheat" for y in range(1844, 1926)}
    plots = {"3": {}, "2.2": fym_events(1844, 1925), "2.1": fym_events(1885, 1925)}
    series = {p: {y: v for (q, y), v in obs.items() if q == p and 1879 <= y <= 1925 and C.a0(y, "wheat") is not None}
              for p in plots}
    rwf_obs = {(a, b): float(np.mean([obs[("3", y)] for y in range(a, b + 1) if ("3", y) in obs])) for a, b, _ in RWF}
    return dict(site="rothamsted", first=1843, last=1925, calendar=cal, plots=plots, series=series, target=BB_START,
                rwf_obs=rwf_obs)


def woburn_group(crop, zipname, prefix):
    z = zipfile.ZipFile(CACHE / zipname)
    rows = list(csv.DictReader(io.StringIO(z.read(f"{prefix}/crop_data.csv").decode("utf-8-sig"))))
    keep = {"1": 1926, "7": 1926, "10/a": 1906, "11/a": 1906, "11/b": 1926}
    plots, series = {k: {} for k in keep}, {k: {} for k in keep}
    acc = {}
    for r in rows:
        y = int(r["harvest_year"])
        key = "/".join(v for v in (r["plot"], r["sub_plot"], r["sub_sub_plot"]) if v not in ("*", ""))
        if key not in keep:
            continue
        ev = plots[key]
        lvl = r["fym_factor_level"]
        if lvl != "nil":
            t, n = float(r["fym_amount"]), float(r["fym_n"])
            month = (y - 1, 10) if (lvl == "FYM1.5" and crop == "wheat") else (y, 2)
            ev.setdefault(month, []).append(("fym", t * C.FYM_C_PER_T, n))
        if r["n_factor_level"] != "nil" and r["fertilizer_n_amount"] not in ("", "*"):
            ev.setdefault((y, 4), []).append(("fert", float(r["fertilizer_n_amount"])))
        if r["rape_cake_factor_level"] != "nil" and r["rape_cake_n"] not in ("", "*"):
            rc = float(r["rape_cake_n"])
            ev.setdefault((y, 2), []).append(("residue", rc * RAPE_CAKE_CN / 1000.0, RAPE_CAKE_CN))
        if 1879 <= y <= keep[key]:
            try:
                g, a = float(r["grain"]), float(r["area_ha"])
            except ValueError:
                continue
            s = acc.setdefault((key, y), [0.0, 0.0]); s[0] += g * a; s[1] += a
    rule = "wheat" if crop == "wheat" else "barley"
    for (k, y), (ga, aa) in acc.items():
        if C.a0(y, rule) is not None:
            series[k][y] = ga / aa
    cal = {y: crop for y in range(1877, 1927)}
    return dict(site="woburn", first=1876, last=1926, calendar=cal, plots=plots, series=series, target=None, crop=crop)


def exhaustion_histories():
    wb1 = openpyxl.load_workbook(EXH / "01-EX4-YLD5601.xlsx", read_only=True, data_only=True)
    rows = list(wb1["crop_data"].iter_rows(values_only=True))
    ix = {k: i for i, k in enumerate(rows[0]) if k}
    kind = lambda n: {"winter wheat": "wheat", "spring barley": "barley", "oats": "oats", "potatoes": "potato", "fallow": "fallow",  # noqa: E731
                      "red clover": "clover", "cow peas": "fallow", "cowpea": "fallow"}.get((n or "").strip().lower(), (n or "").strip().lower())
    cal = {p: {} for p in range(1, 11)}; ev = {p: {} for p in range(1, 11)}
    for r in rows[1:]:
        if r[0] is None:
            continue
        y, p, k = int(r[ix["harvest_year"]]), int(r[ix["plot"]]), kind(r[ix["crop"]])
        cal[p][y] = k
        n = r[ix["fertilizer_n_amount"]]
        if str(r[ix["fym_factor_level"]]).strip() == "FYM":
            ev[p].setdefault((y, 3), []).append(("fym", 35 * C.FYM_C_PER_T, 225.0))
        if isinstance(n, (int, float)) and n > 0:
            ev[p].setdefault((y, 3 if k == "wheat" else 4), []).append(("fert", float(n)))
    wb2 = openpyxl.load_workbook(EXH / "01-EX4-YLD0239.xlsx", read_only=True, data_only=True)
    rows = list(wb2["crop_data"].iter_rows(values_only=True))
    ix = {k: i for i, k in enumerate(rows[0]) if k}
    obs = {}
    for r in rows[1:]:
        if r[0] is None:
            continue
        y, p, k = int(r[ix["harvest_year"]]), int(r[ix["plot"]]), kind(r[ix["crop"]])
        cal[p][y] = k
        g = r[ix["grain_yield"]]
        if k in ("wheat", "barley", "oats") and isinstance(g, (int, float)):
            obs[(p, y)] = (float(g), k)
    for p in cal:
        for y in range(1923, 1935):
            cal[p].setdefault(y, "barley")
        clover = sorted(y for y, k in cal[p].items() if k == "clover")
        for y in clover:
            ev[p].setdefault((y, 10), []).append(("residue",) + CLOVER_YEARLY)
        if clover:
            ev[p].setdefault((clover[-1], 11), []).append(("residue",) + CLOVER_PLOUGHED)
    return cal, ev, obs


def exhaustion_group():
    cal, ev, obs = exhaustion_histories()
    series = {p: {y: g for (q, y), (g, k) in obs.items() if q == p and C.a0(y, "wheat" if k == "wheat" else "barley") is not None}
              for p in range(1, 11)}
    return dict(site="rothamsted", first=1855, last=1935, calendars=cal, plots=ev, series=series, target=HOOS_START)


def rwf_calendars():
    a = {y: ("wheat" if (y - 1857) % 2 == 0 else "fallow") for y in range(1856, 1926)}
    b = {y: ("fallow" if (y - 1857) % 2 == 0 else "wheat") for y in range(1856, 1926)}
    a.update({y: "wheat" for y in range(1844, 1856)}); b.update({y: "wheat" for y in range(1844, 1856)})
    return a, b


class Development:
    def __init__(self):
        self.bb = broadbalk_group()
        self.ww = woburn_group("wheat", "woburn_wheat_0.zip", "01-WXW6YLD7726")
        self.wb = woburn_group("barley", "woburn_barley_0.zip", "01-WXB6YLD7726")
        self.el = exhaustion_group()
        self.drain = {}
        for g in (self.bb, self.ww, self.wb):
            g["drainage"] = C.monthly_drainage(g["site"], g["first"], g["last"], g["calendar"])[0]
        self.el_drain = {}
        for p, cal in self.el["calendars"].items():
            key = tuple(sorted(cal.items()))
            if key not in self.el_drain:
                self.el_drain[key] = C.monthly_drainage("rothamsted", 1855, 1935, cal)[0]
        self.rwf_cal = rwf_calendars()
        self.rwf_drain = [C.monthly_drainage("rothamsted", 1843, 1925, c)[0] for c in self.rwf_cal]

    def predict(self, params):
        out = {"bb": {}, "ww": {}, "wb": {}, "el": {}, "soc": {}, "rwf": {}}
        for name, g in (("bb", self.bb), ("ww", self.ww), ("wb", self.wb)):
            for key, ev in g["plots"].items():
                res = C.run(g["site"], g["first"], g["last"], g["calendar"], ev, params, drainage=g["drainage"], target_total=g["target"])
                out[name][key] = {s["harvest"][0]: s["grain_t_ha"] for s in res["seasons"] if s["grain_t_ha"] is not None}
                if name == "bb":
                    iom = inert(BB_START)
                    out["soc"][key] = {s["harvest"][0]: s["soc_active"] + iom for s in res["seasons"]}
        for p, cal in self.el["calendars"].items():
            res = C.run("rothamsted", 1855, 1935, cal, self.el["plots"][p], params, drainage=self.el_drain[tuple(sorted(cal.items()))],
                        target_total=HOOS_START)
            out["el"][p] = {s["harvest"][0]: s["grain_t_ha"] for s in res["seasons"] if s["grain_t_ha"] is not None}
        wf = {}
        for cal, dr in zip(self.rwf_cal, self.rwf_drain):
            res = C.run("rothamsted", 1843, 1925, cal, {}, params, drainage=dr, target_total=BB_START)
            for s in res["seasons"]:
                if s["grain_t_ha"] is not None and s["harvest"][0] >= 1857:
                    wf[s["harvest"][0]] = s["grain_t_ha"]
        for a, b, _ in RWF:
            m_wf = np.mean([wf[y] for y in range(a, b + 1) if y in wf])
            m_c = np.mean([out["bb"]["3"][y] for y in range(a, b + 1) if y in out["bb"]["3"]])
            out["rwf"][(a, b)] = (float(m_wf), float(m_c))
        return out

    def loss(self, params, detail=False):
        pr = self.predict(params)
        lg = lambda o, p: math.log(max(o, 0.05) / max(p, 0.05))   # noqa: E731
        groups = {}
        groups["broadbalk"] = [np.mean([lg(o, pr["bb"][k][y]) ** 2 for y, o in s.items()]) for k, s in self.bb["series"].items()]
        groups["woburn"] = [np.mean([lg(o, pr[n][k][y]) ** 2 for y, o in s.items()])
                            for n, g in (("ww", self.ww), ("wb", self.wb)) for k, s in g["series"].items() if s]
        groups["exhaustion"] = [np.mean([lg(o, pr["el"][k][y]) ** 2 for y, o in s.items()]) for k, s in self.el["series"].items() if s]
        groups["soc"] = [np.mean([math.log(v / pr["soc"][k][y]) ** 2 for y, v in s.items()]) for k, s in SOC.items()]
        terms = []
        for a, b, d in RWF:
            y3 = self.bb["rwf_obs"][(a, b)]
            m_wf, m_c = pr["rwf"][(a, b)]
            terms.append((math.log(max(m_wf, .05) / max(m_c, .05)) - math.log((y3 + d) / y3)) ** 2)
        groups["wheat_fallow"] = [float(np.mean(terms))]
        total = float(np.mean([np.mean(v) for v in groups.values()]))
        if detail:
            return total, {k: [float(x) for x in v] for k, v in groups.items()}, pr
        return total


class Objective:
    def __init__(self, dev, names):
        self.dev, self.names = dev, names

    def __call__(self, v):
        return self.dev.loss(params_from(v, self.names))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def development_report(dev, params):
    total, groups, pr = dev.loss(params, detail=True)
    rep = dict(loss=total, groups={k: float(np.mean(v)) for k, v in groups.items()}, series={})
    for name, g, key in (("broadbalk", dev.bb, "bb"), ("woburn_wheat", dev.ww, "ww"), ("woburn_barley", dev.wb, "wb"), ("exhaustion", dev.el, "el")):
        for k, s in g["series"].items():
            if not s:
                continue
            ys = sorted(s)
            o = np.array([s[y] for y in ys]); p = np.array([pr[key][k][y] for y in ys])
            crop = "wheat" if key in ("bb", "ww") else "barley"
            a0 = np.array([C.potential(y, crop)[0] for y in ys])
            mae = lambda q: float(np.mean(np.abs(np.log10(np.maximum(o, .05) / np.maximum(q, .05)))))   # noqa: E731
            rep["series"][f"{name}:{k}"] = dict(n=len(ys), observed_mean=float(o.mean()), predicted_mean=float(p.mean()),
                                               MAE_log10=mae(p), A0_MAE_log10=mae(a0), years=ys, observed=o.tolist(), predicted=p.tolist())
    rep["soc"] = {k: {str(y): [v, pr["soc"][k][y]] for y, v in s.items()} for k, s in SOC.items()}
    rep["soc_model_1843_1925"] = {k: {str(y): v for y, v in pr["soc"][k].items() if y % 5 == 0} for k in pr["soc"]}
    rep["wheat_fallow"] = {f"{a}-{b}": dict(target_delta=d, observed_plot3=dev.bb["rwf_obs"][(a, b)],
                                            model_wheat_fallow=pr["rwf"][(a, b)][0], model_continuous=pr["rwf"][(a, b)][1])
                           for a, b, d in RWF}
    return rep


def fit(a):
    from scipy.optimize import differential_evolution
    OUT.mkdir(parents=True, exist_ok=True)
    dev = Development()
    names = list(BOUNDS)
    f = Objective(dev, names)
    t = time.time()
    print("one evaluation", round(f([25, 0.3, 2.5, 0.2, 0.5]), 4), round(time.time() - t, 2), "s", flush=True)
    res = differential_evolution(f, [BOUNDS[n] for n in names], seed=20261106, maxiter=a.maxiter, popsize=10, tol=1e-6,
                                 polish=True, updating="deferred", workers=a.workers)
    best = dict(zip(names, map(float, res.x)))
    params = params_from(res.x, names)
    rep = development_report(dev, params)
    sel = dict(plan="calibration/soil_fertility_20261106/plan_round2.json", status="round-2 development fit on spent data; frozen before the single Broadbalk 1926-1967 evaluation",
               parameters=asdict(params), fitted=best, objective=float(res.fun), evaluations=int(res.nfev),
               producers={p: sha(p) for p in PRODUCERS}, groups=rep["groups"],
               clover=dict(yearly=CLOVER_YEARLY, ploughed=CLOVER_PLOUGHED), starts=dict(broadbalk=BB_START, hoosfield=HOOS_START))
    (OUT / "selection.json").write_text(json.dumps(sel, indent=1))
    (OUT / "development.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(best), "loss", round(res.fun, 4), rep["groups"])
    for k, v in rep["series"].items():
        print(f"  {k:22s} n {v['n']:2d} obs {v['observed_mean']:.2f} pred {v['predicted_mean']:.2f} MAE {v['MAE_log10']:.3f} (A0 {v['A0_MAE_log10']:.3f})")
    print("SOC", {k: {y: (round(o, 1), round(m, 1)) for y, (o, m) in v.items()} for k, v in rep["soc"].items()})
    print("wheat-fallow", rep["wheat_fallow"])


# --- evaluation: Broadbalk 1926-1967 ------------------------------------------------------------

SECTION_PARENT = {"IA": "I", "IB": "I", "VA": "V", "VB": "V"}


def broadbalk_1926_management():
    z = zipfile.ZipFile(R2 / "01-YLD192667.zip")
    rows = list(csv.DictReader(io.StringIO(z.read("01-BKyld2667/yield_data.csv").decode("utf-8-sig"))))
    plots = {}
    for r in rows:
        if r["strip"] not in ("3", "21", "22", "5", "6", "7", "8"):
            continue
        y, st, sec = int(r["harvest_year"]), r["strip"], r["section"]
        plots.setdefault((st, sec), {})[y] = dict(crop=r["cropping"].strip().lower(), fym=r["fym_applied"], n=r["total_fertilizer_n_amount"],
                                                  fym_level=r["fym_factor_level"], n_level=r["n_factor_level"])
    chains = {}
    for (st, sec), yrs in plots.items():
        if sec in ("I", "V") and any(k in plots for k in ((st, sec + "A"), (st, sec + "B"))):
            continue
        hist = dict(yrs)
        parent = SECTION_PARENT.get(sec)
        if parent:
            hist = {**plots.get((st, parent), {}), **yrs}
        chains[(st, sec)] = hist
    return chains


def strip_history(st):
    """Calendar and events 1843-1925 for a strip (development knowledge, declared)."""
    cal = {y: "wheat" for y in range(1844, 1926)}
    if st == "22":
        ev = fym_events(1844, 1925)
    elif st == "21":
        ev = fym_events(1885, 1925)
    else:
        ev = {}
    return cal, ev


def eval_plot_inputs(st, hist):
    cal, ev = strip_history(st)
    ev = {k: list(v) for k, v in ev.items()}
    if st in ("6", "7", "8"):          # secondary only: N strips get their 1926-67 rate from 1852 (declared)
        rates = [float(h["n"]) for h in hist.values() if h["crop"] == "wheat" and h["n"] not in ("", "*")]
        rate = max(set(rates), key=rates.count) if rates else 0.0
        for y in range(1852, 1926):
            ev.setdefault((y, 4), []).append(("fert", rate))
    for y, h in sorted(hist.items()):
        cal[y] = "wheat" if h["crop"] == "wheat" else "fallow"
        if h["crop"] == "wheat":
            if h["fym_level"].strip().upper() == "FYM":
                ev.setdefault((y - 1, 10), []).append(("fym", 35 * C.FYM_C_PER_T, 225.0))
            try:
                n = float(h["n"])
            except ValueError:
                n = 0.0
            if n > 0:
                ev.setdefault((y, 4), []).append(("fert", n))
    return cal, ev


def predict_1926(params, chains):
    out = {}
    cache = {}
    for (st, sec), hist in sorted(chains.items()):
        cal, ev = eval_plot_inputs(st, hist)
        key = tuple(sorted(cal.items()))
        if key not in cache:
            cache[key] = C.monthly_drainage("rothamsted", 1843, 1967, cal)[0]
        res = C.run("rothamsted", 1843, 1967, cal, ev, params, drainage=cache[key], target_total=BB_START if params.wet_deposition else None)
        out[f"{st}|{sec}"] = {str(s["harvest"][0]): s["grain_t_ha"] for s in res["seasons"] if s["harvest"][0] >= 1926 and s["grain_t_ha"] is not None}
    return out


def observed_1926():
    z = zipfile.ZipFile(R2 / "01-YLD192667.zip")
    rows = list(csv.DictReader(io.StringIO(z.read("01-BKyld2667/yield_data.csv").decode("utf-8-sig"))))
    obs = {}
    for r in rows:
        if r["cropping"].strip().lower() != "wheat":
            continue
        try:
            g = float(r["grain"])
        except ValueError:
            continue
        obs[f"{r['strip']}|{r['section']}", r["harvest_year"]] = g
    return obs


def last_fallow(hist, y):
    ys = [t for t, h in hist.items() if t < y and h["crop"] == "fallow"]
    return max(ys) if ys else None


def score_1926(pred, obs, chains):
    lg = lambda x: math.log10(max(x, 0.05))   # noqa: E731
    # T1
    o, p, a0 = [], [], []
    for (pl, y), g in obs.items():
        if not pl.startswith("3|") or y not in pred.get(pl, {}):
            continue
        a = C.a0(int(y), "wheat")
        if a is None:
            continue
        o.append(g); p.append(pred[pl][y]); a0.append(a)
    o, p, a0 = map(np.array, (o, p, a0))
    err = lambda q: float(np.mean(np.abs(np.log10(np.maximum(o, .05) / np.maximum(q, .05)))))   # noqa: E731
    t1 = dict(n=len(o), MAE_model=err(p), MAE_A0=err(a0), mean_log10_bias=float(np.mean(np.log10(np.maximum(p, .05) / np.maximum(o, .05)))),
              observed_mean=float(o.mean()), predicted_mean=float(p.mean()), A0_mean=float(a0.mean()))
    # T2
    ro, rp = [], []
    for (pl, y), g in obs.items():
        st, sec = pl.split("|")
        if st not in ("21", "22"):
            continue
        base = obs.get((f"3|{sec}", y))
        if base is None or y not in pred.get(pl, {}) or y not in pred.get(f"3|{sec}", {}):
            continue
        ro.append(lg(g) - lg(base)); rp.append(lg(pred[pl][y]) - lg(pred[f"3|{sec}"][y]))
    ro, rp = np.array(ro), np.array(rp)
    t2 = dict(n=len(ro), MAE_model=float(np.mean(np.abs(ro - rp))), MAE_null=float(np.mean(np.abs(ro))),
              Pearson_r=float(np.corrcoef(rp, ro)[0, 1]), observed_mean=float(ro.mean()), predicted_mean=float(rp.mean()))

    # T3
    def fallow_effect(strip):
        fo, fp = [], []
        years = sorted({int(y) for (pl, y) in obs if pl.startswith(strip + "|")})
        for y in years:
            first, later = [], []
            for (st, sec), hist in chains.items():
                if st != strip:
                    continue
                pl, ys = f"{st}|{sec}", str(y)
                if (pl, ys) not in obs or ys not in pred.get(pl, {}):
                    continue
                lf = last_fallow(hist, y)
                if lf == y - 1:
                    first.append(pl)
                elif lf is None or lf <= y - 2:
                    later.append(pl)
            if first and later:
                fo.append(np.mean([lg(obs[(q, str(y))]) for q in first]) - np.mean([lg(obs[(q, str(y))]) for q in later]))
                fp.append(np.mean([lg(pred[q][str(y)]) for q in first]) - np.mean([lg(pred[q][str(y)]) for q in later]))
        fo, fp = np.array(fo), np.array(fp)
        return dict(n=len(fo), MAE_model=float(np.mean(np.abs(fo - fp))), MAE_null=float(np.mean(np.abs(fo))),
                    observed_mean=float(fo.mean()), predicted_mean=float(fp.mean()),
                    Pearson_r=float(np.corrcoef(fp, fo)[0, 1]) if len(fo) > 2 and np.ptp(fp) > 0 else None)
    t3 = fallow_effect("3")
    rep = {s: fallow_effect(s) for s in ("21", "22")}
    q = dict(T1=bool(t1["MAE_model"] <= t1["MAE_A0"] and abs(t1["mean_log10_bias"]) <= 0.10),
             T2=bool(t2["MAE_model"] <= 0.95 * t2["MAE_null"] and t2["Pearson_r"] > 0),
             T3=bool(t3["predicted_mean"] > 0 and t3["MAE_model"] <= 0.95 * t3["MAE_null"]))
    q["qualifies"] = all(q.values())
    # secondary: N strips level
    nl = {}
    for st in ("5", "6", "7", "8"):
        oo, pp = [], []
        for (pl, y), g in obs.items():
            if pl.startswith(st + "|") and y in pred.get(pl, {}):
                oo.append(g); pp.append(pred[pl][y])
        if oo:
            oo, pp = np.array(oo), np.array(pp)
            nl[st] = dict(n=len(oo), observed_mean=float(oo.mean()), predicted_mean=float(pp.mean()),
                          MAE_log10=float(np.mean(np.abs(np.log10(np.maximum(oo, .05) / np.maximum(pp, .05))))))
    return dict(T1_level=t1, T2_manure=t2, T3_fallow=t3, T3_reported_FYM_strips=rep, secondary_N_strips=nl, qualification=q)


def evaluate(a):
    sel = json.loads((OUT / "selection.json").read_text())
    bad = [p for p, h in sel["producers"].items() if sha(p) != h]
    if bad:
        raise SystemExit(f"producer changed since the frozen selection: {bad}")
    src = json.loads((ROOT / "calibration/soil_fertility_20261106/sources.json").read_text())["broadbalk_1926_1967"]
    assert hashlib.sha256((ROOT / src["file"]).read_bytes()).hexdigest() == src["sha256"]
    chains = broadbalk_1926_management()
    params = Params(**sel["parameters"])
    r1 = json.loads((ROOT / "output/soil_fertility_20261106/selection.json").read_text())["parameters"]
    preds = {"round2": predict_1926(params, chains), "round1": predict_1926(Params(**r1), chains)}
    txt = json.dumps(preds, indent=1, sort_keys=True)
    (OUT / "predictions_1926_1967.json").write_text(txt)
    h = hashlib.sha256(txt.encode()).hexdigest()
    print("predictions written", h[:16], flush=True)
    obs = observed_1926()                                     # the single read of 1926-1967 grain
    res = {k: score_1926(v, obs, chains) for k, v in preds.items()}
    res["predictions_sha256"] = h
    (OUT / "evaluation.json").write_text(json.dumps(res, indent=1))
    for k in ("round2", "round1"):
        r = res[k]
        print(f"== {k}: {r['qualification']}")
        t1, t2, t3 = r["T1_level"], r["T2_manure"], r["T3_fallow"]
        print(f"  T1 n {t1['n']} MAE {t1['MAE_model']:.3f} (A0 {t1['MAE_A0']:.3f}) bias {t1['mean_log10_bias']:+.3f} obs {t1['observed_mean']:.2f} pred {t1['predicted_mean']:.2f} A0 {t1['A0_mean']:.2f}")
        print(f"  T2 n {t2['n']} MAE {t2['MAE_model']:.3f} null {t2['MAE_null']:.3f} r {t2['Pearson_r']:+.2f} obs {t2['observed_mean']:+.3f} pred {t2['predicted_mean']:+.3f}")
        print(f"  T3 n {t3['n']} MAE {t3['MAE_model']:.3f} null {t3['MAE_null']:.3f} obs {t3['observed_mean']:+.3f} pred {t3['predicted_mean']:+.3f}")
        print("  T3 FYM strips", {s: (round(v['observed_mean'], 3), round(v['predicted_mean'], 3)) for s, v in r["T3_reported_FYM_strips"].items()})
        print("  N strips", {s: (round(v['observed_mean'], 2), round(v['predicted_mean'], 2)) for s, v in r["secondary_N_strips"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=("fit", "evaluate"))
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--maxiter", type=int, default=40)
    a = ap.parse_args()
    fit(a) if a.stage == "fit" else evaluate(a)
