import numpy as np
import pytest
from polity.settlement_support import permanent_food_ceiling,allocate_settlement,paired_reach


def test_annual_grain_is_not_a_permanent_settlement_without_storage():
    pulse=np.zeros((12,1));pulse[3]=1200
    assert permanent_food_ceiling(pulse,kcal_day=1,year_days=360,store_days=0,loss_fraction_year=0)[0]==0
    cap=permanent_food_ceiling(pulse,kcal_day=1,year_days=360,store_days=360,loss_fraction_year=0)
    assert cap[0]==pytest.approx(1200/360,rel=1e-6)


def test_one_food_pool_supports_civilians_and_cohort_once():
    arrivals=np.full((12,1),300*30.)
    plan=allocate_settlement(arrivals,np.array([400.]),np.array([True]),institutional_request=100,minimum_community=50,kcal_day=1,year_days=360,loss_fraction_year=0)
    assert plan.institutional_active[0]
    assert plan.institutional_people[0]==100
    assert plan.civilian_people[0]==pytest.approx(200,rel=1e-6)
    assert plan.total_people[0]==pytest.approx(300,rel=1e-6)
    assert plan.food_year.consumed[0]<=arrivals.sum()+1e-6
    assert abs(plan.food_year.ledger_residual[0])<1e-5


def test_community_can_persist_when_joint_institution_is_infeasible():
    arrivals=np.full((12,1),120*30.)
    plan=allocate_settlement(arrivals,np.array([400.]),np.array([True]),institutional_request=100,minimum_community=50,kcal_day=1,year_days=360,loss_fraction_year=0)
    assert plan.community_viable[0] and not plan.institutional_active[0]
    assert plan.civilian_people[0]==pytest.approx(120,rel=1e-6)
    assert plan.institutional_people[0]==0


def test_missing_affiliation_does_not_remove_residents_or_create_authority():
    plan=allocate_settlement(np.full((12,1),300*30.),np.array([200.]),np.array([False]),kcal_day=1,year_days=360,loss_fraction_year=0)
    assert plan.civilian_people[0]==200 and plan.institutional_people[0]==0
    assert not plan.institutional_active[0]


def test_source_removal_changes_reach_without_population_power_weights():
    out=np.array([[1.,1.8,3.],[2.,.5,2.]])
    back=np.array([[1.,2.5,1.],[2.,.5,2.]])
    reach=paired_reach(out,back)
    baseline=reach.any(0);supplied=reach[np.array([True,False])].any(0)
    np.testing.assert_array_equal(baseline,[True,True,True])
    np.testing.assert_array_equal(supplied,[True,False,False])
    assert not paired_reach([1.9],[1.9],ration_days=3)[0]


def test_shorter_storage_and_lower_supply_cannot_improve_capacity():
    food=np.zeros((12,2));food[[1,7]]=[[3000,1200],[2000,2200]]
    a=permanent_food_ceiling(food,kcal_day=1,store_days=90,loss_fraction_year=0)
    b=permanent_food_ceiling(food*.5,kcal_day=1,store_days=90,loss_fraction_year=0)
    c=permanent_food_ceiling(food,kcal_day=1,store_days=30,loss_fraction_year=0)
    assert np.all(b<=a+1e-8) and np.all(c<=a+1e-8)


def test_marked_registry_join_uses_grid_positions_and_preserves_unknowns(monkeypatch):
    from polity import fields as F
    from scripts.review_settlement_integration import candidates
    raw=[dict(kind='fortified town',row=0,col=0,x_px=100.,y_px=100.),dict(kind='fortified town',row=0,col=5,x_px=500.,y_px=100.)]
    monkeypatch.setattr(F,'settlements',lambda shape:raw)
    monkeypatch.setattr(F,'polity_fills',lambda shape:(None,{1:dict(name='Claim',hex='#ffffff'),2:dict(name='Recorded',hex='#000000')}))
    r=dict(towns=[dict(raw[0],col=1),raw[1]],claim=np.zeros((1,6),int))
    registry=dict(records=[dict(id='one',name='Known',kind='fortified town',x=1.8,y=.2,node=0,actor='Recorded',symbol_verified=True),dict(id='two',name='Unknown',kind='fortified town',x=10.2,y=.2,node=5,actor=None,symbol_verified=True)])
    market=[dict(market_id=1,row=0,col=1,inbound_catchment_people=100),dict(market_id=2,row=0,col=1,inbound_catchment_people=200),dict(market_id=3,row=0,col=5,inbound_catchment_people=50)]
    sites,actors=candidates(r,registry,(1,6),2,market)
    assert len(sites)==2 and sites[0]['served_people']==300
    assert sites[0]['market_ids']==[1,2]
    assert sites[0]['node']==1 and sites[0]['actor']=='Recorded'
    assert sites[1]['actor'] is None and sites[1]['actor_index']==-1
    assert all(s['marked'] for s in sites)


def test_lower_supply_and_smaller_cohort_do_not_invent_residents():
    arrivals=np.full((12,2),200*30.)
    request=np.array([1000.,30.]);affiliated=np.array([True,True])
    big=allocate_settlement(arrivals,request,affiliated,kcal_day=1,year_days=360,loss_fraction_year=0)
    small=allocate_settlement(arrivals,request,affiliated,institutional_request=25,kcal_day=1,year_days=360,loss_fraction_year=0)
    assert np.all(small.civilian_people<=request)
    assert not big.institutional_active[1] and not small.institutional_active[1]
    assert small.civilian_people[0]>big.civilian_people[0]
    assert small.total_people[0]==pytest.approx(big.total_people[0],rel=1e-6)
