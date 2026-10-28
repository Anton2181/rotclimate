"""Liquid-only multilevel phase/fall equilibrium with gravitational drag heat.

Uses the same fixed cell/face geometry as resolved hydrostatic transport.
Instantaneous terminal fall, uniform drag per distance, no ice/cloud storage
or retained precipitation kinetic energy. No momentum feedback is implied.
"""
from dataclasses import dataclass
import numpy as np

from .column_thermodynamics import CP,G
from .moist_enthalpy import gas_enthalpy,liquid_enthalpy
from .phase_adjustment import _saturation
from .falling_water_energy import _equilibrium


@dataclass
class MultilevelPhase:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    downward_liquid_kg_m2: np.ndarray  # leaving each cell through its lower face
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    condensation_kg_m2: np.ndarray
    evaporation_kg_m2: np.ndarray
    fall_heat_j_m2: np.ndarray
    certificate: dict


def adjust_multilevel_fall(temperature_k,vapor_kg_m2,layer_mass_kg_m2,pressure_pa,
                           vertical_edges_m,cell_height_m=None):
    """Top-to-bottom phase roots; every traversed cell gets local fall work.

For cell k receiving liquid Lin, drag heat is
g*Lin*(edge_above-zk)+g*Lout*(zk-edge_below), where Lout=Lin-x and x is
the vapor change. Thus the root uses extra=g*Lin*cell_width and beta=g*
(zk-edge_below) in Hnew=Hinitial+extra-beta*x. Both incoming liquid sensible
enthalpy and newly produced outgoing rain participate in the equilibrium.
The ground is at edge0=0 and all surviving rain leaves at lower-cell T.
"""
    t,w,m,p=[np.asarray(a,float) for a in [temperature_k,vapor_kg_m2,layer_mass_kg_m2,pressure_pa]]
    edges=np.asarray(vertical_edges_m,float)
    if (t.ndim<1 or t.shape[0]<2 or any(a.shape!=t.shape for a in [w,m,p])
            or edges.shape!=(t.shape[0]+1,) or not np.isfinite(edges).all()
            or edges[0]!=0 or np.any(np.diff(edges)<=0)):
        raise ValueError('Need matching vertical states and ascending edges from ground0')
    expand=(-1,)+(1,)*(t.ndim-1)
    if cell_height_m is None:z=np.broadcast_to((.5*(edges[:-1]+edges[1:])).reshape(expand),t.shape).copy()
    else:
        z=np.asarray(cell_height_m,float)
        if z.shape==(t.shape[0],):z=z.reshape(expand)
        try:z=np.broadcast_to(z,t.shape).copy()
        except ValueError as exc:raise ValueError('Need matching cell heights') from exc
    lower=edges[:-1].reshape(expand);upper=edges[1:].reshape(expand)
    if (not all(np.isfinite(a).all() for a in [t,w,m,p,z]) or np.any(m<=0)
            or np.any(w<0) or np.any(w/m>.2) or np.any((t<180)|(t>330))
            or np.any((p<10000)|(p>110000)) or np.any(np.diff(p,axis=0)>=0)
            or np.any(z<=lower) or np.any(z>=upper) or not np.isfinite(_saturation(t,p)).all()):
        raise ValueError('Need terrestrial dilute liquid states with decreasing pressure and heights inside their cells')
    new_t=np.empty_like(t);new_w=np.empty_like(w);outgoing=np.empty_like(w)
    condensed=np.empty_like(w);evaporated=np.empty_like(w);heat=np.empty_like(w)
    incoming=np.zeros_like(w[0]);liquid_t=t[-1];max_phase_error=0.
    for k in range(t.shape[0]-1,-1,-1):
        base=G*incoming*(edges[k+1]-edges[k]);beta=G*(z[k]-edges[k])
        tk,wk,rain,change,error=_equilibrium(t[k],w[k],m[k],p[k],incoming,liquid_t,
            extra_heat=base,feedback_per_vapor_change=beta)
        new_t[k],new_w[k],outgoing[k]=tk,wk,rain
        condensed[k],evaporated[k]=np.maximum(-change,0),np.maximum(change,0)
        heat[k]=G*incoming*(edges[k+1]-z[k])+G*rain*(z[k]-edges[k])
        incoming,liquid_t=rain,tk;max_phase_error=max(max_phase_error,error)
    rain=outgoing[0];rain_h=liquid_enthalpy(new_t[0],rain)
    before=gas_enthalpy(t,w,m)+G*(m+w)*z
    after=gas_enthalpy(new_t,new_w,m)+G*(m+new_w)*z
    energy_error=after.sum(0)+rain_h-before.sum(0)
    water_error=w.sum(0)-new_w.sum(0)-rain
    potential_loss=G*np.sum((w-new_w)*z,axis=0)
    heat_error=heat.sum(0)-potential_loss
    tolerance=500*np.finfo(float).eps*np.maximum(np.abs(before).sum(0)+CP*m.sum(0)*273.15,1.)
    if np.any(np.abs(energy_error)>tolerance) or np.any(heat<0):
        raise RuntimeError('Multilevel atmospheric static energy plus exported rain failed')
    cert=dict(levels=t.shape[0],maximum_column_water_residual_kg_m2=float(np.abs(water_error).max()),
        maximum_static_energy_plus_rain_residual_j_m2=float(np.abs(energy_error).max()),
        maximum_fall_heat_minus_potential_release_residual_j_m2=float(np.abs(heat_error).max()),
        maximum_layer_phase_feedback_residual_j_m2=max_phase_error,
        scope='Resolved fixed-pressure liquid-only equilibrium and instantaneous terminal fall; no ice/drop kinetic storage/momentum feedback')
    return MultilevelPhase(new_t,new_w,outgoing,rain,rain_h,condensed,evaporated,heat,cert)
