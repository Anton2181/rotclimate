"""The search objective must rank candidates by the adopted release policy."""
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.gate_calibrate import score
from scripts.gate_v3 import score as release_score


def test_v3_accepts_overall_gain_despite_a_worse_group():
    groups = dict(training=['a', 'b', 'c'], holdout=['d'])
    ref = {n: (2., 1.) for n in 'abcd'}
    candidate = {**{n: (1.6, .8) for n in 'abc'}, 'd': (2.2, 1.1)}
    old, _ = score(candidate, ref, groups)
    new, info = score(candidate, ref, groups, policy='v3')
    assert old == pytest.approx(1.075)
    assert new == pytest.approx(.875)
    assert info['groups']['holdout'] == pytest.approx(1.1)
    assert info['penalty'] == 0


def test_v3_retired_regions_have_equal_weight_without_group_penalties():
    ref = {n: (2., 1.) for n in 'abc'}
    candidate = dict(a=(1., .5), b=(2.2, 1.1), c=(2.2, 1.1))
    cost, info = score(candidate, ref, dict(dev=['a']), dict(retired=['b', 'c']), policy='v3')
    assert cost == pytest.approx(.9)
    assert info['S31'] == .5
    assert info['n'] == 3
    assert info['penalty'] == 0
    # Legacy plans keep their original objective, including the extra-group penalty.
    assert score(candidate, ref, dict(dev=['a']), dict(retired=['b', 'c']))[0] == pytest.approx(.7)


def test_v3_keeps_temperature_and_rain_safeguards_separate():
    cost, info = score(dict(a=(1., 1.1)), dict(a=(2., 1.)), dict(dev=['a']), policy='v3')
    assert info['S'] == pytest.approx(.8)
    assert info['penalty'] == pytest.approx(.18)
    assert cost == pytest.approx(.98)


@pytest.mark.parametrize('errors,groups,extra', [
    ({'a': (np.nan, 1.)}, {'dev': ['a']}, {}),
    ({'a': (-1., 1.)}, {'dev': ['a']}, {}),
    ({'a': (1., 1.)}, {'dev': ['a']}, {'retired': ['a']}),
    ({}, {'dev': ['a']}, {}),
])
def test_v3_rejects_invalid_or_reweighted_measurements(errors, groups, extra):
    with pytest.raises(ValueError):
        score(errors, {'a': (2., 1.)}, groups, extra, policy='v3')


def test_search_score_matches_independent_r42_release_gate():
    root = Path(__file__).resolve().parents[1]
    run = root / 'output/desert_refit3_20261101/v3'
    reference, candidate, extra = {}, {}, {}
    for part in ['dev31', 'retired_a', 'retired_b', 'retired_c']:
        rows = []
        for fit, dest in [('r41', reference), ('candidate', candidate)]:
            data = json.loads((run / f'{fit}_{part}/summary.json').read_text())['regions']
            dest.update(data)
            rows = list(data)
        if part != 'dev31':
            extra[part] = rows
    policy = json.loads((root / 'calibration/local_accuracy_20261023/policy_v3.json').read_text())
    def metrics(rows):
        return {n: (r['temperature']['monthly_mae_C'], r['rain']['loss']) for n, r in rows.items()}
    cost, info = score(metrics(candidate), metrics(reference), policy['groups'], extra, policy='v3')
    release = release_score(reference, candidate, list(reference))
    assert info['n'] == 49
    assert info['S'] == pytest.approx(release['S'], abs=1e-14)
    assert cost == pytest.approx(.9626111459489867, abs=1e-14)

