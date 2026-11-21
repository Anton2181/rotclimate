"""Side project: world refit with two targets only (calibration/two_target_20261121/plan.json).

    .venv/bin/python -I scripts/two_target_world.py search [--resume]
    .venv/bin/python -I scripts/two_target_world.py check     # ds8 layouts 1-3: start vs best
"""
import json, sys
from dataclasses import asdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
from earth_benchmark import load_params
from world_campaign_r50 import SPACE, FIXED, assert_world_only
from local_benchmark_protocol import write_json
from rotclimate import calibrate as C

FOLDER = ROOT / 'calibration/two_target_20261121'


def search(plan, resume):
    base = load_params(ROOT / plan['start']).replace(downsample=plan['downsample'])
    C._set_space(SPACE); enc = C.encode(base)
    fixed = {n: float(enc[C.NAMES.index(n)]) for n in FIXED}
    ctrl = FOLDER / 'start_score.json'
    if not ctrl.exists():
        r = C.evaluate_params(base, 'twotarget', seeds=plan['layouts'], ensemble_objective='climate')
        write_json(ctrl, r); print('start', r['two_target'], flush=True)
    best = C.calibrate(FOLDER / 'world', plan['evaluations'], base, sigma0=plan['sigma'], popsize=plan['popsize'],
                       workers=plan['workers'], seed=plan['seed'], fixed=fixed, mode='twotarget', seeds=plan['layouts'],
                       race=0., stds={'north_bearing': 0.05}, resume=resume, ensemble_objective='climate')
    assert_world_only(load_params(FOLDER / 'world/best_params.json'), base)
    write_json(FOLDER / 'best_result.json', best); print('done', best.get('two_target'), flush=True)


def check(plan):
    out = {}
    for tag, path in [('start', ROOT / plan['start']), ('best', FOLDER / 'world/best_params.json')]:
        p = load_params(path).replace(downsample=8)
        r = C.evaluate_params(p, 'twotarget', seeds=[1, 2, 3], ensemble_objective='climate')
        out[tag] = dict(two_target=r['two_target'], accuracy=r['accuracy'], recall=r['recall'],
                        zonefit=r['zonefit_score'], mediterranean=r['mediterranean'])
        print(tag, json.dumps(out[tag]['two_target']), flush=True)
    write_json(FOLDER / 'ds8_check.json', out)


if __name__ == '__main__':
    plan = json.loads((FOLDER / 'plan.json').read_text())
    search(plan, '--resume' in sys.argv) if sys.argv[1] == 'search' else check(plan)
