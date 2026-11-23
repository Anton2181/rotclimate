"""Screen named parameter sets against an adopted reference on the policy v5 development pool (61 regions).

    python3 -I scripts/screen_v5.py OUTDIR REF_DIR REF_NAME BASE_PARAMS NAME '{"k": v}' [NAME '{...}' ...]
REF_DIR holds REF_NAME_<part> runs for dev31, retired_a/b/c, tropical_t and sealed_r. Prints S61 with its bootstrap 90 %
interval, T, P, S49, and the largest per-region movers.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
import refit_e75 as R
from gate_v3 import paired, score
from score_ci import ci

out, R.REF, R.REF_NAME, base = Path(sys.argv[1]), ROOT / sys.argv[2], sys.argv[3], json.loads((ROOT / sys.argv[4]).read_text())
R.OUT = out; out.mkdir(parents=True, exist_ok=True)
R.PARTS.update(tropical_t='calibration/tropical_check_20261122t/regions.json', sealed_r='calibration/sealed_20261122r/regions.json')
t = set(json.loads((ROOT / R.PARTS['tropical_t']).read_text())) | set(json.loads((ROOT / R.PARTS['sealed_r']).read_text()))
args = sys.argv[5:]
for name, js in zip(args[::2], args[1::2]):
    p = dict(base); p.update(json.loads(js)); R.evaluate(name, p)
    Rr, Cc = paired(out / name, R.REF_NAME, None, list(R.PARTS))
    s, s49 = score(Rr, Cc, list(Rr)), score(Rr, Cc, [n for n in Rr if n not in t])
    import numpy as np
    a = np.array([[Cc[n]['temperature']['monthly_mae_C'], Rr[n]['temperature']['monthly_mae_C'], Cc[n]['rain']['loss'], Rr[n]['rain']['loss']] for n in Rr])
    b = ci(a)
    print(f"== {name}  S61 {s['S']:.4f} [{b['q05']:.4f}, {b['q95']:.4f}] (T {s['T']:+.3f} P {s['P']:+.3f})  S49 {s49['S']:.4f}", flush=True)
    sc = {n: 0.5 * Cc[n]['temperature']['monthly_mae_C'] / Rr[n]['temperature']['monthly_mae_C'] + 0.5 * Cc[n]['rain']['loss'] / Rr[n]['rain']['loss'] for n in Rr}
    for n in sorted(sc, key=sc.get)[:6] + sorted(sc, key=sc.get)[-6:]:
        a_, b_ = Rr[n], Cc[n]
        print(f"   {n:20s} s {sc[n]:.3f}  T {a_['temperature']['monthly_mae_C']:.2f}->{b_['temperature']['monthly_mae_C']:.2f} bias {a_['temperature']['annual_bias_C']:+.2f}->{b_['temperature']['annual_bias_C']:+.2f}  Ploss {a_['rain']['loss']:.3f}->{b_['rain']['loss']:.3f}", flush=True)
