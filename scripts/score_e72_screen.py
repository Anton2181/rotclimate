"""Score the e72 dev31 screen against calibration/east_asia_p6_20261107/plan_e72.json.

    .venv/bin/python -I scripts/score_e72_screen.py                       # e72 profiles
    .venv/bin/python -I scripts/score_e72_screen.py k05s k10s k10s_o5      # e72b profiles (plan_e72b.json)
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/east_asia_p6_20261107"
EAST_ASIA = ["east_china", "north_china_plain", "korea", "japan", "manchuria"]
PROFILES = ["baseline", "k05", "k10", "k10_o5"]


def load(name):
    s = json.loads((OUT / f"{name}_dev31" / "summary.json").read_text())
    if s.get("complete") is not True:
        raise ValueError("incomplete " + name)
    return s


def main():
    base = load("baseline")
    regions = sorted(base["regions"])
    def loss(s, rs): return float(np.mean([s["regions"][r]["rain"]["loss"] for r in rs]))
    def tmae(s, rs): return float(np.mean([s["regions"][r]["temperature"]["monthly_mae_C"] for r in rs]))
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from benchmark_local import GROUPS            # training / holdout / midlatitude / dev12 membership
    group_regions = {g: [r for r in m if r in base["regions"]] for g, m in GROUPS.items()}
    res = dict(plan="calibration/east_asia_p6_20261107/plan_e72.json", profiles={})
    b_ea, b_all, b_t = loss(base, EAST_ASIA), loss(base, regions), tmae(base, regions)
    import sys as _s
    names = _s.argv[1:] or PROFILES[1:]
    for p in names:
        s = load(p)
        ea, al, t = loss(s, EAST_ASIA), loss(s, regions), tmae(s, regions)
        row = dict(east_asia_loss=ea / b_ea, all_loss=al / b_all, all_tmae=t / b_t,
                   regions={r: dict(loss=s["regions"][r]["rain"]["loss"] / base["regions"][r]["rain"]["loss"],
                                    tmae=s["regions"][r]["temperature"]["monthly_mae_C"] - base["regions"][r]["temperature"]["monthly_mae_C"])
                            for r in regions})
        grp = {}
        for g, members in group_regions.items():
            if members:
                grp[g] = loss(s, members) / loss(base, members)
        row["groups"] = grp
        row["promising"] = bool(row["east_asia_loss"] <= 0.97 and row["all_loss"] <= 1.005 and row["all_tmae"] <= 1.005
                                and all(v <= 1.01 for k, v in grp.items() if k in ("training", "holdout", "midlatitude")))
        spent = OUT / f"{p}_spent_f" / "summary.json"
        if spent.exists():                       # e72d: the spent set f as an explicit development check
            sys.path.insert(0, str(ROOT / "scripts"))
            import gate_v3 as G
            R = G.load(OUT / "gate" / "r43_sealed_f"); C = G.load(OUT / f"{p}_spent_f")
            row["spent_f"] = G.score(R, C, list(R))
            row["promising"] = bool(row["promising"] and row["spent_f"]["S"] <= 1.0)
            print(f"        spent set f: S {row['spent_f']['S']:.4f} (T {row['spent_f']['T']:+.4f}, P {row['spent_f']['P']:+.4f}); eastern_siberia rain x{C['eastern_siberia']['rain']['loss'] / R['eastern_siberia']['rain']['loss']:.3f}")
        res["profiles"][p] = row
        print(f"{p:7s} East Asia loss x{row['east_asia_loss']:.4f}  all loss x{row['all_loss']:.4f}  all T MAE x{row['all_tmae']:.4f}  groups "
              + " ".join(f"{k} {v:.4f}" for k, v in grp.items()) + f"  promising {row['promising']}")
        print("        " + "  ".join(f"{r} {row['regions'][r]['loss']:.3f}/{row['regions'][r]['tmae']:+.2f}" for r in EAST_ASIA))
        moved = sorted(regions, key=lambda r: abs(row["regions"][r]["loss"] - 1), reverse=True)[:8]
        print("        largest changes: " + ", ".join(f"{r} {row['regions'][r]['loss']:.3f}" for r in moved))
    (OUT / ("e72_screen_score.json" if names == PROFILES[1:] else ("e72d_screen_score.json" if names[0].startswith("d") else "e72b_screen_score.json"))).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
