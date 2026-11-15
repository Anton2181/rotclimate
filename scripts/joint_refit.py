"""Coordinate-descent refit declared in a plan json (calibration/rain_shadow_20261115/joint_refit.json).

    python3 -I scripts/joint_refit.py PLAN.json OUTDIR
Each evaluation: candidate on dev31 + retired a, b, c; S49 against r44 (output/rain_shadow_20261115/gate_e75/ref).
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
import refit_e75 as R


def main():
    plan = json.loads(Path(sys.argv[1]).read_text()); R.OUT = Path(sys.argv[2]); R.OUT.mkdir(parents=True, exist_ok=True)
    if 'reference' in plan: R.REF = ROOT / plan['reference']
    best = json.loads((ROOT / plan['start'].split(' with ')[0]).read_text())
    best.update(plan['start_set'] if 'start_set' in plan else {'storm_convection': 0.5})
    from dataclasses import asdict
    sys.path.insert(0, str(ROOT)); from rotclimate.config import Params
    defaults = asdict(Params())
    for k in plan['knobs']: best.setdefault(k, defaults[k])          # knobs absent from the start file take the code default   # rain-shadow refit: storm_convection 0.5
    bounds = plan.get('bounds', {}); log = []; n = 0
    s = R.evaluate('j00_start', best); bestS = s['S']; log.append(dict(name='j00_start', set={}, **s)); print('start', round(bestS, 4), flush=True)
    for level in range(3):
        for k, (kind, step) in plan['knobs'].items():
            st = step ** (0.5 ** level) if kind == 'mul' else step * 0.5 ** level
            for sign in (1, -1):
                if n >= 39: break
                v = best[k] * (st if sign > 0 else 1 / st) if kind == 'mul' else best[k] + sign * st
                lo, hi = bounds.get(k, (-1e9, 1e9)); v = min(max(v, lo), hi)
                if v == best[k]: continue
                trial = dict(best); trial[k] = v; n += 1; name = f'j{n:02d}_{k}_{v:.4g}'
                s = R.evaluate(name, trial); log.append(dict(name=name, set={k: v}, **s))
                print(name, round(s['S'], 4), 'T %+.3f P %+.3f' % (s['T'], s['P']), flush=True)
                if s['S'] < bestS: best, bestS = trial, s['S']; break
            (R.OUT / 'search.json').write_text(json.dumps(dict(log=log, best_S=bestS), indent=1) + '\n')
    (R.OUT / 'best_params.json').write_text(json.dumps(best, indent=1)); print('best', round(bestS, 4), flush=True)


if __name__ == '__main__':
    main()
