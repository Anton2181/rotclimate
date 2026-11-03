import numpy as np
import pytest

from harvest.upland_food import UplandSeason,upland_food_year


def season(crop,start,duration,energy):
    return UplandSeason(crop,start,duration,energy,1.,1.,.55)


def test_each_supplied_crop_uses_its_own_water_budget_without_half_weighting():
    seasons=[season('wheat',0,100,200),season('millet',150,100,300)]
    r=upland_food_year(np.full(365,5.),np.ones(365),seasons,total_available=100,
        fallow_coefficient=.2,fallow_depletion_fraction=.55,minimum_et_ratio=.5)
    np.testing.assert_allclose(r.harvest.sum(),500)
    assert r.harvest[100]==200 and r.harvest[250]==300
    assert abs(r.water.ledger_residual)<1e-7


def test_dry_field_does_not_receive_an_extrapolated_food_harvest():
    with pytest.raises(ValueError,match='analysis domain'):
        upland_food_year(np.zeros(365),np.ones(365),[season('wheat',0,100,200)],
            total_available=100,fallow_coefficient=.2,fallow_depletion_fraction=.55,minimum_et_ratio=.5)


def test_same_field_cannot_hold_overlapping_crops_or_ponded_rice():
    options=dict(total_available=100,fallow_coefficient=.2,fallow_depletion_fraction=.55,minimum_et_ratio=.5)
    for crops in [[season('wheat',0,100,200),season('millet',90,100,300)],[season('rice',0,100,200)]]:
        with pytest.raises(ValueError):upland_food_year(np.ones(365),np.ones(365),crops,**options)
