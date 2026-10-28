"""Independent analytic limits and invariants for proposed thermal branches."""
import numpy as np
import pytest
from rotclimate.thermal_layer_winds import pressure_thermal_shear,project_thermal_branches
from rotclimate.column_mass import ColumnMassProjection
from rotclimate.reservoir_transport import ReservoirTransport


def test_linear_common_pressure_temperature_has_analytic_thermal_wind_signs():
    # Coordinate convention: rows run south; north gradient is positive2K/100km.
    j,i=np.mgrid[:5,:7];dx=100000.;t=280+3*i-2*j;f=1e-4
    du,dv=pressure_thermal_shear(t,dx,f)
    f10=2*7.292e-5*np.sin(np.radians(10))
    expected=287.05*np.log(7/3)*f/(f*f+f10*f10)/dx
    np.testing.assert_allclose(du,-2*expected,rtol=1e-14)
    np.testing.assert_allclose(dv,3*expected,rtol=1e-14)
    backwards=pressure_thermal_shear(t,dx,-f)
    np.testing.assert_array_equal(backwards[0],-du);np.testing.assert_array_equal(backwards[1],-dv)


def test_uniform_temperature_and_equatorial_limits_are_exact():
    for f in [0.,1e-4,-1e-4]:
        for shear in pressure_thermal_shear(np.full((4,5),280.),56000.,f):
            np.testing.assert_array_equal(shear,0.)
    t=280+np.arange(20).reshape(4,5)
    for shear in pressure_thermal_shear(t,56000.,0.):np.testing.assert_array_equal(shear,0.)


def terrain_case():
    shape=(7,9);j,i=np.mgrid[:shape[0],:shape[1]];dx=56000.
    projection=ColumnMassProjection(200+100*i+20*j,dx)
    lower=(np.full(shape,5.),np.full(shape,1.))
    # Cold pole, warm equator: upper eastward wind should exceed lower.
    shear=pressure_thermal_shear(270+1.5*j+.4*i,dx,7e-5)
    return projection,lower,shear


def test_shared_projection_keeps_shear_and_mass_continuity_over_terrain():
    projection,lower,shear=terrain_case();result=project_thermal_branches(projection,lower,shear)
    np.testing.assert_allclose(result.upper[0]-result.lower[0],shear[0],atol=2e-14)
    np.testing.assert_allclose(result.upper[1]-result.lower[1],shear[1],atol=2e-14)
    operator=ReservoirTransport(projection.mass,result.lower,result.upper,projection.cell_m)
    assert operator.dry_residual<1e-10
    assert result.certificate['maximum_common_correction_ms']>0
    # A nontrivial dry-continuous circulation still has layer exchange.
    assert np.abs(operator.upward_air).max()>1e-8


def test_constructed_thermal_flow_transports_uniform_specific_humidity_unchanged():
    projection,lower,shear=terrain_case();result=project_thermal_branches(projection,lower,shear)
    operator=ReservoirTransport(projection.mass,result.lower,result.upper,projection.cell_m)
    expected=18*operator.layer_mass
    solved,_=operator.solve(np.zeros_like(expected),np.zeros_like(expected),expected,diffusion=60000.)
    np.testing.assert_allclose(solved,expected,atol=2e-11,rtol=2e-11)


def test_common_projection_is_minimum_dry_mass_correction_with_fixed_shear():
    projection,lower,shear=terrain_case();result=project_thermal_branches(projection,lower,shear)
    rng=np.random.default_rng(137);shape=projection.shape
    pu,pv,_=projection.project(rng.normal(size=shape),rng.normal(size=shape))
    desired_upper=tuple(a+b for a,b in zip(lower,shear))
    energy=lambda lo,up:sum(weight*np.sum(projection.mass*((wind[0]-target[0])**2+(wind[1]-target[1])**2))
        for weight,wind,target in [(.25,lo,lower),(.75,up,desired_upper)])
    optimum=energy(result.lower,result.upper)
    for sign in [-1,1]:
        alternative_lower=(result.lower[0]+sign*pu,result.lower[1]+sign*pv)
        alternative_upper=(result.upper[0]+sign*pu,result.upper[1]+sign*pv)
        assert energy(alternative_lower,alternative_upper)>optimum


