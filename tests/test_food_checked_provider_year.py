import numpy as np
import pytest

from polity.food_checked_provider_year import select_food_checked_provider_years

A=(0,0,1);B=(1,0,2);C=(2,0,3)


def run(**changes):
    args=dict(active=np.array([True]),baseline_complete=np.ones((12,1),bool),joint_complete=np.ones((12,1),bool),baseline_food=np.array([True]),joint_food=np.array([True]),
        baseline_tasks=[{A}],joint_tasks=[{A,B}],funded_tasks=[{A,B,C}]);args.update(changes);return select_food_checked_provider_years(**args)


def test_baseline_food_failure_recovers_only_from_joint_own_food_and_work():
    r=run(baseline_food=np.array([False]),joint_tasks=[{B}]);assert r.policy.tolist()==[1] and r.qualified.all()
    assert r.baseline_task_counts.tolist()==[0] and r.qualified_tasks==(frozenset({B}),)


def test_food_failed_joint_cannot_replace_a_qualified_baseline():
    r=run(joint_food=np.array([False]));assert r.policy.tolist()==[0] and r.qualified_tasks==(frozenset({A}),)
    assert r.selected_mandatory_complete.all() and r.selected_food_no_shortage.all()


def test_no_food_and_work_combination_across_conflicting_calendars():
    incomplete=np.ones((12,1),bool);incomplete[3,0]=False
    r=run(baseline_food=np.array([False]),joint_complete=incomplete)
    assert not r.qualified.any() and r.policy.tolist()==[0] and r.qualified_tasks==(frozenset(),)
    assert r.selected_mandatory_complete.all() and not r.selected_food_no_shortage.any()


def test_qualified_baseline_requires_strict_identity_superset_to_switch():
    r=run();assert r.policy.tolist()==[1] and r.qualified_tasks==(frozenset({A,B}),)
    r=run(joint_tasks=[{B,C}]);assert r.policy.tolist()==[0] and r.qualified_tasks==(frozenset({A}),)
    r=run(joint_tasks=[{A}]);assert r.policy.tolist()==[0]


def test_inactive_empty_obligations_and_unknown_food_flags_fail_closed():
    r=run(active=np.array([False]));assert not r.qualified.any() and not r.selected_mandatory_complete.any() and not r.selected_food_no_shortage.any()
    for changes in [dict(baseline_food=np.array([1])),dict(joint_food=np.array([[True]])),dict(baseline_complete=np.ones((11,1),bool))]:
        with pytest.raises(ValueError):run(**changes)


def test_input_flags_preserved_and_extra_unfunded_jobs_refused():
    food=np.array([False]);before=food.copy();run(baseline_food=food);np.testing.assert_array_equal(food,before)
    with pytest.raises(ValueError):run(joint_tasks=[{A,(3,0,99)}])
