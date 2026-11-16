import numpy as np
import pytest

from harvest.exact_crop_windows import exact_crop_windows,select_exact_windows
from scripts.land_people import crop_yield,CROPS


def flat(forbidden=None):
    climate=np.full((12,2),15,np.float32);rain=np.full_like(climate,100)
    pet=np.full((12,2),30.);soil=np.full_like(climate,50)
    crop=dict(CROPS['barley'],months=(3,4))
    return exact_crop_windows(climate,rain,pet,soil,np.array([.2,.7],np.float32),crop,forbidden=forbidden)


def test_original_first_best_energy_and_mask_are_exact():
    result=flat();T=np.full((12,2),15,np.float32);P=np.full_like(T,100);PET=np.full((12,2),30.);S=np.full_like(T,50)
    energy,mask=crop_yield(T,P,PET,S,np.array([.2,.7],np.float32),dict(CROPS['barley'],months=(3,4)))
    np.testing.assert_array_equal(result.energy,energy);np.testing.assert_array_equal(result.first_masks,mask)
    np.testing.assert_array_equal(np.flatnonzero(result.first_masks[:,0]),[0,1,2])


def test_calendar_extremes_preserve_first_length_start_tie_order():
    result=flat()
    assert np.all(result.boundary_bits==4095) and np.all(result.window_count==24)
    assert np.all(result.earliest_boundary==0) and np.all(result.latest_boundary==11)
    np.testing.assert_array_equal(np.flatnonzero(result.earliest_masks[:,0]),[9,10,11])
    np.testing.assert_array_equal(np.flatnonzero(result.latest_masks[:,0]),[8,9,10])


def test_one_ulp_lower_energy_is_not_a_tie():
    values=np.array([[1.],[np.nextafter(1.,2.)]])
    result=select_exact_windows(values,[(0,1),(5,1)],np.zeros((12,1),bool))
    assert result.window_count[0]==1 and result.boundary_bits[0]==1<<6
    assert result.earliest_boundary[0]==result.latest_boundary[0]==6


def test_flood_filter_excludes_growing_bins_but_not_the_next_boundary():
    forbidden=np.zeros((12,2),bool);forbidden[0]=True
    result=flat(forbidden)
    assert not result.first_eligible.any()
    assert np.all(result.window_count==17)
    assert np.all(result.earliest_boundary==0)
    assert not (result.earliest_masks&forbidden).any() and not (result.latest_masks&forbidden).any()


def test_all_forbidden_positive_windows_cannot_invent_a_date():
    with pytest.raises(ValueError):flat(np.ones((12,2),bool))


def test_zero_yield_does_not_acquire_a_calendar():
    result=select_exact_windows(np.zeros((2,1)),[(0,2),(4,3)],np.zeros((12,1),bool))
    assert result.boundary_bits[0]==0 and result.window_count[0]==0
    assert result.earliest_boundary[0]==result.latest_boundary[0]==-1
    assert not result.first_masks.any()
