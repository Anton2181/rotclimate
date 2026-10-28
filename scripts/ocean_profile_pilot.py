"""Fixed paired ocean-target pilot in an explicitly advanced source epoch."""
from pathlib import Path
from multiprocessing import Pool
import argparse
import importlib.metadata
import json
import math
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, freeze, identity, write_json
from paired_physics_pilot import run_one
from tradeoff_search import evaluate, diverse_starts, pareto_names
from ocean_source_epoch import validate_epoch, current_sources, reference_sources


def run_ocean_one(job):
    """Retain failed evidence and materialize its immutable attempted parameters."""
    row=run_one(job)
    if row['status']!='passed':
        from dataclasses import asdict
        from rotclimate import earth,joint
        from earth_benchmark import load_params
        from benchmark_local import DEV12_SPECS
        name,region,updates,plan,token,out=job
        earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
        case=earth.region_case(region,float(plan['cell_km']))
        numerical=plan.get('profile_numerics',{}).get(name,{})
        theta=joint.update_block(load_params(ROOT/plan['physics']),'physics',updates)
        theta=joint.update_block(theta,'numerics',numerical)
        params=earth.earth_params(joint.earth_profile(theta),case)
        original=dict(row)
        row=dict(row,params=asdict(params),original_failed_record=original,
                 failed_parameter_materialization='Reconstructed from the same frozen case, declared updates and constructor; no model rerun')
        write_json(Path(out)/name/(region+'.json'),row)
    return row


def ocean_certificate_failures(row):
    if row['status'] != 'passed':
        return []  # Base evaluator records the numerical failure.
    p = row['params']; failures = []
    if not p['moisture_reservoirs']:
        return []
    steps=row['numerics']['moisture_reservoirs']['steps']
    expected=max(8,int(round(117./(p['year_days']/p['steps_per_year']))))+p['steps_per_year']
    if len(steps)!=expected:
        return ['Missing primer/scored ocean certificates']
    for step in steps:
        if not p['moisture_ocean_hydrostatic']:
            if p['moisture_ocean_rh_taper'] != 0 or 'ocean_target_scheme' in step:
                failures.append('Legacy ocean mode/taper certificate changed')
            continue
        if (step.get('ocean_target_scheme') != 'hydrostatic-rh'
                or step.get('ocean_rh_taper') != p['moisture_ocean_rh_taper']
                or step.get('ocean_target_thermal_profile') != 'environmental'
                or step.get('ocean_target_lapse_k_km') != 6.):
            failures.append('Missing/changed actual hydrostatic ocean mode')
        cells = step.get('ocean_target_cells')
        if not isinstance(cells, int) or cells < 0:
            failures.append('Invalid actual ocean-target cell count'); continue
        keys = ['minimum_ocean_surface_rh', 'maximum_ocean_surface_rh',
                'minimum_ocean_target_water_mm', 'maximum_ocean_target_water_mm']
        if cells:
            if any(not isinstance(step.get(k), (int, float)) or not math.isfinite(step[k]) or step[k] <= 0 for k in keys):
                failures.append('Invalid ocean humidity/water target'); continue
            if not 0 < step[keys[0]] <= step[keys[1]] <= 1 or step[keys[2]] > step[keys[3]]:
                failures.append('Ocean target bounds failed')
            if p['ocean_rh_warm'] == 0 and (step[keys[0]] != p['ocean_rh'] or step[keys[1]] != p['ocean_rh']):
                failures.append('Actual ocean surface RH differs from declared scalar')
        elif any(step.get(k) is not None for k in keys):
            failures.append('Nonempty ocean target on a sea-free grid')
    return sorted(set(failures))


