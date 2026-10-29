"""Closed-domain conservative upwind transport on terrain pressure ports.

Vertical mass flux comes from the actual layer dry-mass divergence. It closes
at both rigid boundaries for column-mass-admissible horizontal flow. This is a
transport building block, not open-boundary weather or a coupled momentum step.
"""
import numpy as np
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import splu
from .column_thermodynamics import G
from .terrain_apertures import horizontal_apertures,mass_flux_divergence


class TerrainTransport:
    def __init__(self,grid,east_speed_ms,south_speed_ms,cell_m,dt_s):
        self.shape=grid.dry_mass_kg_m2.shape;self.mass=grid.dry_mass_kg_m2.copy();self.dt=float(dt_s)
        a=horizontal_apertures(grid);u=np.asarray(east_speed_ms,float);v=np.asarray(south_speed_ms,float)
        if not np.isfinite([cell_m,dt_s]).all() or min(cell_m,dt_s)<=0 or u.shape!=a.east_kg_m2.shape or v.shape!=a.south_kg_m2.shape or not np.isfinite(u).all() or not np.isfinite(v).all():raise ValueError('Need finite native face velocities and positive spacing/time step')
        divergence=mass_flux_divergence(a,u,v,cell_m);self.interface_omega_pa_s=np.zeros_like(grid.edges_pa);self.interface_omega_pa_s[:-1]=-G*np.cumsum(divergence[::-1],axis=0)[::-1]
        scale=max(float(abs(self.interface_omega_pa_s).max()),1e-8)
        if abs(self.interface_omega_pa_s[0]).max()>1e-9*scale+1e-12:raise ValueError('Horizontal flow does not close fixed column dry mass')
        ids=np.arange(self.mass.size).reshape(self.shape);rows=[];cols=[];values=[]
        def port(left,right,flux):
            positive=np.maximum(flux,0);negative=np.maximum(-flux,0)
            rows.extend([left,right,right,left]);cols.extend([left,right,left,right]);values.extend([positive,negative,-positive,-negative])
        for mu,velocity,kind in [(a.east_kg_m2,u,'east'),(a.south_kg_m2,v,'south')]:
            k,l,j,i=np.nonzero(mu);jr,ir=(j,i+1) if kind=='east' else (j+1,i)
            port(ids[k,j,i],ids[l,jr,ir],mu[k,l,j,i]*velocity[k,l,j,i]/cell_m)
        # Positive omega is downward: upper layer k -> lower layer k-1.
        k,j,i=np.indices((self.shape[0]-1,*self.shape[1:]));k=k+1
        port(ids[k,j,i].ravel(),ids[k-1,j,i].ravel(),(self.interface_omega_pa_s[1:-1]/G).ravel())
        advection=coo_matrix((np.concatenate(values),(np.concatenate(rows),np.concatenate(cols))),shape=(self.mass.size,self.mass.size)).tocsc()
        reference=max(float(abs(advection).sum(axis=1).max()),1e-100)
        self.maximum_native_dry_mass_residual_kg_m2_s=float(abs(np.asarray(advection.sum(axis=1)).ravel()).max())
        if self.maximum_native_dry_mass_residual_kg_m2_s>1e-10*reference+1e-13:raise RuntimeError('Actual horizontal/vertical layer mass does not close')
        if abs(np.asarray(advection.sum(axis=0)).ravel()).max()>1e-12*reference+1e-13:raise RuntimeError('Interior tracer fluxes do not cancel')
        self.matrix=diags(self.mass.ravel()/self.dt)+advection;self.factor=splu(self.matrix.tocsc())

    def advance(self,specific_tracer,*,source_per_area_s=0.,nonnegative=True):
        q=np.asarray(specific_tracer,float);source=np.asarray(source_per_area_s,float)
        try:source=np.broadcast_to(source,self.shape)
        except ValueError as exc:raise ValueError('Need matching tracer source') from exc
        if q.shape!=self.shape or not np.isfinite(q).all() or not np.isfinite(source).all() or (nonnegative and np.any(q<0)):raise ValueError('Need finite supported tracer/source fields')
        rhs=(self.mass*q/self.dt+source).ravel()
        if nonnegative and np.any(rhs<0):raise ValueError('Cooling/removal exceeds the available tracer source')
        new=self.factor.solve(rhs).reshape(self.shape);residual=(self.matrix@new.ravel()-rhs);scale=abs(self.matrix)@abs(new.ravel())+abs(rhs);relative=float(np.max(abs(residual)/np.maximum(scale,np.finfo(float).tiny)))
        if relative>1e-12 or (nonnegative and np.min(new)<0):raise RuntimeError('Actual native tracer solve failed')
        balance=float((self.mass*(new-q)).sum()-self.dt*source.sum())
        return new,dict(actual_tracer_source_residual_per_area_sum=balance,maximum_rowwise_backward_error=relative,maximum_native_dry_mass_residual_kg_m2_s=self.maximum_native_dry_mass_residual_kg_m2_s,source_sum_per_area_s=float(source.sum()),scope='Closed-domain implicit upwind native-pressure fluxes and continuity-derived vertical transfer; one shared factor per velocity/time step, no tracer renormalization or clipping.')
