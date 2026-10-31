"""World refit for the invented map on r40 physics (calibration/map_world_r40/plan.json).

    python -I scripts/world_campaign_r40.py search [--resume]   # coarse ds32 search over five known layouts
    python -I scripts/world_campaign_r40.py review              # coarse screen, native ds8 check, nine-layout audit

The rules are r39's (scripts/refit_r39_world.py, check_r39_world.py,
audit_r39_surroundings.py) with two lessons from its failed campaigns: train
on all five known layouts, and validate on nine new ones with the paired
bootstrap gate instead of a two-layout batch.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash, freeze, write_json, identity
from check_r39_world import assert_world_only, world_failures, measured
from check_r39_world_transfer import measure
from check_r39_world_robust import result_from_member
from rotclimate import calibrate as C
from rotclimate.config import Params
from rotclimate.score import evaluate, objective

FOLDER = ROOT / 'calibration/map_world_r40'
OUT = ROOT / 'output/r40_world'
SEED = 594901


def paired_interval(differences):
    values = np.sort(np.asarray(differences, float))
    if values.shape != (9,) or not np.isfinite(values).all():
        raise ValueError('Need nine finite paired differences')
    means = values[np.random.default_rng(SEED).integers(0, 9, size=(20000, 9))].mean(1)
    lower, upper = np.quantile(means, [.025, .975])
    return dict(mean=float(values.mean()), lower=float(lower), upper=float(upper),
                passed=bool(values.mean() > 0 and lower > 0), draws=20000, seed=SEED)


def search(plan, resume):
    base = load_params(ROOT / plan['start']).replace(downsample=plan['downsample'])
    old = load_params(ROOT / plan['old_atlas'] / 'params.json').replace(downsample=plan['downsample'])
    physics = load_params(ROOT / plan['physics'])
    allowed = {k for k in C.WORLD_GENES if not k.startswith('tier')} | {'tier_tops', 'downsample'}
    for key, value in asdict(base).items():
        if key not in allowed and value != getattr(physics, key):
            raise ValueError('Shared physics changed: ' + key)
    C._set_space(C.SPACE_WORLD); encoded = C.encode(base)
    fixed = {name: float(encoded[C.NAMES.index(name)]) for name in ['tilt', 'retrograde']}
    paths = list((ROOT / 'rotclimate').glob('*.py')) + [Path(__file__), FOLDER / 'plan.json', FOLDER / 'start.json',
                                                        ROOT / plan['physics'], ROOT / plan['old_atlas'] / 'params.json']
    freeze(FOLDER / 'protocol.json', dict(plan=plan, start=asdict(base), fixed_genes=fixed,
                                          sources={str(p.relative_to(ROOT)): file_hash(p) for p in paths}))
    control = FOLDER / 'coarse_old_control.json'
    if not control.exists():
        print('Evaluating matched old-world coarse control', flush=True)
        result = C.evaluate_params(old, 'zonefit', seeds=plan['layouts'], ensemble_objective='climate')
        write_json(control, result); print('Old-world control:', result['score'], flush=True)
    best = C.calibrate(FOLDER / 'world', plan['evaluations'], base, sigma0=plan['sigma'], popsize=plan['popsize'],
                       workers=plan['workers'], seed=plan['seed'], fixed=fixed, mode='zonefit', seeds=plan['layouts'],
                       race=0., stds=plan['stds'], resume=resume, ensemble_objective='climate')
    assert_world_only(load_params(FOLDER / 'world/best_params.json'), base)
    write_json(FOLDER / 'best_result.json', best)
    print('World fit complete; run the review.', flush=True)


def review(plan):
    if not (FOLDER / 'best_result.json').exists():
        raise SystemExit('The search must finish first')
    rows = [json.loads(line) for line in (FOLDER / 'world/evals.jsonl').read_text().splitlines() if line.strip()]
    if len(rows) > plan['evaluations']:
        raise ValueError('World search exceeded its frozen budget')
    old = json.loads((FOLDER / 'coarse_old_control.json').read_text())
    old_metrics = dict(zonefit=old['score'], accuracy=old['accuracy'], recall=old['recall'], mediterranean=old['mediterranean'])
    eligible, seen, screen = [], set(), []
    for row in sorted(rows, key=lambda r: (-r['score'], r['eval'])):
        if row.get('error') or row.get('raced') or not row.get('observed_numerics', {}).get('all_checks_passed'):
            continue
        key = identity(row['params'])
        if key in seen:
            continue
        seen.add(key)
        metric = dict(zonefit=row['score'], accuracy=row['accuracy'], recall=row['recall'], mediterranean=row['mediterranean'])
        failures = world_failures(metric, old_metrics, native=False)
        screen.append(dict(eval=row['eval'], score=row['score'], failures=failures))
        if not failures:
            eligible.append(row)
    eligible = eligible[:2]
    OUT.mkdir(parents=True, exist_ok=True)
    sources = list((ROOT / 'rotclimate').glob('*.py')) + list((ROOT / 'data/source').glob('*')) + [
        Path(__file__), FOLDER / 'plan.json', FOLDER / 'protocol.json', FOLDER / 'world/evals.jsonl',
        ROOT / 'atlases/earth_fit/params.json', ROOT / 'atlases/earth_fit/summary.json']
    run = freeze(OUT / 'protocol.json', dict(plan=plan, coarse_screen=screen, finalists=[r['eval'] for r in eligible],
                                            sources={str(p.relative_to(ROOT)): file_hash(p) for p in sources if p.is_file()}))
    write_json(OUT / 'coarse_selection.json', dict(screen=screen, selected=[r['eval'] for r in eligible]))
    pub = json.loads((ROOT / 'atlases/earth_fit/summary.json').read_text())
    reference = dict(zonefit=pub['zonefit'], accuracy=pub['strict_accuracy'], recall=pub['recall'], mediterranean=pub['mediterranean'])
    start = load_params(FOLDER / 'start.json'); native = []; selected = None
    (FOLDER / 'finalists').mkdir(exist_ok=True)
    for row in eligible:
        tag = f'candidate_{row["eval"]:03d}'; p = Params(**row['params']).replace(downsample=8)
        assert_world_only(p, start)
        parameter_file = FOLDER / 'finalists' / (tag + '.json'); p.to_json(parameter_file)
        print(tag + ': native layouts 1-3', flush=True)
        try:
            metric = measured(p, [1, 2, 3], OUT / (tag + '.pkl'), run)
            failures = world_failures(metric, reference, native=True)
            native.append(dict(name=tag, metrics=metric, failures=failures, params=str(parameter_file.relative_to(ROOT))))
        except Exception as error:
            failures = [repr(error)]; native.append(dict(name=tag, failures=failures))
        write_json(OUT / 'progress.json', dict(complete=False, native=native))
        print(tag + (': native passed' if not failures else ': native failed ' + str(failures)), flush=True)
        if not failures:
            selected = (tag, p, parameter_file); break
    audit = None
    if selected:
        tag, p, parameter_file = selected; layouts = plan['audit_layouts']
        old16 = load_params(ROOT / 'atlases/earth_fit/params.json').replace(downsample=16); cand16 = p.replace(downsample=16)
        try:
            a = measure(old16, layouts, 'audit_reference', OUT, run)
            b = measure(cand16, layouts, 'audit_candidate', OUT, run)
            paired = []
            for seed in layouts:
                scores = {}
                for name, q in (('reference', old16), ('candidate', cand16)):
                    ev = evaluate(result_from_member(OUT / 'members' / f'audit_{name}_seed{seed}.pkl', q, seed))
                    scores[name] = dict(zonefit=objective(ev, 'zonefit'), accuracy=ev['accuracy'])
                paired.append(dict(seed=seed, **scores, difference=scores['candidate']['zonefit'] - scores['reference']['zonefit']))
            interval = paired_interval([r['difference'] for r in paired]); failures = []
            if b['zonefit'] < a['zonefit']:
                failures.append('Nine-layout mean-climate zonefit worsened')
            if b['accuracy'] < a['accuracy'] - .01:
                failures.append('Nine-layout strict agreement loss exceeds 0.01')
            if not interval['passed']:
                failures.append('Paired bootstrap lower bound is not positive')
            audit = dict(reference=a, candidate=b, paired=paired, bootstrap=interval, failures=failures, passed=not failures)
        except Exception as error:
            audit = dict(failures=[repr(error)], passed=False)
    passed = bool(selected and audit['passed'])
    result = dict(complete=True, identity=run, native=native, audit=audit, eligible_for_publication=passed,
                  params=str(selected[2].relative_to(ROOT)) if passed else None,
                  checkpoint=str((OUT / (selected[0] + '.pkl')).relative_to(ROOT)) if passed else None,
                  decision='Stage an atlas from the verified native checkpoint.' if passed else 'Keep the canonical r38 atlas; no world qualifies.')
    write_json(OUT / 'review.json', result); write_json(OUT / 'progress.json', result)
    print(json.dumps(dict(native=[(n['name'], n.get('failures')) for n in native],
                          audit=None if audit is None else dict(passed=audit['passed'], failures=audit['failures'],
                                                               bootstrap=audit.get('bootstrap')),
                          eligible=passed), indent=1), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', choices=['search', 'review']); ap.add_argument('--resume', action='store_true')
    a = ap.parse_args()
    plan = json.loads((FOLDER / 'plan.json').read_text())
    search(plan, a.resume) if a.stage == 'search' else review(plan)


if __name__ == '__main__':
    main()
