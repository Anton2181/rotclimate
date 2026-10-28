"""Analytic tradeoffs, numerical rejection and bounded search coverage."""
from copy import deepcopy
from pathlib import Path
import json
import numpy as np
import pytest
from scripts.tradeoff_search import (skill_objective,coordinates,parameters,
    diverse_starts,pareto_names,evaluate,paired_native)

POLICY=dict(regional_free_ratio=1.05,regional_weight=.25,native_weight=.05,ocean_weight=.05)


def test_average_gain_can_outweigh_a_small_regional_regression():
    candidate=skill_objective([.8,.8,1.08],[.8,.8,1.08],[],[],POLICY)
    baseline=skill_objective([1,1,1],[1,1,1],[],[],POLICY)
    assert candidate['objective']<baseline['objective']
    assert candidate['worst_regional_combined_ratio']==1.08
    assert candidate['regional_squared_regret']>0


def test_large_local_damage_is_penalized_despite_better_mean():
    x=skill_objective([4,*([.4]*6)],[4,*([.4]*6)],[],[],POLICY)
    assert x['mean_combined_ratio']<1
    assert x['objective']>1


def test_native_skill_is_a_soft_cost_and_nonfinite_metrics_are_invalid():
    a=skill_objective([1],[1],[0],[0],POLICY)
    b=skill_objective([1],[1],[2],[1],POLICY)
    assert b['objective']==pytest.approx(a['objective']+.25)
    with pytest.raises(ValueError):skill_objective([np.nan],[1],[],[],POLICY)


def test_sobol_plan_is_bounded_balanced_and_roundtrips_log_parameters():
    p=json.loads(Path('calibration/global_rain_20261028/plan.json').read_text())
    points=np.stack([coordinates(p['profiles'][n],p['design']) for n in p['global_names']])
    assert points.shape==(32,3)
    np.testing.assert_array_equal((points<.5).sum(0),16)
    assert (points>=0).all() and (points<=1).all()
    for x in [[0,0,0],[1,1,1],[.3,.7,.2]]:
        np.testing.assert_allclose(coordinates(parameters(x,p['design']),p['design']),x,atol=1e-14)
    with pytest.raises(ValueError):parameters([1.1,0,0],p['design'])


def test_multiple_starts_remain_separated_instead_of_taking_one_cluster():
    design=dict(bounds={'x':dict(range=[0,1],scale='linear')},start_minimum_distance=.3,local_starts=3)
    updates={n:{'x':x} for n,x in [('a',.1),('b',.11),('c',.5),('d',.95)]}
    scores={n:dict(physical_admissible=True,objective=i) for i,n in enumerate(updates)}
    assert diverse_starts(scores,updates,design)==['a','c','d']


def test_pareto_keeps_distinct_tradeoffs_and_excludes_dominated_or_invalid():
    def row(mean,worst,native):return dict(physical_admissible=True,mean_combined_ratio=mean,worst_regional_combined_ratio=worst,native_squared_regret=native)
    rows={'average':row(.8,1.3,.1),'balanced':row(.9,1.05,.05),'dominated':row(1,1.4,.2),'invalid':dict(physical_admissible=False)}
    assert pareto_names(rows)==['average','balanced']


def test_numerical_failure_cannot_be_bought_with_better_skill(monkeypatch):
    import scripts.tradeoff_search as module
    monkeypatch.setattr(module,'branch_failures',lambda rows,params:['Manufactured failed water equation'])
    p=dict(regions=['r'],control_names=['reference','environment_control'],design={'bounds':{}},fixed_model={},
           circulation_regions=[],extra_circulation_regions=[],objective=POLICY)
    row=dict(region='r',status='passed',case_identity='same',params={},
        numerics=dict(all_checks_passed=True,vapor_flux_budget=dict(horizontal_transport_conservative=True,max_relative_transport_cancellation=0)),
        column_speed=dict(maximum_ms=10,p95_ms=5),temperature=dict(monthly_mae_C=1),rain=dict(loss=1),sst=None)
    records=[dict(row,name='reference'),dict(row,name='environment_control'),dict(row,name='candidate')]
    records[-1]['rain']={'loss':.1}
    score=evaluate('candidate',records,p)
    assert not score['physical_admissible'] and 'objective' not in score


def test_native_metrics_require_the_same_actual_footprint():
    wind=dict(native_cells=4,area_km2=100.,vector_rmse_ms=2.)
    humidity=dict(native_cells=4,area_km2=100.,partial_water_mae_mm=1.,partial_q_ratio_mae=.01)
    a=dict(case_identity='same',report=dict(scores={'q925_300':{'ocean':wind}},humidity={'scores':{'ocean':humidity}}))
    assert paired_native(a,deepcopy(a),'ocean')==[0,0,0]
    b=deepcopy(a);b['report']['humidity']['scores']['ocean']['area_km2']=101
    with pytest.raises(ValueError):paired_native(a,b,'ocean')
