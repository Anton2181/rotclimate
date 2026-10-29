import numpy as np
import pytest
from rotclimate.rainfall_validation import aggregate_footprints,rainfall_metrics


def test_centered_footprint_includes_half_cells_instead_of_shifted_block():
    field=np.zeros((9,9));field[2,2]=16
    result=aggregate_footprints(field,np.ones_like(field,dtype=bool),np.ones_like(field),stride=4)
    # Center(4,4) integrates half of pixel2 along each dimension:16*.25/16.
    assert result['mean'][1,1]==.25
    assert result['valid_area_km2'][1,1]==16 and result['coverage'][1,1]==1
    constant=aggregate_footprints(np.full((2,9,9),3.),np.ones((9,9),bool),np.ones((9,9)),stride=4)
    np.testing.assert_allclose(constant['mean'],3.)


def test_land_only_means_keep_actual_area_and_do_not_treat_missing_sea_as_zero():
    field=np.full((9,9),np.nan);valid=np.zeros((9,9),bool);valid[4,4]=True;field[4,4]=7.;area=np.ones((9,9));area[4,4]=3.
    r=aggregate_footprints(field,valid,area,stride=4)
    assert r['mean'][1,1]==7 and r['valid_area_km2'][1,1]==3
    assert r['coverage'][1,1]==3/18
    field[4,4]=np.nan
    with pytest.raises(ValueError):aggregate_footprints(field,valid,area,stride=4)


def test_scoring_rejects_missing_scored_cells_instead_of_improving_by_dropping_them():
    m=np.array([True,True,False]);sim=np.array([1.,3.,np.nan]);obs=np.array([2.,2.,np.nan]);area=np.array([1.,3.,np.nan])
    r=rainfall_metrics(sim,obs,area,m)
    assert r['mae_mm_day']==1 and r['rmse_mm_day']==1 and r['bias_mm_day']==.5
    sim[1]=np.nan
    with pytest.raises(ValueError):rainfall_metrics(sim,obs,area,m)
    with pytest.raises(ValueError):rainfall_metrics(obs,obs,area,np.zeros(3,bool))


def test_initialization_uncertainty_cannot_cancel_by_averaging_predictions_before_scoring():
    observed=np.array([2.,2.]);area=np.ones(2);mask=np.ones(2,bool);wet=np.full(2,4.);dry=np.zeros(2)
    branch_mean=(rainfall_metrics(wet,observed,area,mask)['mae_mm_day']+rainfall_metrics(dry,observed,area,mask)['mae_mm_day'])/2
    cancelled=rainfall_metrics((wet+dry)/2,observed,area,mask)['mae_mm_day']
    assert branch_mean==2 and cancelled==0
