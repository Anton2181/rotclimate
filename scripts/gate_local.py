"""Score candidates against the frozen local-accuracy gate (calibration/local_accuracy_20261023/policy.json,
and policy_v2.json from r30 on: the same rules over 31 regions, with the 12 newer ones as a fourth group).

    python3 -I scripts/gate_local.py REFERENCE_DIR CANDIDATE_DIR ...
Each DIR holds a summary.json from scripts/benchmark_local.py. Every group present in both summaries
must not worsen.
"""
import json, sys
from pathlib import Path


def score(s, ref):
    return 0.5 * s["T_monthly_mae"] / ref["T_monthly_mae"] + 0.5 * s["P_loss"] / ref["P_loss"]


def main():
    ref = json.loads((Path(sys.argv[1]) / "summary.json").read_text())
    groups = [g for g in ("training", "holdout", "midlatitude", "dev12") if g in ref["groups"]]
    print(f"{'candidate':28s} {'S all':>7s} " + " ".join(f"{'S ' + g[:5]:>8s}" for g in groups)
          + f" {'T mMAE':>7s} {'P loss':>7s}  verdict")
    for d in sys.argv[2:]:
        c = json.loads((Path(d) / "summary.json").read_text())
        S = {g: score(c["groups"][g], ref["groups"][g]) for g in groups if g in c["groups"]}
        Sa = score(c["all"], ref["all"])
        dT = c["all"]["T_monthly_mae"] / ref["all"]["T_monthly_mae"] - 1
        dP = c["all"]["P_loss"] / ref["all"]["P_loss"] - 1
        ok = len(S) == len(groups) and Sa <= 0.995 and all(v <= 1.0 for v in S.values()) and dT <= 0.01 and dP <= 0.01
        print(f"{Path(d).name:28s} {Sa:7.4f} " + " ".join(f"{S.get(g, float('nan')):8.4f}" for g in groups)
              + f" {dT:+7.2%} {dP:+7.2%}  " + ("PASSES 56 km gate" if ok else "fails"))


if __name__ == "__main__":
    main()
