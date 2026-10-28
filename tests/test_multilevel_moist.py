"""Resolved composed gas-static-energy and ground-rain ledgers."""
import numpy as np
from rotclimate.column_thermodynamics import CP,G,LV
from rotclimate.moist_enthalpy import CP_VAPOR,REFERENCE_K
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.regional_energy_step import static_energy
from rotclimate.multilevel_moist import advance_multilevel_moist


def test_four_layer_stagnant_composition_conserves_actual_energy_and_water_with_rain():
    nz,ny,nx=4,2,3
    m=np.broadcast_to(np.array([1000.,2000.,3000.,2000.])[:,None,None],(nz,ny,nx)).copy()
    t=np.broadcast_to(np.array([300.,285.,268.,250.])[:,None,None],m.shape)
    p=np.broadcast_to(np.array([95000.,80000.,60000.,40000.])[:,None,None],m.shape)
    edges=np.array([0.,1000.,3000.,6000.,10000.]);z=np.broadcast_to((.5*(edges[:-1]+edges[1:]))[:,None,None],m.shape)
    w=saturation_vapor_mass(t,m,p)*np.array([.95,.98,1.4,1.8])[:,None,None]
    out=advance_multilevel_moist(m,0.,0.,1e5,t,w,p,edges,3600.,t,.01)
    assert out.ground_rain_kg_m2.max()>0
    assert abs(w.sum()-out.vapor_kg_m2.sum()-out.ground_rain_kg_m2.sum())<1e-10
    assert abs(static_energy(t,w,m,z).sum()-out.static_energy_j_m2.sum()-out.ground_rain_enthalpy_j_m2.sum())<1e-4
    assert out.fall_heat_j_m2.sum()>0


def test_actual_vapor_and_heat_sources_balance_after_multilevel_phase():
    mass=np.full((4,2,3),2000.);edges=np.linspace(0,9000,5);z=np.broadcast_to((.5*(edges[:-1]+edges[1:]))[:,None,None],mass.shape)
    t=np.broadcast_to(np.array([298.,280.,265.,250.])[:,None,None],mass.shape)
    p=np.broadcast_to(np.array([95000.,75000.,55000.,35000.])[:,None,None],mass.shape)
    w=saturation_vapor_mass(t,mass,p)*.9;dt=3600.;evap=np.zeros_like(w);evap[0]=1/86400.
    out=advance_multilevel_moist(mass,0.,0.,1e5,t,w,p,edges,dt,t,.01,heating_w_m2=10.,evaporation_kg_m2_s=evap)
    expected=dt*(10.*mass.size+np.sum(evap*(LV+CP_VAPOR*(t-REFERENCE_K)+G*z)))
    actual=out.static_energy_j_m2.sum()+out.ground_rain_enthalpy_j_m2.sum()-static_energy(t,w,mass,z).sum()
    assert abs(actual-expected)<1e-4
    assert abs(out.certificate['combined_water_residual_kg_m2_s_cell_sum'])<1e-12