def evaluate_ocean(name, records, plan):
    score = evaluate(name, records, plan)
    failures = [r['region'] + ': ' + f for r in records if r['name'] == name for f in ocean_certificate_failures(r)]
    if failures:
        return dict(physical_admissible=False, failures=score.get('failures', []) + failures)
    return score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); path = args.plan.resolve(); out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Preserve previous output; use a fresh pilot directory')
    out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(path.read_text()); start = time.monotonic(); phase = 'freeze'; records = []; scores = {}; history = []
    try:
        declaration=str(path.relative_to(ROOT))
        if subprocess.check_output(['git','show','HEAD:'+declaration],cwd=ROOT)!=path.read_bytes():
            raise ValueError('Commit the literal ocean declaration before any integration')
        if plan['design']['sampler'] != 'paired hydrostatic ocean pilot' or plan['design']['local_poll_order']:
            raise ValueError('Expected fixed paired ocean experiment, no local proposals')
        validate_epoch(plan['source_epoch'])
        parent = ROOT / plan['parent_protocol']; old = json.loads(parent.read_text())
        sources = current_sources(old['sources'], plan['source_epoch'])
        added, reference_refresh = reference_sources(plan); sources.update(added)
        for source in [path, Path(__file__), ROOT / 'scripts/ocean_source_epoch.py', ROOT / 'scripts/tradeoff_search.py', parent]:
            sources[str(source.relative_to(ROOT))] = file_hash(source)
        for archive in plan['profile_control_archives'].values():
            for region in plan['regions']:
                for suffix in ['.json', '.npz']:
                    source = ROOT / archive / (region + suffix)
                    sources[str(source.relative_to(ROOT))] = file_hash(source)
                if region in plan['extra_circulation_regions']:
                    source = ROOT / archive / (region + '_extra.npz')
                    sources[str(source.relative_to(ROOT))] = file_hash(source)
        token = freeze(out / 'protocol.json', dict(plan=plan, sources=sources, source_transition=plan['source_epoch'],
                       reference_refresh=reference_refresh, packages={n: importlib.metadata.version(n) for n in ['numpy', 'scipy', 'numba']}))

        def check_sources():
            if time.monotonic() - start > plan['maximum_seconds']:
                raise TimeoutError('Frozen ocean pilot deadline exceeded')
            for name, sha in sources.items():
                if file_hash(ROOT / name) != sha:
                    raise ValueError('Frozen source/input changed: ' + name)

        def save(complete=False):
            write_json(out / 'progress.json', dict(complete=complete, identity=token, records=records, scores=scores,
                       history=history, seconds=time.monotonic() - start, actual_integrations=len(records), physics_or_atlas_adoption=False))

        with Pool(2) as pool:
            for name in [*plan['control_names'], *plan['global_names']]:
                phase = 'controls' if name in plan['control_names'] else 'global'; check_sources()
                rows = pool.map(run_ocean_one, [(name, r, plan['profiles'][name], plan, token, str(out)) for r in plan['regions']])
                records.extend(rows)
                if name in plan['control_names']:
                    if any(r['status'] != 'passed' for r in rows):
                        raise ValueError('Historical exact control failed')
                else:
                    if name=='global01' and any(r['status']!='passed' for r in rows):
                        raise ValueError('Matched legacy source-epoch control failed')
                    scores[name] = evaluate_ocean(name, records, plan)
                history.append(dict(name=name, stage=phase, updates=plan['profiles'][name], score=scores.get(name)))
                check_sources(); save(); print('PROFILE ' + name + ' ' + json.dumps(scores.get(name, {'control': 'exact'})), flush=True)
        starts = diverse_starts(scores, plan['profiles'], plan['design'])
        write_json(out / 'local_starts.json', dict(identity=token, starts=starts, selection_rule=plan['design']))
        check_sources(); save(True)
        shortlist = sorted((n for n, s in scores.items() if s.get('validation_ready')), key=lambda n: (scores[n]['objective'], n))[:2]
        write_json(out / 'review.json', dict(complete=True, identity=token, scores=scores,
                   physical_admissible=sum(s.get('physical_admissible', False) for s in scores.values()),
                   pareto_front=pareto_names(scores), validation_shortlist=shortlist, local_starts=starts,
                   actual_integrations=len(records), strictly_passed=sum(r['status'] == 'passed' for r in records),
                   failed_integrations=sum(r['status'] != 'passed' for r in records), seconds=time.monotonic() - start,
                   physics_or_atlas_adoption=False, scope='Fixed source-advanced ocean pilot; no local refinement or automatic adoption'))
    except BaseException as error:
        if 'save' in locals():
            save(False)
        write_json(out / 'failure.json', dict(phase=phase, error=repr(error), actual_integrations=len(records),
                   seconds=time.monotonic() - start, physics_or_atlas_adoption=False))
        raise


if __name__ == '__main__':
    main()
