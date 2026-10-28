"""Stability, common-pressure derivatives and hydrostatic invariants."""
import numpy as np
import pytest
from scipy.integrate import quad
from rotclimate.separated_thermal_profile import profile,separated_thermal_shear,parameters,active_interval,G,CP
from rotclimate.thermal_layer_winds import hydrostatic_thermal_shear


def test_no_anomaly_recovers_single_profile_and_no_terrain_generated_shear():
    j,i=np.mgrid[:5,:7];a=285+.4*i-.3*j;ps=101325*np.exp(-(.04*i+.01*j))
    x,_=separated_thermal_shear(a,a,ps,56000,7e-5)
    y,_=hydrostatic_thermal_shear(a,ps,56000,7e-5)
    for actual,expected in zip(x,y):np.testing.assert_allclose(actual,expected,atol=1e-11,rtol=1e-11)
    x,_=separated_thermal_shear(np.full(a.shape,310.),np.full(a.shape,275.),ps,56000,7e-5)
    for component in x:np.testing.assert_array_equal(component,0.)


def test_dry_static_stability_holds_for_extreme_warm_and_cold_anomalies():
    a,b=np.meshgrid(np.linspace(170,340,7),np.linspace(170,340,9))
    p=101325*np.geomspace(.08,1,1000)[:,None,None]
    t,_,_,lapse=profile(a,b,p)
    assert lapse.max()<=G/CP*1000+1e-10
    theta=t/(p/101325)**(287.05/1004)
    assert np.diff(theta,axis=0).max()<1e-9
    _,cert=separated_thermal_shear(a,b,np.full(a.shape,101325.),56000,7e-5)
    assert cert['stability_limited_cells']>0


@pytest.mark.parametrize('a,b',[(300.,280.),(310.,270.),(180.,240.),(280.,280.)])
def test_analytic_temperature_partials_match_independent_perturbations(a,b):
    a=np.full((3,4),a);b=np.full((3,4),b);p=101325*np.geomspace(.1,1,19)[:,None,None]
    _,da,db,_=profile(a,b,p);eps=1e-4
    numerical_a=(profile(a+eps,b,p)[0]-profile(a-eps,b,p)[0])/(2*eps)
    numerical_b=(profile(a,b+eps,p)[0]-profile(a,b-eps,p)[0])/(2*eps)
    np.testing.assert_allclose(da,numerical_a,atol=2e-8,rtol=2e-8)
    np.testing.assert_allclose(db,numerical_b,atol=2e-8,rtol=2e-8)


def test_temperature_gradient_can_reverse_with_height():
    j,i=np.mgrid[:5,:7];a=300-.3*j;b=280+.5*j
    lower=profile(a,b,95000.)[0];upper=profile(a,b,35000.)[0]
    assert np.all(-np.gradient(lower,axis=0)>0)
    assert np.all(-np.gradient(upper,axis=0)<0)


@pytest.mark.parametrize('base_a,base_b',[(300.,280.),(190.,235.),(220.,220.)])
def test_integrated_shear_matches_independent_scalar_pressure_quadrature(base_a,base_b):
    j,i=np.mgrid[:3,:4];a=base_a+.2*i-.3*j;b=base_b+.1*i+.2*j;ps=101325*np.exp(-.08*i)
    actual,_=separated_thermal_shear(a,b,ps,56000,7e-5)
    # Finite-difference the physical profile wrt the two references, independently
    # of the analytic derivative used by the wind operator.
    for index in np.ndindex(a.shape):
        aa,bb=float(a[index]),float(b[index]);eps=1e-3
        k=287.05*.006/9.80665;gap=287.05/1004-k
        def raw(av,bv,x):
            exponent=min(1/-np.log(.75),gap*av/(av-bv)) if av>bv else 1/-np.log(.75)
            return (bv+(av-bv)*np.exp(exponent*x))*np.exp(k*x)
        for component,(ga,gb,sign) in enumerate([(.3,-.2,-1),(.2,.1,1)]):
            def integrand(x):
                if raw(aa,bb,x)<=200:return 0.
                da=(raw(aa+eps,bb,x)-raw(aa-eps,bb,x))/(2*eps)
                db=(raw(aa,bb+eps,x)-raw(aa,bb-eps,x))/(2*eps)
                return (ga*da+gb*db)/56000
            top=np.log(.375*ps[index]/101325);bottom=np.log(.875*ps[index]/101325)
            from scipy.optimize import brentq
            xs=np.linspace(top,bottom,101);roots=[]
            for left,right in zip(xs[:-1],xs[1:]):
                if (raw(aa,bb,left)-200)*(raw(aa,bb,right)-200)<0:
                    roots.append(brentq(lambda x:raw(aa,bb,x)-200,left,right,xtol=1e-13))
            value=quad(integrand,top,bottom,points=roots,epsabs=1e-14,limit=150)[0]
            f10=2*7.292e-5*np.sin(np.radians(10));expected=sign*287.05*7e-5/(7e-5**2+f10*f10)*value
            assert actual[component][index]==pytest.approx(expected,abs=2e-6)


def test_cold_inversion_with_two_floor_roots_is_integrated_correctly():
    a=np.full((3,3),150.);b=np.full((3,3),240.)
    par=parameters(a,b);top=np.full(a.shape,np.log(.02));bottom=np.zeros(a.shape)
    lo,hi=active_interval(top,bottom,par)
    assert np.all(lo>top);assert np.all(hi<bottom)
    assert np.all(hi>lo)


def test_mode_partition_validation_and_coupled_conservation():
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    from rotclimate.joint import SHARED_FIELDS,validate_partition
    from test_earth import _toy_case
    from test_environmental_partition import reservoir_params
    assert 'moisture_thermal_anomaly_decay' in SHARED_FIELDS;validate_partition()
    with pytest.raises(ValueError,match='must be boolean'):ClimateModel(Params(moisture_thermal_anomaly_decay=1))
    with pytest.raises(ValueError,match='requires thermal'):ClimateModel(Params(moisture_thermal_anomaly_decay=True))
    c=_toy_case();p=reservoir_params(c,moisture_thermal_anomaly_decay=True,moisture_thermal_layer_winds=True,
        moisture_thermal_height_km=1.,moisture_reservoir_temperature_profile='environmental',moisture_reservoir_lapse_k_km=6.,moisture_reservoir_rain_scheme='column-convection')
    r=ClimateModel(p,grid=c.grid).run(diagnose_moisture=True)
    assert r.numerics['all_checks_passed']
    steps=r.numerics['thermal_layer_winds']['steps'];assert len(steps)==len(r.days)+8
    assert all(s['thermal_profile']=='stable-separated' and s['maximum_possible_lapse_k_km']<=G/CP*1000+1e-9 for s in steps)


def test_hypsometric_heights_give_a_subadiabatic_temperature_lapse():
    a=np.full((3,4),320.);b=np.full_like(a,260.)
    x=np.linspace(0,np.log(.2),4000);pressure=101325*np.exp(x)[:,None,None]
    temperature=profile(a,b,pressure)[0]
    thickness=-287.05/9.80665*.5*(temperature[1:]+temperature[:-1])*np.diff(x)[:,None,None]
    lapse=-(np.diff(temperature,axis=0)/thickness)*1000
    assert lapse.max()<=9.80665/1004*1000+1e-5
