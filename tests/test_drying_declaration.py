"""Selection provenance must survive addition of new experiment axes."""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from scripts import prepare_drying_ablation as declaration
from scripts.local_benchmark_protocol import identity, file_hash, write_json


@pytest.fixture
def parent(tmp_path, monkeypatch):
    monkeypatch.setattr(declaration, 'ROOT', tmp_path)
    folder = tmp_path / 'parent'
    folder.mkdir()
    keys = ['eddy_rate', 'precip_tau_days', 'convective_rh', 'westerly_speed']
    design = dict(bounds={k: dict(range=[0., 1.], scale='linear') for k in keys},
                  sampler='paired wind bracket', local_starts=1,
                  start_minimum_distance=.35, local_poll_order=[])
    controls = ['reference', 'transport_control', 'column_control', 'environment_control']
    plan = dict(design=design, control_names=controls, regions=['r'],
                profiles={n: {} for n in controls}, profile_numerics={n: {} for n in controls},
                candidate_numerics={})
    protocol = dict(plan=plan, sources={})
    token = identity(protocol)
    scores = {n: dict(physical_admissible=True, objective=i + 1.) for i, n in enumerate(['a', 'b'])}
    records = [dict(name=n, updates={k: x for k in keys},
                    params=dict(subsidence_drying=.02, monsoon_descent=.015)) for n, x in [('a', .1), ('b', .9)]]
    write_json(folder / 'protocol.json', protocol)
    write_json(folder / 'review.json', dict(complete=True, identity=token, scores=scores, validation_shortlist=[]))
    write_json(folder / 'progress.json', dict(complete=True, records=records))
    write_json(folder / 'scientific_verification.json', dict(
        status='passed', identity=token, protocol_sha256=file_hash(folder / 'protocol.json'),
        review_sha256=file_hash(folder / 'review.json')))

    def git_output(args, **kwargs):
        if args[1] == 'log':
            return 'committed-parent\n'
        assert args[:2] == ['git', 'show']
        return (tmp_path / args[2].removeprefix('HEAD:')).read_bytes()

    monkeypatch.setattr(declaration.subprocess, 'check_output', git_output)
    return folder, deepcopy(design)


def test_added_drying_axes_do_not_mutate_saved_parent_selection(parent, tmp_path):
    folder, original = parent
    target = tmp_path / 'new-plan.json'
    declaration.prepare(folder, target)
    plan = json.loads(target.read_text())
    selection = plan['drying_ablation']['anchor_selection']
    assert selection['bounds'] == original['bounds']
    assert len(selection['bounds']) == 4 and len(plan['design']['bounds']) == 6
    assert plan['drying_ablation']['anchors'] == ['a', 'b']
    assert json.loads((folder / 'protocol.json').read_text())['plan']['design'] == original


def test_uncommitted_parent_is_rejected_before_a_plan_is_written(parent, tmp_path, monkeypatch):
    folder, _ = parent
    monkeypatch.setattr(declaration.subprocess, 'check_output',
                        lambda args, **kwargs: 'committed-parent\n' if args[1] == 'log' else b'changed')
    target = tmp_path / 'new-plan.json'
    with pytest.raises(ValueError, match='Commit current parent archive'):
        declaration.prepare(folder, target)
    assert not target.exists()
