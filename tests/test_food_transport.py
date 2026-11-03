import numpy as np

from polity.food_transport import FoodRoute,provision_food


def test_shared_farm_food_is_conserved_and_rural_priority_is_explicit():
    r=provision_food([[10,0,0]],[[6,6,6]],
        [FoodRoute(0,1,0,10,1),FoodRoute(0,2,0,10,2)],storage_capacity=0,priority=[0,1,1])
    np.testing.assert_allclose(r.consumed,[[6,4,0]])
    assert r.shipped.sum()==4 and abs(r.annual_ledger_residual)<1e-8


def test_direction_and_capacity_cannot_be_replaced_by_undirected_access():
    r=provision_food([[10,0]],[[4,6]],[FoodRoute(0,1,0,3,1)],storage_capacity=0,priority=[0,1])
    np.testing.assert_allclose(r.consumed,[[4,3]])
    reverse=provision_food([[10,0]],[[4,6]],[FoodRoute(1,0,0,10,1)],storage_capacity=0,priority=[0,1])
    assert reverse.consumed[0,1]==0


def test_transit_time_and_seasonal_departure_capacity_control_arrival():
    harvest=np.zeros((4,2));harvest[0,0]=8
    demand=np.zeros_like(harvest);demand[[1,2],1]=4
    r=provision_food(harvest,demand,[FoodRoute(0,1,2,[8,0,0,0],1)],storage_capacity=0,priority=[0,1])
    assert r.consumed[1,1]==0 and r.consumed[2,1]==4
    assert abs(r.annual_ledger_residual)<1e-8


def test_losses_are_physical_and_transport_cost_does_not_eat_food():
    r=provision_food([[10,0]],[[0,8]],[FoodRoute(0,1,0,10,100,.8)],storage_capacity=0,priority=[0,1])
    np.testing.assert_allclose([r.consumed.sum(),r.transport_loss,r.transport_cost],[8,2,1000])
    no_loss=provision_food([[10,0]],[[0,10]],[FoodRoute(0,1,0,10,100)],storage_capacity=0,priority=[0,1])
    assert no_loss.consumed.sum()==10 and no_loss.transport_loss==0


def test_storage_and_spoilage_between_harvest_and_shipping_are_accounted():
    r=provision_food([[2,0],[0,0]],[[0,0],[0,2]],
        [FoodRoute(0,1,0,[0,2],1)],storage_capacity=[2,0],priority=[0,1],storage_survival=[[1,1],[.5,1]])
    assert r.consumed.sum()==1 and r.storage_loss==1
    assert abs(r.annual_ledger_residual)<1e-8


def test_periodic_stocks_and_cargo_cannot_feed_people_without_production():
    r=provision_food(np.zeros((3,2)),np.ones((3,2)),
        [FoodRoute(0,1,1,10,1),FoodRoute(1,0,1,10,1)],storage_capacity=100,priority=[0,1])
    assert r.consumed.sum()==r.stocks.sum()==r.shipped.sum()==0
