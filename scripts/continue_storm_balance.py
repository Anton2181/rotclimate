"""Continue the fixed storm proposal with the user's Mediterranean target rule.

Default is read-only. --run reuses worlds 301/302, checks world 1, settling and
validation, and publishes only if all pass. No search or changed climate physics.
The original zero-increase rejection and experiment files remain preserved.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_storm_balance as storm

night = storm.night
MED_TARGET = .05


def script_id():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def guard_failures(row, anchor):
    """Protect the dry zones; allow already-good Mediterranean worlds up to 5%."""
    failures = []
    for zone in ('cold_dry', 'hot_dry'):
        drop = anchor['zone_recall'][zone] - row['zone_recall'][zone]
        if drop > night.GUARDS[f'{zone}_max_drop'] + 1e-12:
            failures.append(f'{zone} agreement fell by {100 * drop:.2f} percentage points')
    drop = anchor['accuracy'] - row['accuracy']
    if drop > night.GUARDS['accuracy_max_drop'] + 1e-12:
        failures.append(f'overall agreement fell by {100 * drop:.2f} percentage points')
    limit = max(MED_TARGET, anchor['mediterranean']['dry_share'])
    if row['mediterranean']['dry_share'] > limit + 1e-12:
        failures.append(f'Mediterranean dry area {row["mediterranean"]["dry_share"]:.2%} exceeds its {limit:.2%} limit')
    drop = anchor['mediterranean']['cs_share'] - row['mediterranean']['cs_share']
    if drop > night.GUARDS['med_cs_max_drop'] + 1e-12:
        failures.append(f'Mediterranean Cs area fell by {100 * drop:.2f} percentage points')
    return failures


def worst_improves(trial, controls, seeds):
    a = max(controls[s]['row']['mediterranean']['dry_share'] for s in seeds)
    b = max(trial[str(s)]['row']['mediterranean']['dry_share'] for s in seeds)
    return dict(anchor=a, trial=b, passed=b < a - 1e-12)


def load_inputs(source, retry_source, completed_source):
    old, controls = storm.load_inputs(source, retry_source)
    completed_source = Path(completed_source).resolve()
    if json.loads((completed_source / 'experiment.json').read_text()) != old:
        raise ValueError('Completed storm checks do not match the fixed proposal and original source.')
    prior = json.loads((completed_source / 'comparison.json').read_text())
    if prior['stage'] != 'complete' or prior['decision'] != 'rejected':
        raise ValueError('This continuation requires the completed, previously rejected storm check.')
    reused = {s: storm.load_checked(storm.case_job(old, completed_source,
                       f'train_storm_balance_s{s}', s)) for s in (301, 302)}
    guards = {k: v for k, v in night.GUARDS.items() if k != 'med_dry_max_increase'}
    guards.update(med_dry_limit='max(anchor dry share, 0.05)', worst_med_dry_must_improve=True)
    plan = dict(old, original_diagnostic_id=old['diagnostic_id'], diagnostic_id=script_id(),
                completed_source=str(completed_source), guards=guards,
                previous_guards=old['guards'], reused_inputs={str(s): d['input_id'] for s, d in reused.items()},
                user_preference='Allow up to 5% dry Mediterranean land on worlds already below that target, '
                                'while requiring improvement on the worst world.',
                note='One fixed proposal under the user-selected Mediterranean target rule. '
                     'Original rejection retained; validation worlds already examined; '
                     'candidate finer grid and 73-date sampling untested.')
    return plan, controls, reused


def ensure_sources(plan):
    if (night.source_id() != plan['source_id'] or script_id() != plan['diagnostic_id']
            or storm.script_id() != plan['original_diagnostic_id']):
        raise ValueError('Source or inputs changed; refusing mixed results.')


def run_checks(plan, controls, reused, out):
    out = Path(out).resolve()
    for root in (plan['source'], plan['retry_source'], plan['completed_source']):
        root = Path(root)
        if out == root or root in out.parents:
            raise ValueError('Choose a separate output directory to preserve the earlier experiments.')
    ensure_sources(plan)
    manifest, state_path = out / 'experiment.json', out / 'comparison.json'
    if manifest.exists() and json.loads(manifest.read_text()) != plan:
        raise ValueError('Output contains another policy or experiment; choose a new --out directory.')
    if state_path.exists():
        if not manifest.exists():
            raise ValueError('Output comparison lacks experiment provenance.')
        previous = json.loads(state_path.read_text())
        if previous.get('stage') == 'complete':
            print('Already complete. Read ' + str(out / 'summary.md'), flush=True)
            return previous
    (out / 'cases').mkdir(parents=True, exist_ok=True)
    night.atomic_json(manifest, plan)
    state = dict(stage='development', decision='pending', runs={},
                 checked_worlds={str(s): d for s, d in reused.items()},
                 controls={str(s): d['row'] for s, d in controls.items()},
                 atlas={'status': 'unchanged'}, guards=plan['guards'], note=plan['note'])

    def save():
        night.atomic_json(state_path, state)
        lines = ['# Coastal storm target-rule continuation', '', 'Stage: ' + state['stage'] + '.',
                 '', 'Decision: ' + state['decision'] + '.', '', plan['note'], '',
                 'Mediterranean dry-area limit per world: max(anchor dry area, 5%). '
                 'The worst-world dry area must strictly improve. Other zone limits unchanged.', '',
                 '| World | Anchor Med dry | Trial Med dry | Allowed Med dry | Cold-dry anchor → trial | Hot-dry anchor → trial | Overall trial |',
                 '|---|---:|---:|---:|---:|---:|---:|']
        for seed, d in state['checked_worlds'].items():
            if d['status'] != 'ok':
                continue
            a, b = controls[int(seed)]['row'], d['row']
            lines.append(f"| {seed} | {a['mediterranean']['dry_share']:.2%} | {b['mediterranean']['dry_share']:.2%} | "
                         f"{max(MED_TARGET,a['mediterranean']['dry_share']):.2%} | "
                         f"{a['zone_recall']['cold_dry']:.2%} → {b['zone_recall']['cold_dry']:.2%} | "
                         f"{a['zone_recall']['hot_dry']:.2%} → {b['zone_recall']['hot_dry']:.2%} | {b['accuracy']:.2%} |")
        lines += ['', 'Worlds 301 and 302 are reused from the original completed check.',
                  '', 'Atlas: ' + state['atlas']['status'] + '.']
        if 'reason' in state:
            lines += ['', state['reason']]
        if 'med_goal_met' in state:
            lines += ['', 'Mediterranean dry area <=5% on all five worlds: '
                      + ('met.' if state['med_goal_met'] else 'not met.')]
        (out / 'summary.md').write_text('\n'.join(lines) + '\n')

    def finish(decision, reason):
        state.update(stage='complete', decision=decision, reason=reason)
        save()
        print(reason, flush=True)
        return state

    def evaluate(name, seed, **options):
        ensure_sources(plan)
        j = storm.case_job(plan, out, name, seed, **options)
        d = storm.solve_case(j)
        ensure_sources(plan)
        state['runs'][name] = d
        save()
        if d['status'] == 'ok':
            r = d['row']
            print(f"{name}: Med dry {r['mediterranean']['dry_share']:.2%}, "
                  f"cold-dry {r['zone_recall']['cold_dry']:.2%}, "
                  f"hot-dry {r['zone_recall']['hot_dry']:.2%}, overall {r['accuracy']:.2%}", flush=True)
        return d

    def check(d, seed):
        state['checked_worlds'][str(seed)] = d
        if d['status'] != 'ok':
            return finish('incomplete_numerics', f'World {seed} failed: {d["error"]}. Atlas retained.')
        failures = guard_failures(d['row'], controls[seed]['row'])
        if failures:
            return finish('rejected', f'World {seed}: ' + '; '.join(failures) + '. Atlas retained.')
        save()
        return None

    save()
    for seed, d in reused.items():
        stopped = check(d, seed)
        if stopped is not None:
            return stopped
    stopped = check(evaluate('train_storm_balance_s1', 1, full=True, transport=True), 1)
    if stopped is not None:
        return stopped
    state['development_worst'] = worst_improves(state['checked_worlds'], controls, storm.DEVELOPMENT)
    if not state['development_worst']['passed']:
        return finish('not_better', 'Worst-world Mediterranean dry area did not strictly improve. Atlas retained.')
    state['stage'] = 'warmup'
    warm = evaluate('storm_balance_warm1', 1, warmup=plan['warmup_steps'] // 2, transport=True)
    if warm['status'] != 'ok':
        return finish('incomplete_numerics', 'One-year warm-up check failed: ' + warm['error'] + '. Atlas retained.')
    state['warmup_check'] = night.stability(warm, state['checked_worlds']['1'])
    if not state['warmup_check']['passed']:
        return finish('unsettled', 'One versus two warm-up years exceed the declared limits. Atlas retained.')
    state['stage'] = 'validation'
    save()
    for seed in storm.VALIDATION:
        stopped = check(evaluate(f'validation_storm_balance_s{seed}', seed), seed)
        if stopped is not None:
            return stopped
    state['final_worst'] = worst_improves(state['checked_worlds'], controls,
                                         (*storm.DEVELOPMENT, *storm.VALIDATION))
    if not state['final_worst']['passed']:
        return finish('not_better', 'Worst-world Mediterranean dry area did not improve across all five checks. Atlas retained.')
    state['decision'] = 'qualified'
    state['med_goal_met'] = all(d['row']['mediterranean']['dry_share'] <= MED_TARGET
                                  for d in state['checked_worlds'].values())
    state['stage'] = 'atlas'
    save()
    ensure_sources(plan)
    spec = dict(out=str(out), selected='storm_balance_target', params=asdict(storm.params_for(plan, 1)),
                result=state['checked_worlds']['1']['result'], source_id=plan['source_id'],
                layer_scale=3, warmup_steps=plan['warmup_steps'], fresh_checks_complete=True,
                fine_checks={'status': 'not_run_for_candidate', 'used': False},
                followup={'diagnostic_id': plan['diagnostic_id'], 'guards': plan['guards'],
                          'user_preference': plan['user_preference'], 'note': plan['note']})
    state['atlas'] = storm.publish(spec, out)
    if state['atlas']['status'] != 'published':
        state['stage'] = 'export_failed'
        save()
        return state
    return finish('qualified', 'User-selected Mediterranean target rule, protected-zone, warm-up and validation checks passed; '
                  'coarse-grid atlas published. Candidate finer-grid and denser seasonal sampling remain untested.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=ROOT / 'output/overnight_mediterranean')
    ap.add_argument('--retry-source', type=Path, default=ROOT / 'output/overnight_validation_retry')
    ap.add_argument('--completed-source', type=Path, default=ROOT / 'output/storm_balance_checks')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/storm_balance_target_checks')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args(argv)
    plan, controls, reused = load_inputs(a.source, a.retry_source, a.completed_source)
    print('Same fixed storm proposal. New user-selected rule: Mediterranean dry area <=max(anchor,5%) '
          'on each world, and strictly lower worst-world dry area. Other guards unchanged.', flush=True)
    print('Reuse completed worlds 301/302 and all five anchor results. At most four new sequential runs: '
          'world 1 with two warm-up years, its one-year settling check, then validation worlds 401/402.', flush=True)
    print('Stop on a failed check; publish the coarse-grid atlas only if all pass. '
          'Candidate finer grid and denser seasonal sampling remain untested.', flush=True)
    print('Allow roughly 2–4 hours if all stages run; difficult retries can take longer. Exact matching cases resume.', flush=True)
    if not a.run:
        print('Plan only. Add --run to execute.', flush=True)
        return 0
    state = run_checks(plan, controls, reused, a.out)
    print(f'Read {a.out / "summary.md"}', flush=True)
    return 1 if state['decision'] == 'incomplete_numerics' or state['stage'] == 'export_failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
