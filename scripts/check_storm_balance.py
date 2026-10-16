"""Finish checking one fixed coastal-storm proposal from the overnight sweep.

Default prints a read-only plan. --run checks development worlds, seasonal
settling, then the already examined validation worlds. Reuse converged anchors;
stop at the first failed check. Publish a coarse-grid atlas only after all pass.
No search, finer-grid rerun or relaxation of the declared zone limits.
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
from scripts import overnight_mediterranean as night
from scripts import retry_overnight_validation as retry

DEVELOPMENT = (301, 302, 1)  # Check the world that rejected both earlier proposals first.
VALIDATION = (401, 402)


def script_id():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def load_checked(j):
    d = night.cached(j)
    if not night.passed(d):
        raise ValueError(f'Missing matching converged input: {j["name"]}')
    fields = Path(d['fields'])
    detail = json.loads(fields.with_name(fields.stem.removesuffix('_fields') + '_diagnostic.json').read_text())
    settings = detail['run_settings']
    if (settings['spinup_steps_requested'] != j['spinup']
            or settings['spinup_steps_observed'] != j['spinup']
            or settings['steps_per_year'] != j['params']['steps_per_year']
            or not night.matching_params(detail['params'], night.Params(**j['params']))):
        raise ValueError(f'Wrong warm-up, calendar or parameters in {j["name"]}')
    # Recheck all recorded convergence criteria, not just a successful status.
    return {**d, 'row': night.checked_summary(detail)}


def load_inputs(source, retry_out):
    source, retry_out = Path(source).resolve(), Path(retry_out).resolve()
    experiment = json.loads((source / 'experiment.json').read_text())
    summary = json.loads((source / 'summary.json').read_text())
    if summary['stage'] != 'complete' or night.source_id() != experiment['source_id']:
        raise ValueError('Need the completed overnight experiment with unchanged model and inputs.')
    code = experiment['source_id']
    anchor = night.Params(**experiment['anchor'])
    candidate = night.sweep(night.Params(**experiment['base']))['storm_asym_low']
    screen = load_checked(night.job('screen_storm_asym_low', candidate, 8, source, code))
    if not night.matching_params(screen['row']['params'], candidate):
        raise ValueError('Candidate does not match the fixed overnight proposal.')
    controls = {}
    for seed, name in ((1, 'anchor_warm2'), (302, 'train_anchor_s302'),
                       (301, 'train_anchor_s301'), (401, 'fresh_anchor_s401')):
        controls[seed] = load_checked(night.job(name, anchor.replace(beyond_seed=seed),
            2 * anchor.steps_per_year, source, code, full=seed == 1, transport=seed == 1))
    retry_plan = retry.retry_plan(source)
    j = night.job('anchor_s402_more_iterations', night.Params(**retry_plan['params']),
                  retry_plan['warmup_steps'], retry_out, code, transport=True)
    j['input_id'] = hashlib.sha256((j['input_id'] + retry_plan['diagnostic_id']).encode()).hexdigest()
    controls[402] = load_checked(j)
    changes = {k: v for k, v in asdict(candidate).items()
               if json.dumps(v) != json.dumps(asdict(anchor)[k])}
    if set(changes) != {'storm_asym', 'storm_width'}:
        raise ValueError('The fixed proposal must change only coastal storm asymmetry and storm width.')
    plan = dict(source=str(source), retry_source=str(retry_out), source_id=code,
                diagnostic_id=script_id(), candidate=asdict(candidate),
                changes_from_anchor=changes, development=list(DEVELOPMENT), validation=list(VALIDATION),
                warmup_steps=2 * candidate.steps_per_year, guards=night.GUARDS,
                control_inputs={str(s): d['input_id'] for s, d in controls.items()},
                control_temperature_caps={str(s): d['row']['params']['t_iters'] for s, d in controls.items()},
                note='One fixed proposal; validation surroundings were already examined. '
                     'Candidate finer-grid and 73-date checks are not included.')
    return plan, controls


def params_for(plan, seed):
    return night.Params(**plan['candidate']).replace(
        beyond_seed=seed, t_iters=plan['control_temperature_caps'][str(seed)])


def case_job(plan, out, name, seed, warmup=None, full=False, transport=False):
    j = night.job(name, params_for(plan, seed), plan['warmup_steps'] if warmup is None else warmup,
                  out, plan['source_id'], full=full, transport=transport)
    j['input_id'] = hashlib.sha256((j['input_id'] + plan['diagnostic_id']).encode()).hexdigest()
    return j


def ensure_sources(plan):
    if night.source_id() != plan['source_id'] or script_id() != plan['diagnostic_id']:
        raise ValueError('Source or inputs changed during the checks; refusing mixed results.')


def solve_case(j):
    saved = night.cached(j)
    if saved is not None:
        print(f'Reusing {j["name"]}.', flush=True)
        return load_checked(j) if saved['status'] == 'ok' else saved
    return night.worker(j)


def publish(spec, out):
    path = out / 'export_spec.json'
    for scale in (3, 1):
        spec['layer_scale'] = scale
        night.atomic_json(path, spec)
        with (out / 'atlas_export.log').open('a') as stream:
            done = night.subprocess.run([sys.executable, str(ROOT / 'scripts/overnight_mediterranean.py'),
                '--export-spec', str(path)], cwd=ROOT, stdout=stream, stderr=night.subprocess.STDOUT)
        if done.returncode == 0:
            return json.loads((out / 'atlas_publication.json').read_text())
    return dict(status='export_failed', reason='See atlas_export.log. Previous atlas retained.')


def run_checks(plan, controls, out):
    out = Path(out).resolve()
    for root in (Path(plan['source']), Path(plan['retry_source'])):
        if out == root or root in out.parents:
            raise ValueError('Choose a separate output directory to preserve earlier results.')
    ensure_sources(plan)
    manifest = out / 'experiment.json'
    if manifest.exists() and json.loads(manifest.read_text()) != plan:
        raise ValueError('Output contains a different experiment; choose a new --out directory.')
    state_path = out / 'comparison.json'
    if state_path.exists():
        if not manifest.exists():
            raise ValueError('Output comparison lacks experiment provenance; choose a new --out directory.')
        previous = json.loads(state_path.read_text())
        if previous.get('stage') == 'complete':
            print('These checks already completed. Read ' + str(out / 'summary.md'), flush=True)
            return previous
    (out / 'cases').mkdir(parents=True, exist_ok=True)
    night.atomic_json(manifest, plan)
    state = dict(stage='development', decision='pending', runs={}, checked_worlds={},
                 controls={str(s): d['row'] for s, d in controls.items()},
                 atlas={'status': 'unchanged'}, note=plan['note'])

    def save():
        night.atomic_json(state_path, state)
        lines = ['# Coastal storm balance checks', '', 'Stage: ' + state['stage'] + '.',
                 '', 'Decision: ' + state['decision'] + '.', '', plan['note'], '',
                 '| World | Anchor Med dry | Trial Med dry | Cold-dry anchor → trial | Hot-dry anchor → trial | Overall trial |',
                 '|---|---:|---:|---:|---:|---:|']
        for seed, d in state['checked_worlds'].items():
            if d['status'] != 'ok':
                continue
            a, b = controls[int(seed)]['row'], d['row']
            lines.append(f"| {seed} | {a['mediterranean']['dry_share']:.2%} | {b['mediterranean']['dry_share']:.2%} | "
                         f"{a['zone_recall']['cold_dry']:.2%} → {b['zone_recall']['cold_dry']:.2%} | "
                         f"{a['zone_recall']['hot_dry']:.2%} → {b['zone_recall']['hot_dry']:.2%} | {b['accuracy']:.2%} |")
        lines += ['', 'Atlas: ' + state['atlas']['status'] + '.']
        if 'reason' in state:
            lines += ['', state['reason']]
        if 'med_goal_met' in state:
            lines += ['', 'Mediterranean dry area <=5% on all five checked worlds: '
                      + ('met.' if state['med_goal_met'] else 'not met.')]
        (out / 'summary.md').write_text('\n'.join(lines) + '\n')

    def finish(decision, reason):
        state.update(stage='complete', decision=decision, reason=reason)
        save()
        print(reason, flush=True)
        return state

    def evaluate(name, seed, **options):
        ensure_sources(plan)
        j = case_job(plan, out, name, seed, **options)
        d = solve_case(j)
        ensure_sources(plan)
        state['runs'][name] = d
        save()
        if d['status'] == 'ok':
            r = d['row']
            print(f"{name}: Med dry {r['mediterranean']['dry_share']:.2%}, "
                  f"cold-dry {r['zone_recall']['cold_dry']:.2%}, "
                  f"hot-dry {r['zone_recall']['hot_dry']:.2%}, overall {r['accuracy']:.2%}", flush=True)
        return d

    def check_world(seed, phase):
        d = evaluate(f'{phase}_storm_balance_s{seed}', seed, full=seed == 1, transport=seed == 1)
        state['checked_worlds'][str(seed)] = d
        if d['status'] != 'ok':
            return finish('incomplete_numerics', f'World {seed} failed: {d["error"]}. Atlas retained.')
        failures = night.guard_failures(d['row'], controls[seed]['row'])
        if failures:
            return finish('rejected', f'World {seed}: ' + '; '.join(failures) + '. Atlas retained.')
        save()
        return None

    save()
    for seed in DEVELOPMENT:
        stopped = check_world(seed, 'train')
        if stopped is not None:
            return stopped
    trial_rows = [state['checked_worlds'][str(s)]['row'] for s in DEVELOPMENT]
    if night.rank(trial_rows) >= night.rank([controls[s]['row'] for s in DEVELOPMENT]):
        return finish('not_better', 'The complete development comparison does not improve the declared ranking. Atlas retained.')
    state['stage'] = 'warmup'
    warm = evaluate('storm_balance_warm1', 1, warmup=plan['warmup_steps'] // 2, transport=True)
    if warm['status'] != 'ok':
        return finish('incomplete_numerics', 'One-year warm-up run failed: ' + warm['error'] + '. Atlas retained.')
    state['warmup_check'] = night.stability(warm, state['checked_worlds']['1'])
    if not state['warmup_check']['passed']:
        return finish('unsettled', 'One versus two warm-up years exceed the declared continuous-field limits. Atlas retained.')
    state['stage'] = 'validation'
    save()
    for seed in VALIDATION:
        stopped = check_world(seed, 'validation')
        if stopped is not None:
            return stopped
    state['decision'] = 'qualified'
    state['med_goal_met'] = all(d['row']['mediterranean']['dry_share'] <= .05
                                  for d in state['checked_worlds'].values())
    state['stage'] = 'atlas'
    save()
    ensure_sources(plan)
    spec = dict(out=str(out), selected='storm_balance', params=asdict(params_for(plan, 1)),
                result=state['checked_worlds']['1']['result'], source_id=plan['source_id'],
                layer_scale=3, warmup_steps=plan['warmup_steps'], fresh_checks_complete=True,
                fine_checks={'status': 'not_run_for_candidate', 'used': False},
                followup={'diagnostic_id': plan['diagnostic_id'], 'checked_worlds': list(controls),
                          'note': plan['note']})
    state['atlas'] = publish(spec, out)
    if state['atlas']['status'] != 'published':
        state['stage'] = 'export_failed'  # Re-running reuses climate cases and retries only the export.
        save()
        return state
    return finish('qualified', 'All declared development, warm-up and validation checks passed; coarse-grid atlas published. '
                  'Candidate finer-grid and denser seasonal sampling remain untested.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=ROOT / 'output/overnight_mediterranean')
    ap.add_argument('--retry-source', type=Path, default=ROOT / 'output/overnight_validation_retry')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/storm_balance_checks')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args(argv)
    plan, controls = load_inputs(a.source, a.retry_source)
    print('Fixed proposal: ' + json.dumps(plan['changes_from_anchor']) + '.', flush=True)
    print('Reuse all five converged anchors. Check development worlds 301, 302, 1, '
          'one versus two warm-up years, then validation worlds 401 and 402.', flush=True)
    print('At most six sequential simulations. Two full warm-up years for every scored comparison; '
          'strict solves and unchanged per-world zone limits. Each pair has matching numerical settings.', flush=True)
    print('Stop on the first failed check. Publish the coarse-grid atlas only if all pass; '
          'candidate grid and denser seasonal-sampling checks are not included.', flush=True)
    print('Allow roughly 3–6 hours if all stages run; difficult retries can take longer. '
          'Exact matching cases resume.', flush=True)
    if not a.run:
        print('Plan only. Add --run to execute.', flush=True)
        return 0
    state = run_checks(plan, controls, a.out)
    print(f'Read {a.out / "summary.md"}', flush=True)
    return 1 if state['decision'] == 'incomplete_numerics' or state['stage'] == 'export_failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
