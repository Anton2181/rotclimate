"""Preview (no adoption): equilibrium cereal yields under farming regimes with the frozen,
qualified round-2 soil-fertility selection, on Rothamsted's observed 1878-1937 weather
cycled six times (360 years) from the Broadbalk start state; last 60 years reported.

N input scenarios (total non-fertilizer N, kg/ha/yr, held constant):
  fitted 1850-1925 England = F + measured wet deposition in 1900 (industrial era);
  AD 200 central 10, low 5, high 20 (pre-industrial deposition <= 0.5-2, free-living
  fixation 1-15, seed about 3; literature in reports/SOIL_FERTILITY_ROUND2_20261106.md).

    python -I scripts/soil_fertility_regimes_r2.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

import soil_fertility_common as C  # noqa: E402
from harvest.soil_fertility import Params, Season, simulate, wet_deposition  # noqa: E402
from soil_fertility_round2 import BB_START, CLOVER_PLOUGHED, CLOVER_YEARLY  # noqa: E402

OUT = ROOT / "output/soil_fertility_round2_20261106"
REGIMES = {
    "continuous cereal, nothing returned": ["wheat"],
    "wheat / bare fallow (two-field)": ["wheat", "fallow"],
    "wheat / barley / bare fallow (three-field)": ["wheat", "barley", "fallow"],
    "wheat / barley / clover": ["wheat", "barley", "clover"],
    "continuous cereal + 5 t/ha FYM": ["wheat+fym5"],
    "continuous cereal + 10 t/ha FYM": ["wheat+fym10"],
}
CYCLES, Y0, Y1 = 6, 1878, 1937


def run_regime(seq, params):
    n = Y1 - Y0 + 1
    rows, _, _ = C.forcing_rows(Y0, Y1)
    cal = {y: seq[i % len(seq)].split("+")[0] for i, y in enumerate(range(Y0 + 1, Y1 + 1))}
    drain, _ = C.monthly_drainage("rothamsted", Y0, Y1, cal)
    forcing, seasons, events = [], [], {}
    for c in range(CYCLES):
        off = c * n
        forcing += [dict(r, year=r["year"] + off, drainage=drain[(r["year"], r["month"])]) for r in rows]
        for i, y in enumerate(range(Y0 + 1, Y1 + 1)):
            kind = seq[i % len(seq)]
            base = kind.split("+")[0]
            s = C.season(base, y)
            sh = lambda m: frozenset((yy + off, mm) for yy, mm in m)   # noqa: E731
            curve = {(yy + off, mm): v for (yy, mm), v in (s.curve or {}).items()} or None
            seasons.append(Season(s.crop, (s.harvest[0] + off, s.harvest[1]), sh(s.uptake), sh(s.vegetated), s.potential_t_ha,
                                  f"{base} {y + off}", curve))
            if "+fym" in kind:
                t = float(kind.split("fym")[1])
                events.setdefault((y - 1 + off, 10), []).append(("fym", t * C.FYM_C_PER_T, t * C.FYM_N_PER_T))
            if base == "clover":
                events.setdefault((y + off, 10), []).append(("residue",) + CLOVER_YEARLY)
                events.setdefault((y + off, 11), []).append(("residue",) + CLOVER_PLOUGHED)
    res = simulate(forcing, seasons, params, C.SOILS["rothamsted"]["clay"], C.water_mm("rothamsted"),
                   start=C.start_pools("rothamsted", 0.0, BB_START), events=events)
    last = [s for s in res["seasons"] if s["harvest"][0] > Y0 + (CYCLES - 1) * n]
    grain = [s["grain_t_ha"] for s in last if s["grain_t_ha"] is not None]
    years = len({s["harvest"][0] for s in last})
    return dict(per_cropped_ha=float(np.mean(grain)), per_rotation_ha=float(np.sum(grain) / years),
                cropped_share=len(grain) / years, soc_total_end=res["pools"].active_c + 2.26)


def main():
    sel = json.loads((OUT / "selection.json").read_text())
    base = Params(**sel["parameters"])
    fitted_total = round(base.input_n + wet_deposition(1900), 1)
    scen = {"fitted 1850-1925 England (%.0f)" % fitted_total: fitted_total, "AD 200 high (20)": 20.0, "AD 200 central (10)": 10.0, "AD 200 low (5)": 5.0}
    out = dict(status="preview, not adopted; frozen round-2 selection with the N input replaced as stated", selection=sel["fitted"],
               A0_mean_wheat=C.a0_mean("wheat"), scenarios=scen, regimes={})
    for name, seq in REGIMES.items():
        out["regimes"][name] = {k: run_regime(seq, replace(base, input_n=v, wet_deposition=False)) for k, v in scen.items()}
        print(f"{name:44s} " + "  ".join(f"{k.split(' (')[0][-7:]}: {r['per_cropped_ha']:.2f}/{r['per_rotation_ha']:.2f}"
                                          for k, r in out["regimes"][name].items()), flush=True)
    (OUT / "regimes_preview.json").write_text(json.dumps(out, indent=1))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.6), constrained_layout=True, sharey=True)
    names = list(REGIMES)
    cols = ["#1f5e22", "#4f8f4a", "#8fbf84", "#cfe3c7"]
    for ax, key, title in ((axs[0], "per_cropped_ha", "grain per CROPPED hectare"), (axs[1], "per_rotation_ha", "grain per hectare of the WHOLE rotation")):
        w = 0.2
        for j, k in enumerate(scen):
            v = [out["regimes"][n][k][key] for n in names]
            ax.barh(np.arange(len(names)) + (j - 1.5) * w, v, height=w - 0.02, color=cols[j], label=f"N input {k}")
        ax.axvline(out["A0_mean_wheat"], color="#b5651d", ls="--", lw=1)
        ax.text(out["A0_mean_wheat"], -0.6, " existing response", color="#b5651d", fontsize=8)
        ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9); ax.invert_yaxis()
        ax.set_xlabel("t/ha/yr (last 60 of 360 years, Rothamsted weather 1878-1937 cycled)"); ax.set_title(title, fontsize=10)
        ax.legend(fontsize=7.5, loc="lower right")
    fig.suptitle("Preview only: equilibrium yields by farming regime, qualified round-2 soil-fertility state (Rothamsted soil and weather)", fontsize=11)
    fig.savefig(OUT / "regimes_preview.png", dpi=95)


if __name__ == "__main__" and len(sys.argv) == 1:
    main()


def sweep():
    """Yield per rotation hectare against the total non-fertilizer N input, all regimes."""
    sel = json.loads((OUT / "selection.json").read_text())
    base = Params(**sel["parameters"])
    fitted = base.input_n + wet_deposition(1900)
    inputs = [5, 10, 15, 20, 26, 35, 45, round(fitted, 1)]
    res = {name: {str(i): run_regime(seq, replace(base, input_n=float(i), wet_deposition=False)) for i in inputs} for name, seq in REGIMES.items()}
    (OUT / "regimes_sweep.json").write_text(json.dumps(dict(inputs=inputs, fitted_total=fitted, results=res), indent=1))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.4), constrained_layout=True, sharey=True)
    cols = ["#222", "#8c6d31", "#b5651d", "#2b5d8a", "#5aa05e", "#1f5e22"]
    for ax, key, title in ((axs[0], "per_cropped_ha", "per CROPPED hectare"), (axs[1], "per_rotation_ha", "per hectare of the WHOLE rotation")):
        for (name, r), col in zip(res.items(), cols):
            ax.plot(inputs, [r[str(i)][key] for i in inputs], "o-", color=col, ms=4, lw=1.6, label=name)
        ax.axvspan(20, 35, color="#e8e0c8", alpha=0.6, lw=0)
        ax.text(20.5, ax.get_ylim()[1] * 0.02 + 0.02, "AD 200 if the fitted input scales\nby the literature ratio (~0.4-0.65)", fontsize=7.5)
        ax.axvline(fitted, color="#888", ls=":", lw=1); ax.text(fitted - 0.5, 0.05, "fitted\n1850-1925", fontsize=7.5, ha="right")
        ax.set_xlabel("total non-fertilizer N input in model units, kg N/ha/yr"); ax.set_title(f"equilibrium grain {title}", fontsize=10)
        ax.set_ylabel("t/ha/yr"); ax.legend(fontsize=7.5)
    fig.suptitle("Preview only: equilibrium yield vs the N input the land receives without fertilizer (qualified round-2 model, Rothamsted soil and weather)", fontsize=11)
    fig.savefig(OUT / "regimes_sweep.png", dpi=95)
    for name, r in res.items():
        print(f"{name:44s} " + " ".join(f"{i}:{r[str(i)]['per_rotation_ha']:.2f}" for i in inputs))


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "sweep":
    sweep()
