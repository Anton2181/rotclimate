"""Bootstrap uncertainty for the paired benchmark score S (policy v3/v4 definition) by resampling regions.

    python3 -I scripts/score_ci.py DIR REF_NAME PART[,PART...] [--exclude-part PART] [--n 20000] [--seed 0]
S = 0.5 * mean T_mae(cand) / mean T_mae(ref) + 0.5 * mean P_loss(cand) / mean P_loss(ref) over the regions; regions are
resampled with replacement (paired: a region's candidate and reference values move together). Prints S, the 5-95 %
and 2.5-97.5 % intervals, the share of resamples with S >= 1 (no improvement) and each region's leave-one-out S.
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_v3 import paired


def arrays(d, ref, parts):
    R, C = paired(Path(d), ref, None, parts)
    names = sorted(R)
    a = np.array([[C[n]['temperature']['monthly_mae_C'], R[n]['temperature']['monthly_mae_C'],
                   C[n]['rain']['loss'], R[n]['rain']['loss']] for n in names])
    return names, a


def S(a):
    m = a.mean(0) if a.ndim == 2 else a.mean(-2)
    return 0.5 * m[..., 0] / m[..., 1] + 0.5 * m[..., 2] / m[..., 3]


def ci(a, n=20000, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n, len(a)))
    s = S(a[idx])
    return dict(S=float(S(a)), q05=float(np.quantile(s, .05)), q95=float(np.quantile(s, .95)),
                q025=float(np.quantile(s, .025)), q975=float(np.quantile(s, .975)), p_no_gain=float((s >= 1).mean()),
                sd=float(s.std()), n=len(a))


def main():
    d, ref, parts = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
    names, a = arrays(d, ref, parts)
    r = ci(a)
    print(f"S {r['S']:.4f}  90% [{r['q05']:.4f}, {r['q95']:.4f}]  95% [{r['q025']:.4f}, {r['q975']:.4f}]  sd {r['sd']:.4f}  P(S>=1) {r['p_no_gain']:.3f}  n {r['n']}")
    loo = sorted(((float(S(np.delete(a, i, 0))), n) for i, n in enumerate(names)))
    print('leave-one-out range', round(loo[0][0], 4), loo[0][1], '..', round(loo[-1][0], 4), loo[-1][1])
    if '--json' in sys.argv: print(json.dumps(r))


if __name__ == '__main__':
    main()
