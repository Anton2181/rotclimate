import numpy as np
import pytest

from polity.settlement_residents import allocate_residents, audit_origin_food


def allocate(population, owners, request, *, fraction=1., food_people=1000., affiliated=None):
    n = len(request)
    return allocate_residents(np.broadcast_to(np.asarray(food_people) * 30., (12, n)),
        population, np.array(owners, int), request, np.ones(n, bool) if affiliated is None else affiliated,
        transfer_fraction=fraction, institutional_request=10., minimum_community=5.,
        kcal_day=1., year_days=360., store_days=360., loss_fraction_year=0.)


def test_civilians_and_staff_share_one_origin_budget_not_extra_people():
    result = allocate([100., 60., 25.], [0, 0, -1], [1000.], fraction=.25)
    assert result.destination_budget[0] == 40
    assert result.settlement.institutional_people[0] == 10
    assert result.settlement.civilian_people[0] == 30
    np.testing.assert_allclose(result.transferred_people, [25, 15, 0])
    np.testing.assert_allclose(result.rural_people, [75, 45, 25])
    assert result.rural_people.sum() + result.settlement.total_people.sum() == 185


def test_empty_and_tiny_origins_cannot_fund_cohort_or_minimum_town():
    r = allocate([0., 3.], [0, 1], [100., 100.])
    np.testing.assert_allclose(r.settlement.total_people, [0, 3])
    assert not r.settlement.institutional_active.any()
    assert not r.settlement.community_viable.any()


def test_food_shortfall_returns_unused_people_to_their_origins():
    r = allocate([100., 60.], [0, 0], [1000.], fraction=.5, food_people=20.)
    assert r.settlement.total_people[0] == pytest.approx(20, rel=1e-6)
    np.testing.assert_allclose(r.rural_people, [87.5, 52.5], rtol=1e-6)
    assert r.rural_people.sum() + r.settlement.total_people.sum() == pytest.approx(160)


def test_unknown_affiliation_retains_population_without_inventing_staff():
    r = allocate([100.], [0], [100.], fraction=.5, affiliated=[False])
    assert r.settlement.civilian_people[0] == 50 and r.settlement.institutional_people[0] == 0


def test_no_spare_capacity_creates_more_than_requested_civilians_and_cohort():
    r = allocate([1000.], [0], [25.])
    assert r.settlement.total_people[0] == 35 and r.rural_people[0] == 965


def test_coupled_rural_and_town_meals_conserve_people_and_source_grain():
    r = allocate([100.], [0], [100.], fraction=.2, food_people=20.)
    # Full ration for 80 rural +20 town people. Both draw from this 100-person
    # source harvest; moving to town does not leave a second rural meal claim.
    audit = audit_origin_food(r, np.full((12, 1), 100 * 30.), np.full((12, 1), 20 * 30.),
        origin_capacity_kcal=[36000.], retention=1., delay_bins=0, loss_fraction_year=0.)
    assert audit['rural_people'] + audit['settlement_people'] == pytest.approx(100)
    assert audit['rural_meals_kcal'] + audit['destination_meals_kcal'] == pytest.approx(36000)
    assert abs(audit['joint_residual_kcal']) < 1e-6


def test_destination_food_cannot_steal_the_remaining_rural_meals():
    r = allocate([100.], [0], [100.], fraction=.2, food_people=20.)
    with pytest.raises(ValueError, match='cannot coexist'):
        audit_origin_food(r, np.full((12, 1), 90 * 30.), np.full((12, 1), 20 * 30.),
            origin_capacity_kcal=[36000.], retention=1., delay_bins=0, loss_fraction_year=0.)


def test_origin_shipments_must_match_destinations_including_delay_and_loss():
    food = np.zeros((12, 1)); food[4] = 7200.
    r = allocate_residents(food, [100.], np.array([0]), [100.], [False], transfer_fraction=.2,
        kcal_day=1, year_days=360, store_days=360, loss_fraction_year=0)
    shipped = np.zeros_like(food); shipped[3] = 8000
    audit = audit_origin_food(r, np.full((12, 1), 5000.), shipped, origin_capacity_kcal=[60000],
        retention=.9, delay_bins=1, loss_fraction_year=0.)
    assert audit['transport_loss_kcal'] == pytest.approx(800.)
    with pytest.raises(ValueError, match='do not match'):
        audit_origin_food(r, np.full((12, 1), 5000.), shipped, origin_capacity_kcal=[60000],
            retention=1., delay_bins=1, loss_fraction_year=0.)


@pytest.mark.parametrize('population,owners,fraction', [([-1.], [0], 1.), ([np.nan], [0], 1.),
    ([100.], [2], 1.), ([100.], [-2], 1.), ([100.], [0], 1.1), ([100.], [0], -.1)])
def test_invalid_origin_budgets_are_rejected(population, owners, fraction):
    with pytest.raises(ValueError):
        allocate(population, owners, [100.], fraction=fraction)


def test_input_people_requests_and_food_are_not_mutated():
    people = np.array([100., 50.]); owners = np.array([0, -1]); request = np.array([100.])
    food = np.full((12, 1), 900.)
    originals = [a.copy() for a in (people, owners, request, food)]
    allocate_residents(food, people, owners, request, [True], transfer_fraction=.1)
    for actual, expected in zip((people, owners, request, food), originals):
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize('field', ['rural_people', 'transferred_people', 'arrivals'])
def test_source_food_audit_rejects_changed_population_or_destination_records(field):
    r = allocate([100.], [0], [100.], fraction=.2, food_people=20.)
    getattr(r, field).flat[0] += 1.
    with pytest.raises(ValueError):
        audit_origin_food(r, np.full((12, 1), 100 * 30.), np.full((12, 1), 20 * 30.),
            origin_capacity_kcal=[36000.], retention=1., delay_bins=0, loss_fraction_year=0.)


def test_huge_exports_cannot_hide_rural_meals_in_floating_point_roundoff():
    r = allocate([1.], [0], [1.], fraction=0., food_people=1e20 / 30)
    with pytest.raises(ValueError, match='numerical range'):
        audit_origin_food(r, np.full((12, 1), 1e20), np.full((12, 1), 1e20),
            origin_capacity_kcal=[0.], retention=1., delay_bins=0, loss_fraction_year=0.)
