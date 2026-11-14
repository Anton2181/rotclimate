import numpy as np
import pytest

from harvest.capillary_hydraulics import HydraulicSoil,stationary_profile_cm


def silty():return HydraulicSoil(0,.47,9.08,.0136,-.803,1.342)


def test_saturation_boundary_and_drying_bounds():
    soil=silty();heads=np.r_[0,np.geomspace(1,16000,80)]
    water=soil.water_content(heads);k=soil.conductivity_cm_day(heads)
    assert water[0]==soil.theta_saturated and k[0]==pytest.approx(soil.ksat_cm_day)
    assert np.all((water>=soil.theta_residual)&(water<=soil.theta_saturated))
    assert np.all(np.diff(water)<=0) and np.all(np.diff(k)<=0) and np.all(k>=0)


def test_published_first_step_and_flux_units():
    soil=silty()
    assert soil.conductivity_cm_day(5)==pytest.approx(3.33,abs=.005)
    profile=stationary_profile_cm(soil,[0,10,20],10.)
    np.testing.assert_allclose(profile,[0,7.7,14.1],atol=.05)


def test_zero_flux_is_exact_hydrostatic_profile_even_when_k_underflows():
    heads=np.array([0.,1.,10.,100.,1e100])
    np.testing.assert_array_equal(stationary_profile_cm(silty(),heads,0.),heads)


def test_increasing_flux_reduces_height_for_same_suction():
    heads=np.arange(0,401,10);flux=np.array([0,1,2.5,5,7.5,10])
    profiles=stationary_profile_cm(silty(),heads,flux)
    assert profiles.shape==(6,41)
    assert np.all(np.diff(profiles,axis=1)>0) and np.all(np.diff(profiles,axis=0)<=0)
    assert np.all(profiles<=heads) and np.all(profiles>=0)


def test_nonuniform_head_steps_and_multidimensional_flux_shape():
    class ConstantConductivity:
        def conductivity_cm_day(self,heads):return np.full_like(heads,5.)
    heads=np.array([0.,1.,5.,17.3,100.]);before=heads.copy()
    q=np.array([[0.,10.],[20.,30.]])
    result=stationary_profile_cm(ConstantConductivity(),heads,q)
    np.testing.assert_allclose(result,heads*5/(5+q[...,None]/10))
    np.testing.assert_array_equal(heads,before)


@pytest.mark.parametrize('kwargs',[
    {'theta_residual':-.01},{'theta_residual':.47},{'theta_saturated':1.1},
    {'ksat_cm_day':0},{'alpha_cm_inv':0},{'n':1},{'n':.9},
    {'connectivity':np.nan},{'ksat_cm_day':np.inf},{'n':True},
])
def test_invalid_hydraulic_parameters_refused(kwargs):
    values=dict(theta_residual=0.,theta_saturated=.47,ksat_cm_day=9.08,alpha_cm_inv=.0136,connectivity=-.803,n=1.342);values.update(kwargs)
    with pytest.raises(ValueError):HydraulicSoil(**values)


@pytest.mark.parametrize('heads',[[],[0],[1,10],[0,0,10],[0,10,5],[0,np.nan],[0,np.inf]])
def test_invalid_profile_head_grid_refused(heads):
    with pytest.raises(ValueError):stationary_profile_cm(silty(),heads,1.)


@pytest.mark.parametrize('flux',[-1,np.nan,np.inf])
def test_invalid_prescribed_flux_refused(flux):
    with pytest.raises(ValueError):stationary_profile_cm(silty(),[0,10],flux)


def test_negative_or_nonfinite_suction_refused():
    for head in [-1,np.nan,np.inf]:
        with pytest.raises(ValueError):silty().water_content(head)
        with pytest.raises(ValueError):silty().conductivity_cm_day(head)
