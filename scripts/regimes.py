"""Regime-stratified scoring (plan_20261124 A2).

    python3 -I scripts/regimes.py classify OUT.json CELLS_DIR [CELLS_DIR ...]
        Tag every region found in the given cells/ directories with a climate regime from its OBSERVED
        region-mean monthly climate (Koppen-style rules below; model output is not used). Freeze the result.
    python3 -I scripts/regimes.py score REGIMES.json DIR REF_NAME PART[,PART...]
        Paired score S (policy v3+ definition) of DIR/candidate_<part> against DIR/<REF_NAME>_<part>, overall and per
        regime, with the bootstrap 90 % interval of each.

Regimes (first rule that applies; months are calendar months of the run, where southern regions are mirrored
into the northern hemisphere, so 'summer' is always months 4-9):
  highland      mean elevation of the scored cells > 1,500 m
  arid          annual rain below the Koppen threshold 20 T + (280 if >= 70 % of rain in summer, 0 if >= 70 % in
                winter, else 140) mm
  tropical_wet  coldest month >= 18 C and driest month >= 60 mm
  tropical_dry  coldest month >= 18 C (savanna / monsoon)
  mediterranean driest summer month < 40 mm and < 1/3 of the wettest winter month, unless the wettest summer
                month has >= 10x the driest winter month (Koppen: monsoon w takes precedence over s)
  continental   coldest month < -3 C
  temperate     everything else (maritime, humid subtropical)
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))

SUMMER = slice(3, 9)


def regime(T, P, elev):
    Ta, Pa = T.mean(), P.sum()
    ps = P[SUMMER].sum() / max(Pa, 1e-9)
    thr = 20 * Ta + (280 if ps >= 0.7 else 0 if ps <= 0.3 else 140)
    winter = np.r_[P[:3], P[9:]]
    if elev > 1500: return 'highland'
    if Pa < thr: return 'arid'
    if T.min() >= 18: return 'tropical_wet' if P.min() >= 60 else 'tropical_dry'
    if P[SUMMER].min() < 40 and P[SUMMER].min() < winter.max() / 3 and P[SUMMER].max() < 10 * winter.min(): return 'mediterranean'
    if T.min() < -3: return 'continental'
    return 'temperate'


def classify(out, dirs):
    tags = {}
    for d in dirs:
        for f in sorted(Path(d).glob('*.npz')):
            z = np.load(f)
            tags[f.stem] = regime(z['To'].mean(1), z['Po'].mean(1), float(z['elev'].mean()))
    out.write_text(json.dumps(dict(rules=__doc__.split('Regimes')[1].strip(), regimes=dict(sorted(tags.items()))), indent=1) + '\n')
    from collections import Counter
    print(Counter(tags.values()))


def score(tags, d, ref, parts):
    from gate_v3 import paired
    from score_ci import ci
    R, C = paired(Path(d), ref, None, parts)
    names = sorted(R)
    a = np.array([[C[n]['temperature']['monthly_mae_C'], R[n]['temperature']['monthly_mae_C'],
                   C[n]['rain']['loss'], R[n]['rain']['loss']] for n in names])
    groups = {'ALL': list(range(len(names)))}
    for i, n in enumerate(names):
        groups.setdefault(tags.get(n, 'untagged'), []).append(i)
    res = {}
    for g, idx in groups.items():
        b = ci(a[idx]); m = a[idx].mean(0)
        res[g] = dict(n=len(idx), S=b['S'], q05=b['q05'], q95=b['q95'], T=m[0] / m[1] - 1, P=m[2] / m[3] - 1)
        print(f"{g:14s} n {len(idx):2d}  S {b['S']:.4f} [{b['q05']:.4f}, {b['q95']:.4f}]  T {m[0]/m[1]-1:+.3f}  P {m[2]/m[3]-1:+.3f}")
    return res


if __name__ == '__main__':
    if sys.argv[1] == 'classify':
        classify(Path(sys.argv[2]), sys.argv[3:])
    else:
        score(json.loads(Path(sys.argv[2]).read_text())['regimes'], sys.argv[3], sys.argv[4], sys.argv[5].split(','))
