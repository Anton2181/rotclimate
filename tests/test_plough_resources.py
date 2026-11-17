import numpy as np
import pytest

from harvest.plough_resources import plan_plough_package


def inputs(**changes):
    result = dict(origin_id='origin-A', maximum_package_hectares=10.,
        human_hours_per_hectare=4., operator_hours_per_hectare=2.,
        draft_team_hours_per_hectare=3., allowed=[True], available_hours=[[20., 6., 9.]])
    result.update(changes)
    return result


def test_analytical_completion_and_operator_subset_not_extra_people():
    p = plan_plough_package(**inputs())
    assert p.completed_hectares == pytest.approx(3.)
    np.testing.assert_allclose(p.resource_hours_used, [[12., 6., 9.]])
    np.testing.assert_allclose(p.unused_resource_hours, [[8., 0., 0.]])
    assert p.origin_id == 'origin-A'
    assert p.resource_names == ('total_human', 'qualified_operator_subset', 'draft_team')
    assert p.scope == 'plough_package_only' and p.complete_crop_activity is False
    assert not hasattr(p, 'output') and not hasattr(p, 'grain')


@pytest.mark.parametrize(('availability', 'area'), [
    ([[8., 8., 100.]], 2.),       # human time
    ([[100., 4., 100.]], 2.),    # qualified operator subset
    ([[100., 100., 3.]], 1.),    # independent draft service
    ([[100., 100., 0.]], 0.),    # no team supplied
])
def test_each_required_resource_can_bind(availability, area):
    p = plan_plough_package(**inputs(available_hours=availability))
    assert p.completed_hectares == pytest.approx(area)


def test_operator_and_team_in_different_periods_cannot_be_combined():
    p = plan_plough_package(**inputs(allowed=[True, True],
        available_hours=[[20., 20., 0.], [20., 0., 30.]]))
    assert p.completed_hectares == 0


def test_other_duties_reduce_the_shared_net_human_budget():
    # A supplied20-hour human budget with12 hours already committed leaves8.
    p = plan_plough_package(**inputs(available_hours=[[20. - 12., 4., 100.]]))
    assert p.completed_hectares == pytest.approx(2.)
    assert p.resource_hours_used[0, 0] + 12. == pytest.approx(20.)


def test_hours_outside_the_window_do_not_complete_the_package():
    p = plan_plough_package(**inputs(allowed=[False, True],
        available_hours=[[100., 100., 100.], [0., 0., 0.]]))
    assert p.completed_hectares == 0


def test_calendar_origin_and_time_unit_rescaling_preserve_completion():
    available = np.array([[4., 2., 3.], [0., 0., 0.], [8., 4., 6.]])
    mask = np.array([True, False, True])
    p = plan_plough_package(**inputs(available_hours=available, allowed=mask))
    shifted = plan_plough_package(**inputs(available_hours=np.roll(available, 1, axis=0), allowed=np.roll(mask, 1)))
    scaled = plan_plough_package(**inputs(available_hours=available * 2, allowed=mask,
        human_hours_per_hectare=8., operator_hours_per_hectare=4., draft_team_hours_per_hectare=6.))
    assert p.completed_hectares == shifted.completed_hectares == scaled.completed_hectares == pytest.approx(3.)


def test_zero_land_and_fractional_area_are_explicit():
    assert plan_plough_package(**inputs(maximum_package_hectares=0)).completed_hectares == 0
    p = plan_plough_package(**inputs(origin_id=0, maximum_package_hectares=1.5))
    assert p.origin_id == 0 and p.completed_hectares == pytest.approx(1.5)


def test_missing_draft_definition_has_no_default():
    supplied = inputs(); del supplied['draft_team_hours_per_hectare']
    with pytest.raises(TypeError): plan_plough_package(**supplied)


@pytest.mark.parametrize('changes', [
    {'draft_team_hours_per_hectare': None}, {'draft_team_hours_per_hectare': 0},
    {'operator_hours_per_hectare': 0}, {'human_hours_per_hectare': -1},
    {'operator_hours_per_hectare': 5}, {'human_hours_per_hectare': True},
    {'draft_team_hours_per_hectare': np.inf}, {'operator_hours_per_hectare': [2]},
    {'maximum_package_hectares': -1}, {'maximum_package_hectares': np.nan},
    {'available_hours': [[3, 4, 10]]}, {'available_hours': [[20, 6]]},
    {'available_hours': None}, {'available_hours': [[20, 6, -1]]},
    {'available_hours': [[20, np.nan, 9]]}, {'allowed': [1]},
    {'allowed': [False]}, {'allowed': [True, True]},
    {'origin_id': ''}, {'origin_id': True}, {'origin_id': ['A', 'B']},
])
def test_missing_or_incompatible_resource_contract_is_rejected(changes):
    with pytest.raises(ValueError): plan_plough_package(**inputs(**changes))
