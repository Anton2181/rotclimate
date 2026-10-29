"""Common-pressure hydrostatic gradient diagnostic over terrain.

A shared analytic reference is removed before differencing geopotential. Layer
anomalies are constant within their own log-pressure intervals; each horizontal
port averages the geopotential difference over its exact pressure opening.
This is not yet a momentum/pressure-work-compatible weather integration scheme.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import G,RD
from .terrain_hydrostatics import reference_geopotential
from .terrain_apertures import horizontal_apertures


def _mean_log_pressure(bottom,top):
    """Exact pressure-weighted log(p) mean, stable for thin intervals."""
    r=(bottom-top)/top;small=abs(r)<1e-3
    # Integral_0^r log(1+x) dx /r = sum (-1)^(n+1) r^n/(n*(n+1)).
    correction=np.zeros_like(r)
    for n in range(7,0,-1):correction=r*(correction+(-1.)**(n+1)/(n*(n+1)))
    regular=np.zeros_like(r);np.divide(np.log1p(r),r,out=regular,where=~small)
    regular=(1+r)*regular-1
    return np.log(top)+np.where(small,correction,regular)


@dataclass(frozen=True)
class TerrainPressureForces:
    east_ms2: np.ndarray  # left level, right level, y, face
    south_ms2: np.ndarray  # north level, south level, face, x


def common_pressure_force(grid,elevation_m,temperature_anomaly_k,cell_m,*,reference_temperature_k=288.15,reference_pressure_pa=101325.,reference_lapse_k_m=.0065):
    """Average -dPhi/dx at shared pressure, with explicit common reference.

    Elevation is actual fixed ground height. Reference temperature/pressure are
    spatially uniform scalars. Anomalies are relative to the same analytic dry
    reference T(p), constant per layer; zero anomaly means hydrostatic rest only
    when ps and ground height also match that reference. No below-ground value
    is extrapolated. Exterior ports are not represented.
    """
    horizontal_apertures(grid)  # validates native pressure geometry
    p=grid.edges_pa;h=np.asarray(elevation_m,float);delta=np.asarray(temperature_anomaly_k,float)
    if h.shape!=p.shape[1:] or delta.shape!=p[:-1].shape or not np.isfinite(h).all() or not np.isfinite(delta).all() or not np.isfinite(cell_m) or cell_m<=0:raise ValueError('Need matching finite ground/anomaly fields and positive grid spacing')
    if np.ndim(reference_temperature_k) or np.ndim(reference_pressure_pa):raise ValueError('Reference temperature and pressure must be common spatial scalars')
    ground_offset=G*h-reference_geopotential(p[0],reference_temperature_k,sea_level_pressure_pa=reference_pressure_pa,lapse_k_m=reference_lapse_k_m)
    integrated=delta*np.log(p[:-1]/p[1:]);below=np.concatenate([np.zeros_like(integrated[:1]),np.cumsum(integrated[:-1],axis=0)],axis=0)
    base=ground_offset+RD*below
    def pair(left,right,dl,dr,bl,br):
        bottom=np.minimum(left[:-1,None],right[None,:-1]);top=np.maximum(left[1:,None],right[None,1:]);opened=bottom>top
        safe_bottom=np.where(opened,bottom,top);mean=_mean_log_pressure(safe_bottom,top)
        phi_left=bl[:,None]+RD*dl[:,None]*(np.log(left[:-1,None])-mean)
        phi_right=br[None,:]+RD*dr[None,:]*(np.log(right[None,:-1])-mean)
        return np.where(opened,(phi_left-phi_right)/cell_m,0.)
    east=pair(p[:,:,:-1],p[:,:,1:],delta[:,:,:-1],delta[:,:,1:],base[:,:,:-1],base[:,:,1:])
    south=pair(p[:,:-1],p[:,1:],delta[:,:-1],delta[:,1:],base[:,:-1],base[:,1:])
    return TerrainPressureForces(east,south)
