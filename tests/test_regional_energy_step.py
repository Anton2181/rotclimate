"""Dry-adiabatic, heat-reservoir and actual moist-static-energy budgets."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import CP,G,LV
from rotclimate.moist_enthalpy import CP_VAPOR,REFERENCE_K
from rotclimate.regional_baroclinic import RegionalMode,mass_divergence,solve_regional_mode
from rotclimate.regional_energy_step import advance_energy,static_energy


def stagnant(mass,dx=1e5):
    ny,nx=mass.shape
    return RegionalMode(np.zeros((ny,nx+1)),np.zeros((ny+1,nx)),np.zeros_like(mass),np.zeros_like(mass),{})


def test_stagnant_heating_and_vapor_source_have_independent_energy_solution():
    mass=np.full((3,4),10000.);m=np.stack([.25*mass,.75*mass]);z=np.array([500.,4500.])[:,None,None]
    t=np.broadcast_to(np.array([295.,255.])[:,None,None],m.shape);w=np.broadcast_to(np.array([20.,3.])[:,None,None],m.shape)
    evap=np.zeros_like(w);evap[0]=1/86400.;power=np.broadcast_to(np.array([50.,-20.])[:,None,None],m.shape);dt=86400.
    out=advance_energy(stagnant(mass),mass,1e5,t,w,z,dt,t,[.009,.002],evaporation_kg_m2_s=evap,heating_w_m2=power)
    expected_w=w+dt*evap
    energy0=(CP*m+CP_VAPOR*w)*t+(LV-CP_VAPOR*REFERENCE_K)*w+G*(m+w)*z
    expected_e=energy0+dt*(power+evap*(LV+CP_VAPOR*(t-REFERENCE_K)+G*z))
    expected_t=(expected_e-(LV-CP_VAPOR*REFERENCE_K)*expected_w-G*(m+expected_w)*z)/(CP*m+CP_VAPOR*expected_w)
    np.testing.assert_allclose(out.vapor_kg_m2,expected_w,rtol=1e-13,atol=1e-11)
    np.testing.assert_allclose(out.temperature_k,expected_t,rtol=1e-13,atol=1e-10)


def test_injecting_vapor_at_local_temperature_carries_exact_energy_without_spurious_warming():
    mass=np.full((3,4),9000.);t=np.broadcast_to(np.array([293.,250.])[:,None,None],(2,3,4))
    out=advance_energy(stagnant(mass),mass,1e5,t,2.,[500.,4500.],86400.,t,[.009,.002],evaporation_kg_m2_s=[2/86400.,0.])
    np.testing.assert_allclose(out.temperature_k,t,atol=1e-10,rtol=1e-13)
    np.testing.assert_allclose(out.vapor_kg_m2[0],4.,atol=1e-12)


def test_closed_overturning_cools_rising_air_and_warms_descending_air_without_external_heat():
    mass=np.full((2,2),10000.);dx=1e5;u=np.zeros((2,3));u[:,1]=2.;v=np.zeros((3,2))
    mode=RegionalMode(u,v,np.zeros_like(mass),mass_divergence(u,v,mass,dx),{})
    t=np.full((2,2,2),290.);m=np.stack([.25*mass,.75*mass]);z=np.array([500.,4500.])[:,None,None]
    out=advance_energy(mode,mass,dx,t,0.,z,86400.,t,0.)
    assert out.temperature_k[1,0,0]<290 # upward dry transfer cools in the upper box
    assert out.temperature_k[0,0,1]>290 # downward dry transfer warms below
    assert np.sum(CP*m*(out.temperature_k-t))==pytest.approx(0.,abs=1e-5)
    assert out.static_energy_j_m2.sum()==pytest.approx(static_energy(t,0.,m,z).sum(),abs=1e-5)
    assert abs(out.certificate['column_energy_budget_residual_w_m2_cell_sum'])<1e-8


def test_uniform_moist_static_energy_and_q_are_an_exact_dry_adiabatic_transport_equilibrium():
    j,i=np.mgrid[:9,:13];mass=10000*(1-.4*np.exp(-((i-7)**2+(j-4)**2)/5));dx=1e5
    mode=solve_regional_mode(.001*np.exp(-((i-6)**2+(j-5)**2)/8),dx,7e-5,column_mass=mass,
        wave_speed_ms=50.,momentum_drag_s=1/(5*86400.),thermal_drag_s=1/(20*86400.),boundaries=dict(west='impedance',east='impedance'))
    m=np.stack([.25*mass,.75*mass]);z=np.array([500.,4500.])[:,None,None];q=.006;k=325000.
    t=np.broadcast_to((k-q*(LV-CP_VAPOR*REFERENCE_K)-G*(1+q)*z)/(CP+CP_VAPOR*q),m.shape)
    out=advance_energy(mode,mass,dx,t,q*m,z,86400.,t,q)
    np.testing.assert_allclose(out.temperature_k,t,atol=1e-9,rtol=1e-12)
    np.testing.assert_allclose(out.vapor_kg_m2,q*m,atol=1e-9,rtol=1e-12)
    # Vertical lapse follows moist fixed-q static energy, not a temperature reset.
    np.testing.assert_allclose(t[0]-t[1],G*(1+q)*4000/(CP+CP_VAPOR*q),atol=1e-12)


@pytest.mark.parametrize('changes',[dict(dt_s=0),dict(heating_w_m2=-1e9),dict(height_m=[4500.,500.]),dict(evaporation_kg_m2_s=-1.)])
def test_invalid_energy_step_rejected(changes):
    mass=np.full((3,4),10000.);args=dict(temperature_k=[290.,250.],vapor_kg_m2=2.,height_m=[500.,4500.],dt_s=86400.,external_temperature_k=[290.,250.],external_mixing_ratio=[.009,.002])
    args.update(changes)
    with pytest.raises(ValueError):advance_energy(stagnant(mass),mass,1e5,**args)
