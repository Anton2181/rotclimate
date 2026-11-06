"""Preview (no adoption): equilibrium cereal yields under farming regimes with the frozen
soil-fertility selection, on Rothamsted's observed 1878-1937 weather cycled four times
(240 years) from the selection's spin-up state. Reports grain per cropped hectare and per
hectare of the whole rotation (fallow and clover years count as land without grain), over
the last 60 years. Non-fertilizer N input: the fitted value (19th-20th century England,
including industrial deposition) and lower illustrative values.

    python -I scripts/soil_fertility_regimes.py --out output/soil_fertility_20261106
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

import soil_fertility_common as C  # noqa: E402
from harvest.soil_fertility import Params, Season, simulate  # noqa: E402

REGIMES = {
    "continuous cereal, nothing returned": ["wheat"],
    "wheat / bare fallow": ["wheat", "fallow"],
    "wheat / barley / bare fallow": ["wheat", "barley", "fallow"],
    "wheat / barley / clover": ["wheat", "barley", "clover"],
    "continuous cereal + 5 t/ha FYM": ["wheat+fym5"],
    "continuous cereal + 10 t/ha FYM": ["wheat+fym10"],
}
CYCLES, Y0, Y1 = 4, 1878, 1937


def run_regime(seq, params):
    n = Y1 - Y0 + 1
    rows_real, _, _ = C.forcing_rows(Y0, Y1)
    cal_real = {}
    for i, y in enumerate(range(Y0 + 1, Y1 + 1)):
        cal_real[y] = seq[i % len(seq)].split("+")[0]
    drain, _ = C.monthly_drainage("rothamsted", Y0, Y1, cal_real)
    forcing, seasons, events = [], [], {}
    for c in range(CYCLES):
        off = c * n
        for r in rows_real:
            forcing.append(dict(r, year=r["year"] + off, drainage=drain[(r["year"], r["month"])]))
        for i, y in enumerate(range(Y0 + 1, Y1 + 1)):
            kind = seq[i % len(seq)]
            base = kind.split("+")[0]
            s = C.season(base, y)
            sh = lambda m: frozenset((yy + off, mm) for yy, mm in m)   # noqa: E731
            seasons.append(Season(s.crop, (s.harvest[0] + off, s.harvest[1]), sh(s.uptake), sh(s.vegetated), s.potential_t_ha, f"{base} {y + off}"))
            if "+fym" in kind:
                t = float(kind.split("fym")[1])
                events.setdefault((y - 1 + off, 10), []).append(("fym", t * C.FYM_C_PER_T, t * C.FYM_N_PER_T))
            if base == "clover":
                events.setdefault((y + off, 10), []).append(("residue", 1.5, 15.0))
                events.setdefault((y + off, 11), []).append(("residue", 2.0, 15.0))
    res = simulate(forcing, seasons, params, C.SOILS["rothamsted"]["clay"], C.water_mm("rothamsted"),
                   start=C.start_pools("rothamsted", params.prior_manure), events=events)
    last = [s for s in res["seasons"] if s["harvest"][0] > Y0 + (CYCLES - 1) * n]
    grain = [s["grain_t_ha"] for s in last if s["grain_t_ha"] is not None]
    years = len({s["harvest"][0] for s in last})
    return dict(per_cropped_ha=float(np.mean(grain)), per_rotation_ha=float(np.sum(grain) / years),
                cropped_share=len(grain) / years, soc_active_end=res["pools"].active_c)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/soil_fertility_20261106")
    a = ap.parse_args()
    sel = json.loads((a.out / "selection.json").read_text())
    base = Params(**sel["parameters"])
    inputs = [round(base.input_n, 1), 15.0, 8.0]
    out = dict(status="preview, not adopted; frozen selection parameters except the N input where stated",
               selection=sel["parameters"], A0_mean_wheat=C.a0_mean("wheat"), regimes={})
    for name, seq in REGIMES.items():
        out["regimes"][name] = {str(i): run_regime(seq, replace(base, input_n=i)) for i in inputs}
        r = out["regimes"][name]
        print(f"{name:40s} " + "  ".join(f"I={i}: crop {r[str(i)]['per_cropped_ha']:.2f} rot {r[str(i)]['per_rotation_ha']:.2f}" for i in inputs), flush=True)
    (a.out / "regimes_preview.json").write_text(json.dumps(out, indent=1))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(13.5, 5.2), constrained_layout=True, sharey=True)
    names = list(REGIMES)
    cols = {str(inputs[0]): "#2f7d32", "15.0": "#7aa56f", "8.0": "#c2d6b9"}
    for ax, key, title in ((axs[0], "per_cropped_ha", "grain per CROPPED hectare"), (axs[1], "per_rotation_ha", "grain per hectare of the WHOLE rotation")):
        w = 0.26
        for j, i in enumerate(inputs):
            v = [out["regimes"][n][str(i)][key] for n in names]
            ax.barh(np.arange(len(names)) + (j - 1) * w, v, height=w - 0.02, color=cols[str(i)],
                    label=f"N input {i} kg/ha/yr" + (" (fitted, 1840s-1930s England)" if j == 0 else ""))
        ax.axvline(out["A0_mean_wheat"], color="#b5651d", ls="--", lw=1)
        ax.text(out["A0_mean_wheat"], len(names) - 0.4, " existing response", color="#b5651d", fontsize=8)
        ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9); ax.invert_yaxis()
        ax.set_xlabel("t/ha/yr (last 60 of 240 years, Rothamsted weather 1878-1937 cycled)"); ax.set_title(title, fontsize=10)
        ax.legend(fontsize=8, loc="lower right")
    fig.suptitle("Preview only: equilibrium cereal yields under farming regimes, frozen soil-fertility state (Rothamsted soil and weather)", fontsize=11)
    fig.savefig(a.out / "regimes_preview.png", dpi=95)


if __name__ == "__main__":
    main()
