"""County seats across 1,800 years of China: which spacing rule carries over.

    python3 -I scripts/plot_polity_eras.py --out output/polity_earth/seat_rule.png

Reads calibration/polity_20261025/eras_e1.json (scripts/polity_eras_check.py --stage e1).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SURFACE, INK, INK_SOFT, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]


def style(ax, title):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(color=GRID, lw=0.8, axis="y"); ax.set_axisbelow(True); ax.tick_params(colors=INK_SOFT, length=0)
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    e = json.loads((ROOT / "calibration/polity_20261025/eras_e1.json").read_text())
    plt.rcParams.update({"font.size": 9.5, "text.color": INK, "axes.labelcolor": INK_SOFT})
    fig, ax = plt.subplots(1, 2, figsize=(13, 5), facecolor=SURFACE, constrained_layout=True,
                           gridspec_kw={"width_ratios": [1.5, 1]})
    A = ax[0]; style(A, "County seats per era: recorded and predicted with the AD 2 constants")
    eras = ["742AD", "1102AD", "1820AD"]
    rules = list(e["test"].keys())
    x = np.arange(len(eras)); w = 0.2
    actual = [e["test"][rules[0]]["eras"][y]["actual"] for y in eras]
    A.bar(x - 1.5 * w, actual, w * 0.92, color=INK_SOFT, label="recorded seats")
    for k, r in enumerate(rules):
        vals = [e["test"][r]["eras"][y]["predicted"] for y in eras]
        A.bar(x + (k - 0.5) * w, vals, w * 0.92, color=SERIES[k],
              label=f"{r} · deviance {e['test'][r]['summed']:,.0f}")
    names = ["Tang 742", "Song 1102", "Qing 1820"]
    A.set_xticks(x, [f"{n}\n{e['eras'][y]['people_M']:.0f} M people · {e['eras'][y]['area_Mkm2']:.1f} M km²"
                     for n, y in zip(names, eras)])
    A.set_ylabel("seats"); A.legend(frameon=False, fontsize=8.5, loc="upper left")
    B = ax[1]; style(B, "AD 2: fit of seats ~ people^β × area^(1−β)")
    fits = e["fit_2AD"]["by_beta"]
    b = sorted(float(k) for k in fits); dv = [fits[str(k) if str(k) in fits else k]["deviance"] for k in
                                             [str(v) if str(v) in fits else v for v in b]]
    B.plot(b, dv, color=SERIES[2], lw=2, marker="o", ms=5, markeredgecolor=SURFACE)
    best = e["fit_2AD"]["best_beta"]
    B.axvline(float(best), color=INK_SOFT, lw=1, ls=":")
    B.text(float(best) + 0.02, max(dv) * 0.9, f"best β = {float(best):g}", fontsize=9, color=INK_SOFT)
    B.text(0.0, dv[0], "  one per\n  fixed area", fontsize=8.5, color=INK_SOFT, va="bottom")
    B.text(1.0, dv[-1], "one per N  \npeople  ", fontsize=8.5, color=INK_SOFT, ha="right", va="bottom")
    B.set_xlabel("β"); B.set_ylabel("Poisson deviance, 103 commanderies")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
