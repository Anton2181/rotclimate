"""World refit for the invented map on r41 physics with planet levers (calibration/map_world_r41_planet/plan.json).

    python -I scripts/world_campaign_r41.py search [--resume]   # guarded ds32 search over five known layouts
    python -I scripts/world_campaign_r41.py review              # finalists, native ds8 check, nine-layout audit

r40's campaign (scripts/world_campaign_r40.py) with three changes the plan
freezes: the planet levers ruled legal for the invented world (tilt, orbit,
starlight, greenhouse, land by latitude) are free; the off-map continuation is
fixed at the 300 km measured on Earth; and the search optimises inside the
coarse screen (calibrate mode 'guarded' with the 'world_screen' reference)
instead of screening afterwards, since r40's best coarse worlds only traded
painted zones against each other.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash, freeze, write_json, identity
from check_r39_world import world_failures, measured
from check_r39_world_transfer import measure
from check_r39_world_robust import result_from_member
from world_campaign_r40 import paired_interval
from rotclimate import calibrate as C
from rotclimate.config import Params
from rotclimate.score import evaluate, objective

FOLDER = ROOT / 'calibration/map_world_r41_planet'
OUT = ROOT / 'output/r41_world_planet'
GUARDS = FOLDER / 'guard_reference.json'
PLANET = [("tilt", 8.0, 45.0), ("eccentricity", 0.0, 0.06), ("perihelion_after_solstice", -182.5, 182.5),
          ("solar_flux", 0.96, 1.04), ("greenhouse_wm2", -2.0, 8.0), ("ebm_land_scale", 0.4, 1.8)]
SPACE = [g for g in C.SPACE_WORLD if g[0] != 'tilt'] + PLANET
FIXED = ('retrograde', 'beyond_continuity_km')
LOCKED = ('retrograde', 'planet_radius', 'year_days', 'map_width_mi', 'map_height_mi', 'beyond_continuity_km',
          'winter_solstice_day')


def allowed():
    return ({name for name, *_ in SPACE if not name.startswith('tier')} | {'tier_tops', 'downsample'}) - set(FIXED)


def assert_world_only(candidate, start):
    for key in LOCKED:
        a, b = getattr(candidate, key), getattr(start, key)
        if (a != b) if isinstance(a, bool) else not np.isclose(a, b, rtol=0, atol=1e-10):
            raise ValueError('Locked planet changed: ' + key)
    ok = allowed()
    for key, value in asdict(candidate).items():
        if key not in ok and value != getattr(start, key):
            raise ValueError('Shared physics changed: ' + key)


def metrics_of(row):
    return dict(zonefit=row['score'] + row.get('guard_penalty', 0.0), accuracy=row['accuracy'], recall=row['recall'],
                mediterranean=row['mediterranean'])


def search(plan, resume):
    base = load_params(ROOT / plan['start']).replace(downsample=plan['downsample'])
    old = load_params(ROOT / plan['old_atlas_params']).replace(downsample=plan['downsample'])
    physics = load_params(ROOT / plan['physics'])
    ok = allowed() | {'beyond_continuity_km'}
    for key, value in asdict(base).items():
        if key not in ok and value != getattr(physics, key):
            raise ValueError('Shared physics changed: ' + key)
    if abs(base.beyond_continuity_km - 300.0) > 1e-9:
        raise ValueError('The plan fixes the continuation at 300 km')
    C._set_space(SPACE); encoded = C.encode(base)
    fixed = {name: float(encoded[C.NAMES.index(name)]) for name in FIXED}
    decoded = C.decode(encoded, base)
    for name, *_ in SPACE:
        if not name.startswith('tier') and name != 'retrograde' and not np.isclose(getattr(decoded, name), getattr(base, name), atol=1e-9):
            raise ValueError('The start does not round-trip: ' + name)
    paths = list((ROOT / 'rotclimate').glob('*.py')) + [Path(__file__), FOLDER / 'plan.json', FOLDER / 'start.json',
                                                        ROOT / plan['physics'], ROOT / plan['old_atlas_params']]
    freeze(FOLDER / 'protocol.json', dict(plan=plan, start=asdict(base), space=SPACE, fixed_genes=fixed,
                                          sources={str(p.relative_to(ROOT)): file_hash(p) for p in paths}))
    control = FOLDER / 'coarse_old_control.json'
    if not control.exists():
        print('Evaluating matched r41-atlas coarse control', flush=True)
        result = C.evaluate_params(old, 'zonefit', seeds=plan['layouts'], ensemble_objective='climate')
        write_json(control, result); print('r41 control:', result['score'], flush=True)
    ref = json.loads(control.read_text())
    guards = dict(form='world_screen', strict=ref['accuracy'], recall=ref['recall'],
                  med_dry=ref['mediterranean']['dry_share'], med_cs=ref['mediterranean']['cs_share'])
    if GUARDS.exists() and json.loads(GUARDS.read_text()) != json.loads(json.dumps(guards)):
        raise ValueError('Guard reference changed')
    write_json(GUARDS, guards)
    os.environ['ROTCLIMATE_GUARDS'] = str(GUARDS)
    best = C.calibrate(FOLDER / 'world', plan['evaluations'], base, sigma0=plan['sigma'], popsize=plan['popsize'],
                       workers=plan['workers'], seed=plan['seed'], fixed=fixed, mode='guarded', seeds=plan['layouts'],
                       race=0., stds=plan['stds'], resume=resume, ensemble_objective='climate')
    assert_world_only(load_params(FOLDER / 'world/best_params.json'), base)
    write_json(FOLDER / 'best_result.json', best)
    print('World fit complete; run the review.', flush=True)


def cell_allowances(plan, control_recall):
    """amendment_cell_screen.json: each zone's coarse recall allowance, max(0.03, 2 binomial standard errors)."""
    from rotclimate.geography import build_grid
    from rotclimate.geography import TARGET_KEYS
    g = build_grid(load_params(ROOT / plan['old_atlas_params']).replace(downsample=plan['downsample']))
    land = g.inmap & g.land
    out = {}
    for k, zone in TARGET_KEYS.items():
        n = int(((g.target == k) & land).sum()); r = control_recall[zone]
        out[zone] = max(0.03, 2.0 * float(np.sqrt(max(r * (1 - r), 0.0) / max(n, 1))))
    return out


