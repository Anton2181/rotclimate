"""W6 selection exactly as calibration/map_world_r58_planet/plan.json declares it ("selection"):

the best completed zero-penalty world by raw zonefit_rivers; native check at downsample 8, mean layouts 1-3 against the r51 start world
at ds8: numerical success and zonefit_rivers not below the start. If it fails, the r51 start world is used. Whatever the zone agreement,
the atlas uses r51 physics (owner).

Each world is simulated with the release build's own checkpoint (build_atlas_variant --simulate-only), so the selected world's
checkpoint is the release checkpoint (output/r58_world/candidate_001.pkl).

    .venv/bin/python -I scripts/select_world_r58.py
"""
import json, os, pickle, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from earth_benchmark import load_params
from rotclimate.config import Params
from rotclimate.score import evaluate, objective

FOLDER = ROOT / 'calibration/map_world_r58_planet'; OUT = ROOT / 'output/r58_world'; DEST = ROOT / 'calibration/map_world_r58'
PY = str(ROOT / '.venv/bin/python')


def simulate(name, params_file):
    ck = OUT / f'{name}.pkl'
    if not ck.exists():
        cmd = [PY, '-u', '-I', str(ROOT / 'scripts/build_atlas_variant.py'), '--params', str(params_file), '--name', f'_select_r58_{name}',
               '--title', 'selection', '--eyebrow', 'selection', '--downsample', '8', '--seeds', '1,2,3', '--workers', '3', '--fit-objective', 'zonefit_rivers', '--require-verified', '--simulate-only', '--checkpoint', str(ck)]
        print('simulating', name, flush=True)
        try:
            subprocess.run(cmd, check=True, cwd=ROOT, env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
        finally:
            shutil.rmtree(ROOT / 'atlases' / f'_select_r58_{name}', ignore_errors=True)
    r = pickle.load(ck.open('rb'))['result']
    ev = evaluate(r)
    return dict(name=name, params=str(params_file.relative_to(ROOT)), checkpoint=str(ck.relative_to(ROOT)),
                numerics_passed=bool(r.numerics.get('all_checks_passed')), fit=float(objective(ev, 'zonefit_rivers')), zonefit=float(objective(ev, 'zonefit')),
                strict_accuracy=float(ev['accuracy']), recall={k: float(v) for k, v in ev['recall'].items()})


def main():
    plan = json.loads((FOLDER / 'plan.json').read_text())
    rows = [json.loads(l) for l in (FOLDER / 'world/evals.jsonl').read_text().splitlines() if l.strip()]
    if not (FOLDER / 'best_result.json').exists(): raise SystemExit('The search must finish first')
    if len(rows) > plan['evaluations']: raise ValueError('World search exceeded its budget')
    ok = [r for r in rows if not r.get('error') and not r.get('raced') and r.get('observed_numerics', {}).get('all_checks_passed')
          and r.get('guard_penalty', 0.0) == 0.0]
    best = max(ok, key=lambda r: (r['score'], -r['eval']))
    OUT.mkdir(parents=True, exist_ok=True); DEST.mkdir(parents=True, exist_ok=True)
    start = load_params(FOLDER / 'start.json')
    cand = Params(**best['params']).replace(downsample=8)
    for k in ('retrograde', 'planet_radius', 'year_days', 'map_width_mi', 'map_height_mi', 'beyond_continuity_km', 'winter_solstice_day', 'tier_tops'):
        assert json.dumps(getattr(cand, k)) == json.dumps(getattr(start, k)), k
    phys = load_params(ROOT / 'calibration/local_accuracy_20261023/r58w_params.json')
    from rotclimate.joint import SHARED_FIELDS
    assert all(getattr(cand, k) == getattr(phys, k) for k in SHARED_FIELDS), 'candidate physics is not r58w'
    cand_file = DEST / f'candidate_{best["eval"]:03d}.json'; cand.to_json(cand_file)
    start_file = DEST / 'params_start.json'; start.replace(downsample=8).to_json(start_file)
    res = dict(plan=str((FOLDER / 'plan.json').relative_to(ROOT)), rule=plan['selection'], coarse_best=dict(eval=best['eval'], score=best['score'],
               guard_penalty=best.get('guard_penalty', 0.0), eligible=len(ok), evaluations=len(rows)))
    c = simulate('candidate', cand_file); s = simulate('start', start_file); res['candidate'] = c; res['start'] = s
    if c['numerics_passed'] and c['fit'] >= s['fit']:
        chosen = c
    else:
        chosen = s                                   # W5 plan: the start world (r51 world geometry on r58)
    res['selected'] = chosen['name']
    shutil.copy(ROOT / chosen['params'], DEST / 'params.json')
    shutil.copy(ROOT / chosen['checkpoint'], OUT / 'candidate_001.pkl')
    (DEST / 'selection.json').write_text(json.dumps(res, indent=1) + '\n'); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
