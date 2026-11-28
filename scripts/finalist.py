"""Meta M3: declared finalist objective (policy v7).

    .venv/bin/python -I scripts/finalist.py REF_NAME CAND_DIR [CAND_DIR ...]

For each candidate directory (screen_v6 / PPE layout: candidate_<part> beside REF_NAME_<part> links, 8 dev6 parts) prints
    obj = S97 + 0.25 x mean of the five largest max(0, s_i - 1)
where s_i = 0.5 T_i / T_ref,i + 0.5 P_i / P_ref,i per region. The finalist is the candidate with the lowest obj (no
judgment calls): it rewards the pool score and charges concentrated harm (JJ failed on the boxes a low-S candidate
had over-wetted). Writes CAND_DIR/finalist.json.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from gate_v3 import paired, score

PARTS = ["dev31", "retired_a", "retired_b", "retired_c", "tropical_t", "sealed_r", "sealed_S18", "sealed_U18"]
K, W = 5, 0.25


def objective(d, ref):
    R, C = paired(d, ref, None, PARTS)
    s = score(R, C, list(R))["S"]
    si = {n: 0.5 * C[n]["temperature"]["monthly_mae_C"] / R[n]["temperature"]["monthly_mae_C"]
             + 0.5 * C[n]["rain"]["loss"] / R[n]["rain"]["loss"] for n in R}
    worst = sorted(si.items(), key=lambda x: -x[1])[:K]
    pen = W * sum(max(0.0, v - 1.0) for _, v in worst) / K
    return dict(S=s, penalty=pen, obj=s + pen, worst=worst, n=len(R))


def main():
    ref, dirs = sys.argv[1], [Path(a) for a in sys.argv[2:]]
    rows = []
    for d in dirs:
        r = objective(d, ref); (d / "finalist.json").write_text(json.dumps(r, indent=1)); rows.append((r["obj"], d, r))
    for o, d, r in sorted(rows, key=lambda x: x[0]):
        print(f"{d.name:12s} obj {o:.4f}  S{r['n']} {r['S']:.4f}  penalty {r['penalty']:.4f}  worst " +
              " ".join(f"{n} {v:.3f}" for n, v in r["worst"][:3]))
    print("finalist:", sorted(rows, key=lambda x: x[0])[0][1].name)


if __name__ == "__main__":
    main()
