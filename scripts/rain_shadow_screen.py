"""Rain-shadow contrast screen (calibration/rain_shadow_20261115/plan.json).

    python3 -I scripts/rain_shadow_screen.py OUTDIR [--only NAME ...]
Runs benchmark_local on the three pair regions for r44 and each one-knob variant, then scores the declared metric.
"""
import json, subprocess, sys, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; PLAN = json.loads((ROOT / 'calibration/rain_shadow_20261115/plan.json').read_text())
PY = str(ROOT / '.venv/bin/python')


def variants():
    yield 'r44', {}
    for k, vals in PLAN['knobs_one_at_a_time'].items():
        for v in vals: yield f'{k}={v}', {k: v}


def score(folder):
    out = {}; errs = []
    summ = json.loads((folder / 'summary.json').read_text())
    for reg, b in PLAN['pairs'].items():
        d = np.load(folder / 'cells' / f'{reg}.npz'); res = {}
        for side, (x0, x1, y0, y1) in b.items():
            m = (d['lon'] >= x0) & (d['lon'] < x1) & (d['lat'] >= y0) & (d['lat'] < y1) & (d['elev'] < 1800)
            res[side] = (float(np.median(d['Ps'][:, m].sum(0))), float(np.median(d['Po'][:, m].sum(0))))
        e = abs(np.log(res['lee'][0] / res['windward'][0]) - np.log(res['lee'][1] / res['windward'][1]))
        errs.append(e); out[reg] = dict(sim=dict(w=res['windward'][0], l=res['lee'][0]), obs=dict(w=res['windward'][1], l=res['lee'][1]), contrast_err=float(e))
    regs = summ.get('regions', summ)
    loss = [regs[r]['P_loss'] if 'P_loss' in regs[r] else regs[r]['rain']['loss'] for r in PLAN['pairs']] if isinstance(regs, dict) and all(r in regs for r in PLAN['pairs']) else None
    return dict(pairs=out, contrast_err=float(np.mean(errs)), summary_keys=list(summ)[:12], rain_loss=loss)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); only = sys.argv[3:] if '--only' in sys.argv else None
    res = {}
    for name, sets in variants():
        if only and name not in only: continue
        f = out / name.replace('=', '_')
        if not (f / 'summary.json').is_file():
            cmd = [PY, str(ROOT / 'scripts/benchmark_local.py'), '--fit', str(ROOT / PLAN['reference']), '--regions', *PLAN['pairs'], '--workers', '3', '--out', str(f)]
            if sets: cmd += ['--set', json.dumps(sets)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        res[name] = score(f); print(name, round(res[name]['contrast_err'], 3), res[name]['rain_loss'], flush=True)
    (out / 'screen.json').write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()