def coarse_failures(metric, old, allow):
    failures = []
    if metric['accuracy'] < old['accuracy'] - .01:
        failures.append('Coarse strict accuracy lost more than 0.01')
    for zone, value in old['recall'].items():
        if metric['recall'][zone] < value - allow[zone]:
            failures.append(zone + ': recall exceeded loss allowance')
    if metric['mediterranean']['dry_share'] > old['mediterranean']['dry_share'] + .01:
        failures.append('Mediterranean dry share exceeded allowance')
    if metric['mediterranean']['cs_share'] < old['mediterranean']['cs_share'] - .03:
        failures.append('Mediterranean Cs share exceeded loss allowance')
    return failures


def review(plan, amended=False):
    global OUT
    if amended:
        OUT = ROOT / 'output/r41_world_planet_amended'
    if not (FOLDER / 'best_result.json').exists():
        raise SystemExit('The search must finish first')
    published = ROOT / 'atlases/earth_fit/params.json'
    if json.loads(published.read_text()) != json.loads((ROOT / plan['old_atlas_params']).read_text()):
        raise SystemExit('The published Earth-fit atlas is not the r41 atlas this plan compares against')
    rows = [json.loads(line) for line in (FOLDER / 'world/evals.jsonl').read_text().splitlines() if line.strip()]
    if len(rows) > plan['evaluations']:
        raise ValueError('World search exceeded its frozen budget')
    old = json.loads((FOLDER / 'coarse_old_control.json').read_text())
    old_metrics = dict(zonefit=old['score'], accuracy=old['accuracy'], recall=old['recall'], mediterranean=old['mediterranean'])
    allow = cell_allowances(plan, old_metrics['recall']) if amended else None
    eligible, seen, screen = [], set(), []
    for row in sorted(rows, key=lambda r: (-(r['score'] + r.get('guard_penalty', 0.0)), r['eval'])):
        if row.get('error') or row.get('raced') or not row.get('observed_numerics', {}).get('all_checks_passed'):
            continue
        key = identity(row['params'])
        if key in seen:
            continue
        seen.add(key)
        metric = metrics_of(row)
        if amended:
            failures = coarse_failures(metric, old_metrics, allow)
        else:
            failures = world_failures(metric, old_metrics, native=False)
            if row.get('guard_penalty', 0.0) > 0:
                failures.append('Guard penalty above zero')
        if metric['zonefit'] <= old_metrics['zonefit']:
            failures.append('Raw zonefit does not beat the coarse control')
        screen.append(dict(eval=row['eval'], zonefit=metric['zonefit'], guard_penalty=row.get('guard_penalty', 0.0),
                           hot_dry=row['recall'].get('hot_dry'), failures=failures))
        if not failures:
            eligible.append(row)
    eligible = eligible[:2]
    OUT.mkdir(parents=True, exist_ok=True)
    sources = list((ROOT / 'rotclimate').glob('*.py')) + list((ROOT / 'data/source').glob('*')) + [
        Path(__file__), FOLDER / 'plan.json', FOLDER / 'protocol.json', FOLDER / 'world/evals.jsonl',
        *([FOLDER / 'amendment_cell_screen.json'] if amended else []),
        published, ROOT / 'atlases/earth_fit/summary.json']
    run = freeze(OUT / 'protocol.json', dict(plan=plan, amended=amended, allowances=allow, coarse_screen=screen, finalists=[r['eval'] for r in eligible],
                                            sources={str(p.relative_to(ROOT)): file_hash(p) for p in sources if p.is_file()}))
    write_json(OUT / 'coarse_selection.json', dict(control=old_metrics, screen=screen, selected=[r['eval'] for r in eligible]))
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
        old16 = load_params(published).replace(downsample=16); cand16 = p.replace(downsample=16)
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
                  decision='Stage an atlas from the verified native checkpoint.' if passed else 'Keep the r41 atlas geometry; no world qualifies.')
    write_json(OUT / 'review.json', result); write_json(OUT / 'progress.json', result)
    print(json.dumps(dict(native=[(n['name'], n.get('failures')) for n in native],
                          audit=None if audit is None else dict(passed=audit['passed'], failures=audit['failures'],
                                                               bootstrap=audit.get('bootstrap')),
                          eligible=passed), indent=1), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', choices=['search', 'review']); ap.add_argument('--resume', action='store_true')
    ap.add_argument('--amended', action='store_true', help='amendment_cell_screen.json: coarse allowances scaled to zone cell counts')
    a = ap.parse_args()
    plan = json.loads((FOLDER / 'plan.json').read_text())
    search(plan, a.resume) if a.stage == 'search' else review(plan, a.amended)


if __name__ == '__main__':
    main()
