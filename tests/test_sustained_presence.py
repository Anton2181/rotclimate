import numpy as np
import pytest
from scipy.sparse import csr_matrix
from polity.sustained_presence import rural_cereal,collected_supply,stored_collection,site_food,fixed_path_days


def test_rural_meals_and_storage_loss_precede_export():
    rural=rural_cereal(np.array([1200.,0.]),np.array([1,0],np.uint16),reserve_days=365)
    np.testing.assert_allclose(rural.harvest.sum(0),[1200,0])
    np.testing.assert_allclose(rural.year.consumed,[720,0],atol=1e-6)
    np.testing.assert_allclose(rural.overflow.sum(0),rural.year.overflow)
    assert rural.overflow[:,0].sum()<480
    assert np.max(np.abs(rural.year.ledger_residual))<1e-6


def test_calendar_alternatives_never_make_extra_harvests():
    for calendar,expected in [('first',1),('last',10)]:
        rural=rural_cereal(np.array([100.]),np.array([(1<<1)|(1<<10)],np.uint16),calendar=calendar)
        assert rural.harvest.sum()==100
        assert rural.harvest[expected,0]==100
    with pytest.raises(ValueError):rural_cereal(np.array([100.]),np.array([0],np.uint16))


def test_collection_unique_cells_capacity_delay_and_conservation():
    overflow=np.full((12,3),10.);ids=np.array([1,1,2]);access=np.ones_like(overflow,bool);access[0,2]=False
    flow=collected_supply(overflow,ids,access,2,collection_fraction=.5,freight_capacity=7,retention=.8,delay_bins=1)
    assert flow['departures'][0,0]==7
    assert flow['arrivals'][1,1]==0
    np.testing.assert_allclose(flow['arrivals'].sum()+flow['transport_loss']+flow['uncollected'],overflow.sum())
    assert flow['arrivals'][0,0]==flow['departures'][-1,0]*.8


def test_no_inherited_city_food_and_stores_cannot_fix_annual_deficit():
    arrivals=np.zeros((12,1));arrivals[3]=1200
    year,met=site_food(arrivals,people=1,kcal_day=12/365,reserve_days=365,loss_fraction_year=0)
    assert year.unmet.sum()==pytest.approx(0,abs=1e-7)
    year,_=site_food(np.zeros((12,1)),people=100,reserve_days=365)
    assert year.consumed.sum()==0 and year.initial_stock[0]==0
    year,_=site_food(np.ones((12,1)),people=1,kcal_day=1,reserve_days=365,loss_fraction_year=0)
    assert year.unmet.sum()==pytest.approx(353)


def test_fixed_routes_use_same_parent_site_both_ways():
    graph=csr_matrix([[0,2,0],[5,0,3],[0,7,0.]])
    out,back=fixed_path_days(graph,np.array([0,0,1]),np.array([1,2]))
    np.testing.assert_allclose(out,[0,2,5]);np.testing.assert_allclose(back,[0,5,12])
    with pytest.raises(ValueError):fixed_path_days(graph,np.array([0,0,1]),np.array([2,1]))


def test_origin_stores_bridge_harvest_and_respect_dispatch_closure():
    food=np.zeros((12,2));food[2]=[1200,2400];ids=np.array([1,1]);access=np.ones_like(food,bool)
    flow=stored_collection(food,ids,access,1,collection_fraction=1,freight_capacity=200,retention=1,loss_fraction_year=0)
    np.testing.assert_allclose(flow['departures'],200)
    opened=np.ones((12,1),bool);opened[[0,11]]=False
    closed=stored_collection(food,ids,access,1,collection_fraction=1,freight_capacity=200,retention=.9,loss_fraction_year=.05,dispatch_open=opened)
    assert np.all(closed['departures'][[0,11]]==0)
    np.testing.assert_allclose(food.sum(),closed['arrivals'].sum()+closed['transport_loss']+closed['collection_storage_loss']+closed['uncollected'],rtol=1e-8)
    assert closed['max_collection_ledger_residual']<1e-6


def test_protected_rural_meals_prevent_export_of_an_early_glut():
    annual=np.array([1200.]);bits=np.array([1],np.uint16)
    short=rural_cereal(annual,bits,reserve_days=180)
    assert short.overflow.sum()>0 and short.year.unmet.sum()>0
    assert short.exportable.sum()==0
    full=rural_cereal(annual,bits,reserve_days=365)
    assert full.exportable.sum()>0
