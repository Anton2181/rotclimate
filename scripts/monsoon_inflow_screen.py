"""Stage screens of calibration/monsoon_inflow_20261121/plan.json against r49's recorded runs.

    .venv/bin/python -I scripts/monsoon_physics_screen.py STAGE_ID '{"knob": value}' ['{"knob": value}' ...]
"""
import glob, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PY = str(ROOT / '.venv/bin/python')
R49 = ROOT / 'calibration/local_accuracy_20261023/r49_params.json'
REF = ROOT / 'output/plateau_height_20261120/refit/j29_convective_rain_0.5497'
GROUPS = [(['mexico', 'iberia', 'california'], None), (['texas_plains'], 'calibration/local_accuracy_20261023/regions_dev12.json'),
          (['sahel_niger', 'najd_arabia', 'bengal'], 'calibration/sealed_20261031b/regions.json')]
TARGET = ['mexico', 'texas_plains', 'sahel_niger', 'bengal']; GUARD = ['najd_arabia', 'iberia', 'california']


def run(stage, setting):
    name = '_'.join(f'{k}{v:g}' for k, v in setting.items()); out = ROOT / f'output/monsoon_inflow_20261121/{stage}/screen/{name}'
    for i, (regs, spec) in enumerate(GROUPS):
        if (out / f'g{i}' / 'summary.json').exists(): continue
        cmd = [PY, '-I', str(ROOT / 'scripts/benchmark_local.py'), '--fit', str(R49), '--set', json.dumps(setting), '--regions', *regs,
               '--workers', str(len(regs)), '--out', str(out / f'g{i}')] + (['--region-specs', str(ROOT / spec)] if spec else [])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ref = {Path(f).stem: json.load(open(f)) for f in glob.glob(str(REF / 'candidate_*/cases/*.json'))}
    sc = {}
    for f in glob.glob(str(out / 'g*/cases/*.json')):
        n = Path(f).stem; c = json.load(open(f))
        sc[n] = 0.5 * c['temperature']['monthly_mae_C'] / ref[n]['temperature']['monthly_mae_C'] + 0.5 * c['rain']['loss'] / ref[n]['rain']['loss']
    target = sum(sc[r] for r in TARGET) / len(TARGET); worst = max(GUARD, key=lambda r: sc[r])
    return dict(setting=setting, scores=sc, target_mean=target, worst_guard=[worst, sc[worst]], passes=target <= 0.98 and sc[worst] <= 1.02)


if __name__ == '__main__':
    stage = sys.argv[1]; res = [run(stage, json.loads(a)) for a in sys.argv[2:]]
    out = ROOT / f'output/monsoon_inflow_20261121/{stage}/screen.json'; out.write_text(json.dumps(res, indent=1) + '\n')
    for r in res:
        print(r['setting'], 'target %.3f' % r['target_mean'], 'worst guard %s %.3f' % tuple(r['worst_guard']), 'PASS' if r['passes'] else 'fail',
              ' | ' + ' '.join(f'{k}={v:.3f}' for k, v in sorted(r['scores'].items())))
    ok = [r for r in res if r['passes']]
    print('stage', stage, 'screen', 'PASS: start ' + json.dumps(min(ok, key=lambda r: r['target_mean'])['setting']) if ok else 'FAIL')
