"""Dry hydrostatic geometry for a future atmosphere that follows terrain.

This module does not alter the current flat-bottomed prototype. Variable
column masses require compatible momentum, pressure work and boundary fluxes
before these interfaces can be used in a prognostic model.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import G,RD


def surface_pressure_from_height(elevation_m,sea_level_temperature_k,*,sea_level_pressure_pa=101325.,lapse_k_m=.0065):
    """Integrate dp/dz=-p*g/(R*T) for T(z)=T0-lapse*z.

    Temperatures are dry-gas reference temperatures, not observed forcing.
    The zero-lapse limit is isothermal and continuous. No pressure floor,
    underground atmosphere, or hidden renormalization is introduced.
    """
    h,t0,p0=np.broadcast_arrays(*[np.asarray(a,float) for a in [elevation_m,sea_level_temperature_k,sea_level_pressure_pa]])
    if (not all(np.isfinite(a).all() for a in [h,t0,p0]) or np.any((t0<180)|(t0>350)|(p0<=0)) or not np.isfinite(lapse_k_m) or not 0<=lapse_k_m<=.012):
        raise ValueError('Need finite terrain, positive pressure, supported dry reference temperature/lapse')
    surface_t=t0-lapse_k_m*h
    if np.any((surface_t<150)|(surface_t>350)):raise ValueError('Terrain extends outside the declared hydrostatic temperature domain')
    if lapse_k_m==0:log_ratio=-G*h/(RD*t0)
    else:log_ratio=G/(RD*lapse_k_m)*np.log1p(-lapse_k_m*h/t0)
    pressure=p0*np.exp(log_ratio)
    if np.any(~np.isfinite(pressure)|(pressure<=0)):raise ValueError('Unrepresentable terrain pressure')
    return pressure


def reference_geopotential(pressure_pa,sea_level_temperature_k,*,sea_level_pressure_pa=101325.,lapse_k_m=.0065):
    """Analytic geopotential of the same dry hydrostatic reference profile.

    For matching reference pressure/temperature, phi(ps(h))=g*h. This is a
    diagnostic for later terrain pressure-gradient balance, not a force scheme.
    """
    p,t0,p0=np.broadcast_arrays(*[np.asarray(a,float) for a in [pressure_pa,sea_level_temperature_k,sea_level_pressure_pa]])
    if (not all(np.isfinite(a).all() for a in [p,t0,p0]) or np.any((p<=0)|(p0<=0)|(t0<180)|(t0>350)) or not np.isfinite(lapse_k_m) or not 0<=lapse_k_m<=.012):raise ValueError('Invalid dry reference profile')
    log_ratio=np.log(p/p0)
    if lapse_k_m==0:return -RD*t0*log_ratio
    return -G*t0/lapse_k_m*np.expm1(RD*lapse_k_m/G*log_ratio)


@dataclass(frozen=True)
class TerrainPressureGrid:
    edges_pa: np.ndarray
    centers_pa: np.ndarray
    dry_mass_kg_m2: np.ndarray
    surface_pressure_pa: np.ndarray
    top_pressure_pa: float


def terrain_pressure_grid(surface_pressure_pa,sigma_edges,*,top_pressure_pa=38000.):
    """Hybrid p=ptop+sigma*(ps-ptop), bottom first, fixed pressure top.

    sigma must include exactly1 and0, strictly decreasing. A column whose
    surface intersects or exceeds the top is rejected, never clipped. Dry
    layer masses vary horizontally; they sum to (ps-ptop)/g per column.
    """
    ps=np.asarray(surface_pressure_pa,float);sigma=np.asarray(sigma_edges,float)
    if (not np.isfinite(ps).all() or not np.isfinite(top_pressure_pa) or top_pressure_pa<=0 or np.any(ps<=top_pressure_pa)
            or sigma.ndim!=1 or len(sigma)<2 or not np.isfinite(sigma).all() or sigma[0]!=1 or sigma[-1]!=0 or np.any(np.diff(sigma)>=0)):
        raise ValueError('Need positive atmospheric depth and strictly decreasing sigma interfaces from1 to0')
    s=sigma.reshape((-1,)+(1,)*ps.ndim);edges=top_pressure_pa+s*(ps-top_pressure_pa);mass=-np.diff(edges,axis=0)/G
    if np.any(mass<=0):raise ValueError('Collapsed pressure cell')
    return TerrainPressureGrid(edges,.5*(edges[:-1]+edges[1:]),mass,ps.copy(),float(top_pressure_pa))
