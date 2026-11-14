import numpy as np
import pytest
from harvest.soil_drying import (SoilState, adjusted_depletion_fraction, root_stress,
                                 soil_profile, soil_state, soil_step, surface_coefficients)


def profile():return soil_profile(.25, .10, 1., .1, 9.)


def test_tew_and_taw_share_top_water_without_double_counting():
    p=profile();s=soil_state(p,1.)
    assert p.taw_mm==150 and p.tew_mm==20
    assert s.total_mm==155 and s.root_available_mm==150
    assert s.total_mm != p.taw_mm+p.tew_mm


def test_below_wilting_pool_cannot_supply_roots():
    p=profile();s=SoilState(0,0,5)
    r=soil_step(p,s,0,5,1.,1.2,.55)
    assert r.ks==0 and r.root_uptake_mm==0 and r.evaporation_mm>0


def test_dry_surface_does_not_evaporate_deep_root_water_directly():
    p=profile();s=SoilState(0,100,0)
    r=soil_step(p,s,0,5,0,1.2,.55)
    assert r.kr==0 and r.evaporation_mm==0 and r.state.deep_mm==100


def test_paid_wetting_fills_pools_and_reports_drainage():
    p=profile();s=soil_state(p)
    a=soil_step(p,s,3,0,0,1.2,.55)
    assert a.state.bound_mm==3 and a.state.root_available_mm==0
    b=soil_step(p,a.state,200,0,0,1.2,.55)
    assert b.state.total_mm==155 and b.drainage_mm==48
    assert s.total_mm==0 and a.state.total_mm==3


def test_surface_and_root_diagnostic_endpoints():
    kr,ke=surface_coefficients([0,9,20],9,20,.15,1.2)
    np.testing.assert_allclose(kr,[1,1,0]);np.testing.assert_allclose(ke,[1.05,1.05,0])
    np.testing.assert_allclose(root_stress([160,96,48,0],160,.4),[1,1,.5,0])
    assert surface_coefficients(0,9,20,.15,1.2,0)[1]==0


def test_demand_adjustment_uses_daily_units_and_declared_bounds():
    np.testing.assert_allclose(adjusted_depletion_fraction(.55,[0,5,10,100]),[.75,.55,.35,.1])


def test_root_and_surface_compete_for_shared_top_stock():
    p=soil_profile(.25,.1,.1,.1,9)
    r=soil_step(p,soil_state(p,1.),0,100,1,1.2,.55)
    assert r.evaporation_mm+r.root_uptake_mm<=20+1e-12
    assert r.state.total_mm>=0


def test_daily_mass_and_vector_scalar_equivalence():
    p=soil_profile([.25,.32],[.1,.14],[1.,1.5],[.1,.15],[9,12])
    s=soil_state(p,[1,.3]);before=s.total_mm.copy()
    r=soil_step(p,s,[5,20],[4.5,6],[1,.3],1.2,[.55,.4])
    np.testing.assert_allclose(before+[5,20],r.state.total_mm+r.evaporation_mm+r.root_uptake_mm+r.drainage_mm)
    for i in range(2):
        single=soil_step(soil_profile([.25,.32][i],[.1,.14][i],[1.,1.5][i],[.1,.15][i],[9,12][i]),SoilState(s.top_mm[i],s.deep_mm[i],s.bound_mm[i]),[5,20][i],[4.5,6][i],[1,.3][i],1.2,[.55,.4][i])
        assert single.state.total_mm==r.state.total_mm[i]
    np.testing.assert_array_equal(s.total_mm,before)


def test_half_day_scales_flux_without_hidden_monthly_steps():
    p=profile();s=soil_state(p,1)
    full=soil_step(p,s,0,4,0,1.2,.55)
    half=soil_step(p,s,0,4,0,1.2,.55,step_days=.5)
    assert half.evaporation_mm==pytest.approx(full.evaporation_mm/2)


@pytest.mark.parametrize('args',[(.1,.2,1,.1,2),(.25,.1,.05,.1,2),(.25,.1,1,0,2),(.25,.1,1,.1,20),(.25,np.nan,1,.1,2)])
def test_invalid_profile_refused(args):
    with pytest.raises(ValueError):soil_profile(*args)


@pytest.mark.parametrize('change',[dict(water_mm=-1),dict(eto_mm_day=np.inf),dict(kcb=2),dict(depletion_fraction=1),dict(exposed_fraction=1.1),dict(step_days=0),dict(step_days=30)])
def test_invalid_forcing_refused(change):
    args=dict(water_mm=0,eto_mm_day=5,kcb=1,kcmax=1.2,depletion_fraction=.55);args.update(change)
    with pytest.raises(ValueError):soil_step(profile(),soil_state(profile()),**args)


def test_invalid_or_overfull_state_refused():
    with pytest.raises(ValueError):SoilState(-1,0,0)
    with pytest.raises(ValueError):soil_step(profile(),SoilState(16,0,0),0,5,1,1.2,.55)


def test_demand_overflow_refused():
    with pytest.raises(ValueError):soil_step(profile(),soil_state(profile()),0,np.finfo(float).max,2,2,.55)
