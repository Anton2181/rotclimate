"""Screen named parameter sets against an adopted reference under policy v4 (dev49 + tropical set t).

    python3 -I scripts/screen_v4.py OUTDIR REF_DIR REF_NAME BASE_PARAMS NAME '{"k": v}' [NAME '{...}' ...]
Prints S55 (gate), S49 (guard), S_t and the per-region temperature/rain changes of the largest movers.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
import refit_e75 as R
from gate_v3 import paired, score

out, R.REF, R.REF_NAME, base = Path(sys.argv[1]), ROOT / sys.argv[2], sys.argv[3], json.loads((ROOT / sys.argv[4]).read_text())
R.OUT = out; out.mkdir(parents=True, exist_ok=True); R.PARTS['tropical_t'] = 'calibration/tropical_check_20261122t/regions.json'
args = sys.argv[5:]
for name, js in zip(args[::2], args[1::2]):
    p = dict(base); p.update(json.loads(js)); R.evaluate(name, p)
    Rr, Cc = paired(out / name, R.REF_NAME, None, list(R.PARTS))
    t = list(json.loads((ROOT / R.PARTS['tropical_t']).read_text()))
    s55, s49, st = score(Rr, Cc, list(Rr)), score(Rr, Cc, [n for n in Rr if n not in t]), score(Rr, Cc, t)
    print(f"== {name}  S55 {s55['S']:.4f} (T {s55['T']:+.3f} P {s55['P']:+.3f})  S49 {s49['S']:.4f}  S_t {st['S']:.4f}", flush=True)
    mv = sorted(Rr, key=lambda n: -abs(Cc[n]['temperature']['monthly_mae_C'] - Rr[n]['temperature']['monthly_mae_C']))[:10]
    for n in mv:
        a, b = Rr[n], Cc[n]
        print(f"   {n:20s} T {a['temperature']['monthly_mae_C']:.2f}->{b['temperature']['monthly_mae_C']:.2f} bias {a['temperature']['annual_bias_C']:+.2f}->{b['temperature']['annual_bias_C']:+.2f}  Ploss {a['rain']['loss']:.3f}->{b['rain']['loss']:.3f}", flush=True)
