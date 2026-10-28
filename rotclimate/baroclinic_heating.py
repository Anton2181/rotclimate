"""First hydrostatic Boussinesq mode with rigid lids and constant stability.

Derives a gravity-wave speed and heating projection rather than treating a
temperature target or arbitrary pressure thickness as mode heating. This is
an idealized vertical atmosphere, not the compressible Earth column model.
"""
from dataclasses import dataclass
import numpy as np

from .column_thermodynamics import CP, G


@dataclass
class FirstModeHeating:
    forcing_m2_s3: np.ndarray
    wave_speed_ms: float
    velocity_scale: float
    physical_modal_energy_factor: float
    column_heating_w_m2: np.ndarray
    buoyancy_forcing_amplitude_m_s3: np.ndarray
    captured_buoyancy_forcing_norm_fraction: np.ndarray
    certificate: dict


def project_first_mode(layer_heating_w_m2, total_dry_mass_kg_m2, vertical_edges_fraction,
                       *, depth_m, buoyancy_frequency_s, reference_temperature_k,
                       lower_fraction=.25):
    """Project accounted layer heat on sin(pi*z/H), z positive upward.

Uniform reference density M/H and constant N: horizontal velocity/pressure
profiles are -cos(pi*z/H), buoyancy and vertical velocity are sin(pi*z/H).
For layer-specific heating h=Hlayer/Mlayer, buoyancy source is g*h/(cp*Tref).
Its sine coefficient Bdot1=2 int_0^1 bdot(s) sin(pi*s) ds gives Qamp=Bdot1/m,
where m=pi/H and c=N/m. Layer-average wind contrast uses scale
S=sin(pi*a)/(pi*a*(1-a)), so the existing solver receives Q=S*Qamp.

The returned velocity scale connects continuous mode amplitude to lower/upper
mean winds -(1-a)U and aU. Multiply solver energy/work by 1/(2*S²) to obtain
the continuous first-mode reference-mass budget. This normalization matters:
coarse layer means alone do not capture within-layer velocity variance.

Piecewise-constant layer heating is integrated exactly in the vertical. Net
column heat is retained, including the part outside this one vertical mode.
Its full moist/internal energy is not the same as modal available-energy work.
"""
    edges=np.asarray(vertical_edges_fraction,float)
    heat=np.asarray(layer_heating_w_m2,float)
    mass=np.asarray(total_dry_mass_kg_m2,float)
    scales=np.asarray([depth_m,buoyancy_frequency_s,reference_temperature_k],float)
    a=float(lower_fraction)
    if (edges.ndim!=1 or len(edges)<2 or not np.isfinite(edges).all()
            or edges[0]!=0 or edges[-1]!=1 or np.any(np.diff(edges)<=0)):
        raise ValueError("Need strictly ascending vertical fractions from zero to one")
    if (heat.ndim<1 or heat.shape[0]!=len(edges)-1 or mass.shape!=heat.shape[1:]
            or not np.isfinite(heat).all() or not np.isfinite(mass).all() or np.any(mass<=0)):
        raise ValueError("Need matching finite layer heating and positive total dry mass")
    if not np.isfinite(scales).all() or np.any(scales<=0) or not np.isfinite(a) or not 0<a<1:
        raise ValueError("Need positive depth, stability and reference temperature; lower fraction in(0,1)")
    h,n,tref=scales
    dz=np.diff(edges).reshape((-1,)+(1,)*mass.ndim)
    specific=heat/(dz*mass)
    buoyancy=G*specific/(CP*tref)
    weights=(2/np.pi*(np.cos(np.pi*edges[:-1])-np.cos(np.pi*edges[1:])))
    weights=weights.reshape(dz.shape)
    first=np.sum(weights*buoyancy,axis=0)
    wavenumber=np.pi/h
    velocity_scale=float(np.sin(np.pi*a)/(np.pi*a*(1-a)))
    forcing=velocity_scale*first/wavenumber
    full_norm=np.sum(dz*buoyancy**2,axis=0)
    captured_norm=.5*first**2
    captured=np.divide(captured_norm,full_norm,out=np.zeros_like(full_norm),where=full_norm>0)
    if np.any(captured>1+1e-12):
        raise RuntimeError("First-mode projection exceeds the full heating norm")
    cert=dict(depth_m=float(h),buoyancy_frequency_s=float(n),reference_temperature_k=float(tref),
        vertical_wavenumber_per_m=float(wavenumber),lower_fraction=a,
        wave_speed_ms=float(n/wavenumber),velocity_scale=velocity_scale,
        physical_modal_energy_factor=1/(2*velocity_scale**2),
        minimum_captured_buoyancy_forcing_norm_fraction=float(captured.min()),
        maximum_captured_buoyancy_forcing_norm_fraction=float(captured.max()),
        scope="Constant-N uniform-reference-density hydrostatic Boussinesq first mode, rigid lids; no compressible vertical eigenmode, radiation or full atmospheric energy solution")
    return FirstModeHeating(forcing,float(n/wavenumber),velocity_scale,1/(2*velocity_scale**2),
        heat.sum(axis=0),first,captured,cert)
