from dataclasses import asdict

import numpy as np
import pytest

from polity.earth_fixed_dispatch import fixed_dispatch_food
from polity.earth_storage_loss import fixed_storage_food, KCAL


def args(grain=3., blocked=False):
    return (np.array([[grain]])*KCAL, np.array([[6]]), np.array([1.]), np.array([.5]),
            np.full((4, 1), -1 if blocked else 0, int), np.full((4, 1), 0. if blocked else .8),
            np.zeros((4, 1, 1)))


def equal(actual, expected):
    for key, value in expected.items():
        if hasattr(value, 'stock_path'):
            for field, array in asdict(value).items():
                np.testing.assert_array_equal(asdict(actual[key])[field], array)
        else:
            np.testing.assert_array_equal(actual[key], value)


@pytest.mark.parametrize('loss', [.05, 0.])
def test_own_quota_controls_reproduce_all_original_food_fields(loss):
    common=dict(marketed_share=.5, reference_market=np.array([KCAL]), commercial_days=90, loss=loss)
    equal(fixed_dispatch_food(*args(), **common), fixed_storage_food(*args(), **common))


def test_explicit_own_reference_is_exactly_the_unchanged_control():
    common=dict(marketed_share=.5, reference_market=np.array([KCAL]), commercial_days=90, loss=0.)
    original=fixed_storage_food(*args(), **common)
    equal(fixed_dispatch_food(*args(), **common, dispatch_reference=original['marketed'].sum(0)), original)


def test_fixed_quota_changes_departure_request_without_resizing_capacity_or_grain():
    common=dict(marketed_share=.5, reference_market=np.array([KCAL]), commercial_days=90, loss=0.)
    original=fixed_storage_food(*args(), **common)
    new=fixed_dispatch_food(*args(), **common, dispatch_reference=np.array([.6*KCAL]))
    np.testing.assert_array_equal(new['marketed'], original['marketed'])
    np.testing.assert_array_equal(new['dispatch'], np.full((12, 1), .6*KCAL/12))
    assert np.max(new['export_food'].stock_path) <= KCAL*90/365
    assert new['departures'].sum() != original['departures'].sum()


def test_newly_marketable_zero_reference_origin_gets_no_quota_or_carried_stock():
    new=fixed_dispatch_food(*args(grain=1.01), marketed_share=.5, reference_market=np.zeros(1),
                            commercial_days=90, loss=0., dispatch_reference=np.zeros(1))
    assert new['marketed'].sum()>0
    assert new['dispatch'].sum()==new['departures'].sum()==new['export_food'].stock_path.sum()==0


def test_blocked_routes_still_block_explicit_quotas():
    new=fixed_dispatch_food(*args(blocked=True), marketed_share=.5, reference_market=np.array([KCAL]),
                            commercial_days=90, loss=0., dispatch_reference=np.array([KCAL]))
    assert new['dispatch'].sum()==new['direct'].sum()==new['town_food'].consumed.sum()==0


@pytest.mark.parametrize('invalid', [np.array([-1.]), np.array([np.nan]), np.array([1., 2.]), np.array(1.)])
def test_invalid_dispatch_reference_is_rejected(invalid):
    with pytest.raises(ValueError):
        fixed_dispatch_food(*args(), marketed_share=.5, reference_market=np.array([KCAL]),
                            commercial_days=90, loss=0., dispatch_reference=invalid)
