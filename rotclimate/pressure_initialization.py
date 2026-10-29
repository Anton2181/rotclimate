"""Declared transfer of archived model temperature/two water reservoirs.

The regional smoke test flattens terrain using one fixed environmental lapse,
then initializes a pressure column. Lower/upper vapor integrals are preserved;
uniform relative humidity within each source reservoir is a reconstruction
assumption. Initial phase-conversion rain is returned separately from run rain.
No observations or archived winds enter this pure transfer operator.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import G,RD,CP
from .pressure_coordinate import pressure_coordinate
from .phase_adjustment import saturation_vapor_mass
from .pressure_moist import enthalpy_phase,gas_energy


def select_recorded_day(days,scored_indices,solved_days,target_day):
    d,s,all_days=np.asarray(days,float),np.asarray(scored_indices),np.asarray(solved_days,float)
    if (d.ndim!=1 or s.shape!=d.shape or all_days.ndim!=1 or s.dtype.kind not in 'iu'
            or not np.isfinite(d).all() or not np.isfinite(all_days).all() or not np.isfinite(target_day)
            or np.any((s<0)|(s>=len(all_days)))):raise ValueError('Need valid scored-day mapping')
    found=np.flatnonzero(np.isclose(d,target_day,rtol=0,atol=1e-9))
    if len(found)!=1:raise ValueError('Declared model day must match one scored record exactly')
    index=int(s[found[0]])
    if not np.isclose(all_days[index],target_day,rtol=0,atol=1e-9):raise ValueError('Solved/scored calendar mapping differs')
    return index


@dataclass
class PressureInitialization:
    raw_temperature_k: np.ndarray
    raw_vapor_kg_m2: np.ndarray
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    initial_rain_kg_m2: np.ndarray
    initial_rain_enthalpy_j_m2: np.ndarray
    certificate: dict


def initialize_archived_column(surface_temperature_c,lower_water_kg_m2,upper_water_kg_m2,elevation_m,
                               pressure_edges_pa,*,lower_cell_count=1,lapse_k_m=.006,cap_temperature_k=200.):
    ts,lower,upper,height=map(lambda a:np.asarray(a,float),[surface_temperature_c,lower_water_kg_m2,upper_water_kg_m2,elevation_m])
    if (ts.ndim!=2 or min(ts.shape)<2 or any(a.shape!=ts.shape for a in [lower,upper,height])
            or not all(np.isfinite(a).all() for a in [ts,lower,upper,height]) or np.any(lower<0) or np.any(upper<0)
            or not np.isfinite([lapse_k_m,cap_temperature_k]).all() or not 0<lapse_k_m<G/CP):
        raise ValueError('Need matching finite regional model fields, nonnegative water and stable fixed lapse')
    coordinate=pressure_coordinate(pressure_edges_pa);n=len(coordinate.centers_pa)
    if not isinstance(lower_cell_count,int) or isinstance(lower_cell_count,bool) or not 1<=lower_cell_count<n:
        raise ValueError('Need a nonempty lower/upper pressure split')
    sea_level=ts+273.15+lapse_k_m*height
    if not 150<=cap_temperature_k<=330 or np.any(sea_level<cap_temperature_k) or np.any(sea_level>330):
        raise ValueError('Declared flattened reference exceeds supported temperature range; no clipping')
    p=coordinate.centers_pa[:,None,None];ps=coordinate.edges_pa[0]
    cap_pressure=ps*(cap_temperature_k/sea_level)**(G/(RD*lapse_k_m))
    temperature=np.where(p>=cap_pressure[None],sea_level[None]*(p/ps)**(RD*lapse_k_m/G),cap_temperature_k)
    mass=np.broadcast_to(coordinate.cell_mass_kg_m2[:,None,None],temperature.shape)
    pressure=np.broadcast_to(p,temperature.shape);capacity=saturation_vapor_mass(temperature,mass,pressure)
    water=np.empty_like(temperature);k=lower_cell_count
    water[:k]=lower[None]*capacity[:k]/capacity[:k].sum(0)
    water[k:]=upper[None]*capacity[k:]/capacity[k:].sum(0)
    lower_error=float(np.max(abs(water[:k].sum(0)-lower)));upper_error=float(np.max(abs(water[k:].sum(0)-upper)))
    if np.any(water/mass>.2):raise ValueError('Transferred water exceeds dilute pressure-model domain')
    adjusted_t,adjusted_w,rain,rain_h=enthalpy_phase(temperature,water,mass,pressure)
    before=gas_energy(temperature,water,mass);after=gas_energy(adjusted_t,adjusted_w,mass)
    energy_error=after.sum(0)+rain_h-before.sum(0);water_error=adjusted_w.sum(0)+rain-lower-upper
    relative=float(np.max(abs(energy_error))/max(float(np.max(np.sum(abs(before),axis=0))),1.))
    water_relative=float(np.max(abs(water_error))/max(float(np.max(lower+upper)),1.))
    if max(relative,water_relative)>1e-12:raise RuntimeError('Initial conversion water/enthalpy/rain budget failed')
    cert=dict(lower_cell_count=k,lower_dry_mass_fraction=float(coordinate.cell_mass_kg_m2[:k].sum()/coordinate.cell_mass_kg_m2.sum()),
        fixed_lapse_k_m=lapse_k_m,isothermal_cap_k=cap_temperature_k,maximum_lower_water_remap_error_kg_m2=lower_error,
        maximum_upper_water_remap_error_kg_m2=upper_error,relative_initial_phase_energy_error=relative,
        relative_initial_phase_water_error=water_relative,initial_conversion_mean_rain_mm=float(rain.mean()),
        scope='Point-sampled archived model fields, terrain flattened by fixed lapse, uniform RH within each water reservoir. Initial conversion rain booked separately. Not balanced Earth weather or a climate forecast.')
    return PressureInitialization(temperature,water,adjusted_t,adjusted_w,rain,rain_h,cert)