@pytest.mark.parametrize('t,dx,f',[(np.ones((2,4))*280,1,1e-4),(np.zeros((3,4)),1,1e-4),
    (np.ones((3,4))*280,0,1e-4),(np.ones((3,4))*280,1,np.nan)])
def test_invalid_thermal_inputs_rejected(t,dx,f):
    with pytest.raises(ValueError):pressure_thermal_shear(t,dx,f)


def test_hydrostatic_common_pressure_gradient_ignores_terrain_only_variations():
    from rotclimate.thermal_layer_winds import hydrostatic_thermal_shear
    j,i=np.mgrid[:7,:9];ps=101325*np.exp(-(100*i+25*j)/8000.)
    actual,_=hydrostatic_thermal_shear(np.full(ps.shape,290.),ps,56000.,7e-5)
    for component in actual:np.testing.assert_array_equal(component,0.)
    # The incorrect moving-pressure temperature gradient would manufacture wind.
    sigma_temperature=290*(.6*ps/101325)**(287.05*.006/9.80665)
    naive=pressure_thermal_shear(sigma_temperature,56000.,7e-5)
    assert np.hypot(*naive).max()>.1


@pytest.mark.parametrize('reference,lapse',[(290.,6.),(225.,6.),(290.,0.)])
def test_hydrostatic_integral_matches_fixed_pressure_quadrature(reference,lapse):
    from scipy.integrate import quad
    from rotclimate.thermal_layer_winds import hydrostatic_thermal_shear
    j,i=np.mgrid[:5,:7];t=reference+.3*i-.2*j;ps=101325*np.exp(-(.04*i+.01*j))
    f=7e-5;dx=56000.;actual,_=hydrostatic_thermal_shear(t,ps,dx,f,lapse_k_km=lapse)
    k=287.05*lapse/1000/9.80665;f10=2*7.292e-5*np.sin(np.radians(10))
    integral=np.zeros_like(t)
    for index in np.ndindex(t.shape):
        lower,upper=np.log(.875*ps[index]/101325),np.log(.375*ps[index]/101325)
        crossing=np.log(200/t[index])/k if k else None
        points=[crossing] if crossing is not None and upper<crossing<lower else None
        integral[index]=quad(lambda x:np.exp(k*x) if t[index]*np.exp(k*x)>200 else 0,upper,lower,points=points,epsabs=1e-12)[0]
    coefficient=287.05*f/(f*f+f10*f10)*integral/dx
    np.testing.assert_allclose(actual[0],-.2*coefficient,rtol=1e-11,atol=1e-12)
    np.testing.assert_allclose(actual[1],.3*coefficient,rtol=1e-11,atol=1e-12)


def test_new_mode_partition_validation_and_coupled_ledgers():
    from test_earth import _toy_case
    from test_environmental_partition import reservoir_params
    from rotclimate.config import Params
    from rotclimate.joint import SHARED_FIELDS,validate_partition
    from rotclimate.model import ClimateModel
    assert 'moisture_thermal_layer_winds' in SHARED_FIELDS;validate_partition()
    with pytest.raises(ValueError,match='must be boolean'):ClimateModel(Params(moisture_thermal_layer_winds=1))
    with pytest.raises(ValueError,match='require independent'):ClimateModel(Params(moisture_thermal_layer_winds=True))
    case=_toy_case();p=reservoir_params(case,moisture_thermal_layer_winds=True,moisture_thermal_height_km=1.,
        moisture_reservoir_temperature_profile='environmental',moisture_reservoir_rain_scheme='column-convection')
    r=ClimateModel(p,grid=case.grid).run(diagnose_moisture=True)
    assert r.numerics['all_checks_passed']
    cert=r.numerics['thermal_layer_winds'];assert len(cert['steps'])==len(r.days)+8
    assert cert['max_scaled_dry_column_residual']<1e-10
    assert all(s['thermal_lapse_k_km']==p.moisture_reservoir_lapse_k_km for s in cert['steps'])
