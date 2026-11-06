"""Development diagnostic: the dual soil-water ledger on Broadbalk's observed seasons
(calibration/low_input_yields_20261105/water_ledger_development.json).

    python -I scripts/broadbalk_water_ledger.py --out output/broadbalk_water_20261106
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from harvest.earth_yields import load_weather  # noqa: E402
from harvest.soil_water_dual import dual_soil_water, kcb_curve  # noqa: E402

PLAN = ROOT / "calibration/low_input_yields_20261105/water_ledger_development.json"
YPLAN = ROOT / "calibration/low_input_yields_20261105/plan.json"
CACHE = ROOT / "data/cache/era_low_input_20261105"
FC, WP, ZE, ZR = 0.335, 0.205, 0.10, 1.5
TAW = 1000 * (FC - WP) * ZR
TEW = 1000 * (FC - 0.5 * WP) * ZE
REW, P_FRAC = 9.5, 0.55
START = date(1878, 1, 1)


def daily_weather(weather, last_year, every):
    days, rain, et0 = [], [], []
    for year in range(1878, last_year + 1):
        for month in range(1, 13):
            r = weather[(year, month)]
            n = monthrange(year, month)[1]
            P = r["P"] if math.isfinite(r["P"]) else 0.0
            pet = r["PET"] if math.isfinite(r["PET"]) else 0.0
            events = [d for d in range(n) if d % every == every // 2] or [n // 2]
            for d in range(n):
                days.append(date(year, month, d + 1))
                et0.append(pet / n)
                rain.append(P / len(events) if d in events else 0.0)
    return days, np.array(rain), np.array(et0)


def run(cases, weather, last_year, every):
    days, rain, et0 = daily_weather(weather, last_year, every)
    idx = {d: i for i, d in enumerate(days)}
    seasons = {}
    for c in cases:
        if c["stratum"] != "unmanured_plot3":
            continue
        r = c["source_records"][0]
        seasons[c["year"]] = (date.fromisoformat(r["sow_date"]), date.fromisoformat(r["harvest_date"]))
    kcb = np.zeros(len(days))
    for year, (s, h) in seasons.items():
        kcb = np.maximum(kcb, kcb_curve(np.arange(len(days)), idx[s], idx[h]))
    led = dual_soil_water(rain, et0, kcb, total_available=TAW, depletion_fraction=P_FRAC, total_evaporable=TEW,
                          readily_evaporable=REW, initial_depletion=TAW / 2)
    rows = {}
    for year, (s, h) in seasons.items():
        a, b = idx[s], idx[h] + 1
        w0, w1 = idx[date(year - 1, 10, 1)], idx[date(year, 4, 1)]
        g0, g1 = idx[date(year, 4, 1)], idx[date(year, 8, 1)]
        T, Tp = led.transpiration, led.potential_transpiration
        rows[year] = dict(season_T_ratio=float(T[a:b].sum() / max(Tp[a:b].sum(), 1e-9)),
                          season_T=float(T[a:b].sum()), season_E=float(led.evaporation[a:b].sum()),
                          season_ET=float(T[a:b].sum() + led.evaporation[a:b].sum()),
                          winter_drainage=float(led.drainage[w0:w1].sum()),
                          spring_summer_T_ratio=float(T[g0:g1].sum() / max(Tp[g0:g1].sum(), 1e-9)),
                          season_days=b - a)
    return days, rain, et0, kcb, led, rows, seasons


def corr(x, y):
    from scipy.stats import pearsonr, spearmanr
    x, y = np.asarray(x, float), np.asarray(y, float)
    return dict(pearson=float(pearsonr(x, y)[0]), spearman=float(spearmanr(x, y)[0]), n=int(len(x)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/broadbalk_water_20261106")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    yplan = json.loads(YPLAN.read_text())
    last = yplan["split"]["evaluation"][1]
    prepared = json.loads((CACHE / "prepared_wheat.json").read_text())
    cases = prepared["cases"]
    weather = load_weather(CACHE, last, yplan["site"]["latitude"])
    obs = {(c["year"], c["stratum"]): c["observed_t_ha"] for c in cases}
    out = dict(plan=str(PLAN.relative_to(ROOT)), status="development diagnostic on a spent pool; no fit, no adoption",
               soil=dict(TAW_mm=TAW, TEW_mm=TEW, REW_mm=REW, p=P_FRAC), runs={})
    keep = None
    for every in (3, 1, 7):
        days, rain, et0, kcb, led, rows, seasons = run(cases, weather, last, every)
        years = sorted(rows)
        res = dict(ledger_residual_mm=led.ledger_residual,
                   totals_mm=dict(rain=float(rain.sum()), transpiration=float(led.transpiration.sum()),
                                  evaporation=float(led.evaporation.sum()), drainage=float(led.drainage.sum())),
                   years=rows, correlations={})
        for stratum in ("unmanured_plot3", "fym_only"):
            ys = [y for y in years if (y, stratum) in obs]
            yv = [obs[(y, stratum)] for y in ys]
            for k in ("season_T_ratio", "spring_summer_T_ratio", "winter_drainage", "season_E", "season_ET"):
                res["correlations"][f"{stratum}:{k}"] = corr([rows[y][k] for y in ys], yv)
        out["runs"][f"rain_every_{every}_days"] = res
        if every == 3:
            keep = (days, rain, et0, kcb, led, rows, seasons, years)
    (a.out / "diagnostic.json").write_text(json.dumps(out, indent=1))
    days, rain, et0, kcb, led, rows, seasons, years = keep
    figures(a.out, days, rain, et0, kcb, led, rows, seasons, years, obs)
    r3 = out["runs"]["rain_every_3_days"]
    print("closure", r3["ledger_residual_mm"], r3["totals_mm"])
    for k, v in r3["correlations"].items():
        print(f"  {k:40s} r {v['pearson']:+.2f}  rho {v['spearman']:+.2f}  n {v['n']}")
    for ev in (1, 7):
        c = out["runs"][f"rain_every_{ev}_days"]["correlations"]
        print(f"rain every {ev} d: plot3 winter drainage r {c['unmanured_plot3:winter_drainage']['pearson']:+.2f}, "
              f"T ratio r {c['unmanured_plot3:season_T_ratio']['pearson']:+.2f}")


def figures(out, days, rain, et0, kcb, led, rows, seasons, years, obs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    idx = {d: i for i, d in enumerate(days)}
    # 1. two contrasting seasons: the wettest and the driest winter
    wet = max(years, key=lambda y: rows[y]["winter_drainage"]); dry = min(years, key=lambda y: rows[y]["winter_drainage"])
    fig, axs = plt.subplots(2, 1, figsize=(12, 8.2), constrained_layout=True, sharex=False)
    for ax, year in zip(axs, (wet, dry)):
        a, b = idx[date(year - 1, 9, 1)], idx[date(year, 8, 31)] + 1
        x = np.array(days[a:b])
        stored = TAW - led.root_depletion[a:b]
        ax.fill_between(x, 0, stored, color="#9cc3e4", alpha=0.55, label="water held in the root zone (above wilting point)")
        ax.axhline(TAW * (1 - P_FRAC), color="#3b6e9e", lw=0.8, ls="--")
        ax.text(x[3], TAW * (1 - P_FRAC) + 3, "below this, transpiration is cut", fontsize=8, color="#3b6e9e")
        ax2 = ax.twinx()
        ax2.bar(x, led.drainage[a:b], width=1.0, color="#2b5d8a", label="drainage")
        cT = np.cumsum(led.transpiration[a:b]); cE = np.cumsum(led.evaporation[a:b])
        ax.plot(x, cT, color="#2f7d32", lw=1.8, label="transpiration, cumulative")
        ax.plot(x, cE, color="#b5651d", lw=1.8, label="soil evaporation, cumulative")
        ax.plot(x, 150 * kcb[a:b], color="#6a6a6a", lw=0.8, ls=":", label="basal crop coefficient × 150")
        s, h = seasons[year]
        for d, lab in ((s, "sown"), (h, "harvested")):
            ax.axvline(d, color="#333", lw=0.8); ax.text(d, TAW * 0.97, " " + lab, fontsize=8, va="top")
        ax.set_ylim(0, max(TAW, cT.max()) * 1.05); ax2.set_ylim(0, max(15, led.drainage[a:b].max() * 3))
        ax.set_ylabel("mm"); ax2.set_ylabel("drainage, mm/day", color="#2b5d8a")
        r = rows[year]
        ax.set_title(f"{year - 1}–{year} season: winter drainage {r['winter_drainage']:.0f} mm, transpiration {r['season_T_ratio']:.0%} of potential, "
                     f"evaporation {r['season_E']:.0f} mm; observed unfertilised grain {obs.get((year, 'unmanured_plot3'), float('nan')):.2f} t/ha", fontsize=10)
        if ax is axs[0]:
            h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper right", ncol=2)
    fig.suptitle("Broadbalk, Rothamsted: the dual crop-water ledger on observed weather (FAO-56; the wettest and the driest winter, 1879–1925)", fontsize=11)
    fig.savefig(out / "ledger_seasons.png", dpi=95)
    plt.close(fig)
    # 2. yields against the ledger's season terms
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    for ax, key, lab in ((axs[0], "winter_drainage", "winter drainage, Oct–Mar (mm)"),
                         (axs[1], "season_T_ratio", "season transpiration / potential"),
                         (axs[2], "season_E", "season soil evaporation (mm)")):
        for stratum, col, name in (("unmanured_plot3", "#b5651d", "unfertilised (plot 3)"), ("fym_only", "#2f7d32", "manure only")):
            ys = [y for y in years if (y, stratum) in obs]
            xv = np.array([rows[y][key] for y in ys]); yv = np.array([obs[(y, stratum)] for y in ys])
            r = np.corrcoef(xv, yv)[0, 1]
            ax.scatter(xv, yv, s=18, color=col, alpha=0.8, label=f"{name}, r = {r:+.2f}")
        ax.set_xlabel(lab); ax.set_ylabel("observed grain, t/ha"); ax.legend(fontsize=8)
    fig.suptitle("Broadbalk 1879–1925 (45 seasons; development data, already spent): observed wheat yields against the ledger", fontsize=11)
    fig.savefig(out / "yields_vs_ledger.png", dpi=95)


if __name__ == "__main__":
    main()
