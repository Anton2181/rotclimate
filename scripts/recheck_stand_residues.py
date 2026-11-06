"""Recheck the stand-scaled residue fix on SPENT data with the frozen round-2 parameters
(no refit): development series and the Broadbalk 1926-1967 scores, linear vs stand-scaled.

    python -I scripts/recheck_stand_residues.py
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import soil_fertility_round2 as R  # noqa: E402
from harvest.soil_fertility import Params  # noqa: E402

sel = json.loads((R.OUT / "selection.json").read_text())
base = Params(**sel["parameters"])
fixed = replace(base, stand_residues=True)
dev = R.Development()
out = {}
for name, p in (("linear (frozen)", base), ("stand-scaled", fixed)):
    rep = R.development_report(dev, p)
    chains = R.broadbalk_1926_management()
    ev = R.score_1926(R.predict_1926(p, chains), R.observed_1926(), chains)
    out[name] = dict(loss=rep["loss"], groups=rep["groups"],
                     series={k: dict(MAE_log10=v["MAE_log10"], predicted_mean=v["predicted_mean"], observed_mean=v["observed_mean"])
                             for k, v in rep["series"].items()},
                     broadbalk_1926_1967={k: ev[k] for k in ("T1_level", "T2_manure", "T3_fallow", "qualification")})
    t1, t2, t3 = ev["T1_level"], ev["T2_manure"], ev["T3_fallow"]
    print(f"{name:16s} dev loss {rep['loss']:.4f} groups " + " ".join(f"{k} {v:.3f}" for k, v in rep["groups"].items()))
    print(f"   1926-67: T1 {t1['MAE_model']:.3f} bias {t1['mean_log10_bias']:+.3f} | T2 {t2['MAE_model']:.3f} | T3 {t3['MAE_model']:.3f} | {ev['qualification']}")
for k in out["linear (frozen)"]["series"]:
    a, b = out["linear (frozen)"]["series"][k], out["stand-scaled"]["series"][k]
    if abs(a["MAE_log10"] - b["MAE_log10"]) > 0.0005:
        print(f"   changed {k:22s} MAE {a['MAE_log10']:.3f} -> {b['MAE_log10']:.3f}  pred {a['predicted_mean']:.3f} -> {b['predicted_mean']:.3f}")
(R.OUT / "recheck_stand_residues.json").write_text(json.dumps(out, indent=1, default=float))
