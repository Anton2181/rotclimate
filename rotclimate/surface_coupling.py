"""First-order conservative coupling of finite liquid surface and moist air.

Local explicit radiation/exchange precede dynamics. All atmospheric rain is
returned to the finite surface with actual liquid enthalpy, exactly once.
No terrain, runoff, ice, deep-ocean heat supply or surface-stress closure.
"""
from dataclasses import dataclass
import numpy as np
from .column_forcing import two_stream_radiation,bulk_surface_exchange
from .moist_enthalpy import CP_VAPOR,CP_LIQUID,REFERENCE_K
from .column_thermodynamics import CP,LV
from .pressure_moist import PressureMoistState,gas_energy,enthalpy_phase
from .pressure_boundary import advance_boundary_with_convection


@dataclass
class SurfaceState:
    temperature_k: np.ndarray
    liquid_kg_m2: np.ndarray
    substrate_capacity_j_m2_k: np.ndarray


@dataclass
class SurfaceCouplingResult:
    atmosphere: PressureMoistState
    surface: SurfaceState
    rain_kg_m2: np.ndarray
    rain_enthalpy_j_m2: np.ndarray
    certificate: dict


def _field(value,shape,name,minimum=None):
    try:a=np.broadcast_to(np.asarray(value,float),shape).copy()
    except ValueError as exc:raise ValueError('Need matching '+name) from exc
    if not np.isfinite(a).all() or (minimum is not None and np.any(a<minimum)):raise ValueError('Invalid '+name)
    return a


def checked_surface(surface,shape):
    t=_field(surface.temperature_k,shape,'surface temperature',180.)
    m=_field(surface.liquid_kg_m2,shape,'surface liquid',0.)
    c=_field(surface.substrate_capacity_j_m2_k,shape,'substrate heat capacity')
    if np.any(t>330) or np.any(c<=0):raise ValueError('Need terrestrial surface temperature and positive substrate heat capacity')
    return SurfaceState(t,m,c)


def surface_enthalpy(surface):
    return (surface.substrate_capacity_j_m2_k+CP_LIQUID*surface.liquid_kg_m2)*(surface.temperature_k-REFERENCE_K)


def receive_precipitation(surface,rain_kg_m2,rain_enthalpy_j_m2):
    """Receive liquid mass AND its energy; capacity increases with liquid mass."""
    shape=np.broadcast_shapes(np.shape(surface.temperature_k),np.shape(surface.liquid_kg_m2),np.shape(surface.substrate_capacity_j_m2_k),np.shape(rain_kg_m2),np.shape(rain_enthalpy_j_m2));s=checked_surface(surface,shape)
    rain=_field(rain_kg_m2,shape,'returned rain',0.);h=_field(rain_enthalpy_j_m2,shape,'returned liquid enthalpy')
    if np.any((rain==0)&(h!=0)):raise ValueError('Liquid enthalpy requires liquid mass')
    mass=s.liquid_kg_m2+rain;enthalpy=surface_enthalpy(s)+h
    t=REFERENCE_K+enthalpy/(s.substrate_capacity_j_m2_k+CP_LIQUID*mass)
    return checked_surface(SurfaceState(t,mass,s.substrate_capacity_j_m2_k),shape)


