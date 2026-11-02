import json
from copy import deepcopy
from pathlib import Path
import subprocess

import pytest

from scripts import validate_r42_multistart as validation


def row(t, p, case='same'):
    return dict(status='passed', numerics={'all_checks_passed': True},
                case_identity=case, cells=3, temperature={'monthly_mae_C': t}, rain={'loss': p})


def test_aggregate_gain_allows_regional_regressions_but_not_unpaired_or_invalid_results():
    reference = {'a': row(1., 1.), 'b': row(1., 1.)}
    candidate = {'a': row(.5, .5), 'b': row(1.1, 1.1)}
    score = validation.paired_score(reference, candidate, ['a', 'b'])
    assert score['S'] == pytest.approx(.8)
    candidate['b']['case_identity'] = 'different observations'
    with pytest.raises(ValueError, match='observations differ'):
        validation.paired_score(reference, candidate, ['a', 'b'])
    candidate['b'] = row(1.1, float('nan'))
    with pytest.raises(ValueError, match='Invalid climate errors'):
        validation.paired_score(reference, candidate, ['a', 'b'])
    candidate['b'] = row(.1, .1); candidate['b']['numerics']['all_checks_passed'] = False
    with pytest.raises(ValueError, match='Unverified'):
        validation.paired_score(reference, candidate, ['a', 'b'])
    with pytest.raises(ValueError, match='every declared region'):
        validation.paired_score(reference, {'a': row(.1, .1)}, ['a', 'b'])


def test_reproduction_checks_individual_errors_not_just_a_matching_average():
    rows = {'a': row(1., 1.), 'b': row(2., 2.)}
    validation.reproduce(rows, {'a': [1., 1.], 'b': [2., 2.]})
    with pytest.raises(ValueError, match='does not reproduce'):
        validation.reproduce(rows, {'a': [2., 2.], 'b': [1., 1.]})


def test_selection_requires_complete_nonduplicated_records_from_every_start(tmp_path):
    plans = []
    for chain in range(1, 4):
        plan = tmp_path / f'plan{chain}.json'; plan.write_text('{"evals":2}')
        plans.append(plan.name)
        folder = tmp_path / 'search' / f'chain_{chain}'; folder.mkdir(parents=True)
        (folder / 'evals.jsonl').write_text('{"n":0}\n{"n":1}\n')
    campaign = dict(plans=plans, output='search')
    assert len(validation.records_for_selection(tmp_path, campaign)) == 6
    (folder / 'evals.jsonl').write_text('{"n":0}\n{"n":0}\n')
    with pytest.raises(ValueError, match='All declared starts'):
        validation.records_for_selection(tmp_path, campaign)


def test_publication_preserves_unrelated_staged_work_and_can_resume_unchanged_results(tmp_path):
    root = tmp_path / 'repo'; root.mkdir()
    remote = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', '-q', str(remote)], check=True)
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True)
    git('init', '-q'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.org')
    (root / 'user.txt').write_text('old'); git('add', '.'); git('commit', '-qm', 'base')
    git('remote', 'add', 'origin', str(remote))
    (root / 'user.txt').write_text('new'); git('add', 'user.txt')
    folder = root / validation.PREFIX; folder.mkdir(parents=True)
    (folder / 'result.json').write_text('{}')
    plan = dict(remote='origin', push_ref='refs/heads/test')
    commit = validation.publish(root, folder, 'own results', plan)
    assert git('show', 'HEAD:user.txt') == 'old'
    assert git('diff', '--cached', '--name-only').strip() == 'user.txt'
    assert validation.publish(root, folder, 'same results', plan) == commit
    with pytest.raises(ValueError, match='unrelated'):
        validation.publish(root, root, 'unsafe', plan)
