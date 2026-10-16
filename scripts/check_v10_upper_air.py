"""Two matched upper-air-target cases, with completed baselines reused.

Default prints the plan. --run performs at most two regional cases, no search,
downloads or atlas update. Resume with the same command and unchanged sources.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_upper_air as experiment, v10_time
from experiments import v10_forcing_audit as atmosphere
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256
from scripts import overnight_v10 as night, review_v10_overnight as review


def source_id():
    digest = hashlib.sha256(night.code_id().encode())
    for path in (Path(__file__), Path(experiment.__file__), Path(v10_time.__file__), Path(review.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare(source):
    manifest = json.loads((source/'manifest.json').read_text())
    state = json.loads((source/'state.json').read_text())
    if state['status'] != 'complete' or manifest['code_sha256'] != night.code_id():
        raise ValueError('Need unchanged completed overnight evidence.')
    audit_path = ROOT/'output/v10_forcing_audit/manifest.json'
    if sha256(audit_path) != manifest['audit_manifest_sha256']:
        raise ValueError('Atmospheric audit changed.')
    texts, downloads = atmosphere.acquire(ROOT/'data/v10_atmosphere', False)
    if downloads != json.loads(audit_path.read_text())['reference_downloads']:
        raise ValueError('Cached atmospheric references changed.')
    fields = atmosphere.fields_from_cache(texts)
    cases = {}
    profiles = {}
    references = {}
    baselines = {}
    fingerprints = {}
    for region in ('california', 'iberia'):
        key = f'c120_{region}_g60_s41'
        baseline = state['cases'][key]
        folder = source/'cases'/key
        config = json.loads((folder/'config.json').read_text())
        if config['settings'] != manifest['settings'][120] or config['seed'] != 41 or config['region'] != region:
            raise ValueError('Matched baseline configuration changed.')
        for name, digest in baseline['evidence_sha256'].items():
            if Path(name).name != name or sha256(folder/name) != digest:
                raise ValueError('Matched baseline evidence changed.')
        case = review.prepared_case(source, manifest, region, 60)
        if config['spacing_m'] != case.domain.dx:
            raise ValueError('Baseline spacing mismatch.')
        local, height = review.pressure_reference(case, fields)
        if (height[:, 2:] < case.domain.elevation_m).any():
            raise ValueError('Upper-air reference intersects model ground.')
        cases[region] = case
        profiles[region] = review.profile_from_json(manifest['profiles'][region])
        references[region] = local
        baselines[region] = baseline
        fingerprints[region] = {'key': key, 'evidence_sha256': baseline['evidence_sha256'],
            'input_sha256': manifest['base_inputs_sha256'][region],
            'local_air_sha256': hashlib.sha256(local.astype('<f8').tobytes()).hexdigest()}
    protocol = {'schema': 1, 'code_sha256': source_id(),
        'overnight_manifest_sha256': sha256(source/'manifest.json'),
        'reference_downloads': downloads, 'settings': manifest['settings'][120],
        'profiles': manifest['profiles'], 'baseline_fingerprints': fingerprints,
        'change': 'Only upper two temperature targets and consequent boundary saturation caps use spatial pressure-level air.',
        'grid_km': 60, 'weather_seed': 41, 'minimum_cycles': 3, 'maximum_cycles': 6,
        'initial_state': 'Same frozen legacy-target initialization as matched baselines; repeat until settled.',
        'time_fix': 'Allow positive CFL-safe fragments at forcing/month boundaries; discard no time.',
        'temperature': 'Still observation-informed forcing; no independent temperature forecast.',
        'atlas_publication': False}
    return protocol, cases, profiles, references, baselines


def report(out, state, baselines):
    lines = ['# Upper-air target check', '', f"Status: {state['status']}. Two fixed regional cases; no calibration or atlas update.", '',
        '| Region | Baseline rain MAE | New rain MAE | Rain / reference | Coverage | Settled |',
        '|---|---:|---:|---:|---:|---|']
    for region, row in state['cases'].items():
        lines.append(f"| {region} | {baselines[region]['score']:.2f} | {row['score']:.2f} | {row['annual_rain_ratio']:.2f} | {row['wet_reference_coverage']:.1%} | {row['settling']['passed']} |")
    lines += ['', 'Upper two relaxation targets use cached spatial pressure-level air. '
        'Geometry, lower targets, mean winds, humidity multiplier and storm catalogue are unchanged. '
        'Boundary humidity caps respond consistently to the changed upper temperature.', '',
        'Final-year metadata contains monthly layer rain and signed horizontal/vertical thermal '
        'transport, relaxation, evaporation and condensation changes over scored land. '
        'These are large potentially cancelling contributions, not net heating or independent causes.', '',
        'The old overnight acceptance results are preserved. New-case eligibility is a provisional '
        'screen under its declared new targets, not permission to update an atlas.']
    if state.get('error'):
        lines += ['', 'Stopped: '+state['error']]
    atomic_json(out/'state.json', state)
    (out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out, source, hours=1.):
    protocol, cases, profiles, references, baselines = prepare(source)
    out.mkdir(parents=True, exist_ok=True)
    path = out/'manifest.json'
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError('Experiment source/input changed; preserve output and choose a new --out.')
    if not path.exists():
        atomic_json(path, protocol)
    state_path = out/'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'cases': {}}
    state['status'] = 'running'
    interrupted = [False]
    old_handler = signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))
    deadline = time.monotonic()+hours*3600
    def stop():
        return interrupted[0] or time.monotonic() >= deadline
    def log(message):
        print(message, flush=True)
        with (out/'run.log').open('a') as file:
            file.write(night.utc()+' '+message+'\n')
    try:
        report(out, state, baselines)
        settings = night.model.Settings(**protocol['settings'])
        for region, case in cases.items():
            if source_id() != protocol['code_sha256']:
                raise ValueError('Source changed during the experiment.')
            job = f'upper_air_{region}_g60_s41'
            if region in state['cases']:
                for name, digest in state['cases'][region]['evidence_sha256'].items():
                    if Path(name).name != name or sha256(out/'cases'/job/name) != digest:
                        raise ValueError('Completed experiment evidence changed.')
                continue
            local = references[region]
            def integrate(domain, profile, config, seed, initial, **kwargs):
                return experiment.year(domain, profile, config, seed, initial, local,
                    case.score_mask, **kwargs)
            log(f'{region}: start fixed upper-air target check, three to six repeated years.')
            row = night.run_case(job, case, profiles[region], settings, out, stop, log,
                integrator=integrate, max_years=6)
            state['cases'][region] = row
            report(out, state, baselines)
            if not row['settling']['passed']:
                raise RuntimeError('Six cycles did not settle; inspect before continuing.')
        state['status'] = 'complete'
    except night.model.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError, RuntimeError, FloatingPointError, OSError) as error:
        state['status'] = 'needs_diagnosis'
        state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT, old_handler)
        report(out, state, baselines)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_overnight_20261015')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_upper_air_check')
    args = parser.parse_args(argv)
    print('Two new 60 km cases: California and Iberia, fixed setting 120 and weather seed 41. Baselines reused.', flush=True)
    print('Three to six repeated years each; recent comparable runs suggest about 10–20 minutes total, with a one-hour cap.', flush=True)
    print('Monthly checkpoints; rerun to resume. No downloads, search or atlas publication.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_upper_air.py --run')
        return 0
    result = run(args.out, args.source)
    print('Status: '+result['status'], flush=True)
    return 0 if result['status'] in ('complete', 'interrupted', 'budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
