import copy
import numpy as np
import pytest
from polity.service_demand import allocate_requests
from polity.service_capacity import supported_staff_hours,fulfil_services
from polity.settlement_support import allocate_settlement


def food_plan(people=300):
    return allocate_settlement(np.full((12,1),people*30.),np.array([400.]),np.array([True]),
        institutional_request=100,minimum_community=50,kcal_day=1,year_days=360,loss_fraction_year=0)


def test_different_service_costs_share_one_budget_instead_of_reusing_it():
    a=allocate_requests([[1]],[10],[1]);b=allocate_requests([[1]],[10],[1])
    result=fulfil_services([a,b],staff_hours=[15],hours_per_request=[[1],[2]])
    np.testing.assert_allclose(result.provider_requests,[[5],[5]])
    np.testing.assert_allclose(result.provider_hours_by_channel,[[5],[10]])
    np.testing.assert_allclose(result.origin_unmet,[[5],[5]])
    np.testing.assert_allclose(result.unused_provider_hours,[0])


def test_unreachable_and_capacity_deficits_are_separate_and_conserved():
    a=allocate_requests([[1,0]],[10,20],[1])
    result=fulfil_services([a],staff_hours=[4],hours_per_request=1)
    np.testing.assert_allclose(result.origin_served,[[4,0]])
    np.testing.assert_allclose(result.origin_unreachable,[[0,20]])
    np.testing.assert_allclose(result.origin_capacity_unmet,[[6,0]])


def test_one_pass_does_not_claim_maximum_flow_or_reroute_spare_capacity():
    a=allocate_requests([[1],[1]],[10],[1,1])
    result=fulfil_services([a],staff_hours=[0,10],hours_per_request=1)
    np.testing.assert_allclose(result.origin_served,[[5]])
    np.testing.assert_allclose(result.unused_provider_hours,[0,5])


def test_food_and_other_duties_bound_services_without_adding_residents():
    plan=food_plan();before=copy.deepcopy(plan)
    budget=supported_staff_hours(plan,hours_per_staff=2,committed_hours=50)
    np.testing.assert_allclose(budget.gross_hours,[200]);np.testing.assert_allclose(budget.available_hours,[150])
    demand=allocate_requests([[1]],plan.total_people,[1])
    result=fulfil_services([demand],staff_hours=budget.available_hours,hours_per_request=1)
    np.testing.assert_allclose(result.provider_requests,[[150]])
    np.testing.assert_array_equal(plan.total_people,before.total_people)
    np.testing.assert_array_equal(plan.food_year.consumed,before.food_year.consumed)
    no_staff=food_plan(120)
    np.testing.assert_allclose(supported_staff_hours(no_staff,hours_per_staff=2,committed_hours=0).available_hours,[0])


def test_zero_work_or_all_committed_hours_leave_requests_unserved():
    plan=food_plan();budget=supported_staff_hours(plan,hours_per_staff=2,committed_hours=200)
    a=allocate_requests([[1]],plan.total_people,[1]);before=a.choice_probabilities.copy()
    result=fulfil_services([a],staff_hours=budget.available_hours,hours_per_request=1)
    np.testing.assert_allclose(result.origin_served,[[0]])
    np.testing.assert_allclose(result.origin_unmet,[plan.total_people])
    np.testing.assert_array_equal(a.choice_probabilities.toarray(),before.toarray())


def test_overspent_or_unsupported_ledger_is_rejected():
    plan=food_plan()
    with pytest.raises(ValueError,match='exceeds'):supported_staff_hours(plan,hours_per_staff=2,committed_hours=201)
    plan.total_people[0]+=1000
    with pytest.raises(ValueError,match='same feasible'):supported_staff_hours(plan,hours_per_staff=2,committed_hours=0)
    plan=food_plan();plan.food_year.unmet[0]=plan.food_year.needed[0]
    with pytest.raises(ValueError,match='Repeating food'):supported_staff_hours(plan,hours_per_staff=2,committed_hours=0)


def test_invalid_or_tampered_service_inputs_do_not_create_capacity():
    a=allocate_requests([[1]],[10],[1])
    for budget,cost in [([-1],1),([np.nan],1),([1],0),([1],np.inf),([1,2],1)]:
        with pytest.raises(ValueError):fulfil_services([a],staff_hours=budget,hours_per_request=cost)
    with pytest.raises(ValueError):fulfil_services([],staff_hours=[1],hours_per_request=1)
    a.choice_probabilities.data[:]=2
    with pytest.raises(ValueError):fulfil_services([a],staff_hours=[100],hours_per_request=1)


def test_large_spare_budget_never_overflows_and_tiny_work_is_not_free():
    a=allocate_requests([[1]],[1e-100],[1])
    with np.errstate(over='raise'):
        result=fulfil_services([a],staff_hours=[1e300],hours_per_request=1)
    np.testing.assert_array_equal(result.origin_served,[[1e-100]])
    with pytest.raises(ValueError,match='numerical range'):
        fulfil_services([a],staff_hours=[1],hours_per_request=1e-300)
