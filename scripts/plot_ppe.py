"""History-matching graphs for the PPE searches W1-W4 (calibration/ppe_20261123/W*_records).

    python3 -I scripts/plot_ppe.py OUTDIR
"""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.ticker
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import ppe

C1, C2, INK, INK2, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
CAP = 1.10
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
REC = ROOT / "calibration/ppe_20261123"
TITLE = {1: "W1  subsidence warming, 12 knobs (ref r51)", 2: "W2  widened box, 12 knobs (ref r52)",
         3: "W3  dry heating + terrain eddies, 10 knobs", 4: "W4  e52c stable layer, 9 knobs"}


def load(w):
    plan = json.loads((REC / f"plan_W{w}.json").read_text())
    out = REC / f"W{w}_records"
    res, names, X, Y, Rf = ppe.training(plan, out)
    tn = ppe.t_names_of(plan)
    s55, t, p, s49 = ppe.gate_terms(Y, Rf, names, tn)
    obj = ppe.objective(plan, s55, t, p, s49)
    return plan, out, res, X, obj, s55


def fig_waves(dst):
    fig, axs = plt.subplots(2, 2, figsize=(10, 6.4), sharey=True)
    for w, ax in zip([1, 2, 3, 4], axs.flat):
        plan, out, res, X, obj, s55 = load(w)
        wave = np.array([r["wave"] for r in res]); i = np.arange(len(res))
        y = np.minimum(s55, CAP); bad = obj > s55 + 1e-9
        ax.axhspan(0.995, 1.005, color=GRID, lw=0)
        ax.axhline(1.0, color=INK2, lw=1, ls=(0, (3, 3)))
        for sel, c, lab in [(wave == 1, C1, "Sobol design"), (wave > 1, C2, "emulator-chosen")]:
            ax.scatter(i[sel & ~bad], y[sel & ~bad], s=16, c=c, edgecolors="#fcfcfb", linewidths=0.6, label=lab, zorder=3)
            ax.scatter(i[sel & bad], y[sel & bad], s=14, facecolors="none", edgecolors=c, linewidths=0.9, zorder=3,
                       label=lab + ", fails T/P/S49 limit")
        ax.step(i, np.minimum.accumulate(obj), where="post", color=INK, lw=1.5, label="best so far", zorder=4)
        b = int(np.argmin(obj))
        ax.annotate(f"best {obj[b]:.4f}", (b, obj[b]), xytext=(6, -14), textcoords="offset points", color=INK, fontsize=8)
        ax.set_title(TITLE[w], loc="left", fontsize=9.5, color=INK)
        ax.set_ylim(0.98, CAP + 0.005); ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_xlabel("evaluation")
    axs[0, 0].set_ylabel("score S vs reference (< 1 better)"); axs[1, 0].set_ylabel("score S")
    axs[0, 0].legend(frameon=False, fontsize=7.5, loc="upper right", ncol=1)
    fig.suptitle("PPE history matching: every evaluated parameter set\nline = best admissible so far; above 1.10 drawn at 1.10; grey band = score noise ±0.005",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(); fig.savefig(dst, dpi=160); plt.close(fig)


def fig_emulator(dst):
    plan, out, res, X, obj, s55 = load(4)
    em = json.loads((out / "emulator.json").read_text())
    loo = np.array(em["loo"])
    des = {d["name"]: d.get("predicted_objective") for d in json.loads((out / "design.json").read_text())}
    w2 = [(des[r["name"]], o) for r, o in zip(res, obj) if r["wave"] == 2 and des.get(r["name"])]
    w2 = np.array(w2)
    fig, ax = plt.subplots(figsize=(5.4, 5))
    lo, hi = 0.985, 1.10
    ax.plot([lo, hi], [lo, hi], color=INK2, lw=1, ls=(0, (3, 3)))
    m = (loo[:, 0] < hi) & (loo[:, 1] < hi)
    ax.scatter(loo[m, 1], loo[m, 0], s=18, c=C1, edgecolors="#fcfcfb", linewidths=0.6, label="wave 1, leave-one-out")
    ax.scatter(w2[:, 0], w2[:, 1], s=26, c=C2, edgecolors="#fcfcfb", linewidths=0.6, label="wave 2, predicted then run")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("emulator prediction (S)"); ax.set_ylabel("actual (S)")
    ax.set_title(f"W4 emulator check  (LOO RMSE {em['loo_rmse_S55']:.3f}, r {em['loo_corr']:.2f})", loc="left", fontsize=9.5, color=INK)
    ax.grid(color=GRID, lw=0.6); ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(dst, dpi=160); plt.close(fig)


def fig_knobs(dst):
    plan, out, res, X, obj, s55 = load(4)
    knobs = list(plan["knobs"]); sens = json.loads((out / "emulator.json").read_text())["sensitivity"]
    knobs.sort(key=lambda k: -sens.get(k, 0))
    vals = {k: np.array([r["x"][k] for r in res]) for k in knobs}
    b = int(np.argmin(obj)); y = np.minimum(s55, 1.12); bad = obj > s55 + 1e-9
    fig, axs = plt.subplots(3, 3, figsize=(10, 7.6), sharey=True)
    for k, ax in zip(knobs, axs.flat):
        lo, hi, sc = plan["knobs"][k]
        ax.axhspan(0.995, 1.005, color=GRID, lw=0); ax.axhline(1.0, color=INK2, lw=1, ls=(0, (3, 3)))
        ax.scatter(vals[k][~bad], y[~bad], s=12, c=C1, edgecolors="none")
        ax.scatter(vals[k][bad], y[bad], s=11, facecolors="none", edgecolors=C1, linewidths=0.7)
        ax.scatter([vals[k][b]], [s55[b]], s=60, c=C2, edgecolors=INK, linewidths=0.8, zorder=4)
        if sc == "log":
            ax.set_xscale("log"); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_xticks(np.round(np.geomspace(lo, hi, 4), 2 if hi < 10 else -1))
        ax.set_xlim(lo * (0.95 if sc == "log" else 1) - (0 if sc == "log" else 0.03 * (hi - lo)),
                    hi * (1.05 if sc == "log" else 1) + (0 if sc == "log" else 0.03 * (hi - lo)))
        ax.set_title(f"{k}  (sensitivity {sens.get(k, 0):.2f})", loc="left", fontsize=8.5, color=INK)
        ax.set_ylim(0.99, 1.125); ax.grid(axis="y", color=GRID, lw=0.6)
    for ax in axs[:, 0]: ax.set_ylabel("score S")
    fig.suptitle("W4: score against each knob, sorted by emulator sensitivity\norange = best (the declared base r52 + e52c 0.3); hollow = fails T/P/S49 limit; above 1.12 drawn at 1.12",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(); fig.savefig(dst, dpi=160); plt.close(fig)


if __name__ == "__main__":
    d = Path(sys.argv[1]); d.mkdir(parents=True, exist_ok=True)
    fig_waves(d / "ppe_waves.png"); fig_emulator(d / "ppe_w4_emulator.png"); fig_knobs(d / "ppe_w4_knobs.png")
    print("ok")