def advance_surface_forcing(model,atmosphere,surface,dt_s,*,longwave_optical_depth,shortwave_optical_depth,
                            reference_height_m,roughness_m,scalar_roughness_m=None,availability_scale_kg_m2=100.,
                            solar_in_w_m2=0.,longwave_in_w_m2=0.,surface_albedo=.2,surface_emissivity=1.):
    """Explicit local flux step, then enthalpy phase and actual rain return.

    Reject exhausted liquid/vapor or thermal-domain violations; no clipped
    source or silently discarded dew. The caller must reduce an excessive dt.
    Returned atmosphere has zero pending rain: rain is already in the surface
    and separately exposed in SurfaceCouplingResult for accumulation/maps.
    """
    if not np.isfinite(dt_s) or dt_s<=0:raise ValueError('Need a finite positive forcing timestep')
    dt=float(dt_s);s=checked_surface(surface,model.shape);t=np.asarray(atmosphere.temperature_k,float);w=np.asarray(atmosphere.vapor_kg_m2,float)
    if t.shape!=model.mass.shape or w.shape!=t.shape or not np.isfinite(t).all() or not np.isfinite(w).all() or np.any(w<0) or np.any((t<180)|(t>330)|(w/model.mass>.2)):raise ValueError('Invalid forcing atmosphere')
    model._velocity(atmosphere.u_east,atmosphere.v_south)
    scale=_field(availability_scale_kg_m2,model.shape,'liquid availability scale')
    if np.any(scale<=0):raise ValueError('Need a positive liquid availability scale')
    radiation=two_stream_radiation(t,s.temperature_k,longwave_optical_depth,shortwave_optical_depth,
        solar_in_w_m2=solar_in_w_m2,longwave_in_w_m2=longwave_in_w_m2,surface_albedo=surface_albedo,surface_emissivity=surface_emissivity)
    uc=.5*(atmosphere.u_east[0,:,:-1]+atmosphere.u_east[0,:,1:]);vc=.5*(atmosphere.v_south[0,:-1]+atmosphere.v_south[0,1:])
    flux=bulk_surface_exchange(s.temperature_k,t[0],w[0]/model.mass[0],model.column.edges_pa[0],model.column.centers_pa[0],
        np.hypot(uc,vc),reference_height_m,roughness_m,scalar_roughness_m=scalar_roughness_m,
        water_availability=np.minimum(s.liquid_kg_m2/scale,1.))
    transfer=dt*flux['vapor_flux_kg_m2_s'];new_w=w.copy();new_w[0]+=transfer;liquid=s.liquid_kg_m2-transfer
    if np.any(new_w<0) or np.any(liquid<0):raise ValueError('Surface/vapor reservoir exhausted; reduce forcing timestep')
    old_h=gas_energy(t,w,model.mass);new_h=old_h+dt*radiation['atmospheric_heating_w_m2']
    exchange=dt*(flux['sensible_heat_w_m2']+flux['vapor_enthalpy_flux_w_m2']);new_h[0]+=exchange
    surface_h=surface_enthalpy(s)+dt*radiation['surface_heating_w_m2']-exchange
    new_t=(new_h-(LV-CP_VAPOR*REFERENCE_K)*new_w)/(CP*model.mass+CP_VAPOR*new_w)
    if not np.isfinite(new_t).all() or np.any((new_t<180)|(new_t>330)):raise ValueError('Forcing thermal state outside180–330K; reduce timestep')
    if model.phase_enabled:new_t,new_w,rain,rain_h=enthalpy_phase(new_t,new_w,model.mass,model.pressure)
    else:rain=np.zeros(model.shape);rain_h=np.zeros(model.shape)
    if np.any((new_t<180)|(new_t>330)|(new_w/model.mass>.2)):raise ValueError('Phase-adjusted forcing state outside supported domain; reduce timestep')
    liquid+=rain;surface_h+=rain_h
    surface_t=REFERENCE_K+surface_h/(s.substrate_capacity_j_m2_k+CP_LIQUID*liquid)
    new_surface=checked_surface(SurfaceState(surface_t,liquid,s.substrate_capacity_j_m2_k),model.shape)
    final_h=gas_energy(new_t,new_w,model.mass);external=dt*radiation['net_top_incoming_w_m2']
    energy_error=float(final_h.sum()+surface_enthalpy(new_surface).sum()-old_h.sum()-surface_enthalpy(s).sum()-external.sum())
    water_error=float(new_w.sum()+liquid.sum()-w.sum()-s.liquid_kg_m2.sum())
    energy_scale=max(float(abs(old_h).sum()+abs(surface_enthalpy(s)).sum()),1.)
    if abs(energy_error)>2000*np.finfo(float).eps*energy_scale or abs(water_error)>1e-10*max(float(w.sum()+s.liquid_kg_m2.sum()),1.):raise RuntimeError('Actual gas/surface energy or water forcing budget failed')
    cert=dict(actual_gas_surface_energy_source_residual_j_m2=energy_error/model.n,actual_gas_surface_water_residual_kg_m2=water_error/model.n,
        mean_net_top_incoming_w_m2=float(radiation['net_top_incoming_w_m2'].mean()),mean_vapor_transfer_kg_m2=float(transfer.mean()),
        mean_sensible_heat_w_m2=float(flux['sensible_heat_w_m2'].mean()),mean_vapor_enthalpy_flux_w_m2=float(flux['vapor_enthalpy_flux_w_m2'].mean()),
        mean_local_rain_returned_kg_m2=float(rain.mean()),all_rain_returned_to_surface=True,
        scope='First-order explicit local grey radiation and neutral heat/water exchange, then liquid phase and surface return. Top boundary declared externally; no dynamic midpoint or balanced-state claim.')
    clean=PressureMoistState(new_t,new_w,atmosphere.u_east.copy(),atmosphere.v_south.copy(),np.zeros(model.shape),np.zeros(model.shape),cert)
    return SurfaceCouplingResult(clean,new_surface,rain,rain_h,cert)


