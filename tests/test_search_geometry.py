import numpy as np
from scripts.audit_search_geometry import leave_start_out


def test_held_start_outcomes_cannot_change_their_own_predictions():
    rng=np.random.default_rng(8);x=rng.normal(size=(24,3));y=x@rng.normal(size=(3,2))
    starts=np.repeat([1,2,3],8)
    before=leave_start_out(x,y,starts)
    changed=y.copy();changed[starts==2]+=100
    after=leave_start_out(x,changed,starts)
    np.testing.assert_array_equal(before[1]['predicted_component_changes'],after[1]['predicted_component_changes'])
    assert before[1]['combined_mae']<.01 and after[1]['combined_mae']>99
