import numpy as np
import pytest
from harvest.work_maps import cereal_work,tied_harvest_boundaries,boundary_count
from harvest.crop_sequences import CropWindow,CropCatalogue
from harvest.labour import FarmOperation,minimum_farm_work


def test_work_units_and_food_balance_match_unconstrained_farm_planner():
    energy=np.array([[100.,200.],[150.,100.]])
    result=cereal_work(energy,[10.,20.],[2.,4.],food_target=300.)
    assert result.hours==pytest.approx([30.,15.])
    assert result.land==pytest.approx([3.,1.5])
    assert result.reaping==pytest.approx([6.,3.])
    for i in range(2):
        p=minimum_farm_work(energy[:,i],[FarmOperation('A',0,[True],[10.]),FarmOperation('B',1,[True],[20.])],
            required_output=300.,land_hectares=100,available_hours=[[1000.]])
        assert p.resource_hours_used.sum()==pytest.approx(result.hours[i])


def test_missing_output_is_unavailable_and_one_available_crop_is_used():
    r=cereal_work([[0.,0.],[0.,100.]],[10.,20.],[2.,4.],food_target=100.)
    assert np.isnan(r.hours[0]) and np.isnan(r.land[0]) and r.crop[0]==0
    assert r.hours[1]==20 and r.crop[1]==2


def test_more_food_scales_work_and_area_but_not_crop():
    a=cereal_work([[100.],[150.]],[10.,20.],[2.,4.],food_target=100.)
    b=cereal_work([[100.],[150.]],[10.,20.],[2.,4.],food_target=300.)
    assert b.hours==pytest.approx(3*a.hours) and b.land==pytest.approx(3*a.land)
    np.testing.assert_array_equal(a.crop,b.crop)


def test_work_choice_is_not_independent_land_minimum():
    r=cereal_work([[100.],[150.]],[10.,20.],[2.,4.],food_target=150.)
    assert r.crop[0]==1 and r.land[0]==1.5  # land-minimum would be barley, 1 ha


def test_harvest_ties_keep_every_boundary_but_not_duplicate_counts():
    windows=[CropWindow('barley',0,3),CropWindow('barley',11,4),CropWindow('barley',3,3)]
    cat=CropCatalogue(windows,[[10.,0.],[10.,0.],[10.,0.]])
    best,mask=tied_harvest_boundaries(cat)
    assert best==pytest.approx([10,0])
    assert mask.tolist()==[(1<<3)|(1<<6),0]
    assert boundary_count(mask).tolist()==[2,0]
    shifted=CropCatalogue([CropWindow(w.crop,(w.start+2)%12,w.length) for w in windows],cat.energy)
    _,shiftmask=tied_harvest_boundaries(shifted)
    assert shiftmask.tolist()==[(1<<5)|(1<<8),0]


@pytest.mark.parametrize('energy,hours,reap,target',[
    ([[1],[np.nan]],[1,2],[1,1],100),([[-1],[1]],[1,2],[1,1],100),
    ([[1],[1]],[0,2],[1,1],100),([[1],[1]],[1,2],[2,1],100),
    ([[1],[1]],[1,2],[1,1],0),([[1]],[1,2],[1,1],100),
])
def test_bad_units_or_inputs_rejected(energy,hours,reap,target):
    with pytest.raises(ValueError):cereal_work(energy,hours,reap,food_target=target)


@pytest.mark.parametrize('mask',[[-1],[4096],[1.5]])
def test_invalid_harvest_mask_rejected(mask):
    with pytest.raises(ValueError):boundary_count(mask)
