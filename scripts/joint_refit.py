"""Coordinate-descent refit declared in a plan json (calibration/rain_shadow_20261115/joint_refit.json).

    python3 -I scripts/joint_refit.py PLAN.json OUTDIR
Each evaluation: candidate on dev31 + retired a, b, c; S49 against r44 (output/rain_shadow_20261115/gate_e75/ref).
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
import refit_e75 as R


def objective(plan, name, params):
    s = R.evaluate(name, params)
    if plan.get('objective_mode') != 'max_dev_pool':
        return s
    from gate_v3 import paired, score
    d = R.OUT / name
    A = score(*paired(d, R.REF_NAME, None, ['dev31', 'retired_a', 'retired_b', 'retired_c']), None) if False else None
    R49, C49 = paired(d, R.REF_NAME, None, ['dev31', 'retired_a', 'retired_b', 'retired_c']); s49 = score(R49, C49, list(R49))
    Rp, Cp = paired(d, R.REF_NAME, None, list(plan['extra_parts'])); sp = score(Rp, Cp, list(Rp))
    return dict(S=max(s49['S'], sp['S']), T=s49['T'], P=s49['P'], S49=s49['S'], S_pool=sp['S'], n=s['n'])


def main():
    plan = json.loads(Path(sys.argv[1]).read_text()); R.OUT = Path(sys.argv[2]); R.OUT.mkdir(parents=True, exist_ok=True)
    if 'reference' in plan: R.REF = ROOT / plan['reference']
    if 'reference_name' in plan: R.REF_NAME = plan['reference_name']
    R.PARTS.update(plan.get('extra_parts', {}))      # extra objective regions (spec file per part)
    best = json.loads((ROOT / plan['start'].split(' with ')[0]).read_text())
    best.update(plan['start_set'] if 'start_set' in plan else {'storm_convection': 0.5})
    from dataclasses import asdict
    sys.path.insert(0, str(ROOT)); from rotclimate.config import Params
    defaults = asdict(Params())
    for k in plan['knobs']: best.setdefault(k, defaults[k])          # knobs absent from the start file take the code default   # rain-shadow refit: storm_convection 0.5
    bounds = plan.get('bounds', {}); log = []; n = 0
    s = objective(plan, 'j00_start', best); bestS = s['S']; log.append(dict(name='j00_start', set={}, **s)); print('start', round(bestS, 4), flush=True)
    for level in range(3):
        for k, (kind, step) in plan['knobs'].items():
            st = step ** (0.5 ** level) if kind == 'mul' else step * 0.5 ** level
            for sign in (1, -1):
                if n >= plan.get('max_evaluations', 40) - 1: break
                v = best[k] * (st if sign > 0 else 1 / st) if kind == 'mul' else best[k] + sign * st
                lo, hi = bounds.get(k, (-1e9, 1e9)); v = min(max(v, lo), hi)
                if v == best[k]: continue
                trial = dict(best); trial[k] = v; n += 1; name = f'j{n:02d}_{k}_{v:.4g}'
                s = objective(plan, name, trial); log.append(dict(name=name, set={k: v}, **s))
                print(name, round(s['S'], 4), 'T %+.3f P %+.3f' % (s['T'], s['P']), ('S49 %.4f pool %.4f' % (s['S49'], s['S_pool'])) if 'S49' in s else '', flush=True)
                if s['S'] < bestS: best, bestS = trial, s['S']; break
            (R.OUT / 'search.json').write_text(json.dumps(dict(log=log, best_S=bestS), indent=1) + '\n')
    (R.OUT / 'best_params.json').write_text(json.dumps(best, indent=1)); print('best', round(bestS, 4), flush=True)


if __name__ == '__main__':
    main()
