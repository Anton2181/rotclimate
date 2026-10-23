from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate import calibrate as C, model, score, biome_targets as B


def member(p):
    shape = (1, 2, 3)
    land = np.ones(shape[1:], bool)
    grid = SimpleNamespace(inmap=land.copy(), land=land.copy(), land_frac=land.astype(float),
                           elev=np.zeros_like(land, float), lat=np.ones_like(land, float)*30,
                           target=np.ones_like(land, int))
    fields = {key:np.full(shape, p.beyond_seed, np.float32) for key in ('T','Tsl','P','W','u','v','E','snow')}
    return model.Result(params=p, grid=grid, days=np.array([100.]),
                        numerics=dict(all_checks_passed=True), **fields)


def fake_evaluation(result):
    # Nonlinear scoring makes score(mean climate) different from mean(scores).
    value = float(result.T.mean())**2
    return dict(indices={}, per_class={'zone':value}, total=value,
                precision={'zone':value}, f1={'zone':value}, recall={'zone':value},
                accuracy=value, label_policy_audit={'display_accuracy':value}, realism={'value':0.})


@pytest.fixture
def synthetic(monkeypatch):
    class FakeModel:
        def __init__(self, p): self.p = p
        def run(self): return member(self.p)
    monkeypatch.setattr(model, 'ClimateModel', FakeModel)
    monkeypatch.setattr(score, 'evaluate', fake_evaluation)
    monkeypatch.setattr(score, 'objective', lambda ev, mode:ev['total'])
    monkeypatch.setattr(C, 'mediterranean_shares', lambda *args:dict(dry_share=0., cs_share=1.))


def test_calibration_scores_exactly_the_same_field_average_as_atlas(synthetic):
    p = Params()
    old = C.evaluate_params(p, 'zonefit', seeds=[1,3])
    new = C.evaluate_params(p, 'zonefit', seeds=[1,3], ensemble_objective='climate')
    atlas = model.run_ensemble(p, [1,3])
    assert old['score'] == 5.
    assert new['score'] == score.objective(score.evaluate(atlas), 'zonefit') == 4.
    assert new['ensemble_objective'] == 'climate' and new['layouts'] == 2 and not new['raced']
    assert new['observed_numerics']['all_checks_passed']


def test_coverage_penalty_is_measured_on_the_published_climate(synthetic, monkeypatch):
    biome = dict(score=.6)
    monkeypatch.setattr(B, 'evaluate', lambda *args:biome)
    monkeypatch.setattr(B, 'rendered_coverage', lambda r:dict(outside_share=0. if r.T.mean()==2. else .04, distance_debt=0.))
    new = C.evaluate_params(Params(), 'whittaker-covered', seeds=[1,3], ensemble_objective='climate')
    assert new['score'] == .6 and new['whittaker_coverage']['outside_share'] == 0.
    assert new['whittaker_coverage']['layouts'] == 2


def test_ensemble_rejects_different_physics_calendar_and_mapped_geography():
    a = member(Params(beyond_seed=1))
    b = member(Params(beyond_seed=2))
    with pytest.raises(ValueError, match='physical parameters'):
        model.ensemble_mean([a, replace(b, params=b.params.replace(ocean_rh=.9))])
    with pytest.raises(ValueError, match='calendar'):
        model.ensemble_mean([a, replace(b, days=np.array([110.]))])
    b.grid.elev[0,0] = 5
    with pytest.raises(ValueError, match='geography'):
        model.ensemble_mean([a, b])


def test_mean_preserves_failed_member_certificates():
    a = member(Params(beyond_seed=1))
    b = member(Params(beyond_seed=2))
    b.numerics = dict(all_checks_passed=False)
    result = model.ensemble_mean([a,b])
    assert not result.numerics['all_checks_passed']
    np.testing.assert_array_equal(result.P, 1.5)


def test_mean_climate_cannot_be_raced_or_resume_as_another_objective(tmp_path):
    with pytest.raises(ValueError, match='every layout'):
        C.evaluate_params(Params(), seeds=[1,2], cutoff=.1, ensemble_objective='climate')
    with pytest.raises(ValueError, match='race=0'):
        C.calibrate(tmp_path, 1, Params(), ensemble_objective='climate')
    (tmp_path/'state.pkl').write_bytes(b'old checkpoint')
    with pytest.raises(ValueError, match='certificate'):
        C.calibrate(tmp_path, 1, Params(), ensemble_objective='climate', race=0, resume=True)


def test_cli_defaults_to_mean_climate_without_racing(monkeypatch, capsys):
    import json
    import sys
    monkeypatch.setattr(sys, 'argv', ['calibrate','--plan','--physics','world'])
    C.main()
    plan = json.loads(capsys.readouterr().out)
    assert plan['ensemble_objective'] == 'climate' and plan['race'] == 0
