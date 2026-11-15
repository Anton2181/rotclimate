"""Screen of plan_e75.json variants with the plan.json pair metric.  python3 -I scripts/rain_shadow_screen_e75.py OUTDIR"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
import rain_shadow_screen as R
PLAN = json.loads((ROOT / 'calibration/rain_shadow_20261115/plan_e75.json').read_text())
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); res = {}
for name, sets in [('r44', {})] + list(PLAN['screen']['variants'].items()) + list(PLAN.get('amendment_1', {}).get('variants', {}).items()):
    f = out / name
    if not (f / 'summary.json').is_file():
        cmd = [R.PY, str(ROOT / 'scripts/benchmark_local.py'), '--fit', str(ROOT / R.PLAN['reference']), '--regions', *R.PLAN['pairs'], '--workers', '3', '--out', str(f)]
        if sets: cmd += ['--set', json.dumps(sets)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res[name] = R.score(f); r = res[name]
    print(name, 'contrast %.3f' % r['contrast_err'], 'loss', [round(x, 3) for x in r['rain_loss']], {k: (round(v['sim']['w']), round(v['sim']['l'])) for k, v in r['pairs'].items()}, flush=True)
(out / 'screen.json').write_text(json.dumps(res, indent=1) + '\n')
