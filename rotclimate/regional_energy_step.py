"""Backward-Euler native-face vapor and moist-static-energy transport.

Isolated fixed-wind thermodynamic step. No phase change, radiation prediction,
pressure work beyond the hydrostatic static-energy approximation, or momentum
feedback is supplied. Positive source mass is water vapor, not external dry air.
"""
from dataclasses import dataclass
import numpy as np

from .column_thermodynamics import CP,G,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K
from .regional_mode_tracer import solve_mode_tracer


@dataclass
class EnergyStep:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    static_energy_j_m2: np.ndarray
    certificate: dict


def _field(value,shape,name,*,minimum=None):
    a=np.asarray(value,float)
    if a.shape==(2,):a=a[:,None,None]
    try:a=np.broadcast_to(a,shape).copy()
    except ValueError as exc:raise ValueError('Need matching '+name) from exc
    if not np.isfinite(a).all() or (minimum is not None and np.any(a<minimum)):
        raise ValueError('Need finite valid '+name)
    return a


def static_energy(temperature_k,vapor_kg_m2,layer_dry_mass_kg_m2,height_m):
    """Positive-reference gas enthalpy plus dry/vapor gravitational potential.

Relative to earlier gas enthalpy this adds constant cp_d*Md*T0. Dry mass is
stationary, so that reference shift does not affect any actual heat change.
"""
    t,w,m,z=map(np.asarray,[temperature_k,vapor_kg_m2,layer_dry_mass_kg_m2,height_m])
    return (CP*m+CP_VAPOR*w)*t+(LV-CP_VAPOR*REFERENCE_K)*w+G*(m+w)*z


def advance_energy(mode,column_mass,cell_m,temperature_k,vapor_kg_m2,height_m,dt_s,
                   external_temperature_k,external_mixing_ratio,*,lower_fraction=.25,
                   evaporation_kg_m2_s=0.,vapor_source_temperature_k=None,heating_w_m2=0.):
    """Move actual vapor and static energy with identical dry donor transport.

The steady donor tracer matrix with removal1/dt is exactly backward Euler:
its apparent 'source' is old state/dt plus physical source; its 'removal' is
new state/dt, NOT rain or heat dissipation. Dry mass is fixed by the mode's
continuity. Vapor injection carries its supplied temperature and local
potential energy; heating is an explicitly supplied external energy rate.

Layer heights are fixed in this step, lower first. Including g*z makes dry
static energy cp*T+g*z the conserved donor quantity, rather than temperature.
It captures hydrostatic ascent cooling in a fixed-level approximation. Do NOT
also add a second adiabatic c²divU temperature tendency from the dry mode.
"""
    mass=np.asarray(column_mass,float)
    if mass.ndim!=2 or not np.isfinite(mass).all() or np.any(mass<=0):
        raise ValueError('Need positive finite 2D dry column mass')
    a=float(lower_fraction)
    if not np.isfinite(a) or not 0<a<1 or not np.isfinite(dt_s) or dt_s<=0:
        raise ValueError('Need positive timestep and lower fraction in(0,1)')
    shape=(2,)+mass.shape
    t=_field(temperature_k,shape,'temperature',minimum=150.)
    w=_field(vapor_kg_m2,shape,'vapor',minimum=0.)
    z=_field(height_m,shape,'height',minimum=0.)
    ext_t=_field(external_temperature_k,shape,'external temperature',minimum=150.)
    ext_q=_field(external_mixing_ratio,shape,'external mixing ratio',minimum=0.)
    evap=_field(evaporation_kg_m2_s,shape,'vapor source',minimum=0.)
    heat=_field(heating_w_m2,shape,'external heating')
    source_t=t if vapor_source_temperature_k is None else _field(vapor_source_temperature_k,shape,'source vapor temperature',minimum=150.)
    m=np.stack([a*mass,(1-a)*mass])
    if np.any(t>370) or np.any(ext_t>370) or np.any(source_t>370) or np.any(z[1]<=z[0]):
        raise ValueError('Need temperatures150–370K and upper height above lower')
    energy=static_energy(t,w,m,z)
    vapor_h=LV+CP_VAPOR*(source_t-REFERENCE_K)+G*z
    external_power=heat+evap*vapor_h
    energy_rhs=energy/dt_s+external_power
    if np.any(energy_rhs<0):raise ValueError('Timestep/heating would require negative static energy')
    vapor_step=solve_mode_tracer(mode,mass,cell_m,w/dt_s+evap,1/dt_s,ext_q,lower_fraction=a)
    external_specific=CP*ext_t+ext_q*(LV+CP_VAPOR*(ext_t-REFERENCE_K))+G*(1+ext_q)*z
    energy_step=solve_mode_tracer(mode,mass,cell_m,energy_rhs,1/dt_s,external_specific,lower_fraction=a)
    new_w,new_energy=vapor_step.water,energy_step.water
    new_t=(new_energy-(LV-CP_VAPOR*REFERENCE_K)*new_w-G*(m+new_w)*z)/(CP*m+CP_VAPOR*new_w)
    if not np.isfinite(new_t).all() or np.any((new_t<150)|(new_t>370)):
        raise RuntimeError('Transported energy implies temperature outside150–370K; choose resolved levels/timestep')
    reconstruction=static_energy(new_t,new_w,m,z)-new_energy
    boundary_energy=np.asarray(energy_step.certificate['outward_boundary_water_per_cell_s'])
    boundary_vapor=np.asarray(vapor_step.certificate['outward_boundary_water_per_cell_s'])
    energy_error=float(((new_energy-energy)/dt_s-external_power).sum()+boundary_energy.sum())
    water_error=float(((new_w-w)/dt_s-evap).sum()+boundary_vapor.sum())
    cert=dict(column_energy_budget_residual_w_m2_cell_sum=energy_error,
        column_water_budget_residual_kg_m2_s_cell_sum=water_error,
        maximum_static_energy_reconstruction_j_m2=float(np.abs(reconstruction).max()),
        total_supplied_heating_w_m2_cell_sum=float(heat.sum()),
        total_vapor_source_enthalpy_w_m2_cell_sum=float((evap*vapor_h).sum()),
        outward_boundary_energy_w_m2_cell_sum=boundary_energy.tolist(),
        outward_boundary_vapor_kg_m2_s_cell_sum=boundary_vapor.tolist(),
        energy_transport=energy_step.certificate,vapor_transport=vapor_step.certificate,
        dt_s=float(dt_s),minimum_temperature_k=float(new_t.min()),maximum_temperature_k=float(new_t.max()),
        scope='Fixed-wind native-face backward-Euler vapor/static-energy step; fixed heights, no phase change or momentum/radiative feedback')
    scale=max(float(np.abs(energy/dt_s).sum()),float(np.abs(external_power).sum()),1.)
    if abs(energy_error)>1e-10*scale or abs(water_error)>1e-10*max(float((w/dt_s+evap).sum()),1.):
        raise RuntimeError('Actual energy/water change failed external-source and boundary budget')
    return EnergyStep(new_t,new_w,new_energy,cert)
