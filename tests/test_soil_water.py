import numpy as np
import pytest

from harvest.soil_water import available_water,periodic_soil_water,soil_water_year


def test_reproduces_fao56_published_example37_daily_depletion_table():
    # FAO56 chapter8: tomato, fixed p=.40, TAW160mm, initial depletion55mm.
    # This is a numerical benchmark, not a proposed 200AD tomato crop.
    taw=available_water(.32,.12,.8)
    r=soil_water_year(np.zeros(10),np.full(10,5.),1.2,total_available=taw,
        depletion_fraction=.4,initial_stored=taw-55,record=True)
    np.testing.assert_allclose(r.depletion_path[1:],[61,67,72.8,78.3,83.4,88.2,92.6,96.9,100.8,104.5],atol=.06)
    assert abs(r.ledger_residual)<1e-10


def test_running_crop_sequence_matches_continuation_without_sowing_refill():
    rain=np.zeros(60);rain[:5]=10;kc=np.r_[np.full(30,.8),np.full(30,1.)]
    kw=dict(total_available=100.,depletion_fraction=.55)
    full=soil_water_year(rain,np.full(60,4),kc,initial_stored=50,**kw)
    first=soil_water_year(rain[:30],np.full(30,4),kc[:30],initial_stored=50,**kw)
    second=soil_water_year(rain[30:],np.full(30,4),kc[30:],initial_stored=first.final_stored,**kw)
    np.testing.assert_allclose(full.final_stored,second.final_stored)
    np.testing.assert_allclose(full.evapotranspiration,first.evapotranspiration+second.evapotranspiration)
    artificial=soil_water_year(rain[30:],np.full(30,4),kc[30:],initial_stored=100,**kw)
    assert artificial.evapotranspiration>second.evapotranspiration


def test_finite_irrigation_runoff_and_drainage_close_one_ledger():
    r=soil_water_year([20,0],[2,2],1,total_available=10,depletion_fraction=.5,
        initial_stored=0,runoff=[5,0],irrigation_request=[4,4],irrigation_supply=[1,2])
    assert r.irrigation_applied==3 and r.irrigation_unmet==5
    assert r.runoff==5 and r.drainage==4
    assert abs(r.ledger_residual)<1e-10


def test_zero_rain_cannot_live_forever_on_initial_soil_water():
    r=periodic_soil_water(np.zeros(30),np.full(30,4.),1,total_available=100,depletion_fraction=.55)
    assert r.initial_stored==r.final_stored==r.evapotranspiration==0
    assert r.potential_evapotranspiration==120


def test_repeating_wet_dry_season_converges_with_bounded_storage_and_closed_budget():
    rain=np.r_[np.full(30,5.),np.zeros(90)]
    r=periodic_soil_water(rain,np.full(120,2.),1,total_available=100,depletion_fraction=.55,record=True)
    assert r.periodic_residual<1e-7 and abs(r.ledger_residual)<1e-8
    assert np.all((r.depletion_path>=0)&(r.depletion_path<=100))
    assert r.evapotranspiration<r.potential_evapotranspiration


@pytest.mark.parametrize('kwargs',[{'total_available':0},{'depletion_fraction':1},{'runoff':[1,0]},
                                  {'initial_stored':101},{'irrigation_supply':-1}])
def test_invalid_water_budgets_are_rejected(kwargs):
    options=dict(total_available=100,depletion_fraction=.55,initial_stored=50);options.update(kwargs)
    with pytest.raises(ValueError):soil_water_year([0,0],[2,2],1,**options)
