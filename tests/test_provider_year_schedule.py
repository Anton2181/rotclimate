import numpy as np
import pytest

from polity.provider_year_schedule import select_provider_years


A = (0, 0, 1); B = (1, 0, 2); C = (2, 0, 3)


def run(**changes):
    args = dict(active=np.array([True]), baseline_complete=np.ones((12, 1), bool), joint_complete=np.ones((12, 1), bool),
        baseline_tasks=[{A}], joint_tasks=[{A, B}], funded_tasks=[{A, B, C}])
    args.update(changes); return select_provider_years(**args)


def test_strict_task_superset_selects_one_joint_year():
    r = run(); assert r.policy.tolist() == [1] and r.mandatory_complete.all()
    assert r.qualified_tasks == (frozenset([A, B]),) and r.added_task_counts.tolist() == [1]


def test_more_tasks_with_lost_baseline_identity_cannot_replace_year():
    r = run(joint_tasks=[{B, C}]); assert r.policy.tolist() == [0]
    assert r.qualified_tasks == (frozenset([A]),) and r.joint_rejected_lost_tasks.all()


def test_equal_task_sets_and_incomplete_joint_year_keep_baseline():
    assert run(joint_tasks=[{A}]).policy.tolist() == [0]
    incomplete = np.ones((12, 1), bool); incomplete[11, 0] = False
    r = run(joint_complete=incomplete); assert r.policy.tolist() == [0] and r.qualified_tasks[0] == frozenset([A])


def test_baseline_failure_can_recover_from_a_complete_joint_year():
    incomplete = np.ones((12, 1), bool); incomplete[5, 0] = False
    r = run(baseline_complete=incomplete); assert r.policy.tolist() == [1]
    assert r.baseline_task_counts.tolist() == [0] and r.added_task_counts.tolist() == [2]


def test_neither_year_complete_is_not_repaired_by_mixing_bins():
    base = np.ones((12, 1), bool); base[0, 0] = False
    joint = np.ones((12, 1), bool); joint[1, 0] = False
    assert (base | joint).all()
    r = run(baseline_complete=base, joint_complete=joint)
    assert r.policy.tolist() == [0] and not r.mandatory_complete.any() and r.qualified_tasks == (frozenset(),)


def test_inactive_or_unknown_context_cannot_pass_empty_obligations():
    r = run(active=np.array([False])); assert not r.mandatory_complete.any() and not r.qualified_tasks[0]


def test_task_additions_must_already_have_an_original_funded_job():
    with pytest.raises(ValueError, match='outside'): run(joint_tasks=[{A, (3, 0, 99)}])


def test_task_identity_types_and_twelve_bin_shapes_are_checked():
    for changes in [dict(joint_complete=np.ones((11, 1), bool)), dict(active=np.array([1])),
                    dict(joint_tasks=[[(0, 0, 1), (0, 0, 1)]]), dict(joint_tasks=[[(12, 0, 1)]]), dict(joint_tasks=[[(False, 0, 1)]])]:
        with pytest.raises(ValueError): run(**changes)


def test_inputs_are_preserved_and_provider_choices_are_independent():
    base = np.ones((12, 2), bool); joint = base.copy(); base[0, 1] = False
    old = base.copy(); tasks = [{A}, {B}]
    r = run(active=np.ones(2, bool), baseline_complete=base, joint_complete=joint,
        baseline_tasks=tasks, joint_tasks=[{A}, {B, C}], funded_tasks=[{A}, {B, C}])
    assert r.policy.tolist() == [0, 1] and r.qualified_tasks == (frozenset([A]), frozenset([B, C]))
    np.testing.assert_array_equal(base, old); assert tasks == [{A}, {B}]
