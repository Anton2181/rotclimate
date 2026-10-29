"""Conservative dry-pressure overlaps for vertical-resolution experiments.

Piecewise-constant source cells; identical pressure lids required. This changes
neither total pressure mass nor thermodynamic supply. Coarsening velocity loses
resolved kinetic variance: that signed loss is exposed, never silently heated.
Remapping is initialization, not a balanced-state or convergence guarantee.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import G,CP,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K
from .pressure_coordinate import pressure_coordinate
from .pressure_moist import gas_energy,enthalpy_phase


@dataclass(frozen=True)
class PressureOverlap:
    source_edges_pa: np.ndarray
    target_edges_pa: np.ndarray
    overlap_mass_kg_m2: np.ndarray
    source_mass_kg_m2: np.ndarray
    target_mass_kg_m2: np.ndarray

    def _source(self,values):
        a=np.asarray(values,float)
        if a.ndim<1 or a.shape[0]!=len(self.source_mass_kg_m2) or not np.isfinite(a).all():
            raise ValueError('Need finite matching source pressure cells')
        return a

    def extensive(self,amount):
        """Map a cell-integrated amount, not its concentration."""
        a=self._source(amount)
        return np.einsum('ij,j...->i...',self.overlap_mass_kg_m2/self.source_mass_kg_m2[None,:],a)

    def intensive(self,value):
        """Map a concentration per dry mass by exact pressure overlap."""
        a=self._source(value)
        return np.einsum('ij,j...->i...',self.overlap_mass_kg_m2/self.target_mass_kg_m2[:,None],a)

    def velocity(self,value):
        """Return mass-weighted velocity and signed unresolved KE per face area.

        Any coarsening variance is an unrepresented energy reservoir. A caller
        must explicitly account for it before treating this as a full model
        state transfer. Pure piecewise-constant refinements have zero loss up
        to roundoff. No conversion of lost resolved energy into heat is assumed.
        """
        a=self._source(value);b=self.intensive(a)
        old=.5*np.einsum('i,i...->...',self.source_mass_kg_m2,a*a)
        new=.5*np.einsum('i,i...->...',self.target_mass_kg_m2,b*b)
        loss=old-new
        if np.any(loss < -300*np.finfo(float).eps*np.maximum(old,1.)):
            raise RuntimeError('Pressure-overlap remap manufactured kinetic energy')
        return b,loss


def pressure_overlap(source_edges_pa,target_edges_pa):
    source=pressure_coordinate(source_edges_pa);target=pressure_coordinate(target_edges_pa)
    if source.edges_pa[0]!=target.edges_pa[0] or source.edges_pa[-1]!=target.edges_pa[-1]:
        raise ValueError('Remapping requires identical top and bottom pressure lids')
    upper=np.minimum(target.edges_pa[:-1,None],source.edges_pa[None,:-1])
    lower=np.maximum(target.edges_pa[1:,None],source.edges_pa[None,1:])
    mass=np.maximum(upper-lower,0.)/G
    np.testing.assert_allclose(mass.sum(0),source.cell_mass_kg_m2,rtol=1e-13,atol=1e-12)
    np.testing.assert_allclose(mass.sum(1),target.cell_mass_kg_m2,rtol=1e-13,atol=1e-12)
    arrays=[source.edges_pa,target.edges_pa,mass,source.cell_mass_kg_m2,target.cell_mass_kg_m2]
    for a in arrays:a.setflags(write=False)
    return PressureOverlap(*arrays)


@dataclass
class MoistColumnRemap:
    raw_temperature_k: np.ndarray
    raw_vapor_kg_m2: np.ndarray
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    rain_kg_m2: np.ndarray
    rain_enthalpy_j_m2: np.ndarray
    certificate: dict


def remap_moist_column(temperature_k,vapor_kg_m2,source_edges_pa,target_edges_pa,*,phase_solver=enthalpy_phase):
    """Overlap dry-mass gas enthalpy and vapor, then book actual target phase.

    Phase rain AND its liquid enthalpy must be transferred to the surface by the
    caller. No surface reservoir is created here and rain is not run rainfall.
    No terrain, vertical interpolation slope, hydrostatic rebalance, velocity
    projection or observed profile is inferred by this operator.
    """
    overlap=pressure_overlap(source_edges_pa,target_edges_pa)
    t=overlap._source(temperature_k);w=overlap._source(vapor_kg_m2)
    mass=overlap.source_mass_kg_m2.reshape((-1,)+(1,)*(t.ndim-1))
    if w.shape!=t.shape or np.any((t<180)|(t>330)|(w<0)|(w/mass>.2)) or not callable(phase_solver):
        raise ValueError('Need supported matching moist pressure-cell states and phase solver')
    old_h=gas_energy(t,w,mass);new_w=overlap.extensive(w);new_h=overlap.extensive(old_h)
    new_mass=overlap.target_mass_kg_m2.reshape((-1,)+(1,)*(t.ndim-1))
    raw_t=(new_h-(LV-CP_VAPOR*REFERENCE_K)*new_w)/(CP*new_mass+CP_VAPOR*new_w)
    coordinate=pressure_coordinate(target_edges_pa);pressure=coordinate.centers_pa.reshape((-1,)+(1,)*(t.ndim-1))
    adjusted_t,adjusted_w,rain,rain_h=phase_solver(raw_t,new_w,np.broadcast_to(new_mass,raw_t.shape),np.broadcast_to(pressure,raw_t.shape))
    if (not all(np.isfinite(a).all() for a in [adjusted_t,adjusted_w,rain,rain_h])
            or np.any((adjusted_t<180)|(adjusted_t>330)|(adjusted_w<0)|(adjusted_w/new_mass>.2)) or np.any(rain<0)):
        raise ValueError('Target pressure remap phase leaves supported state')
    final_h=gas_energy(adjusted_t,adjusted_w,new_mass)
    e=final_h.sum(0)+rain_h-old_h.sum(0);water=adjusted_w.sum(0)+rain-w.sum(0)
    er=float(np.max(abs(e)/np.maximum(abs(old_h).sum(0),1.)))
    wr=float(np.max(abs(water)/np.maximum(w.sum(0),1.)))
    if max(er,wr)>1e-11:raise RuntimeError('Actual pressure-overlap phase energy/water budget failed')
    return MoistColumnRemap(raw_t,new_w,adjusted_t,adjusted_w,rain,rain_h,
        dict(source_cells=len(overlap.source_mass_kg_m2),target_cells=len(overlap.target_mass_kg_m2),
             maximum_energy_rain_residual_j_m2=float(abs(e).max()),maximum_water_rain_residual_kg_m2=float(abs(water).max()),
             relative_energy_error=er,relative_water_error=wr,
             scope='Conservative piecewise-constant pressure overlap, identical lids, vapor and gas enthalpy transfer then target-pressure phase. Rain/liquid enthalpy returned separately. No balanced momentum state, new observations or vertical-resolution convergence claim.'))
