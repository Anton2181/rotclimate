"""Declare two winds by three ocean-target laws after the joint search."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json, identity
from ocean_source_epoch import validate_epoch, reference_sources


def committed(folder):
    for filename in ['protocol.json', 'progress.json', 'review.json', 'scientific_verification.json']:
        path = folder / filename
        payload = subprocess.check_output(['git', 'show', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT)
        if payload != path.read_bytes():
            raise ValueError('Commit parent results first: ' + str(path))


def prepare(parent, target):
    committed(parent)
    protocol = json.loads((parent / 'protocol.json').read_text())
    review = json.loads((parent / 'review.json').read_text())
    receipt = json.loads((parent / 'scientific_verification.json').read_text())
    if (not review['complete'] or review['validation_shortlist'] or receipt['status'] != 'passed'
            or review['identity'] != identity(protocol) or receipt['review_sha256'] != file_hash(parent / 'review.json')):
        raise ValueError('Need completed verified parent without a broader-validation shortlist')
    p = json.loads(json.dumps(protocol['plan']))
    anchor_parent = ROOT / 'output/wind_interaction_20261028'; committed(anchor_parent)
    old_review = json.loads((anchor_parent / 'review.json').read_text())
    anchor = min((n for n, s in old_review['scores'].items() if s.get('physical_admissible')),
                 key=lambda n: (old_review['scores'][n]['objective'], n))
    archive = anchor_parent / anchor
    source = json.loads((archive / (p['regions'][0] + '.json')).read_text())
    if source['numerical_updates'] != p['candidate_numerics']:
        raise ValueError('Retain matched anchor numerical rules')
    snapshot = json.loads((ROOT / 'output/ocean_physics_development/before.json').read_text())
    after_commit = subprocess.check_output(['git', 'rev-parse', '76adf7e'], cwd=ROOT, text=True).strip()
    epoch = dict(before_commit=snapshot['source_epoch'], after_commit=after_commit,
                 files={n: dict(before_sha256=v, after_sha256=file_hash(ROOT / n)) for n, v in snapshot['core_sources'].items()})
    validate_epoch(epoch)
    refs = {}
    for kind, directory in [('thermal', 'output/environmental_reference_20261027_verified'), ('marine_rh', 'output/boundary_rh_20261028')]:
        folder = ROOT / directory
        refs[kind] = dict(directory=directory, protocol_sha256=file_hash(folder / 'protocol.json'),
                          review_sha256=file_hash(folder / 'review.json'), arrays_sha256=file_hash(folder / 'native_profiles.npz'))
    p.pop('joint_global_parent', None)
    p['profiles'] = {n: p['profiles'][n] for n in p['control_names']}
    p['profile_numerics'] = {n: p['profile_numerics'][n] for n in p['control_names']}
    p['profile_control_archives'] = {n: str((parent / n).relative_to(ROOT)) for n in p['control_names']}
    p['profile_control_archives']['global01'] = str(archive.relative_to(ROOT))
    p['base_candidate'].update(moisture_ocean_hydrostatic=False, moisture_ocean_rh_taper=0.)
    p['design']['bounds'].update(moisture_ocean_hydrostatic=dict(range=[0, 1], scale='linear'),
                                  moisture_ocean_rh_taper=dict(range=[0., .5], scale='linear'))
    p['design'].update(sampler='paired hydrostatic ocean pilot', local_starts=1, local_poll_order=[],
                       local_rule='Fixed paired grid only; best-start bookkeeping, no local proposals.')
    grid = []; p['global_names'] = []
    for wind in [4.5, 3.5]:
        for mode, enabled, taper in [('legacy', False, 0.), ('hydrostatic_uniform', True, 0.), ('hydrostatic_half', True, .5)]:
            name = f'global{len(grid) + 1:02}'
            p['profiles'][name] = {**source['updates'], **{k: source['params'][k] for k in ['subsidence_drying', 'monsoon_descent']},
                                   'westerly_speed': wind, 'moisture_ocean_hydrostatic': enabled, 'moisture_ocean_rh_taper': taper}
            p['profile_numerics'][name] = p['candidate_numerics']; p['global_names'].append(name)
            grid.append(dict(name=name, westerly_speed=wind, mode=mode, hydrostatic=enabled, rh_taper=taper))
    relative = str(parent.relative_to(ROOT))
    p['source_epoch'] = epoch
    p['parent_protocol'] = relative + '/protocol.json'; p['parent'] = relative + '/review.json'
    p['parent_source_commit'] = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', relative + '/review.json'], cwd=ROOT, text=True).strip()
    p['ocean_profile_pilot'] = dict(parent=relative, parent_identity=review['identity'],
        parent_review_sha256=file_hash(parent / 'review.json'), parent_progress_sha256=file_hash(parent / 'progress.json'),
        parent_verification_sha256=file_hash(parent / 'scientific_verification.json'),
        anchor_profile=anchor, anchor_archive=str(archive.relative_to(ROOT)), anchor_review=str((anchor_parent / 'review.json').relative_to(ROOT)),
        anchor_review_sha256=file_hash(anchor_parent / 'review.json'), references=refs, grid=grid,
        scope='Legacy versus absolute hydrostatic uniform/half RH targets, at two fixed winds. Reference support is not a coupled climate gain.')
    reference_sources(p)
    p['eligible_profiles'] = p['global_names']; p['planned_maximum_integrations'] = 70
    p['purpose'] = 'Test a physical ocean-water boundary law after finite joint calibration failed to beat the retained wind setting. Separate the absolute hydrostatic uniform target from a half-strength pressure RH taper; both hold the existing declared surface RH. No observed humidity or temperature enters model forcing.'
    p['physical_definition'] = 'Only the eight declared shared axes may differ from the fresh environmental control; literal grid further fixes all but wind and the new ocean modes at the retained rain setting. Four core source replacements are explicitly committed; every other source/input is unchanged. Actual interior water stays independently solved; all planetary properties and numerical/skill requirements are fixed.'
    p['policy_version'] = 'tradeoff_research_v1_hydrostatic_ocean_20261028'
    p['control'] = 'Four exact controls precede six fixed candidate settings. The fresh legacy4.5 candidate must additionally reproduce the retained old wind setting, including every main NPZ field and native companion.'
    p['advance'] = 'Same research shortlist and separately frozen broader Earth/ocean/resolution/world requirements; no local proposals or automatic adoption.'
    p['publication_stem'] = 'ocean_profile'; p['publication_title'] = 'Hydrostatic ocean humidity and rainfall'
    p['previous_study_slug'] = 'global-joint'
    p['publication_design_text'] = 'Two fixed background winds (4.5 and 3.5 m/s) each receive legacy, absolute hydrostatic uniform-RH, and half-taper RH ocean targets. Surface RH retains its calibrated value; total water is not renormalized. Actual sea temperatures drive the profiles and interior humidity remains independently solved. Four exact controls and a matched legacy epoch control protect existing behavior. No local proposals follow.'
    p['generator_sha256'] = file_hash(Path(__file__))
    if target.exists():
        raise ValueError('Preserve previous declaration; choose a fresh plan')
    target.parent.mkdir(parents=True, exist_ok=True); write_json(target, p)
    print(json.dumps(dict(plan=str(target), candidate_profiles=6, maximum_integrations=70,
                          anchor=anchor, ocean_surface_rh=source['params']['ocean_rh']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--parent', type=Path, required=True); parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args(); prepare(args.parent.resolve(), args.plan.resolve())
