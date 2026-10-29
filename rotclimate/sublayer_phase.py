"""Conservative nested liquid-phase columns with retained fine thermal state.

Resolve saturation/falling rain on a fine grid without increasing momentum
degrees of freedom. Restricted coarse T is an energy-equivalent mean; it need
not itself satisfy a single-cell saturation curve. No coarse recondensation
or humidity clipping is applied. Fine state is returned for retention; repeated
coarse reconstruction is a mixing assumption, not an identity.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import CP,G
from .moist_enthalpy import CP_VAPOR,LV,REFERENCE_K,gas_enthalpy
from .multilevel_phase import adjust_multilevel_fall,MultilevelPhase


def _grid(coarse_edges,fine_edges):
    c,f=np.asarray(coarse_edges,float),np.asarray(fine_edges,float)
    if (c.ndim!=1 or f.ndim!=1 or len(c)<3 or len(f)<len(c)
            or not np.isfinite(c).all() or not np.isfinite(f).all()
            or c[0]!=0 or f[0]!=0 or np.any(np.diff(c)<=0) or np.any(np.diff(f)<=0)
            or c[-1]!=f[-1]):raise ValueError('Need nested ascending grids from ground0 with identical endpoints')
    ids=np.searchsorted(f,c)
    if np.any(ids>=len(f)) or not np.allclose(f[ids],c,rtol=0,atol=1e-9):
        raise ValueError('Fine cells must not straddle coarse interfaces')
    return c,f,ids


def _sum(value,ids):return np.stack([np.sum(value[a:b],axis=0) for a,b in zip(ids[:-1],ids[1:])])


def _state(t,w,m,levels):
    t,w,m=map(lambda a:np.asarray(a,float),[t,w,m])
    if (t.ndim<1 or t.shape[0]!=levels or w.shape!=t.shape or m.shape!=t.shape
            or not all(np.isfinite(a).all() for a in [t,w,m]) or np.any((t<180)|(t>330))
            or np.any(w<0) or np.any(m<=0) or np.any(w/m>.2)):
        raise ValueError('Need matching terrestrial temperatures, positive dry masses and dilute nonnegative vapor')
    return t,w,m


def _energy(t,w,m,z):
    zz=z.reshape((-1,)+(1,)*(t.ndim-1))
    return gas_enthalpy(t,w,m)+G*(m+w)*zz


def _slopes(value,z):
    """Monotone centered minmod; endpoints use their single interior slope."""
    diff=np.diff(value,axis=0)/np.diff(z).reshape((-1,)+(1,)*(value.ndim-1))
    result=np.empty_like(value);result[0],result[-1]=diff[0],diff[-1]
    left,right=diff[:-1],diff[1:]
    result[1:-1]=np.where(left*right>0,np.sign(left)*np.minimum(abs(left),abs(right)),0.)
    return result


@dataclass
class RestrictedThermal:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    dry_mass_kg_m2: np.ndarray
    static_energy_j_m2: np.ndarray


def restrict_thermal(fine_temperature_k,fine_vapor_kg_m2,fine_mass_kg_m2,fine_edges_m,coarse_edges_m):
    """Exact water/dry mass/static-energy restriction, including geopotential.

    Mean T is diagnosed from the summed gas static energy at coarse cell
    center heights. It is not an average of saturation or a phase adjustment.
    """
    c,f,ids=_grid(coarse_edges_m,fine_edges_m)
    t,w,m=_state(fine_temperature_k,fine_vapor_kg_m2,fine_mass_kg_m2,len(f)-1)
    z=.5*(f[:-1]+f[1:]);zc=.5*(c[:-1]+c[1:])
    water,dry,energy=(_sum(a,ids) for a in [w,m,_energy(t,w,m,z)])
    zz=zc.reshape((-1,)+(1,)*(t.ndim-1))
    temp=REFERENCE_K+(energy-LV*water-G*(dry+water)*zz)/(CP*dry+CP_VAPOR*water)
    if np.any((temp<180)|(temp>330)) or not np.isfinite(temp).all():
        raise ValueError('Energy-equivalent restricted temperature outside supported terrestrial domain')
    return RestrictedThermal(temp,water,dry,energy)


@dataclass
class RefinedThermal:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    certificate: dict


def refine_thermal(temperature_k,vapor_kg_m2,coarse_mass_kg_m2,coarse_edges_m,
                   fine_edges_m,fine_mass_kg_m2,*,temperature_gradient_k_m=None):
    """Mass-centered limited q/T reconstruction with exact parent energy.

    Fine dry masses are supplied by the declared reference. Limited q slopes
    are reduced if needed to keep q>=0, while retaining each parent's water.
    A parent-wise temperature offset enforces its actual gas+potential energy.
    A supplied temperature gradient is a declared shape, not a heat source.
    """
    c,f,ids=_grid(coarse_edges_m,fine_edges_m)
    t,w,m=_state(temperature_k,vapor_kg_m2,coarse_mass_kg_m2,len(c)-1)
    mf=np.asarray(fine_mass_kg_m2,float)
    if mf.shape!=(len(f)-1,)+t.shape[1:] or not np.isfinite(mf).all() or np.any(mf<=0):
        raise ValueError('Need matching positive finite fine dry masses')
    supplied=_sum(mf,ids)
    if not np.allclose(supplied,m,rtol=1e-12,atol=1e-12):raise ValueError('Fine dry masses must sum to actual parent dry mass')
    z=.5*(f[:-1]+f[1:]);zc=.5*(c[:-1]+c[1:]);q=w/m
    q_slope=_slopes(q,zc)
    if temperature_gradient_k_m is None:t_slope=_slopes(t,zc)
    else:
        gradient=np.asarray(temperature_gradient_k_m,float)
        if gradient.shape==(len(c)-1,):gradient=gradient.reshape((-1,)+(1,)*(t.ndim-1))
        try:t_slope=np.broadcast_to(gradient,t.shape)
        except ValueError as exc:raise ValueError('Need matching finite temperature gradient') from exc
        if not np.isfinite(t_slope).all():raise ValueError('Need finite temperature gradient')
    tf,wf=np.empty_like(mf),np.empty_like(mf);energy=_energy(t,w,m,zc)
    maximum_correction=0.;limited=0
    for k,(a,b) in enumerate(zip(ids[:-1],ids[1:])):
        zz=z[a:b].reshape((-1,)+(1,)*(t.ndim-1));zbar=np.sum(mf[a:b]*zz,axis=0)/supplied[k]
        offset=zz-zbar;perturb=q_slope[k]*offset;negative=np.maximum(-np.min(perturb,axis=0),0.)
        factor=np.minimum(1.,np.divide(q[k],negative,out=np.ones_like(negative),where=negative>0))
        limited+=int(np.count_nonzero(factor<1))
        qf=q[k]+factor*perturb
        if np.any(qf<0) or np.any(qf>.2):raise ValueError('Reconstructed vapor outside dilute nonnegative domain')
        wf[a:b]=mf[a:b]*qf;tf[a:b]=t[k]+t_slope[k]*offset
        current=np.sum(gas_enthalpy(tf[a:b],wf[a:b],mf[a:b])+G*(mf[a:b]+wf[a:b])*zz,axis=0)
        correction=(energy[k]-current)/np.sum(CP*mf[a:b]+CP_VAPOR*wf[a:b],axis=0)
        tf[a:b]+=correction;maximum_correction=max(maximum_correction,float(np.max(abs(correction))))
    if not np.isfinite(tf).all() or np.any((tf<180)|(tf>330)):raise ValueError('Reconstructed temperature outside180–330K')
    parent_water=_sum(wf,ids)-w;parent_energy=_sum(_energy(tf,wf,mf,z),ids)-energy
    relative_water=float(np.max(abs(parent_water))/max(float(np.max(w)),1.))
    relative_energy=float(np.max(abs(parent_energy))/max(float(np.max(abs(energy))),1.))
    if max(relative_water,relative_energy)>1e-12:raise RuntimeError('Nested reconstruction failed actual parent water/static energy')
    return RefinedThermal(tf,wf,dict(maximum_parent_water_error_kg_m2=float(np.max(abs(parent_water))),
        maximum_parent_static_energy_error_j_m2=float(np.max(abs(parent_energy))),
        relative_parent_water_error=relative_water,relative_parent_static_energy_error=relative_energy,
        maximum_conservative_temperature_offset_k=maximum_correction,limited_parent_q_slopes=limited))


@dataclass
class SublayerPhase:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    fine_initial: RefinedThermal
    fine_phase: MultilevelPhase
    certificate: dict


def adjust_sublayer_phase(temperature_k,vapor_kg_m2,coarse_mass_kg_m2,coarse_edges_m,
                         fine_edges_m,fine_mass_kg_m2,fine_pressure_pa,*,temperature_gradient_k_m=None):
    initial=refine_thermal(temperature_k,vapor_kg_m2,coarse_mass_kg_m2,coarse_edges_m,
        fine_edges_m,fine_mass_kg_m2,temperature_gradient_k_m=temperature_gradient_k_m)
    phase=adjust_multilevel_fall(initial.temperature_k,initial.vapor_kg_m2,fine_mass_kg_m2,fine_pressure_pa,fine_edges_m)
    coarse=restrict_thermal(phase.temperature_k,phase.vapor_kg_m2,fine_mass_kg_m2,fine_edges_m,coarse_edges_m)
    c=np.asarray(coarse_edges_m);zc=.5*(c[:-1]+c[1:])
    before=_energy(np.asarray(temperature_k),np.asarray(vapor_kg_m2),np.asarray(coarse_mass_kg_m2),zc)
    energy_error=coarse.static_energy_j_m2.sum(0)+phase.ground_rain_enthalpy_j_m2-before.sum(0)
    water_error=coarse.vapor_kg_m2.sum(0)+phase.ground_rain_kg_m2-np.sum(vapor_kg_m2,axis=0)
    relative=float(np.max(abs(energy_error))/max(float(np.max(np.sum(abs(before),axis=0))),1.))
    relative_water=float(np.max(abs(water_error))/max(float(np.max(np.sum(vapor_kg_m2,axis=0))),1.))
    if max(relative,relative_water)>1e-12:raise RuntimeError('Fine phase and coarse restriction failed actual atmosphere/rain water/energy')
    cert=dict(coarse_levels=len(c)-1,fine_levels=len(fine_edges_m)-1,
        maximum_column_energy_plus_rain_error_j_m2=float(np.max(abs(energy_error))),
        maximum_column_water_plus_rain_error_kg_m2=float(np.max(abs(water_error))),
        relative_column_energy_plus_rain_error=relative,relative_column_water_plus_rain_error=relative_water,
        reconstruction=initial.certificate,phase=phase.certificate,
        scope='Nested fixed-pressure liquid-only phase; coarse means preserve water/static energy but need not obey a single saturation curve. Retain fine state; repeated reconstruction implies mixing. No circulation/ice/radiation adoption.')
    return SublayerPhase(coarse.temperature_k,coarse.vapor_kg_m2,phase.ground_rain_kg_m2,
        phase.ground_rain_enthalpy_j_m2,initial,phase,cert)
