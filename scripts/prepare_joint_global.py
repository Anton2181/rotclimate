"""Prepare fresh six-dimensional coverage after completed paired ablations.

The original search boxes and failed decisions remain intact. Wind amplitude
is extended downwards in a new declaration, with actual native errors still
reported. Earth properties and all other physical coefficients stay fixed.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from scipy.stats import qmc
from local_benchmark_protocol import file_hash, identity, write_json
from tradeoff_search import parameters


def prepare(parent, target):
    protocol = json.loads((parent / 'protocol.json').read_text())
    review = json.loads((parent / 'review.json').read_text())
    progress = json.loads((parent / 'progress.json').read_text())
    verification = json.loads((parent / 'scientific_verification.json').read_text())
    if (not review['complete'] or not progress['complete'] or review['identity'] != identity(protocol)
            or verification['status'] != 'passed' or verification['identity'] != review['identity']
            or verification['protocol_sha256'] != file_hash(parent / 'protocol.json')
            or verification['review_sha256'] != file_hash(parent / 'review.json')):
        raise ValueError('Need complete independently verified parent')
    if review['validation_shortlist']:
        raise ValueError('Broader validation takes priority over another calibration search')
    parent_relative = str(parent.relative_to(ROOT))
    for filename in ['protocol.json', 'review.json', 'progress.json', 'scientific_verification.json']:
        committed = subprocess.check_output(['git', 'show', 'HEAD:' + parent_relative + '/' + filename], cwd=ROOT)
        if committed != (parent / filename).read_bytes():
            raise ValueError('Commit current parent archive first: ' + filename)
    p = json.loads(json.dumps(protocol['plan']))
    if p['design']['sampler'] != 'paired drying ablation':
        raise ValueError('Expected completed drying ablation')
    p.pop('drying_ablation')
    p['profiles'] = {n: p['profiles'][n] for n in p['control_names']}
    p['profile_numerics'] = {n: p['profile_numerics'][n] for n in p['control_names']}
    p['profile_control_archives'] = {n: parent_relative + '/' + n for n in p['control_names']}
    p['design']['bounds']['westerly_speed']['range'] = [2.5, 8.5]
    if len(p['design']['bounds']) != 6:
        raise ValueError('Expected exactly the six declared parent axes')
    p['design'].update(sampler='scrambled Sobol', seed=2026102803, base2_exponent=5,
                       local_starts=1, local_poll_order=[],
                       local_rule='No local proposals in this joint coverage experiment; best-point bookkeeping only.')
    p['global_names'] = []
    for point in qmc.Sobol(6, scramble=True, seed=p['design']['seed']).random_base2(5):
        name = f'global{len(p["global_names"]) + 1:02}'
        p['profiles'][name] = {**p['base_candidate'], **parameters(point, p['design'])}
        p['profile_numerics'][name] = p['candidate_numerics']
        p['global_names'].append(name)
    p['eligible_profiles'] = p['global_names']
    p['parent_protocol'] = parent_relative + '/protocol.json'
    p['parent'] = parent_relative + '/review.json'
    p['parent_source_commit'] = subprocess.check_output(
        ['git', 'log', '-1', '--format=%H', '--', parent_relative + '/review.json'], cwd=ROOT, text=True).strip()
    p['policy_version'] = 'tradeoff_research_v1_joint_global_20261028'
    p['purpose'] = ('Sample joint interactions instead of optimizing wind or legacy column sinks only at '
                    'fixed rain settings. Prior best winds lie at the lower sampled boundary; introduce '
                    'a separately declared 2.5–8.5m/s range while retaining native circulation errors. '
                    'Sample legacy sink strengths continuously from zero to their retained values, '
                    'without claiming that removal is a physical correction.')
    p['physical_definition'] = ('Free only the six declared shared coefficients. Preserve independent water, '
                                'conservative horizontal/donor vertical transport, corrected rain/recycling, '
                                'environmental6K/km, all other actual parameters, geometry and Earth properties. '
                                'Parameter ranges are sensitivity bounds, not physical confidence intervals.')
    p['control'] = 'Four exact profiles on seven regions precede all 32 Sobol profiles; reproduce all archived main fields and native companions.'
    p['advance'] = 'Same research shortlist; no local refinement, adaptive extension or adoption. Any finalist needs separately declared broader validation.'
    p['publication'] = 'Every fixed six-dimensional point, failure, source/input identity and prediction tradeoff. New finite coverage is not a global-optimum certificate.'
    p['publication_stem'] = 'global_joint'
    p['publication_title'] = 'Joint global wind, rain and drying search'
    p['publication_design_text'] = ('Thirty-two fixed scrambled Sobol points jointly cover storm exchange, '
                                  'rain timescale, convective RH, background wind amplitude and both legacy '
                                  'drying coefficients. Wind is separately extended to 2.5–8.5 m/s; drying '
                                  'ranges from zero to its retained strength. All remaining actual parameters '
                                  'and planetary properties stay fixed. No local proposals follow.')
    p['previous_study_slug'] = 'drying-ablation'
    p['planned_maximum_integrations'] = 252
    p['joint_global_parent'] = dict(
        parent=parent_relative, parent_identity=review['identity'],
        parent_review_sha256=file_hash(parent / 'review.json'),
        parent_progress_sha256=file_hash(parent / 'progress.json'),
        parent_verification_sha256=file_hash(parent / 'scientific_verification.json'),
        scope='No parent candidate ready for broader validation; old outcomes and declarations remain unchanged.')
    p['generator_sha256'] = file_hash(Path(__file__))
    if target.exists():
        raise ValueError('Preserve previous declaration; choose a fresh plan')
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json(target, p)
    print(json.dumps(dict(plan=str(target), candidate_profiles=32, maximum_integrations=252), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.parent.resolve(), args.plan.resolve())
