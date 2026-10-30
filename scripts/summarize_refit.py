"""Summaries for scripts/validate_monsoon_refit.sh.

    python -I scripts/summarize_refit.py OUT checks   # gate + 28 km; exit 0 only if both pass
    python -I scripts/summarize_refit.py OUT sealed   # add the sealed six to validation.json
"""
import json
import sys
from pathlib import Path


def paired(out, ref, cand):
    a = json.loads((out / ref / "summary.json").read_text())["regions"]
    b = json.loads((out / cand / "summary.json").read_text())["regions"]
    if any(b[r]["status"] != "passed" for r in a):
        raise SystemExit(f"{cand}: a region did not pass")
    t0 = sum(a[r]["temperature"]["monthly_mae_C"] for r in a) / len(a)
    t1 = sum(b[r]["temperature"]["monthly_mae_C"] for r in a) / len(a)
    p0 = sum(a[r]["rain"]["loss"] for r in a) / len(a)
    p1 = sum(b[r]["rain"]["loss"] for r in a) / len(a)
    return dict(S=0.5 * t1 / t0 + 0.5 * p1 / p0, T=[t0, t1], P=[p0, p1],
                regions={r: dict(T=[a[r]["temperature"]["monthly_mae_C"], b[r]["temperature"]["monthly_mae_C"]],
                                 P=[a[r]["rain"]["loss"], b[r]["rain"]["loss"]]) for r in a})


def main():
    out, what = Path(sys.argv[1]), sys.argv[2]
    if what == "checks":
        review = json.loads((out / "gate_review.json").read_text())["candidates"]
        gate = next(iter(review.values()))
        fine = paired(out, "r39_fine28", "candidate_fine28")
        result = dict(development=gate, fine28=fine, fine28_passes=fine["S"] <= 1.01,
                      passes_checks=bool(gate["passes_development_gate"] and fine["S"] <= 1.01))
        (out / "validation.json").write_text(json.dumps(result, indent=1))
        print(f"development S {gate['score']:.4f} passes {gate['passes_development_gate']} failures {gate['failures']}")
        print(f"28 km S {fine['S']:.4f}; passes both: {result['passes_checks']}")
        sys.exit(0 if result["passes_checks"] else 3)
    result = json.loads((out / "validation.json").read_text())
    result["sealed6"] = paired(out, "r39_sealed6", "candidate_sealed6")
    (out / "validation.json").write_text(json.dumps(result, indent=1))
    print(f"sealed six S {result['sealed6']['S']:.4f}")


if __name__ == "__main__":
    main()
