"""Coverage is a measured constraint on land, never a new biome assignment."""
from types import SimpleNamespace
import numpy as np
import pytest
from rotclimate import biome_targets as B,biomes
from rotclimate.config import Params


def test_unpainted_land_outside_the_union_is_counted_and_ocean_is_excluded():
    c=B.coverage([27.,-5.,100.],[3000.,4000.,10000.],[True,True,False])
    assert c['outside_share']==.5 and c['land_cells']==2 and c['outside_cells']==1
    assert c['distance_debt']>0
    assert biomes.classify([-5.],[4000.]).item()==0


def test_farther_outside_is_worse_even_when_both_are_unclassified():
    a=B.coverage([27.],[6000.],[True]);b=B.coverage([27.],[16000.],[True])
    assert a['outside_share']==b['outside_share']==1
    assert a['distance_debt']<b['distance_debt']
    assert B.covered_score(.6,a)>B.covered_score(.6,b)


def test_invalid_land_has_maximum_debt_and_cannot_disappear():
    r=B.coverage([np.nan,27.],[1000.,3000.],[True,True])
    assert r['outside_share']==.5
    assert r['distance_debt']==B.coverage_policy()['distance_cap']**2/2
    with pytest.raises(ValueError,match='No land'):B.coverage([27.],[3000.],[False])


def test_in_diagram_and_old_target_objectives_are_unchanged():
    c=B.coverage([27.,10.],[3000.,300.],[True,True])
    assert c['outside_share']==c['distance_debt']==0
    assert B.covered_score(.6,c)==.6
    old=B.evaluate({'MAT':np.array([27.]),'MAP':np.array([3000.])},np.array([5]),np.array([True]))
    assert old['score']==1 and 'distance_debt' not in old


def test_fast_rendered_annual_coverage_matches_monthly_field_aggregation(monkeypatch):
    from rotclimate import render
    from rotclimate.koppen import monthly_stats,monthly_weights
    from rotclimate.climate_fields import lapse_at_days
    p=Params(steps_per_year=25,lapse_rate=4.5,lapse_seasonal=.3)
    days=(np.arange(25)+.5)*p.year_days/25
    h=np.array([[0.,1000.],[2000.,3000.]])
    T=18+9*np.sin(2*np.pi*days/p.year_days)[:,None,None]+np.zeros((25,2,2))
    P=2+np.cos(2*np.pi*days/p.year_days)[:,None,None]+np.zeros((25,2,2))
    land=np.ones((2,2),bool)
    monkeypatch.setattr(render,'FullRes',lambda r:SimpleNamespace(land=land,elev=h,up=lambda a:a))
    r=SimpleNamespace(Tsl=T,P=P,days=days,params=p)
    actual=B.rendered_coverage(r)
    st=monthly_stats(T,P,days,p.year_days)
    lapse=monthly_weights(days,p.year_days)@lapse_at_days(p,days)
    surface=st['Tm']-lapse[:,None,None]*h/1000
    expected=B.coverage(surface.mean(0),st['Pm'].sum(0),land)
    for k in expected:assert actual[k]==pytest.approx(expected[k],abs=1e-12)


def test_calibration_averages_layout_penalties_without_changing_old_scores(monkeypatch):
    from rotclimate import calibrate as C,model,score
    grid=SimpleNamespace(target=np.ones(1),inmap=np.ones(1,bool),land=np.ones(1,bool))
    class FakeModel:
        def __init__(self,p):self.p=p
        def run(self):return SimpleNamespace(grid=grid,seed=self.p.beyond_seed)
    ev=dict(indices={},per_class={'zone':.5},total=.5,precision={'zone':.5},f1={'zone':.5},
            recall={'zone':.5},accuracy=.5,label_policy_audit={'display_accuracy':.5},realism={'value':0.})
    monkeypatch.setattr(model,'ClimateModel',FakeModel)
    monkeypatch.setattr(score,'evaluate',lambda r:ev)
    monkeypatch.setattr(score,'objective',lambda ev,mode:.2)
    monkeypatch.setattr(C,'mediterranean_shares',lambda *args:dict(dry_share=0.,cs_share=1.))
    baseline=dict(profile='strict',score=.6,macro_hard=.4,macro_soft=.8,outside_share=0.,
                  per_zone={'zone':dict(cells=1,hard=.4,soft=.8)})
    monkeypatch.setattr(B,'evaluate',lambda *args:baseline)
    monkeypatch.setattr(B,'rendered_coverage',lambda r:dict(outside_share=0. if r.seed==1 else .04,distance_debt=0.))
    result=C.evaluate_params(Params(),mode='whittaker-covered',seeds=[1,2])
    assert result['score']==pytest.approx(.57)
    assert result['whittaker']['score']==.6
    assert result['whittaker_coverage']['outside_share']==.02
    assert result['whittaker_coverage']['layouts']==2 and not result['raced']
