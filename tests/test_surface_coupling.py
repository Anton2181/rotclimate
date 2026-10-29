import numpy as np
import pytest
from rotclimate.open_mean_boundary import OpenMeanRigidLidModel
from rotclimate.surface_coupling import SurfaceState,surface_enthalpy,receive_precipitation,advance_surface_forcing,advance_surface_coupled
from rotclimate.pressure_moist import gas_energy
from rotclimate.moist_enthalpy import CP_LIQUID,REFERENCE_K


def setup(ts=300.,ta=290.,lower_q=.005,water=50.,phase=True):
    p=[101325,85000,65000,40000];u=np.zeros((3,4,6));v=np.zeros((3,5,5));u[:,:,[0,-1]]=3.
    m=OpenMeanRigidLidModel(p,(4,5),200000,1e-4,u_boundary=u,v_boundary=v,
        external_temperature_k=280.,external_mixing_ratio=.003,momentum_drag_s=1/86400,phase_enabled=phase)
    u,v,_=m.project_initial_wind(u,v)
    t=np.broadcast_to(np.array([ta,270.,245.])[:,None,None],m.mass.shape).copy();w=m.mass*np.array([lower_q,.001,.0001])[:,None,None]
    a=m.initial_state(t,w,u,v);s=SurfaceState(np.full(m.shape,ts),np.full(m.shape,water),np.full(m.shape,2e6))
    return m,a,s


def forcing():return dict(longwave_optical_depth=[.3,.2,.1],shortwave_optical_depth=[.02,.02,.02],reference_height_m=700.,roughness_m=.01,scalar_roughness_m=.001,solar_in_w_m2=350.,longwave_in_w_m2=20.)


def test_rain_changes_heat_capacity_and_can_cool_despite_positive_enthalpy():
    s=SurfaceState(290.,50.,1e6);rain=10.;rain_h=CP_LIQUID*rain*(280.-REFERENCE_K)
    new=receive_precipitation(s,rain,rain_h)
    assert rain_h>0 and new.temperature_k<s.temperature_k
    np.testing.assert_allclose(surface_enthalpy(new),surface_enthalpy(s)+rain_h,rtol=1e-12)
    np.testing.assert_allclose(new.liquid_kg_m2,60.)


@pytest.mark.parametrize('dew',[False,True])
def test_finite_surface_evap_or_dew_total_water_and_enthalpy(dew):
    m,a,s=setup(ts=280. if dew else 300.,ta=298. if dew else 290.,lower_q=.013 if dew else .005)
    old_e=gas_energy(a.temperature_k,a.vapor_kg_m2,m.mass).sum()+surface_enthalpy(s).sum();old_w=a.vapor_kg_m2.sum()+s.liquid_kg_m2.sum()
    r=advance_surface_forcing(m,a,s,120,**forcing())
    assert (r.certificate['mean_vapor_transfer_kg_m2']<0)==dew
    new_e=gas_energy(r.atmosphere.temperature_k,r.atmosphere.vapor_kg_m2,m.mass).sum()+surface_enthalpy(r.surface).sum()
    np.testing.assert_allclose(new_e-old_e,120*r.certificate['mean_net_top_incoming_w_m2']*m.n,rtol=1e-10,atol=1e-4)
    np.testing.assert_allclose(r.atmosphere.vapor_kg_m2.sum()+r.surface.liquid_kg_m2.sum(),old_w,rtol=1e-12)
    np.testing.assert_array_equal(r.atmosphere.u_east,a.u_east);np.testing.assert_array_equal(r.atmosphere.ground_rain_kg_m2,0)


def test_forcing_condensation_returns_rain_mass_and_actual_enthalpy_once():
    m,a,s=setup(ts=300.,ta=298.,lower_q=.03) # deliberately initially supersaturated
    r=advance_surface_forcing(m,a,s,30,**forcing());assert r.rain_kg_m2.sum()>0
    transfer=r.certificate['mean_vapor_transfer_kg_m2']
    np.testing.assert_allclose(r.surface.liquid_kg_m2.mean(),s.liquid_kg_m2.mean()-transfer+r.rain_kg_m2.mean(),rtol=1e-12)
    np.testing.assert_array_equal(r.atmosphere.ground_rain_kg_m2,0)
    assert r.certificate['all_rain_returned_to_surface']


def test_actual_open_port_dynamics_surface_radiation_energy_water_budget():
    m,a,s=setup();x=m._velocity(a.u_east,a.v_south)
    old_e=gas_energy(a.temperature_k,a.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)+surface_enthalpy(s).sum();old_w=a.vapor_kg_m2.sum()+s.liquid_kg_m2.sum()
    e_external=0.;w_out=0.;rain=0.
    for _ in range(3):
        r=advance_surface_coupled(m,a,s,120,**forcing());a,s=r.atmosphere,r.surface
        e_external+=r.certificate['net_external_energy_j_m2'];w_out+=r.certificate['net_outward_water_kg_m2'];rain+=r.rain_kg_m2.sum()
        np.testing.assert_array_equal(a.ground_rain_kg_m2,0)
    x=m._velocity(a.u_east,a.v_south);new_e=gas_energy(a.temperature_k,a.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)+surface_enthalpy(s).sum()
    np.testing.assert_allclose(new_e-old_e,e_external*m.n,rtol=1e-10,atol=1e-3)
    np.testing.assert_allclose(a.vapor_kg_m2.sum()+s.liquid_kg_m2.sum()-old_w,-w_out*m.n,rtol=1e-10,atol=1e-9)


def test_dry_surface_has_no_evaporation_and_excess_timestep_rejected():
    m,a,s=setup(water=0.);r=advance_surface_forcing(m,a,s,30,**forcing());assert r.certificate['mean_vapor_transfer_kg_m2']==0
    m,a,s=setup(water=1e-9)
    with pytest.raises(ValueError,match='reservoir exhausted'):advance_surface_forcing(m,a,s,120,availability_scale_kg_m2=1e-9,**forcing())


def test_transparent_no_exchange_rest_limit():
    m=OpenMeanRigidLidModel([101325,85000,65000,40000],(4,5),200000,1e-4)
    a=m.initial_state(280.,0);s=SurfaceState(280.,50.,2e6)
    r=advance_surface_coupled(m,a,s,120,longwave_optical_depth=0,shortwave_optical_depth=0,surface_emissivity=0,reference_height_m=700.,roughness_m=.01)
    np.testing.assert_allclose(r.atmosphere.temperature_k,280.,atol=1e-10);np.testing.assert_allclose(r.surface.temperature_k,280.,atol=1e-10)
    np.testing.assert_array_equal(r.surface.liquid_kg_m2,50.)
