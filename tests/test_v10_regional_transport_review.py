"""Review acceptance and mask semantics only; no climate simulations."""
from types import SimpleNamespace
import numpy as np
import pytest
from scripts import review_v10_regional_transport as review


def test_stopped_prefix_preserves_missing_cases():
    jobs = [{'key': k} for k in ('control', 'bulk', 'parcel')]
    state = {'status': 'needs_diagnosis', 'cases': {'control': {}, 'bulk': {}}}
    assert review.completed_prefix(state, jobs) == ['parcel']
    with pytest.raises(ValueError):
        review.completed_prefix(dict(state, status='complete'), jobs)


@pytest.mark.parametrize('state', [
    {'status': 'running', 'cases': {'control': {}}},
    {'status': 'needs_diagnosis', 'cases': {'bulk': {}}},
    {'status': 'complete', 'cases': {'control': {}, 'unknown': {}}},
])
def test_rejects_live_or_undeclared_evidence(state):
    with pytest.raises(ValueError):
        review.completed_prefix(state, [{'key': 'control'}, {'key': 'bulk'}])


def test_review_cannot_write_to_source_or_atlas(tmp_path):
    source = tmp_path/'experiment'
    for out in (source, source/'review', tmp_path, review.ROOT/'atlas', review.ROOT/'atlas/data/review'):
        with pytest.raises(ValueError):
            review.check_review_path(out, source)
    review.check_review_path(tmp_path/'separate_review', source)


def test_endpoint_reports_scored_instability_separately_from_ocean():
    # One scored cell changes by 10C, three ocean cells stay fixed. Physical
    # temperature is reconstructed from enthalpy and water, not monthly means.
    shape = (2, 2, 2)
    g = SimpleNamespace(mass=np.ones(shape)*100, height_m=np.zeros(shape), pressure=np.ones(shape)*50000)
    case = SimpleNamespace(score_mask=np.array([[True, False], [False, False]]),
                           domain=SimpleNamespace(land=np.array([[True, False], [False, False]])))
    cp, lv = review.run.model.base.CP, review.run.model.base.LV
    water = np.ones(shape)*.01
    old_t = np.zeros(shape)
    new_t = old_t.copy(); new_t[1, 0, 0] = 10.
    def record(t):
        return (SimpleNamespace(energy=g.mass*cp*(t+273.15)+lv*water, water=water),)
    result, delta = review.endpoint_diagnostics(record(old_t), record(new_t), case, g)
    assert delta[1, 0, 0] == pytest.approx(10.)
    assert result['layers'][1]['scored_land_p95_c'] == pytest.approx(10.)
    assert result['max_location_is_scored']
    assert result['max_location_layer_y_x'] == [1, 0, 0]