def advance_surface_coupled(model,atmosphere,surface,dt_s,*,convection_relaxation_s=3600.,neutral_tolerance_k=.01,
                            maximum_convective_sweeps=64,maximum_coupling_iterations=40,**forcing):
    """Local forcing -> conservative dynamics/convection -> actual rain return.

    Surface return is complete. Only result.rain_kg_m2 is a rain diagnostic;
    returned atmosphere has no pending rain that could be credited twice.
    """
    old_surface=checked_surface(surface,model.shape);old_x=model._velocity(atmosphere.u_east,atmosphere.v_south)
    old_energy=float(gas_energy(atmosphere.temperature_k,atmosphere.vapor_kg_m2,model.mass).sum()+.5*np.dot(old_x,old_x)+surface_enthalpy(old_surface).sum())
    old_water=float(atmosphere.vapor_kg_m2.sum()+old_surface.liquid_kg_m2.sum())
    local=advance_surface_forcing(model,atmosphere,old_surface,dt_s,**forcing)
    dynamic=advance_boundary_with_convection(model,local.atmosphere,dt_s,relaxation_s=convection_relaxation_s,
        neutral_tolerance_k=neutral_tolerance_k,max_sweeps=maximum_convective_sweeps,max_iterations=maximum_coupling_iterations)
    new_surface=receive_precipitation(local.surface,dynamic.ground_rain_kg_m2,dynamic.ground_rain_enthalpy_j_m2)
    c=dynamic.certificate;power=c['external_power_w_m2']+c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2']
    external=float(dt_s*(power+local.certificate['mean_net_top_incoming_w_m2']));water_out=float(dt_s*c['outward_boundary_vapor_kg_m2_s'])
    x=model._velocity(dynamic.u_east,dynamic.v_south)
    new_energy=float(gas_energy(dynamic.temperature_k,dynamic.vapor_kg_m2,model.mass).sum()+.5*np.dot(x,x)+surface_enthalpy(new_surface).sum())
    new_water=float(dynamic.vapor_kg_m2.sum()+new_surface.liquid_kg_m2.sum());ee=new_energy-old_energy-external*model.n;we=new_water-old_water+water_out*model.n
    if abs(ee)>3000*np.finfo(float).eps*max(abs(old_energy),1.) or abs(we)>1e-9*max(old_water,1.):raise RuntimeError('Actual coupled air/kinetic/surface/radiation/ports budget failed')
    rain=local.rain_kg_m2+dynamic.ground_rain_kg_m2;rain_h=local.rain_enthalpy_j_m2+dynamic.ground_rain_enthalpy_j_m2
    cert=dict(local_forcing=local.certificate,dynamics_before_surface_return=c,all_rain_returned_to_surface=True,
        net_external_energy_j_m2=external,net_outward_water_kg_m2=water_out,
        actual_total_energy_source_residual_j_m2=ee/model.n,actual_total_water_source_residual_kg_m2=we/model.n,
        scope='First-order local forcing then dynamics/convection with finite liquid/heat surface. All rain returned once; no ice/runoff/stress/deep heating, terrain or Earth adoption.')
    clean=PressureMoistState(dynamic.temperature_k,dynamic.vapor_kg_m2,dynamic.u_east,dynamic.v_south,np.zeros(model.shape),np.zeros(model.shape),cert)
    return SurfaceCouplingResult(clean,new_surface,rain,rain_h,cert)
