"""Explain real rule interactions without seasonal climate simulations."""
import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate.diagnostics import audit_rules
from rotclimate.geography import TARGET_CLASSES
from rotclimate.koppen import CODES
from rotclimate.score import best_zone, membership_factors, memberships


def climate():
    return {k: np.array([v], dtype=float) for k, v in dict(
        Tcold=10, Thot=27, MAT=18, aridity=3, Psdry=80, Pwwet=160, MAP=1500).items()}


def test_compatible_warm_wet_climate_can_lose_to_broader_forest_rule():
    ix = climate()
    mem = memberships(ix)
    assert mem['warm_wet'][0] > 0.9
    assert mem['tree'][0] > mem['warm_wet'][0]
    kop = np.array([CODES.index('Cfa')])
    assert best_zone(mem, koppen=kop)[0] == 6
    r = audit_rules(mem, membership_factors(ix), kop, np.array([3]), np.array([True]), ix, np.zeros(1))
    zone = r['zones']['warm_wet']
    assert zone['failure_partition']['eligible_but_other_label_wins'] == 1
    assert zone['failure_partition']['incompatible_koppen'] == 0


def test_failure_partition_distinguishes_eligibility_weak_rules_and_competition():
    mem = {key: np.zeros(4) for _, key, _, _ in TARGET_CLASSES}
    mem['warm_wet'] = np.array([0.9, 0.9, 0.1, 0.7])
    mem['tree'] = np.array([0.1, 0.1, 0.1, 0.9])
    factors = {key: {'test_factor': v} for key, v in mem.items()}
    kop = np.array([CODES.index(c) for c in ['Cfa', 'Csa', 'Cfa', 'Cfa']])
    zone = audit_rules(mem, factors, kop, np.full(4, 3), np.ones(4, bool))['zones']['warm_wet']
    assert all(v == 0.25 for v in zone['failure_partition'].values())
    assert sum(zone['failure_partition'].values()) == 1
    assert zone['factors']['test_factor']['recall_if_factor_removed'] == 0.75


def test_swamp_requires_all_original_factors_and_no_rule_was_loosened():
    ix = climate()
    factor = membership_factors(ix, slope=np.array([1.]))['swamp']
    assert set(factor) == {'hot_summer', 'mild_winter', 'humidity', 'flat_ground', 'hot_year'}
    expected = np.prod([v[0] for v in factor.values()])
    assert memberships(ix, slope=np.array([1.]))['swamp'][0] == pytest.approx(expected)
    assert factor['hot_year'][0] < 0.01


def test_selected_retrograde_profile_matches_the_saved_winner():
    selected = Params.from_json('calibration/round20_retrograde_selected.json')
    winner = Params.from_json('calibration/r20_pilot/retrograde/best_params.json')
    assert selected == winner
    assert selected.retrograde and selected.solver_require_convergence
    assert (selected.downsample, selected.steps_per_year, selected.picard_iters) == (8, 25, 2)


def test_rule_snapshot_preserves_fields_for_offline_analysis(tmp_path):
    import json
    from types import SimpleNamespace
    from rotclimate.diagnostics import analyse_rules
    from rotclimate.koppen import climate_indices

    Tm, Pm = np.full((12, 2, 3), 21.), np.full((12, 2, 3), 100.)
    summer = np.array([False] * 3 + [True] * 6 + [False] * 3)
    ix = climate_indices(Tm, Pm, summer)
    grid = SimpleNamespace(elev=np.zeros((2, 3)), cell_km=15., target=np.full((2, 3), 3),
                           land=np.ones((2, 3), bool), inmap=np.ones((2, 3), bool),
                           map_slice=lambda: (slice(None), slice(None)))
    ev = dict(indices=ix, memberships=memberships(ix, slope=np.zeros((2, 3))),
              monthly=dict(Tm=Tm, Pm=Pm, summer=summer))
    result = SimpleNamespace(grid=grid, params=Params(retrograde=True))
    path = tmp_path / 'fields.npz'
    audit = analyse_rules(result, ev, snapshot=path)
    assert audit['zones']['warm_wet']['cells'] == 6
    with np.load(path, allow_pickle=False) as fields:
        np.testing.assert_array_equal(fields['membership_warm_wet'], ev['memberships']['warm_wet'])
        np.testing.assert_array_equal(fields['index_MAP'], ix['MAP'])
        assert json.loads(str(fields['params_json']))['retrograde']
        assert 'factor_swamp_hot_year' in fields
