"""Declare a paired legacy-drying ablation only after a failed wind shortlist.

Existing independent donor exchange already transports humidity vertically.
Removing an empirical column sink tests possible overlap; it does not presume
that the sink is redundant or that removal improves rainfall.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, identity, write_json
from tradeoff_search import diverse_starts

VARIANTS = {
    'subsidence_off': {'subsidence_drying': 0.},
    'monsoon_off': {'monsoon_descent': 0.},
    'both_off': {'subsidence_drying': 0., 'monsoon_descent': 0.},
}


def prepare(parent, target):
    protocol = json.loads((parent / 'protocol.json').read_text())
    review = json.loads((parent / 'review.json').read_text())
    progress = json.loads((parent / 'progress.json').read_text())
    verification = json.loads((parent / 'scientific_verification.json').read_text())
    if (not review['complete'] or not progress['complete'] or review['identity'] != identity(protocol)
            or verification['status'] != 'passed'
            or verification['review_sha256'] != file_hash(parent / 'review.json')):
        raise ValueError('Need completed, independently verified parent')
    if review['validation_shortlist']:
        raise ValueError('Broader validation takes priority over another mechanism test')
    parent_relative = str(parent.relative_to(ROOT))
    parent_commit = subprocess.check_output(
        ['git', 'log', '-1', '--format=%H', '--', parent_relative + '/review.json'], cwd=ROOT, text=True).strip()
    if not parent_commit:
        raise ValueError('Commit parent results before declaring this follow-up')
    p = json.loads(json.dumps(protocol['plan']))
    updates = {r['name']: r['updates'] for r in progress['records']}
    selection = dict(p['design'], local_starts=2, start_minimum_distance=.35)
    anchors = diverse_starts(review['scores'], updates, selection)
    if not anchors:
        raise ValueError('No admissible parent anchor')
    retained = {}
    for key in ['subsidence_drying', 'monsoon_descent']:
        values = {r['params'][key] for r in progress['records'] if r['name'] in anchors}
        if len(values) != 1 or not next(iter(values)) > 0:
            raise ValueError('Need one positive shared retained drying coefficient')
        retained[key] = next(iter(values))
    p['profiles'] = {n: p['profiles'][n] for n in p['control_names']}
    p['profile_numerics'] = {n: p['profile_numerics'][n] for n in p['control_names']}
    p['profile_control_archives'] = {n: parent_relative + '/' + n for n in p['control_names']}
    p['design']['bounds'].update({k: dict(range=[0., v], scale='linear') for k, v in retained.items()})
    p['design'].update(sampler='paired drying ablation', local_starts=1, local_poll_order=[],
                       local_rule='No local proposals; fixed paired ablation only.')
    p['global_names'] = []
    grid = []
    for basin, anchor in enumerate(anchors):
        p['profile_control_archives']['source_anchor' + str(basin + 1)] = parent_relative + '/' + anchor
        for variant, changes in VARIANTS.items():
            name = f'global{len(grid) + 1:02}'
            p['profiles'][name] = {**updates[anchor], **retained, **changes}
            p['profile_numerics'][name] = p['candidate_numerics']
            p['global_names'].append(name)
            grid.append(dict(name=name, basin=basin + 1, parent_profile=anchor, variant=variant, changes=changes))
    p.pop('wind_interaction', None)
    p['eligible_profiles'] = p['global_names']
    p['parent_protocol'] = parent_relative + '/protocol.json'
    p['parent'] = parent_relative + '/review.json'
    p['parent_source_commit'] = parent_commit
    p['purpose'] = ('Test whether retained empirical subsidence/monsoon column sinks overlap explicit donor '
                    'vertical transport. Separately switch off each closure and both at two separated parent '
                    'settings. This is an ablation, not a presumed correction or calibration gain.')
    p['policy_version'] = 'tradeoff_research_v1_drying_ablation_20261028'
    p['control'] = 'Four exact profiles on seven regions precede all fixed paired ablations; all archived main fields and native companions must reproduce exactly.'
    p['physical_definition'] = ('Allow only the parent four shared rain/wind coefficients and the two declared drying '
                                'coefficients to differ from the environmental control. Keep all other actual parameters '
                                'and all planetary properties fixed. Do not reset humidity or alter conservative donor transport.')
    p['advance'] = 'No local refinement or adaptive extension. Same shortlist and prospective broader validation requirements as parent; no automatic adoption.'
    p['publication'] = 'Retain each ablation, numerical failures, native errors, regional damage and archived parent anchors. Parent comparisons are not new integrations.'
    p['publication_stem'] = 'drying_ablation'
    p['publication_title'] = 'Legacy drying and explicit vertical transport'
    p['planned_maximum_integrations'] = (4 + len(grid)) * len(p['regions'])
    p['drying_ablation'] = dict(
        parent=parent_relative, parent_identity=review['identity'],
        parent_review_sha256=file_hash(parent / 'review.json'),
        parent_progress_sha256=file_hash(parent / 'progress.json'),
        parent_verification_sha256=file_hash(parent / 'scientific_verification.json'),
        anchor_selection=selection, anchors=anchors, retained=retained, variants=VARIANTS, grid=grid,
        scope='Paired closure ablation on reused regions; neither a global optimization nor independent validation.')
    p['generator_sha256'] = file_hash(Path(__file__))
    if target.exists():
        raise ValueError('Preserve previous declaration; choose a fresh plan')
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json(target, p)
    print(json.dumps(dict(plan=str(target), anchors=anchors, candidate_profiles=len(grid),
                          maximum_integrations=p['planned_maximum_integrations']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.parent.resolve(), args.plan.resolve())
