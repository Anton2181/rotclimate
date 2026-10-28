"""Conservative fixed-wind transport + falling-water phase composition.

This closes the specified gas-static-energy/ground-rain budget, not the
momentum/radiative/kinetic budget of a complete atmosphere.
"""
from dataclasses import dataclass
import numpy as np

from .falling_water_energy import adjust_falling_water
from .regional_energy_step import _field,advance_energy,static_energy


@dataclass
class MoistStep:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    fall_dissipation_j_m2: np.ndarray
    certificate: dict


def advance_moist(mode,column_mass,cell_m,temperature_k,vapor_kg_m2,height_m,
                  representative_pressure_pa,interface_height_m,dt_s,
                  external_temperature_k,external_mixing_ratio,*,lower_fraction=.25,
                  evaporation_kg_m2_s=0.,vapor_source_temperature_k=None,heating_w_m2=0.):
    """Backward-Euler static-energy/vapor transport followed by exact phase.

Rain falls to ground0, carrying liquid enthalpy; drag heating from the actual
lost potential is deposited along the represented upper/lower fall path.
Momentum/winds stay fixed. No new c²divU cooling is added: transport already
includes hydrostatic ascent cooling. This is first-order operator splitting.
"""
    mass=np.asarray(column_mass,float);shape=(2,)+mass.shape
    t=_field(temperature_k,shape,'temperature');w=_field(vapor_kg_m2,shape,'vapor',minimum=0.)
    z=_field(height_m,shape,'height',minimum=0.);p=_field(representative_pressure_pa,shape,'pressure',minimum=10000.)
    a=float(lower_fraction);m=np.stack([a*mass,(1-a)*mass])
    moved=advance_energy(mode,mass,cell_m,t,w,z,dt_s,external_temperature_k,external_mixing_ratio,
        lower_fraction=a,evaporation_kg_m2_s=evaporation_kg_m2_s,
        vapor_source_temperature_k=vapor_source_temperature_k,heating_w_m2=heating_w_m2)
    phase=adjust_falling_water(moved.temperature_k,moved.vapor_kg_m2,m,p,z,interface_height_m)
    final_e=static_energy(phase.temperature_k,phase.vapor_kg_m2,m,z)
    phase_energy=final_e+np.stack([phase.ground_rain_enthalpy_j_m2,np.zeros_like(mass)])-moved.static_energy_j_m2
    # Phase conserves the COLUMN, not each layer: rain carries enthalpy and
    # gravitational work between layers, so only sum vertically here.
    phase_error=phase_energy.sum(0)
    initial_e=static_energy(t,w,m,z)
    cert=moved.certificate
    supplied=cert['total_supplied_heating_w_m2_cell_sum']+cert['total_vapor_source_enthalpy_w_m2_cell_sum']
    boundary=sum(cert['outward_boundary_energy_w_m2_cell_sum'])
    combined_energy=float(((final_e-initial_e).sum()+phase.ground_rain_enthalpy_j_m2.sum())/dt_s-supplied+boundary)
    evap=_field(evaporation_kg_m2_s,shape,'vapor source',minimum=0.)
    combined_water=float(((phase.vapor_kg_m2-w).sum()+phase.ground_rain_kg_m2.sum())/dt_s-evap.sum()
                         +sum(cert['outward_boundary_vapor_kg_m2_s_cell_sum']))
    scale=max(float(np.abs(initial_e/dt_s).sum()),1.)
    if abs(combined_energy)>1e-10*scale or abs(combined_water)>1e-10*max(float(w.sum()/dt_s),1.):
        raise RuntimeError('Composed moist transport/rain step failed actual energy/water ledger')
    result_cert=dict(combined_energy_residual_w_m2_cell_sum=combined_energy,
        combined_water_residual_kg_m2_s_cell_sum=combined_water,
        maximum_phase_static_energy_residual_j_m2=float(np.abs(phase_error).max()),
        transport=cert,phase=phase.certificate,
        scope='Fixed-wind first-order transport/phase splitting, terminal drag heating; no momentum feedback or full atmospheric radiative/mechanical energy')
    return MoistStep(phase.temperature_k,phase.vapor_kg_m2,phase.ground_rain_kg_m2,
        phase.ground_rain_enthalpy_j_m2,phase.fall_dissipation_j_m2,result_cert)
