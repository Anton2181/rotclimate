import numpy as np
import pytest

from polity.settlement_feedback import FeedbackInputs, CerealFeedback, collect_origins
from polity.sustained_presence import stored_collection


def model(*, potential=72000., listed=100., workers=1., hours=600., share=.5, population=100.):
    x = FeedbackInputs(np.array([population]), np.array([0]), np.array([potential]), np.array([1], np.uint16),
        np.array([listed]), np.array([listed / 4]), np.ones((12, 1), bool), np.array([100.]),
        np.array([False]), np.array([potential]))
    return CerealFeedback(x, transfer_fraction=share, hours_worker_year=hours, worker_fraction=workers,
        kcal_day=1., year_days=360., rural_store_days=360., export_store_days=360., destination_store_days=360.,
        loss_fraction_year=0., collection_fraction=1., retention=1., delay_bins=0,
        institutional_request=10., minimum_community=5.)


def test_new_origin_shipments_exactly_reproduce_the_existing_store_rule():
    rng = np.random.default_rng(8); food = rng.uniform(0, 100, (12, 7)); owner = np.array([0, 1, 1, 0, 2, 2, 2])
    access = rng.random((12, 7)) > .2
    args = dict(freight_capacity=np.array([30., 80., 60.]), retention=.95, delay_bins=1,
        store_days=365., loss_fraction_year=.05, year_days=365.)
    old = stored_collection(food, owner + 1, access, 3, collection_fraction=.1, **args)
    new = collect_origins(food, owner, access, 3, fraction=.1, **args)
    np.testing.assert_array_equal(new['departures'], old['departures'])
    np.testing.assert_array_equal(new['arrivals'], old['arrivals'])
    np.testing.assert_allclose(new['origin_departures'].sum(), new['departures'].sum())
    assert not np.any(new['origin_departures'][~access])


def test_transferring_people_changes_both_rural_meals_and_worker_hours():
    m = model(); a = m.evaluate(np.array([0.])); b = m.evaluate(np.array([40.]))
    assert b['rural'][0] == 60 and b['moved'][0] == 40
    assert b['rural_food'].year.needed[0] == 60 * 360
    assert b['work'].annual_hours_available[0] == .6 * a['work'].annual_hours_available[0]
    assert b['work'].reaping_hours_available[0] == .6 * a['work'].reaping_hours_available[0]


def test_finite_people_and_same_food_are_retained_in_the_final_plan():
    r = model().solve(scan_intervals=8, refinements=10)
    assert r['total'][0] == 50
    assert r['rural'][0] + r['plan'].total_people[0] == 100
    assert r['town_food'].unmet[0] == 0 and r['source_supported'][0]
    assert r['plan'].total_people[0] == r['allocation'].transferred_people[0]


def test_removing_workers_can_make_positive_relocation_infeasible():
    # Work limits grain to720 kcal per remaining person; a36,000 kcal total
    # diet is feasible only while at least50 workers remain. At80 moved,
    # only14,400 kcal can be produced, although rural meals themselves fall.
    m = model(potential=100000., listed=1e6, hours=720., share=.8)
    a = m.evaluate(np.array([20.])); b = m.evaluate(np.array([80.]))
    assert a['work'].produced_kcal[0] > b['work'].produced_kcal[0]
    assert a['feasible'][0] and not b['feasible'][0]
    solved = m.solve(scan_intervals=16, refinements=16)
    assert solved['total'][0] == pytest.approx(50., abs=.002)
    assert solved['feasible'][0]


def test_no_export_or_positive_town_is_certified_from_a_rural_deficit():
    r = model(potential=1000.).solve(scan_intervals=4, refinements=4)
    assert r['total'][0] == 0 and r['rural'][0] == 100
    assert r['rural_food'].year.unmet[0] > 0 and not r['source_supported'][0]
    assert r['flow']['origin_departures'].sum() == 0


def test_zero_transfer_is_not_rescued_by_food_or_a_minimum_request():
    r = model(share=0.).solve(scan_intervals=4, refinements=0)
    assert r['total'][0] == 0 and r['rural'][0] == 100


def test_input_arrays_are_not_changed_by_search():
    m = model(); before = {name: np.asarray(value).copy() for name, value in vars(m.x).items()}
    m.solve(scan_intervals=4, refinements=2)
    for name, value in before.items():
        np.testing.assert_array_equal(getattr(m.x, name), value)
