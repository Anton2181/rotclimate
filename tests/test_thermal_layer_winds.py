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
