"""Frozen refit declared in calibration/rain_shadow_20261115/refit_e75.json.  python3 -I scripts/refit_e75.py"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from gate_v3 import paired, score
PLAN = json.loads((ROOT / 'calibration/rain_shadow_20261115/refit_e75.json').read_text())
OUT = ROOT / 'output/rain_shadow_20261115/refit_e75'; REF = ROOT / 'output/rain_shadow_20261115/gate_e75/ref'
PY = str(ROOT / '.venv/bin/python'); REF_NAME = 'r44'
PARTS = {'dev31': None, 'retired_a': 'calibration/sealed_20261031/regions.json', 'retired_b': 'calibration/sealed_20261031b/regions.json', 'retired_c': 'calibration/sealed_20261101c/regions.json'}


def evaluate(name, params):
    d = OUT / name; d.mkdir(parents=True, exist_ok=True); f = d / 'candidate_params.json'; f.write_text(json.dumps(params, indent=1))
    for part, spec in PARTS.items():
        o = d / f'candidate_{part}'
        lk = d / f'{REF_NAME}_{part}'
        if not lk.is_symlink(): lk.symlink_to((REF / f'{REF_NAME}_{part}').resolve())
        if (o / 'summary.json').is_file(): continue
        regs = ['dev31'] if spec is None else list(json.loads((ROOT / spec).read_text()))
        cmd = [PY, '-I', str(ROOT / 'scripts/benchmark_local.py'), '--fit', str(f), '--regions', *regs, '--workers', '4', '--out', str(o)]
        if spec: cmd += ['--region-specs', str(ROOT / spec)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    R, C = paired(d, REF_NAME, None, list(PARTS)); return score(R, C, list(R))


def main():
    best = json.loads((ROOT / PLAN['start']).read_text()); log = []; n = 0
    s = evaluate('e00_start', best); log.append(dict(name='e00_start', set={}, **s)); bestS = s['S']; print('start', round(bestS, 4), flush=True)
    for half in (False, True):
        for k, (kind, step) in PLAN['knobs'].items():
            st = (step ** 0.5 if kind == 'mul' else step / 2) if half else step
            for sign in (1, -1):
                if n >= 15: break
                v = best[k] * (st if sign > 0 else 1 / st) if kind == 'mul' else best[k] + sign * st
                trial = dict(best); trial[k] = v; n += 1; name = f'e{n:02d}_{k}_{v:.4g}'
                s = evaluate(name, trial); log.append(dict(name=name, set={k: v}, **s))
                print(name, round(s['S'], 4), 'T %+.3f P %+.3f' % (s['T'], s['P']), flush=True)
                if s['S'] < bestS: best, bestS = trial, s['S']; break
            (OUT / 'search.json').write_text(json.dumps(dict(log=log, best_S=bestS), indent=1) + '\n')
    (OUT / 'best_params.json').write_text(json.dumps(best, indent=1)); print('best', round(bestS, 4))


if __name__ == '__main__':
    main()
