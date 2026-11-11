import numpy as np
import pytest

from polity.observed_role_contrast import match_full_grid,cell_class_summary,context_auc


def test_nearest_water_cell_is_not_rescued_to_a_distant_land_cell():
    index,status=match_full_grid([50.],[0.],[[50.,50.]],[[0.,1.]],[[False,True]],[[False,True]],[True])
    assert index.tolist()==[0] and status.tolist()==[2]


def test_window_and_permission_failures_remain_explicit():
    index,status=match_full_grid([50.,50.],[0.,1.],[[50.,50.]],[[0.,1.]],[[True,True]],[[True,False]],[False,True])
    assert index.tolist()==[0,1] and status.tolist()==[1,3]


def test_repeated_records_do_not_add_cell_mass_and_mixed_cells_are_retained():
    result=cell_class_summary([1,1,1,2,3],[0,0,1,1,0],[0,0,0,0,2])
    assert result['included_records']=={'0':2,'1':2}
    assert result['represented_cell_class_units']=={'0':1,'1':2}
    assert result['mixed_cells']==1 and result['represented_cells']==2
    assert not result['preparation_gate_passed']


def test_missing_coordinates_and_unknown_context_classes_fail():
    with pytest.raises(ValueError,match='Finite'):
        match_full_grid([np.nan],[0.],[[50.]],[[0.]],[[True]],[[True]],[True])
    with pytest.raises(ValueError,match='binary'):
        cell_class_summary([0],[2],[0])


def test_rank_contrast_handles_perfect_reversed_and_tied_predictors():
    index=[0,1,2,3];classes=[0,0,1,1];status=[0]*4
    assert context_auc(index,classes,status,[0,0,1,1])['AUC']==1
    assert context_auc(index,classes,status,[1,1,0,0])['AUC']==0
    assert context_auc(index,classes,status,[1,1,1,1])['AUC']==.5


def test_duplicated_records_do_not_change_auc_and_mixed_units_are_not_dropped():
    before=context_auc([0,0,1],[0,1,1],[0,0,0],[0,1])
    after=context_auc([0,0,0,0,1],[0,0,0,1,1],[0]*5,[0,1])
    assert before['AUC']==after['AUC']==.75
    assert before['mixed_cells']==after['mixed_cells']==1
    assert context_auc([0],[0],[0],[1])['AUC'] is None
