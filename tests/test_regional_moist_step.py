"""Actual composed water/static-energy budgets, with heat and vapor sources."""
import numpy as np
from rotclimate.column_thermodynamics import G
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.regional_baroclinic import RegionalMode,mass_divergence
from rotclimate.regional_energy_step import static_energy
from rotclimate.regional_moist_step import advance_moist


def test_closed_stagnant_composition_closes_static_energy_plus_exported_rain():
    mass=np.full((3,4),9000.);m=np.stack([.25*mass,.75*mass]);z=np.broadcast_to(np.array([1875.,9375.])[:,None,None],m.shape)
    t=np.broadcast_to(np.array([298.,250.])[:,None,None],m.shape);p=np.broadcast_to(np.array([90000.,40000.])[:,None,None],m.shape)
    w=saturation_vapor_mass(t,m,p)*np.array([.98,1.6])[:,None,None]
    mode=RegionalMode(np.zeros((3,5)),np.zeros((4,4)),np.zeros((3,4)),np.zeros((3,4)),{})
    out=advance_moist(mode,mass,1e5,t,w,z,p,3750.,3600.,t,[.009,.0025])
    assert out.ground_rain_kg_m2.max()>0
    assert abs((w-out.vapor_kg_m2).sum()-out.ground_rain_kg_m2.sum())<1e-10
    assert abs(static_energy(t,w,m,z).sum()-static_energy(out.temperature_k,out.vapor_kg_m2,m,z).sum()-out.ground_rain_enthalpy_j_m2.sum())<1e-4
    assert out.fall_dissipation_j_m2.sum()>0


def test_transport_phase_composition_closes_actual_heat_and_water_sources():
    mass=np.full((2,2),9000.);m=np.stack([.25*mass,.75*mass]);z=np.broadcast_to(np.array([1875.,9375.])[:,None,None],m.shape)
    p=np.broadcast_to(np.array([90000.,40000.])[:,None,None],m.shape)
    t=np.broadcast_to(np.array([298.,250.])[:,None,None],m.shape);w=saturation_vapor_mass(t,m,p)*.98
    u=np.zeros((2,3));u[:,1]=2.;v=np.zeros((3,2));mode=RegionalMode(u,v,np.zeros_like(mass),mass_divergence(u,v,mass,1e5),{})
    out=advance_moist(mode,mass,1e5,t,w,z,p,3750.,3600.,t,[.009,.0025],heating_w_m2=10.,evaporation_kg_m2_s=[1/86400.,0.])
    assert abs(out.certificate['combined_energy_residual_w_m2_cell_sum'])<1e-5
    assert abs(out.certificate['combined_water_residual_kg_m2_s_cell_sum'])<1e-12
