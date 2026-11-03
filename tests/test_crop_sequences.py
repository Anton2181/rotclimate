import numpy as np
import pytest

from harvest.crop_sequences import (CropCatalogue, CropWindow, crop_windows,
                                    optimize_sequences, sequence_candidates)
from scripts.land_people import CROPS, crop_yield


def catalogue(windows, energy):
    return CropCatalogue(tuple(CropWindow(*w) for w in windows), np.asarray(energy, float))


def test_joint_choice_can_sacrifice_individual_best_to_improve_annual_pair():
    c=catalogue([('a',0,6),('a',0,3),('b',3,3)],[10,9,8])
    r=optimize_sequences(c,True)
    assert r.energy==13 and r.first==1 and r.second==2 and r.optimal_count==1
    np.testing.assert_array_equal(np.flatnonzero(r.harvest_boundaries_possible),[3,6])


def test_all_tied_calendars_are_retained_without_claiming_one_harvest_date():
    c=catalogue([('a',0,3),('a',6,3)],[10,10])
    r=optimize_sequences(c,True)
    assert r.energy==10 and r.optimal_count==2
    np.testing.assert_array_equal(np.flatnonzero(r.harvest_boundaries_possible),[3,9])


def test_turnaround_is_enforced_at_both_crop_boundaries_including_year_wrap():
    c=catalogue([('a',9,3),('b',0,3)],[10,8])
    assert optimize_sequences(c,True).energy==14
    assert optimize_sequences(c,True,turnaround=1).energy==10
    # A gap after a alone is insufficient: the other gap wraps into a.
    c=catalogue([('a',1,3),('b',6,7)],[10,8])
    assert optimize_sequences(c,True).energy==14
    assert optimize_sequences(c,True,turnaround=1).energy==10


def test_water_gate_same_crop_policy_and_perennial_exclusion_are_explicit():
    c=catalogue([('a',0,3),('a',6,3)],[[10,10],[8,8]])
    np.testing.assert_array_equal(optimize_sequences(c,[True,False]).energy,[10,10])
    np.testing.assert_array_equal(optimize_sequences(c,[True,False],allow_same_crop=True).energy,[14,10])
    r=optimize_sequences(c,[True,True],perennial_energy=[20,0])
    assert r.first[0]==-2 and r.second[0]==-1 and r.perennial_possible[0]
    assert not r.harvest_boundaries_possible[:,0].any()


def test_zero_yield_and_ineligible_pairs_do_not_manufacture_calendars():
    r=optimize_sequences(catalogue([('a',0,3),('b',6,3)],[0,0]),True)
    assert r.energy==r.optimal_count==0 and r.first==r.second==-1
    assert not r.harvest_boundaries_possible.any()


def test_rotation_and_option_order_preserve_optimum_count_and_timing_union():
    c=catalogue([('a',10,3),('a',4,3),('b',1,3),('b',7,3)],[10,10,8,8])
    r=optimize_sequences(c,True)
    for shift in range(12):
        windows=tuple(CropWindow(w.crop,(w.start+shift)%12,w.length) for w in c.windows[::-1])
        shifted=optimize_sequences(CropCatalogue(windows,c.energy[::-1]),True)
        assert shifted.energy==r.energy and shifted.optimal_count==r.optimal_count
        np.testing.assert_array_equal(shifted.harvest_boundaries_possible,np.roll(r.harvest_boundaries_possible,shift))


def test_enumerated_single_crop_maxima_exactly_reproduce_production_response():
    rng=np.random.default_rng(302)
    t=rng.uniform(-5,35,(12,8));p=rng.uniform(0,150,(12,8));pet=rng.uniform(10,200,(12,8));soil=rng.uniform(0,100,(12,8))
    irr=rng.random(8).astype(np.float32);keep=rng.random(8);rain_keep=rng.random(8)
    c=crop_windows(t,p,pet,soil,irr,keep=keep,rain_keep=rain_keep)
    for name,spec in CROPS.items():
        expected,_=crop_yield(t,p,pet,soil,irr,spec,rain_keep,keep)
        actual=c.energy[[w.crop==name for w in c.windows]].max(0)
        np.testing.assert_array_equal(actual,expected)


def test_full_weight_pair_is_not_counted_twice_and_overlap_is_forbidden():
    c=catalogue([('a',0,3),('b',6,3)],[10,8])
    r=optimize_sequences(c,True,secondary_weight=1)
    assert r.energy==18 and r.optimal_count==1
    c=catalogue([('a',0,6),('b',5,3)],[10,8])
    assert optimize_sequences(c,True).energy==10


@pytest.mark.parametrize('policy',[{'turnaround':-.5},{'turnaround':1.0},{'turnaround':13},{'secondary_weight':0},{'secondary_weight':1.1}])
def test_invalid_sequence_policy_is_rejected(policy):
    with pytest.raises(ValueError):list(sequence_candidates(catalogue([('a',0,3)],[10]),True,**policy))


@pytest.mark.parametrize('start,length',[(0.,3),(0,3.),(-1,3),(12,3),(0,13)])
def test_invalid_window_bins_are_rejected(start,length):
    with pytest.raises(ValueError):CropWindow('a',start,length)


def test_duplicate_windows_cannot_inflate_optimal_schedule_counts():
    with pytest.raises(ValueError,match='Duplicate'):
        catalogue([('a',0,3),('a',0,3)],[10,10])


def test_warm_wet_and_irrigated_crop_responses_include_nonzero_rice_and_cereals():
    t=np.broadcast_to([18.,20.,27.,32.],(12,4));p=np.broadcast_to([60.,120.,20.,160.],(12,4))
    pet=np.full((12,4),100.);soil=np.full((12,4),40.);irr=np.array([0.,.2,1.,.7],dtype=np.float32)
    c=crop_windows(t,p,pet,soil,irr)
    for name,spec in CROPS.items():
        expected,_=crop_yield(t,p,pet,soil,irr,spec)
        assert expected.max()>0
        np.testing.assert_array_equal(c.energy[[w.crop==name for w in c.windows]].max(0),expected)
