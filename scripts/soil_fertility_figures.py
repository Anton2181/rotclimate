"""Figures for the soil-fertility development fit and the Exhaustion Land evaluation.

    python -I scripts/soil_fertility_figures.py --out output/soil_fertility_20261106 [--evaluation]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

NAMES = {"BB_nil": "Broadbalk, unmanured (plot 3)", "BB_fym": "Broadbalk, manure (FYM 35 t/ha/yr)",
         "WW_nil": "Woburn wheat, unmanured", "WW_fym": "Woburn wheat, manure",
         "WB_nil": "Woburn barley, unmanured", "WB_fym": "Woburn barley, manure"}


def development(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = json.loads((out / "development_series.json").read_text())
    sel = json.loads((out / "selection.json").read_text())
    import soil_fertility_common as C
    fig, axs = plt.subplots(3, 2, figsize=(13, 10), constrained_layout=True, sharey=False)
    for ax, k in zip(axs.flat, NAMES):
        s = d[k]
        crop = "wheat" if k[:2] in ("BB", "WW") else "barley"
        a0 = [C.potential(y, crop)[0] for y in s["years"]]
        ax.plot(s["years"], s["observed"], "o-", color="#222", ms=3.5, lw=1.1, label="observed")
        ax.plot(s["years"], s["predicted"], "-", color="#2f7d32", lw=1.8, label=f"fertility state (log error {s['MAE_log10']:.3f})")
        ax.plot(s["years"], a0, "-", color="#b5651d", lw=1.2, alpha=0.8, label=f"existing response, no memory ({s['A0_MAE_log10']:.3f})")
        ax.set_title(NAMES[k], fontsize=10); ax.set_ylabel("grain, t/ha"); ax.legend(fontsize=7.5, loc="upper right")
        ax.set_ylim(0, max(max(s["observed"]), max(s["predicted"])) * 1.25)
    p = sel["parameters"]
    fig.suptitle("Soil-fertility state (RothC + nitrogen), DEVELOPMENT fit on spent Broadbalk and Woburn series: "
                 f"N input {p['input_n']:.1f} kg/ha/yr, uptake {p['uptake_rate']:.2f}/month, potential {p['kappa']:.2f} x A0, prior manure {p['prior_manure']:.2f} t C/yr",
                 fontsize=10.5)
    fig.savefig(out / "development_fit.png", dpi=95)


def evaluation(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    ev = json.loads((out / "evaluation.json").read_text())
    pred = json.loads((out / "predictions.json").read_text())
    from exhaustion_land_eval import observed
    obs = observed()
    fig, axs = plt.subplots(2, 2, figsize=(13.5, 9), constrained_layout=True)
    groups = [((1, 2, 3, 4), "Plots 1-4: cereals throughout; residues of 0, 6 and 26 years of FYM (1876-1901)",
               {1: ("#222", "1 nil"), 2: ("#8c6d31", "2 FYM 1876-81"), 3: ("#2f7d32", "3 FYM 1876-1901"), 4: ("#5aa05e", "4 FYM + N 1876-1901")}),
              ((1, 5, 6, 9), "Plots 5, 6 (mineral N history) and 9 (P history): red clover 1905/06-1911",
               {1: ("#222", "1 nil"), 5: ("#2b5d8a", "5 N"), 6: ("#5b8fc0", "6 N*"), 9: ("#a0522d", "9 P")})]
    for row, (plots, title, style) in enumerate(groups):
        ax = axs[row, 0]
        for pl in plots:
            col, lab = style[pl]
            ys = sorted(y for (q, y) in obs if q == pl)
            ax.plot(ys, [obs[(pl, y)][0] for y in ys], "o", color=col, ms=4, label=f"plot {lab}, observed")
            span = list(range(1902, 1923))
            line = [pred[str(pl)].get(str(y), {}).get("grain") for y in span]
            ax.plot(span, [np.nan if v is None else v for v in line], "-", color=col, lw=1.6)
            ax.plot([1935], [pred[str(pl)]["1935"]["grain"]], "x", color=col, ms=7, mew=1.8)
        if row == 1:
            ax.axvspan(1905, 1911.9, color="#cfe3cf", alpha=0.5, lw=0); ax.text(1906, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] else 2, "clover", fontsize=8)
        ax.set_title(title + "\n(points observed; lines and x the frozen model; 1923-34 not recorded)", fontsize=9.5); ax.set_ylabel("grain, t/ha"); ax.legend(fontsize=7, ncol=2)
    for ax, key, title in ((axs[0, 1], "M1_manure_memory", "M1 manure memory: plots 2-4 relative to plot 1"),
                           (axs[1, 1], "M2_legume_memory", "M2 legume memory: plots 5-6 relative to plot 1, 1912-1935")):
        m = ev[key]
        o, p = np.array(m["observed"]), np.array(m["predicted"])
        ax.scatter(p, o, s=22, color="#2f7d32", alpha=0.85)
        lim = [min(o.min(), p.min(), 0) - 0.05, max(o.max(), p.max()) + 0.05]
        ax.plot(lim, lim, color="#888", lw=0.8); ax.axhline(0, color="#b5651d", lw=0.8, ls="--")
        ax.set_xlim(lim); ax.set_ylim(lim)
        ax.set_xlabel("predicted log10(plot / plot 1)"); ax.set_ylabel("observed log10(plot / plot 1)")
        r = m["Pearson_r"]
        ax.set_title(f"{title}\nerror {m['MAE_model']:.3f} vs no-memory {m['MAE_null']:.3f} (dashed); r = {r:+.2f}; n = {m['n']}", fontsize=9.5)
    q = ev["qualification"]; m3 = ev["M3_level"]
    fig.suptitle(f"Exhaustion Land, Rothamsted, 1902-1935: single frozen evaluation. M1 {'pass' if q['M1'] else 'FAIL'}, M2 {'pass' if q['M2'] else 'FAIL'}, "
                 f"M3 {'pass' if q['M3'] else 'FAIL'} (level error {m3['MAE_model']:.3f} vs existing {m3['MAE_A0']:.3f})", fontsize=11)
    fig.savefig(out / "exhaustion_land.png", dpi=95)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "output/soil_fertility_20261106")
    ap.add_argument("--evaluation", action="store_true")
    a = ap.parse_args()
    evaluation(a.out) if a.evaluation else development(a.out)
