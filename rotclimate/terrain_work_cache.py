"""Precompute the unchanged dry terrain compression quadrature.

For the declared reference plus a constant anomaly in each layer, compression
is exactly C0@U + anomaly*(C1@U). Only static geometry/reference coefficients are
cached. No physical flux, tolerance, time index or momentum equation changes.
"""
from types import MethodType
import numpy as np
from scipy.sparse import coo_matrix
from numpy.polynomial.legendre import leggauss
from .column_thermodynamics import G,RD
from .terrain_apertures import horizontal_apertures,mass_flux_divergence
from .terrain_pressure_work import TerrainCompression,compression_power
from .phase_backend import bind_dependencies


class TerrainWorkCache:
    def __init__(self,grid,cell_m,*,reference_temperature_k=288.15,reference_pressure_pa=101325.,reference_lapse_k_m=.0065):
        self.grid=grid;self.dx=float(cell_m);self.reference=dict(reference_temperature_k=reference_temperature_k,reference_pressure_pa=reference_pressure_pa,reference_lapse_k_m=reference_lapse_k_m);self.edges=grid.edges_pa.copy();self.mass=grid.dry_mass_kg_m2.copy();self.apertures=horizontal_apertures(grid);a=self.apertures
        zero_u=np.zeros_like(a.east_kg_m2);zero_v=np.zeros_like(a.south_kg_m2);compression_power(grid,zero_u,zero_v,self.dx,np.zeros_like(self.mass),**self.reference)
        self.ex=np.nonzero(a.east_kg_m2);self.sy=np.nonzero(a.south_kg_m2);self.nu=len(self.ex[0]);nz,ny,nx=self.mass.shape;columns=[[] for _ in range(ny*nx)];port_id=0
        for index,kind in [(self.ex,'east'),(self.sy,'south')]:
            for kl,kr,j,i in zip(*index):
                jr,ir=(j,i+1) if kind=='east' else (j+1,i);bottom=min(self.edges[kl,j,i],self.edges[kr,jr,ir]);top=max(self.edges[kl+1,j,i],self.edges[kr+1,jr,ir]);columns[j*nx+i].append((top,bottom,1.,port_id));columns[jr*nx+ir].append((top,bottom,-1.,port_id));port_id+=1
        nodes,weights=leggauss(8);alpha=RD*reference_lapse_k_m/G;rows=[];cols=[];c0=[];c1=[];self.minimum_reference=np.full(self.mass.shape,np.inf);self.maximum_reference=np.full(self.mass.shape,-np.inf)
        for j in range(ny):
            for i in range(nx):
                entries=np.asarray(columns[j*nx+i]);top,bottom,sign,ids=entries.T;ids=ids.astype(int);breaks=np.unique(np.r_[self.edges[:,j,i],top,bottom]);middle=.5*(breaks[:-1]+breaks[1:]);half=.5*np.diff(breaks);points=middle[:,None]+half[:,None]*nodes;level=np.searchsorted(-self.edges[:,j,i],-middle)-1;temperature=reference_temperature_k*(points/reference_pressure_pa)**alpha
                omega_per_speed=-np.clip(points[:,:,None]-top,0,bottom-top)*sign/self.dx
                kernel=RD/points*weights*half[:,None]/G
                segment1=np.sum(kernel[:,:,None]*omega_per_speed,axis=1);segment0=np.sum((kernel*temperature)[:,:,None]*omega_per_speed,axis=1);local0=np.zeros((nz,len(ids)));local1=np.zeros_like(local0);np.add.at(local0,level,segment0);np.add.at(local1,level,segment1)
                np.minimum.at(self.minimum_reference[:,j,i],level,temperature.min(1));np.maximum.at(self.maximum_reference[:,j,i],level,temperature.max(1))
                rows.extend(np.repeat(np.arange(nz)*ny*nx+j*nx+i,len(ids)));cols.extend(np.tile(ids,nz));c0.extend(local0.ravel());c1.extend(local1.ravel())
        shape=(self.mass.size,port_id);self.c0=coo_matrix((c0,(rows,cols)),shape=shape).tocsc();self.c1=coo_matrix((c1,(rows,cols)),shape=shape).tocsc();self.c0.eliminate_zeros();self.c1.eliminate_zeros()

    def evaluate(self,grid,east_speed_ms,south_speed_ms,cell_m,temperature_anomaly_k,*,reference_temperature_k=288.15,reference_pressure_pa=101325.,reference_lapse_k_m=.0065):
        reference=dict(reference_temperature_k=reference_temperature_k,reference_pressure_pa=reference_pressure_pa,reference_lapse_k_m=reference_lapse_k_m)
        if grid is not self.grid or float(cell_m)!=self.dx or reference!=self.reference or not np.array_equal(grid.edges_pa,self.edges) or not np.array_equal(grid.dry_mass_kg_m2,self.mass):raise ValueError('Cached geometry/reference changed; construct a new work cache')
        a=self.apertures;u=np.asarray(east_speed_ms,float);v=np.asarray(south_speed_ms,float);delta=np.asarray(temperature_anomaly_k,float)
        if u.shape!=a.east_kg_m2.shape or v.shape!=a.south_kg_m2.shape or delta.shape!=self.mass.shape or not all(np.isfinite(x).all() for x in [u,v,delta]):raise ValueError('Need matching finite velocity/anomaly fields')
        if np.any((self.minimum_reference+delta<180)|(self.maximum_reference+delta>330)):raise ValueError('Unsupported dry reference/anomaly temperature')
        speeds=np.r_[u[self.ex],v[self.sy]];power=(self.c0@speeds+delta.ravel()*(self.c1@speeds)).reshape(self.mass.shape);div=mass_flux_divergence(a,u,v,self.dx);omega=np.zeros_like(self.edges);omega[:-1]=-G*np.cumsum(div[::-1],axis=0)[::-1];boundary=float(abs(omega[0]).max());scale=max(float(abs(omega).max()),1e-8)
        if boundary>1e-9*scale+1e-12:raise ValueError('Horizontal ports do not close fixed column mass at the ground')
        return TerrainCompression(power,omega,boundary)


def cached_work_model(base):
    """Instance-local dependency binding preserves the full advance code body."""
    class CachedTerrainWorkModel(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.work_cache=TerrainWorkCache(self.grid,self.dx,**self.reference)
            self.advance=MethodType(bind_dependencies(base.advance,compression_power=self.work_cache.evaluate),self)
    return CachedTerrainWorkModel
