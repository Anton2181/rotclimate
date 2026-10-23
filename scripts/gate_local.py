"""Score candidates against the frozen local-accuracy gate (calibration/local_accuracy_20261023/policy.json).

    python3 -I scripts/gate_local.py REFERENCE_DIR CANDIDATE_DIR ...
Each DIR holds a summary.json from scripts/benchmark_local.py.
"""
import json, sys
from pathlib import Path


def score(s, ref):
    return 0.5 * s["T_monthly_mae"] / ref["T_monthly_mae"] + 0.5 * s["P_loss"] / ref["P_loss"]


def main():
    ref = json.loads((Path(sys.argv[1]) / "summary.json").read_text())
    print(f"{'candidate':28s} {'S all':>7s} {'S train':>8s} {'S hold':>7s} {'S mid':>7s} {'T mMAE':>7s} {'P loss':>7s}  verdict")
    for d in sys.argv[2:]:
        c = json.loads((Path(d) / "summary.json").read_text())
        S = {g: score(c["groups"][g], ref["groups"][g]) for g in ("training", "holdout", "midlatitude")}
        Sa = score(c["all"], ref["all"])
        dT = c["all"]["T_monthly_mae"] / ref["all"]["T_monthly_mae"] - 1
        dP = c["all"]["P_loss"] / ref["all"]["P_loss"] - 1
        ok = Sa <= 0.995 and all(v <= 1.0 for v in S.values()) and dT <= 0.01 and dP <= 0.01
        print(f"{Path(d).name:28s} {Sa:7.4f} {S['training']:8.4f} {S['holdout']:7.4f} {S['midlatitude']:7.4f} {dT:+7.2%} {dP:+7.2%}  "
              + ("PASSES 56 km gate" if ok else "fails"))


if __name__ == "__main__":
    main()
