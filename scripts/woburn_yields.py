"""Woburn continuous wheat and barley (1879-1926) under Rothamsted's observed weather as a
declared regional proxy: calibration/low_input_yields_20261105/woburn_plan.json (frozen
before any Woburn yield was read).

    python -I scripts/woburn_yields.py --out output/woburn_yields_20261106
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from harvest.crop_sequences import crop_windows  # noqa: E402
from harvest.earth_yields import FLOOR, calendar_keys, load_weather  # noqa: E402
from harvest.soil_water_dual import dual_soil_water, kcb_curve  # noqa: E402
from broadbalk_water_ledger import daily_weather  # noqa: E402
from scripts.land_people import CROPS  # noqa: E402

PLAN = ROOT / "calibration/low_input_yields_20261105/woburn_plan.json"
CACHE = ROOT / "data/cache/era_low_input_20261105"
SELECTION = ROOT / "output/low_input_yields_20261105/selection.json"
FACTORS = ("fym", "rape_cake", "n", "p", "k", "na", "mg")
K_LEACH, D_REF = 0.109, 91.98
SANDY = dict(FC=0.23, WP=0.11, REW=8.0, ZE=0.10, ZR=1.5, P=0.55)


def capacity(year, weather, crop_name):
    """harvest.earth_yields.capacity with the crop as a parameter (identical otherwise)."""
    keys = calendar_keys(date(year - 1, 9, 1), date(year, 8, 1))
    rows = [weather.get(k, {}) for k in keys]
    if not all(r.get("valid", False) and math.isfinite(r["soil_start"]) for r in rows):
        return None
    inputs = [np.array([r[k] for r in rows]) for k in ("T", "P", "PET", "soil_start")]
    crop = CROPS[crop_name]
    catalogue = crop_windows(*inputs, 0., crops={crop_name: crop})
    idx = [i for i, w in enumerate(catalogue.windows) if w.start + w.length <= 12]
    best = max(idx, key=lambda i: catalogue.energy[i])
    return float(catalogue.energy[best] / (1000 * crop["edible"] * crop["kcal"] * (1 - crop["seed"])))


def stratum(row):
    lv = {f: row[f + "_factor_level"].strip() for f in FACTORS}
    lime = row["lime_factor_level"].strip()
    if lime not in ("nil", "L0"):        # woburn_amendment.json: both name the no-lime level
        return None
    if all(v == "nil" for v in lv.values()):
        return "unmanured"
    if lv["fym"] != "nil" and all(lv[f] == "nil" for f in FACTORS if f != "fym"):
        return "fym_only"
    return None


def read_cases(crop, zipname, prefix):
    z = zipfile.ZipFile(CACHE / zipname)
    rows = list(csv.DictReader(io.StringIO(z.read(f"{prefix}/crop_data.csv").decode("utf-8-sig"))))
    groups = {}
    for r in rows:
        s = stratum(r)
        if s is None:
            continue
        try:
            year = int(r["harvest_year"]); grain = float(r["grain"]); area = float(r["area_ha"])
            dd, mm, yy = (int(x) for x in r["sow_date"].strip().split("/"))   # DD/MM/YYYY (amendment)
            sow = date(yy, mm, dd)
        except ValueError:
            continue
        if not (1879 <= year <= 1926) or not math.isfinite(grain) or grain < 0 or area <= 0:
            continue
        groups.setdefault((year, s), []).append((grain, area, sow))
    cases = []
    for (year, s), g in sorted(groups.items()):
        sows = {x[2] for x in g}
        cases.append(dict(crop=crop, year=year, stratum=s, observed_t_ha=sum(x[0] * x[1] for x in g) / sum(x[1] for x in g),
                          area_ha=sum(x[1] for x in g), sow_date=min(sows).isoformat(), sow_dates_differ=len(sows) > 1,
                          records=len(g)))
    return cases


def harvest_dates():
    prep = json.loads((CACHE / "prepared_wheat.json").read_text())["cases"]
    out = {c["year"]: date.fromisoformat(c["source_records"][0]["harvest_date"]) for c in prep if c["stratum"] == "unmanured_plot3"}
    med = int(statistics.median(d.timetuple().tm_yday for d in out.values()))
    return out, med


def ledger_drainage(cases, weather, hdates, hmed):
    days, rain, et0 = daily_weather(weather, 1926, 3)
    idx = {d: i for i, d in enumerate(days)}
    kcb = np.zeros(len(days)); seasons = {}
    for c in cases:
        if c["stratum"] != "unmanured":
            continue
        s = date.fromisoformat(c["sow_date"])
        h = hdates.get(c["year"], date(c["year"], 1, 1) + timedelta(days=hmed - 1))
        if s not in idx or h not in idx or h <= s:
            continue
        kcb = np.maximum(kcb, kcb_curve(np.arange(len(days)), idx[s], idx[h]))
        seasons[c["year"]] = (s, h)
    f = SANDY
    led = dual_soil_water(rain, et0, kcb, total_available=1000 * (f["FC"] - f["WP"]) * f["ZR"], depletion_fraction=f["P"],
                          total_evaporable=1000 * (f["FC"] - 0.5 * f["WP"]) * f["ZE"], readily_evaporable=f["REW"],
                          initial_depletion=0.5 * 1000 * (f["FC"] - f["WP"]) * f["ZR"])
    D = {y: float(led.drainage[idx[date(y - 1, 10, 1)]:idx[date(y, 4, 1)]].sum()) for y in range(1879, 1927)}
    return D, led.ledger_residual, seasons


def metrics(y, p, constant):
    y, p = np.asarray(y, float), np.asarray(p, float)
    err = np.abs(np.log10(np.maximum(y, FLOOR) / np.maximum(p, FLOOR)))
    rmse = float(np.sqrt(np.mean((p - y) ** 2))); ref = float(np.sqrt(np.mean((constant - y) ** 2)))
    r = float(np.corrcoef(p, y)[0, 1]) if np.ptp(p) > 1e-12 and np.ptp(y) > 1e-12 else None
    return dict(n=int(len(y)), MAE_log10=float(err.mean()), MAE_t_ha=float(np.mean(abs(p - y))), RMSE_t_ha=rmse, Pearson_r=r,
                RMSE_skill_vs_constant=1 - rmse / ref if ref > 0 else None, observed_mean=float(y.mean()),
                predicted_mean=float(p.mean()), fraction_within_factor2=float(np.mean(err <= math.log10(2))))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/woburn_yields_20261106")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(PLAN.read_text())
    sel = json.loads(SELECTION.read_text()); scale, constant = sel["scale"], sel["training_mean_t_ha"]
    assert abs(scale - 0.933) < 0.001, scale
    weather = load_weather(CACHE, 1926, 51.81)
    hdates, hmed = harvest_dates()
    result = dict(plan=str(PLAN.relative_to(ROOT)), weather="Rothamsted observed monthly record as a declared regional proxy (about 40 km)",
                  scale=scale, constant_t_ha=constant, crops={})
    series = {}
    for crop, zipname, prefix in (("wheat", "woburn_wheat_0.zip", "01-WXW6YLD7726"), ("barley", "woburn_barley_0.zip", "01-WXB6YLD7726")):
        cases = read_cases(crop, zipname, prefix)
        D, residual, seasons = ledger_drainage(cases, weather, hdates, hmed)
        for c in cases:
            c["A0"] = capacity(c["year"], weather, crop)
            c["winter_drainage_mm"] = D.get(c["year"])
        cases = [c for c in cases if c["A0"] is not None and c["winter_drainage_mm"] is not None]
        res = dict(ledger_residual_mm=residual, strata={})
        for s in ("unmanured", "fym_only"):
            cs = [c for c in cases if c["stratum"] == s]
            if not cs:
                continue
            y = [c["observed_t_ha"] for c in cs]
            A0 = [c["A0"] for c in cs]; A = [scale * x for x in A0]
            B = [scale * c["A0"] * math.exp(-K_LEACH * (c["winter_drainage_mm"] - D_REF) / 100) for c in cs]
            m = {k: metrics(y, p, constant) for k, p in (("A0", A0), ("A", A), ("B", B))}
            m["drainage_vs_log_yield_r"] = float(np.corrcoef([c["winter_drainage_mm"] for c in cs], np.log(np.maximum(y, FLOOR)))[0, 1])
            if crop == "wheat" and s == "unmanured":
                for k in ("A", "B"):
                    cand = m[k]
                    m[f"qualifies_{k}"] = bool(cand["n"] >= 20 and cand["MAE_log10"] <= 0.95 * m["A0"]["MAE_log10"]
                                               and (cand["Pearson_r"] or 0) > 0 and (cand["RMSE_skill_vs_constant"] or 0) > 0)
            res["strata"][s] = m
            series[(crop, s)] = dict(years=[c["year"] for c in cs], y=y, A=A, B=B)
        res["mean_winter_drainage_mm"] = float(np.mean([c["winter_drainage_mm"] for c in cases])) if cases else None
        result["crops"][crop] = res
    (a.out / "evaluation.json").write_text(json.dumps(result, indent=1))
    for crop, r in result["crops"].items():
        for s, m in r["strata"].items():
            print(crop, s, "n", m["A0"]["n"], "obs mean %.3f" % m["A0"]["observed_mean"],
                  "| A0 MAE %.3f r %+.2f skill %+.2f | A MAE %.3f skill %+.2f | B MAE %.3f r %+.2f skill %+.2f | drainage~logY r %+.2f" % (
                      m["A0"]["MAE_log10"], m["A0"]["Pearson_r"] or 0, m["A0"]["RMSE_skill_vs_constant"] or 0,
                      m["A"]["MAE_log10"], m["A"]["RMSE_skill_vs_constant"] or 0,
                      m["B"]["MAE_log10"], m["B"]["Pearson_r"] or 0, m["B"]["RMSE_skill_vs_constant"] or 0, m["drainage_vs_log_yield_r"]),
                  {k: v for k, v in m.items() if k.startswith("qualifies")})
    figure(a.out, series, result)


def figure(out, series, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 1, figsize=(12.5, 8), constrained_layout=True)
    for ax, crop in zip(axs, ("wheat", "barley")):
        s = series.get((crop, "unmanured"))
        if not s:
            continue
        ax.plot(s["years"], s["y"], "o-", color="#222", lw=1.2, ms=4, label="observed, unmanured (Woburn)")
        ax.plot(s["years"], s["A"], "-", color="#b5651d", lw=1.4, label="A: existing response × 0.933 (Broadbalk-trained)")
        ax.plot(s["years"], s["B"], "-", color="#2b5d8a", lw=1.4, label="B: A with the winter-drainage leaching term")
        m = result["crops"][crop]["strata"]["unmanured"]
        ax.set_ylabel("grain, t/ha")
        ax.set_title(f"Woburn continuous {crop}, unmanured: A r = {m['A']['Pearson_r']:+.2f}, skill {m['A']['RMSE_skill_vs_constant']:+.2f}; "
                     f"B r = {m['B']['Pearson_r']:+.2f}, skill {m['B']['RMSE_skill_vs_constant']:+.2f} (log error A {m['A']['MAE_log10']:.3f}, B {m['B']['MAE_log10']:.3f})", fontsize=10)
        ax.legend(fontsize=8)
    fig.suptitle("Reserved second site: Woburn (sandy loam), weather from Rothamsted 40 km away (declared proxy; Woburn's own records begin in 1928)", fontsize=11)
    fig.savefig(out / "woburn.png", dpi=95)


if __name__ == "__main__":
    main()
