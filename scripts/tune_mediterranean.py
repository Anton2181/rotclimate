"""One bounded local calibration with per-world dry-zone protection.

Default prints a read-only plan. --run tries three fixed, one-parameter changes
on development worlds 1, 302 and 301, stopping a candidate as soon as it fails a
per-world constraint. This is exact constraint rejection, not score racing.
At most ten new simulations are needed; completed fresh-world anchors are reused.
No production parameters, classifier rules or atlas files are changed.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diagnose_moisture import case_summary
from scripts.mediterranean_pilot import dry_patch_changes, matching_params
from scripts.validate_mediterranean import finalists, model_code_id

SEEDS = (1, 302, 301)
GUARDS = dict(cold_dry_max_drop=0.02, hot_dry_max_drop=0.03,
              accuracy_max_drop=0.01, med_dry_max_increase=0.0, med_cs_max_drop=0.02)
MED_DRY_GOAL = 0.05


def candidates(base):
    return dict(drier_exchange=base.replace(eddy_rate=base.eddy_rate * 0.9),
                stronger_seasons=base.replace(eddy_seasonality=0.8),
                slightly_narrower=base.replace(storm_width=base.storm_width * 0.95))


def guard_failures(row, anchor):
    """An improvement elsewhere cannot compensate for a failed world/zone."""
    failures = []
    for zone in ('cold_dry', 'hot_dry'):
        drop = anchor['zone_recall'][zone] - row['zone_recall'][zone]
        if drop > GUARDS[f'{zone}_max_drop'] + 1e-12:
            failures.append(f'{zone} agreement fell by {100 * drop:.2f} percentage points')
    drop = anchor['accuracy'] - row['accuracy']
    if drop > GUARDS['accuracy_max_drop'] + 1e-12:
        failures.append(f'overall agreement fell by {100 * drop:.2f} percentage points')
    increase = row['mediterranean']['dry_share'] - anchor['mediterranean']['dry_share']
    if increase > GUARDS['med_dry_max_increase'] + 1e-12:
        failures.append(f'Mediterranean dry area grew by {100 * increase:.2f} percentage points')
    cs_drop = anchor['mediterranean']['cs_share'] - row['mediterranean']['cs_share']
    if cs_drop > GUARDS['med_cs_max_drop'] + 1e-12:
        failures.append(f'Mediterranean Cs area fell by {100 * cs_drop:.2f} percentage points')
    return failures


def load_cached(path, fields, expected, code_id):
    if not path.exists() or not fields.exists():
        return None
    detail = json.loads(path.read_text())
    if detail.get('validation_code_id') != code_id or not matching_params(detail['params'], expected):
        return None
    # A matching JSON beside a stale field archive is not a reusable run.
    import numpy as np
    with np.load(fields, allow_pickle=False) as saved:
        if not matching_params(json.loads(str(saved['params_json'])), expected):
            return None
    return detail


def checked_summary(detail):
    row = case_summary(detail)
    c = row['convergence']
    if not c['usable_for_comparison'] or not c['moisture_convergence_checked']:
        raise RuntimeError('A convergence check failed; result saved. Stopping local calibration.')
    return row


def run_or_reuse(name, seed, params, out, code_id):
    path = out / f'{name}_seed{seed}.json'
    fields = out / f'{name}_seed{seed}_fields.npz'
    detail = load_cached(path, fields, params, code_id)
    if detail is None:
        from scripts.diagnose_numerics import diagnose
        start = time.monotonic()
        print(f'Running {name}, world {seed}...', flush=True)
        def progress(done, total):
            if done == 1 or done % 5 == 0 or done == total:
                print(f'{name}, world {seed}: {done}/{total} seasonal steps; '
                      f'{(time.monotonic() - start) / 60:.1f} min', flush=True)
        try:
            detail = diagnose(params, snapshot=fields, progress=progress)
        except RuntimeError as error:
            (out / f'{name}_seed{seed}_failure.json').write_text(json.dumps(dict(
                params=asdict(params), error=str(error), details=getattr(error, 'details', None),
                validation_code_id=code_id), indent=2) + '\n')
            raise
        detail['validation_code_id'] = code_id
        path.write_text(json.dumps(detail, indent=2) + '\n')
    else:
        print(f'Reusing {name}, world {seed}.', flush=True)
    row = checked_summary(detail)
    print(f"{name}, world {seed}: Mediterranean dry {row['mediterranean']['dry_share']:.1%}, "
          f"cold-dry {row['zone_recall']['cold_dry']:.1%}, "
          f"hot-dry {row['zone_recall']['hot_dry']:.1%}, overall {row['accuracy']:.1%}", flush=True)
    return row, fields


def rank(rows):
    return (max(r['mediterranean']['dry_share'] for r in rows.values()),
            -sum(r['accuracy'] for r in rows.values()) / len(rows))


def decision(anchors, trials):
    complete = {name: trial for name, trial in trials.items()
                if trial['status'] == 'passed' and set(trial['worlds']) == set(SEEDS)}
    eligible = {name: trial for name, trial in complete.items()
                if rank(trial['worlds']) < rank(anchors)}
    best = min(eligible, key=lambda name: rank(eligible[name]['worlds'])) if eligible else None
    return dict(complete_candidates=list(complete), suggested_candidate=best,
                mediterranean_goal_met=best is not None and rank(eligible[best]['worlds'])[0] <= MED_DRY_GOAL,
                note='Development-world screening only. A suggestion needs independent and resolution checks; no atlas update. '
                     'No qualifying improvement means retain the broad seasonal anchor, not expand this search automatically.')


def local_search(base, anchors, anchor_fields, evaluate, save):
    """Bounded probes; save after every world, and never rank incomplete cases."""
    trials = {}
    for name, params in candidates(base).items():
        trial = dict(params=asdict(params), worlds={}, status='running', failures=[])
        trials[name] = trial
        for seed in SEEDS:
            row, fields = evaluate(name, seed, params.replace(beyond_seed=seed))
            row['mediterranean_patch_changes'] = dry_patch_changes(anchor_fields[seed], fields)
            trial['worlds'][seed] = row
            trial['failures'] = guard_failures(row, anchors[seed])
            if trial['failures']:
                trial['status'] = 'rejected'
            elif seed == SEEDS[-1]:
                trial['status'] = 'passed'
            save(trials)
            if trial['failures']:
                print(f"Rejecting {name} on world {seed}: {'; '.join(trial['failures'])}. "
                      'Skipping its remaining worlds.', flush=True)
                break
    return trials


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/mediterranean_tuning')
    a = ap.parse_args()
    base = finalists()['strong_seasonal']
    code_id = model_code_id()
    anchors, anchor_fields = {}, {}
    for seed in (301, 302):
        stem = ROOT / 'output/mediterranean_validation' / f'strong_seasonal_seed{seed}'
        fields = stem.with_name(stem.name + '_fields.npz')
        detail = load_cached(stem.with_suffix('.json'), fields, base.replace(beyond_seed=seed), code_id)
        if detail is None:
            ap.error(f'World {seed} anchor is missing or stale. Complete validate_mediterranean.py first.')
        anchors[seed], anchor_fields[seed] = checked_summary(detail), fields
    for name, p in candidates(base).items():
        changes = {k: v for k, v in asdict(p).items() if v != asdict(base)[k]}
        print(f'{name}: {changes}', flush=True)
    print('Development worlds 1, 302, 301. Reuse completed anchors 301/302; verify anchor 1.\n'
          'Per-world limits: cold-dry loss <= 2 pp, hot-dry loss <= 3 pp, overall loss <= 1 pp, '
          'no Mediterranean dry-area increase or Cs-area loss > 2 pp. '
          'Goal: Mediterranean dry area <= 5% on every world.\n'
          'Three fixed probes, at most 10 new simulations; reject a failed candidate immediately. '
          'Roughly 35–100 minutes at recent speeds; difficult retries may add time. '
          'Exact matching new runs resume. No automatic atlas or production parameter update.', flush=True)
    if not a.run:
        print('Plan only. Add --run to execute.')
        return
    a.out.mkdir(parents=True, exist_ok=True)
    anchors[1], anchor_fields[1] = run_or_reuse('anchor', 1, base.replace(beyond_seed=1), a.out, code_id)
    def save(trials):
        report = dict(validation_code_id=code_id, worlds=list(SEEDS), guards=GUARDS,
                      mediterranean_dry_goal=MED_DRY_GOAL, anchors=anchors, trials=trials,
                      decision=decision(anchors, trials))
        (a.out / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    save({})
    trials = local_search(base, anchors, anchor_fields,
        lambda name, seed, p: run_or_reuse(name, seed, p, a.out, code_id), save)
    print(json.dumps(decision(anchors, trials), indent=2), flush=True)


if __name__ == '__main__':
    main()
