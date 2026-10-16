"""Classification-aware fitting must preserve physical constraints and zone balance."""
from copy import deepcopy

import numpy as np
import pytest

from rotclimate.score import objective
from scripts.spin_rematch import obj
from scripts.round20_pilot import baseline, commands


def evaluation():
    return dict(total=0.6, per_class={str(i): 0.6 for i in range(7)},
                f1={str(i): 0.6 for i in range(7)}, recall={str(i): 0.6 for i in range(7)},
                realism=dict(map_median=900., map_p95=2200., wet_summer_hot=0.02))


def test_zonefit_rewards_classification_without_redefining_fuzzy_fit():
    a = evaluation()
    b = deepcopy(a)
    b['recall']['2'] = 0.05
    assert objective(a, 'f1r') == objective(b, 'f1r')
    assert objective(a, 'zonefit') > objective(b, 'zonefit')
    assert objective(a, 'zonefit') == pytest.approx(0.6)


def test_one_collapsed_zone_is_penalized_even_with_the_same_macro_recall():
    a = evaluation()
    b = deepcopy(a)
    b['recall'] = dict(zip(a['recall'], [0, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7]))
    assert np.mean(list(a['recall'].values())) == pytest.approx(np.mean(list(b['recall'].values())))
    assert objective(a, 'zonefit') > objective(b, 'zonefit')


def test_zonefit_preserves_realism_penalty_strength():
    a, b = evaluation(), evaluation()
    b['realism']['map_median'] = 1700
    for mode in ['f1r', 'zonefit']:
        assert objective(a, mode) - objective(b, mode) == pytest.approx(0.1)


def test_rematch_uses_ensemble_averaged_recall_for_new_objective():
    a, b = evaluation(), evaluation()
    a['recall'] = {k: 0.2 for k in a['recall']}
    b['recall'] = {k: 1.0 for k in b['recall']}
    assert obj([a, b], 'zonefit') == pytest.approx(objective(evaluation(), 'zonefit'))


def test_pilot_starts_are_strict_and_commands_use_new_test_worlds(tmp_path):
    for spin in ['earthlike', 'retrograde']:
        p = baseline(spin)
        assert p.retrograde == (spin == 'retrograde')
        assert p.solver_require_convergence and p.solver_rtol == 1e-6
        assert p.downsample == 8 and p.t_iters == 48
    cmds = commands(tmp_path, 65, 4, 12)
    assert len(cmds) == 3
    assert all(c[c.index('--objective') + 1] == 'zonefit' for c in cmds)
    assert cmds[-1][cmds[-1].index('--first-seed') + 1] == '201'
    assert '--baseline-params' in cmds[-1]


def test_rematch_deduplicates_identical_fits_but_keeps_aliases_and_distinct_physics():
    from scripts.spin_rematch import unique_candidates
    cands = {
        'winner': {'params': {'lat_center': 35., 'beyond_seed': 1}, 'score': 0.4},
        'unchanged-start': {'params': {'lat_center': 35., 'beyond_seed': 3}, 'score': None},
        'different': {'params': {'lat_center': 36., 'beyond_seed': 1}, 'score': 0.3},
    }
    unique, aliases = unique_candidates(cands)
    assert list(unique) == ['winner', 'different']
    assert aliases == {'winner': ['winner', 'unchanged-start'], 'different': ['different']}
