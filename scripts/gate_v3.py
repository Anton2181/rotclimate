"""Policy v3 checks (calibration/local_accuracy_20261023/policy_v3.json) on paired benchmark runs.

    python -I scripts/gate_v3.py dev OUT REF_NAME      # REF/candidate _dev31 + _retired_{a,b,c} -> S49, T, P (and S31)
    python -I scripts/gate_v3.py fine OUT REF_NAME     # REF/candidate _fine28 -> S28
    python -I scripts/gate_v3.py sealed OUT REF_NAME [PART]   # REF/candidate _PART (default sealed_d) -> S
Writes OUT/v3_<stage>.json and exits 0 when the stage passes.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(folder):
    s = json.loads((folder / "summary.json").read_text())
    if s.get("complete") is not True:
        raise ValueError(f"incomplete run: {folder}")
    rows = {}
    for name, r in s["regions"].items():
        if r.get("status") != "passed" or r.get("numerics", {}).get("all_checks_passed") is not True:
            raise ValueError(f"unverified result: {folder} {name}")
        rows[name] = r
    return rows


def paired(out, ref, _unused, parts):
    R, C = {}, {}
    for part in parts:
        r, c = load(out / f"{ref}_{part}"), load(out / f"candidate_{part}")
        if set(r) != set(c):
            raise ValueError(f"different regions in {part}")
        for n in r:
            if r[n]["case_identity"] != c[n]["case_identity"] or r[n]["cells"] != c[n]["cells"]:
                raise ValueError(f"paired geography differs: {n}")
        R.update(r); C.update(c)
    return R, C


def score(R, C, names):
    t = sum(C[n]["temperature"]["monthly_mae_C"] for n in names) / len(names)
    p = sum(C[n]["rain"]["loss"] for n in names) / len(names)
    tr = sum(R[n]["temperature"]["monthly_mae_C"] for n in names) / len(names)
    pr = sum(R[n]["rain"]["loss"] for n in names) / len(names)
    return dict(S=0.5 * t / tr + 0.5 * p / pr, T=t / tr - 1, P=p / pr - 1, n=len(names))


def main():
    stage, out, ref = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    if stage == "dev":
        R, C = paired(out, ref, None, ["dev31", "retired_a", "retired_b", "retired_c"])
        dev31 = list(load(out / f"{ref}_dev31"))
        s49, s31 = score(R, C, list(R)), score(R, C, dev31)
        groups = json.loads((ROOT / "calibration/local_accuracy_20261023/policy_v3.json").read_text())["groups"]
        rep = {g: score(R, C, m)["S"] for g, m in groups.items()}
        for part in ("retired_a", "retired_b", "retired_c"):
            rep[part] = score(R, C, list(load(out / f"{ref}_{part}")))["S"]
        passes = s49["S"] <= 0.995 and s49["T"] <= 0.01 and s49["P"] <= 0.01
        res = dict(stage="dev", S49=s49, S31=s31, groups_reported=rep, passes=bool(passes))
    elif stage == "fine":
        R, C = paired(out, ref, None, ["fine28"])
        s = score(R, C, list(R)); res = dict(stage="fine", S28=s, passes=bool(s["S"] <= 1.01))
    elif stage == "sealed":
        R, C = paired(out, ref, None, [sys.argv[4] if len(sys.argv) > 4 else "sealed_d"])   # e.g. sealed_f
        s = score(R, C, list(R))
        per = {n: dict(T=(C[n]["temperature"]["monthly_mae_C"], R[n]["temperature"]["monthly_mae_C"]),
                       P=(C[n]["rain"]["loss"], R[n]["rain"]["loss"])) for n in R}
        res = dict(stage="sealed", S=s, regions=per, passes=bool(s["S"] <= 1.0))
    else:
        raise SystemExit(__doc__)
    (out / f"v3_{stage}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "regions"}, indent=1))
    sys.exit(0 if res["passes"] else 1)


if __name__ == "__main__":
    main()
