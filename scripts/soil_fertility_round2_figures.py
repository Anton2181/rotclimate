"""Figures for soil-fertility round 2.

    python -I scripts/soil_fertility_round2_figures.py development
    python -I scripts/soil_fertility_round2_figures.py evaluation
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

OUT = ROOT / "output/soil_fertility_round2_20261106"


def development():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = json.loads((OUT / "development.json").read_text())
    sel = json.loads((OUT / "selection.json").read_text())
    fig, axs = plt.subplots(2, 3, figsize=(15, 8.6), constrained_layout=True)
    panels = [("broadbalk:3", "Broadbalk plot 3, unmanured"), ("broadbalk:2.2", "Broadbalk 2.2, FYM since 1843"),
              ("woburn_barley:1", "Woburn barley plot 1, never manured"), ("woburn_barley:11/b", "Woburn barley 11b, FYM")]
    for ax, (k, title) in zip(axs.flat[:4], panels):
        s = d["series"][k]
        ax.plot(s["years"], s["observed"], "o-", color="#222", ms=3, lw=1, label="observed")
        ax.plot(s["years"], s["predicted"], "-", color="#2f7d32", lw=1.8, label=f"round 2 (log error {s['MAE_log10']:.3f})")
        ax.set_title(f"{title}; existing response {s['A0_MAE_log10']:.3f}", fontsize=9.5); ax.set_ylabel("grain, t/ha"); ax.legend(fontsize=8)
        ax.set_ylim(0, max(max(s["observed"]), max(s["predicted"])) * 1.2)
    ax = axs.flat[4]
    for k, col in (("3", "#222"), ("2.2", "#2f7d32"), ("2.1", "#8c6d31")):
        m = d["soc_model_1843_1925"][k]
        ys = sorted(int(y) for y in m)
        ax.plot(ys, [m[str(y)] for y in ys], "-", color=col, lw=1.6, label=f"plot {k} model")
        ob = d["soc"][k]
        ax.plot([int(y) for y in ob], [v[0] for v in ob.values()], "o", color=col, ms=6, label=f"plot {k} measured")
    ax.plot([1843], [28.8], "s", color="#888", ms=6, label="1843 estimate (start)")
    ax.set_title("Broadbalk soil carbon, 0-23 cm (t C/ha): development constraint", fontsize=9.5); ax.legend(fontsize=7, ncol=2); ax.set_ylabel("t C/ha")
    ax = axs.flat[5]
    wf = d["wheat_fallow"]
    labels, obs_d, mod_d = [], [], []
    for k, v in wf.items():
        labels.append(k); obs_d.append(v["target_delta"]); mod_d.append(v["model_wheat_fallow"] - v["model_continuous"])
    x = np.arange(len(labels))
    ax.bar(x - 0.18, obs_d, 0.34, color="#888", label="Alternate Wheat and Fallow (e-RA aggregate)")
    ax.bar(x + 0.18, mod_d, 0.34, color="#2f7d32", label="round-2 model")
    ax.set_xticks(x); ax.set_xticklabels([f"{k}" for k in labels]); ax.axhline(0, color="#444", lw=0.8)
    ax.set_ylabel("wheat after fallow minus continuous wheat, t/ha"); ax.set_title("Fallow benefit: development constraint", fontsize=9.5); ax.legend(fontsize=8)
    p = sel["fitted"]
    fig.suptitle("Soil-fertility round 2, DEVELOPMENT (spent data): fixation+dry input F = %.1f kg N/ha/yr + measured wet deposition, uptake %.2f/month x T/10, "
                 "potential %.2f x A0, FYM humified %.2f, Woburn prior manure %.2f t C/yr" % (p["input_n"], p["uptake_rate"], p["kappa"], p["fym_hum"], p["prior_manure"]),
                 fontsize=10)
    fig.savefig(OUT / "development.png", dpi=95)


def evaluation():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from soil_fertility_round2 import broadbalk_1926_management, last_fallow, observed_1926
    ev = json.loads((OUT / "evaluation.json").read_text())
    pr = json.loads((OUT / "predictions_1926_1967.json").read_text())
    obs = observed_1926()
    chains = broadbalk_1926_management()
    fig, axs = plt.subplots(2, 2, figsize=(14, 9.5), constrained_layout=True)
    ax = axs[0, 0]
    years = list(range(1926, 1968))
    for st, col, lab in (("3", "#222", "strip 3 nil"), ("22", "#2f7d32", "strip 22 FYM since 1843"), ("21", "#8c6d31", "strip 21 FYM since 1885")):
        om = [np.mean([g for (pl, y), g in obs.items() if pl.startswith(st + "|") and int(y) == t] or [np.nan]) for t in years]
        pm = [np.mean([v[str(t)] for pl, v in pr["round2"].items() if pl.startswith(st + "|") and str(t) in v and (pl, str(t)) in obs] or [np.nan]) for t in years]
        ax.plot(years, om, "o", color=col, ms=3.5, label=f"{lab}, observed (mean of sections)")
        ax.plot(years, pm, "-", color=col, lw=1.6)
    p1 = [np.mean([v[str(t)] for pl, v in pr["round1"].items() if pl.startswith("3|") and str(t) in v and (pl, str(t)) in obs] or [np.nan]) for t in years]
    ax.plot(years, p1, ":", color="#b5651d", lw=1.6, label="strip 3, round-1 model")
    ax.set_ylabel("grain, t/ha"); ax.legend(fontsize=7.5); ax.set_title("Broadbalk 1926-1967: lines round-2 model (frozen), points observed", fontsize=9.5)
    r2 = ev["round2"]
    ax = axs[0, 1]
    t1 = r2["T1_level"]
    labels = ["observed", "round 2", "round 1", "existing response"]
    vals = [t1["observed_mean"], t1["predicted_mean"], ev["round1"]["T1_level"]["predicted_mean"], t1["A0_mean"]]
    ax.bar(labels, vals, color=["#222", "#2f7d32", "#b5651d", "#c9a27a"])
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_ylabel("mean grain, strip 3 (t/ha)")
    ax.set_title(f"T1 unmanured level: log error round 2 {t1['MAE_model']:.3f}, round 1 {ev['round1']['T1_level']['MAE_model']:.3f}, existing {t1['MAE_A0']:.3f}; "
                 f"bias {t1['mean_log10_bias']:+.3f}", fontsize=9)
    ax = axs[1, 0]
    # T3 per year
    fo, fp, fy = [], [], []
    lg = lambda x: math.log10(max(x, 0.05))   # noqa: E731
    for t in years:
        first, later = [], []
        for (st, sec), hist in chains.items():
            if st != "3":
                continue
            pl = f"3|{sec}"
            if (pl, str(t)) not in obs or str(t) not in pr["round2"].get(pl, {}):
                continue
            lf = last_fallow(hist, t)
            if lf == t - 1:
                first.append(pl)
            elif lf is None or lf <= t - 2:
                later.append(pl)
        if first and later:
            fy.append(t)
            fo.append(np.mean([lg(obs[(q, str(t))]) for q in first]) - np.mean([lg(obs[(q, str(t))]) for q in later]))
            fp.append(np.mean([lg(pr["round2"][q][str(t)]) for q in first]) - np.mean([lg(pr["round2"][q][str(t)]) for q in later]))
    ax.bar(np.array(fy) - 0.2, fo, 0.4, color="#222", label="observed")
    ax.bar(np.array(fy) + 0.2, fp, 0.4, color="#2f7d32", label="round-2 model")
    ax.axhline(0, color="#444", lw=0.8)
    t3 = r2["T3_fallow"]
    ax.set_ylabel("log10(first wheat after fallow / later wheats)")
    ax.set_title(f"T3 fallow benefit, strip 3, same year: observed mean {t3['observed_mean']:+.3f} (x{10 ** t3['observed_mean']:.2f}), "
                 f"model {t3['predicted_mean']:+.3f} (x{10 ** t3['predicted_mean']:.2f}); error {t3['MAE_model']:.3f} vs null {t3['MAE_null']:.3f}", fontsize=9)
    ax.legend(fontsize=8)
    ax = axs[1, 1]
    t2 = r2["T2_manure"]
    ro, rp = [], []
    for (pl, y), g in obs.items():
        st, sec = pl.split("|")
        if st in ("21", "22") and (f"3|{sec}", y) in obs and y in pr["round2"].get(pl, {}) and y in pr["round2"].get(f"3|{sec}", {}):
            ro.append(lg(g) - lg(obs[(f"3|{sec}", y)])); rp.append(lg(pr["round2"][pl][y]) - lg(pr["round2"][f"3|{sec}"][y]))
    ax.scatter(rp, ro, s=12, color="#2f7d32", alpha=0.6)
    lim = [min(min(ro), min(rp), 0) - 0.05, max(max(ro), max(rp)) + 0.05]
    ax.plot(lim, lim, color="#888", lw=0.8); ax.axhline(0, color="#b5651d", ls="--", lw=0.8)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("predicted log10(FYM strip / strip 3)"); ax.set_ylabel("observed")
    ax.set_title(f"T2 manure contrast: error {t2['MAE_model']:.3f} vs no-memory {t2['MAE_null']:.3f}; r = {t2['Pearson_r']:+.2f}; "
                 f"obs x{10 ** t2['observed_mean']:.2f}, model x{10 ** t2['predicted_mean']:.2f}", fontsize=9)
    q = r2["qualification"]
    fig.suptitle(f"Broadbalk 1926-1967, single frozen evaluation of soil-fertility round 2: T1 {'pass' if q['T1'] else 'FAIL'}, "
                 f"T2 {'pass' if q['T2'] else 'FAIL'}, T3 {'pass' if q['T3'] else 'FAIL'}", fontsize=11)
    fig.savefig(OUT / "evaluation_1926_1967.png", dpi=95)


if __name__ == "__main__":
    {"development": development, "evaluation": evaluation}[sys.argv[1]]()
