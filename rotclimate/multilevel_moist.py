"""Resolved fixed-wind moist static-energy transport and phase composition.

Shared cells/interfaces with the hydrostatic column, but winds are supplied:
thermal-state-to-momentum feedback is not closed by this operator alone.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import CP,G,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K
from .regional_energy_step import static_energy
from .multilevel_transport import _field,solve_multilevel
from .multilevel_phase import adjust_multilevel_fall


@dataclass
class MultilevelMoist:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    static_energy_j_m2: np.ndarray
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    fall_heat_j_m2: np.ndarray
    certificate: dict


def advance_multilevel_moist(layer_mass,u_east,v_south,cell_m,temperature_k,vapor_kg_m2,
                              pressure_pa,vertical_edges_m,dt_s,external_temperature_k,
                              external_mixing_ratio,*,cell_height_m=None,heating_w_m2=0.,
                              evaporation_kg_m2_s=0.,vapor_source_temperature_k=None):
    mass=np.asarray(layer_mass,float)
    if mass.ndim!=3 or not np.isfinite(mass).all() or np.any(mass<=0) or not np.isfinite(dt_s) or dt_s<=0:
        raise ValueError('Need finite positive fixed layer masses and timestep')
    edges=np.asarray(vertical_edges_m,float)
    if edges.shape!=(mass.shape[0]+1,) or not np.isfinite(edges).all() or edges[0]!=0 or np.any(np.diff(edges)<=0):
        raise ValueError('Need ascending vertical edges from ground0')
    zvalue=(.5*(edges[:-1]+edges[1:])) if cell_height_m is None else cell_height_m
    z=_field(zvalue,mass.shape,'cell heights',minimum=0.)
    t=_field(temperature_k,mass.shape,'temperature',minimum=180.)
    w=_field(vapor_kg_m2,mass.shape,'vapor',minimum=0.)
    p=_field(pressure_pa,mass.shape,'pressure',minimum=10000.)
    ext_t=_field(external_temperature_k,mass.shape,'external temperature',minimum=180.)
    ext_q=_field(external_mixing_ratio,mass.shape,'external vapor ratio',minimum=0.)
    evap=_field(evaporation_kg_m2_s,mass.shape,'vapor source',minimum=0.)
    heat=_field(heating_w_m2,mass.shape,'external heating')
    source_t=t if vapor_source_temperature_k is None else _field(vapor_source_temperature_k,mass.shape,'source vapor temperature',minimum=180.)
    if np.any(t>330) or np.any(ext_t>330) or np.any(source_t>330):raise ValueError('Liquid phase composition supports180–330K initial states')
    old_e=static_energy(t,w,mass,z)
    vapor_h=LV+CP_VAPOR*(source_t-REFERENCE_K)+G*z
    power=heat+evap*vapor_h
    energy_source=old_e/dt_s+power
    if np.any(energy_source<0):raise ValueError('External cooling/timestep would require negative static energy')
    water_step=solve_multilevel(mass,u_east,v_south,cell_m,w/dt_s+evap,1/dt_s,ext_q)
    ext_energy=CP*ext_t+ext_q*(LV+CP_VAPOR*(ext_t-REFERENCE_K))+G*(1+ext_q)*z
    energy_step=solve_multilevel(mass,u_east,v_south,cell_m,energy_source,1/dt_s,ext_energy)
    moved_w,moved_e=water_step.amount,energy_step.amount
    moved_t=(moved_e-(LV-CP_VAPOR*REFERENCE_K)*moved_w-G*(mass+moved_w)*z)/(CP*mass+CP_VAPOR*moved_w)
    phase=adjust_multilevel_fall(moved_t,moved_w,mass,p,edges,z)
    final_e=static_energy(phase.temperature_k,phase.vapor_kg_m2,mass,z)
    boundary_e=sum(energy_step.certificate['outward_boundary_per_layer_cell_s'])
    boundary_w=sum(water_step.certificate['outward_boundary_per_layer_cell_s'])
    energy_error=float(((final_e-old_e).sum()+phase.ground_rain_enthalpy_j_m2.sum())/dt_s-power.sum()+boundary_e)
    water_error=float(((phase.vapor_kg_m2-w).sum()+phase.ground_rain_kg_m2.sum())/dt_s-evap.sum()+boundary_w)
    scale=max(float(np.abs(old_e/dt_s).sum()),float(np.abs(power).sum()),1.)
    if abs(energy_error)>1e-10*scale or abs(water_error)>1e-10*max(float((w/dt_s+evap).sum()),1.):
        raise RuntimeError('Resolved moist composition failed actual atmosphere/rain/source budget')
    cert=dict(levels=mass.shape[0],combined_energy_residual_w_m2_cell_sum=energy_error,
        combined_water_residual_kg_m2_s_cell_sum=water_error,
        external_heating_w_m2_cell_sum=float(heat.sum()),vapor_source_enthalpy_w_m2_cell_sum=float((evap*vapor_h).sum()),
        outward_boundary_energy_w_m2_cell_sum=boundary_e,outward_boundary_vapor_kg_m2_s_cell_sum=boundary_w,
        water_transport=water_step.certificate,energy_transport=energy_step.certificate,phase=phase.certificate,
        scope='Fixed-wind resolved vapor/static-energy/terminal-rain phase composition; no momentum/radiation/ice feedback')
    return MultilevelMoist(phase.temperature_k,phase.vapor_kg_m2,final_e,phase.ground_rain_kg_m2,
        phase.ground_rain_enthalpy_j_m2,phase.fall_heat_j_m2,cert)
