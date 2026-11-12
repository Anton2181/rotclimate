import numpy as np
from polity.settlement_feedback import FeedbackInputs, CerealFeedback
from polity.settlement_dispatch import DispatchFeedback
from polity.settlement_residents import audit_origin_food


def fixture(*, staff_hours=600., share=.5, opened=None):
    x = FeedbackInputs(np.array([100.]), np.array([0]), np.array([72000.]), np.array([1], np.uint16),
        np.array([100.]), np.array([25.]), np.ones((12, 1), bool), np.array([100.]), np.array([True]), np.array([72000.]))
    options = dict(transfer_fraction=share, hours_worker_year=600, worker_fraction=1., kcal_day=1., year_days=360.,
        rural_store_days=360., export_store_days=360., destination_store_days=90., loss_fraction_year=0.,
        collection_fraction=1., retention=1., delay_bins=0, institutional_request=10., minimum_community=5.)
    return DispatchFeedback(x, outward_days=np.ones((12, 1)), inward_days=np.ones((12, 1)), load_kcal=6000.,
        monthly_open=np.ones(12, bool) if opened is None else opened, staff_hours_year=staff_hours, **options), CerealFeedback(x, **options)


def test_smaller_dispatch_keeps_people_fed_and_source_inventory_balanced():
    m, old = fixture(); result = m.solve(scan_intervals=4, refinements=4)
    assert result['total'][0] == 50 and result['staff'][0] == 10
    assert result['flow']['origin_departures'].sum() < old.evaluate(np.array([50.]))['flow']['origin_departures'].sum()
    assert result['town_food'].unmet[0] < 1e-5 and result['collection_hours'].max() <= 10 * 600 / 12
    audit = audit_origin_food(result['allocation'], result['rural_food'].harvest, result['flow']['origin_departures'],
        origin_capacity_kcal=result['rural_food'].year.needed + result['flow']['export_capacity'],
        retention=1., delay_bins=0, loss_fraction_year=0.)
    assert audit['source_food_feasible'] and abs(audit['joint_residual_kcal']) < 1e-5


def test_insufficient_work_refuses_food_instead_of_reusing_unfunded_shipments():
    m, old = fixture(staff_hours=12.)
    assert old.evaluate(np.array([50.]))['feasible'][0]
    assert not m.evaluate(np.array([50.]))['feasible'][0]
    result = m.solve(scan_intervals=4, refinements=4)
    assert result['total'][0] == 0 and not result['flow']['origin_departures'].any()
    assert result['rural'][0] == 100


def test_closed_months_cannot_borrow_hours_or_ninety_day_food_from_other_bins():
    opened = np.ones(12, bool); opened[6:10] = False
    m, _ = fixture(opened=opened)
    trial = m.evaluate(np.array([50.]))
    assert not trial['flow']['origin_departures'][6:10].any()
    assert not trial['feasible'][0]


def test_zero_transfer_and_zero_staff_are_not_rescued_by_an_oversupply():
    m, _ = fixture(share=0.)
    result = m.solve(scan_intervals=4, refinements=0)
    assert not result['total'].any() and not result['flow']['origin_departures'].any()
    m, _ = fixture(); m.x.affiliated[:] = False
    result = m.solve(scan_intervals=4, refinements=0)
    assert not result['total'].any() and not result['flow']['origin_departures'].any()


def test_search_leaves_original_population_crop_and_path_inputs_unchanged():
    m, _ = fixture(); before = {k: np.array(v, copy=True) for k, v in vars(m.x).items()}
    m.solve(scan_intervals=4, refinements=2)
    for k, v in before.items():
        np.testing.assert_array_equal(getattr(m.x, k), v)
