"""All-level linear dry pressure/momentum/thermal evolution on shared cells.

Energy-adjoint Lorenz vertical grid, closed horizontal C-grid, no vertical
mode truncation. The pressure-invisible thermal computational mode is retained
and reported. Velocity is restricted to zero depth-mass-mean baroclinic flow;
divergence-free barotropic motion is excluded. This is not a nonlinear moist
or complete mechanical energy law.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import bmat,eye,kron
from scipy.sparse.linalg import splu
from .hydrostatic_wave import HydrostaticWave


@dataclass
class CellWaveState:
    u_east: np.ndarray
    v_south: np.ndarray
    buoyancy_cells: np.ndarray
    certificate: dict


class CellThermalWave:
    def __init__(self,column,shape,cell_m,coriolis,*,momentum_drag_s=0.,buoyancy_drag_s=0.):
        # Reuse tested horizontal C-grid geometry and skew rotation only.
        # Its single-mode vertical state/evolution is never used here.
        base=HydrostaticWave(column,0,shape,cell_m,coriolis,
            momentum_drag_s=momentum_drag_s,buoyancy_drag_s=buoyancy_drag_s)
        self.column,self.shape,self.dx=column,base.shape,base.dx
        self.n,self.nz,self.nu,self.nv=base.n,len(column.centers_m),base.nu,base.nv
        self.r,self.rt=base.r,base.rt
        m,e=column.cell_mass_kg_m2,column.thermal_energy_weight
        self.velocity_scale=np.sqrt(m/column.total_mass)
        self.thermal_scale=np.sqrt(e/column.total_mass)
        vertical=np.sqrt(m)[:,None]*column.hydrostatic_matrix/np.sqrt(e)[None,:]
        rotation=base.operator[:base.nu,base.nu:base.nu+base.nv]
        rotation=kron(eye(self.nz),rotation,format='csc')
        px=kron(vertical,base.gx,format='csc');py=kron(vertical,base.gy,format='csc')
        self.n_u,self.n_v,self.n_b=self.nz*self.nu,self.nz*self.nv,self.nz*self.n
        self.operator=bmat([[self.r*eye(self.n_u),rotation,px],[-rotation.T,self.r*eye(self.n_v),py],
            [-px.T,-py.T,self.rt*eye(self.n_b)]],format='csc')
        self.identity=eye(self.n_u+self.n_v+self.n_b,format='csc');self.factors={}

    def _field(self,value,shape,name):return HydrostaticWave._field(value,shape,name)

    def _pack(self,state):
        ny,nx=self.shape
        u=self._field(state.u_east,(self.nz,ny,nx+1),'all-level east velocity')
        v=self._field(state.v_south,(self.nz,ny+1,nx),'all-level south velocity')
        b=self._field(state.buoyancy_cells,(self.nz,ny,nx),'cell buoyancy')
        if np.any(u[:,:,[0,-1]]) or np.any(v[:,[0,-1]]):raise ValueError('Closed walls require exactly zero exterior normal flow')
        mass=self.column.cell_mass_kg_m2[:,None,None]
        for velocity in [u,v]:
            mean=np.sum(mass*velocity,axis=0);scale=np.sum(np.abs(mass*velocity),axis=0)
            # LU roundoff can leave minute flow where the exact velocity is
            # zero. Use an explicit absolute mean-velocity tolerance as well
            # as a relative test; do not project or reset the solved state.
            if np.any(np.abs(mean)>1e-10*scale+self.column.total_mass*1e-13):
                raise ValueError('Velocity violates the closed-lid zero column-mass-mean flow')
        return np.r_[(u[:,:,1:-1]*self.velocity_scale[:,None,None]).ravel(),
            (v[:,1:-1]*self.velocity_scale[:,None,None]).ravel(),(b*self.thermal_scale[:,None,None]).ravel()]

    def _unpack(self,x,certificate):
        ny,nx=self.shape;u=np.zeros((self.nz,ny,nx+1));v=np.zeros((self.nz,ny+1,nx))
        u[:,:,1:-1]=x[:self.n_u].reshape(self.nz,ny,nx-1)/self.velocity_scale[:,None,None]
        v[:,1:-1]=x[self.n_u:self.n_u+self.n_v].reshape(self.nz,ny-1,nx)/self.velocity_scale[:,None,None]
        b=x[self.n_u+self.n_v:].reshape(self.nz,ny,nx)/self.thermal_scale[:,None,None]
        return CellWaveState(u,v,b,certificate)

    def initial_state(self,buoyancy_cells,u_east=0.,v_south=0.):
        ny,nx=self.shape
        state=CellWaveState(self._field(u_east,(self.nz,ny,nx+1),'east velocity'),
            self._field(v_south,(self.nz,ny+1,nx),'south velocity'),
            self._field(buoyancy_cells,(self.nz,ny,nx),'cell buoyancy'),{})
        x=self._pack(state)
        state.certificate=dict(kinetic_plus_thermal_available_energy_m2_s2=float(.5*np.dot(x,x)/self.n),
            **self.column.energy_partition(state.buoyancy_cells))
        return state

    def pressure_cells(self,state):
        self._pack(state);return self.column.pressure_from_buoyancy(state.buoyancy_cells)

    def vertical_velocity(self,state):
        self._pack(state)
        div=(np.diff(state.u_east,axis=2)+np.diff(state.v_south,axis=1))/self.dx
        return self.column.vertical_velocity(div)

    def advance(self,state,dt_s,*,buoyancy_source_s3=0.):
        if not np.isfinite(dt_s) or dt_s<=0:raise ValueError('Need finite positive timestep')
        q=self._field(buoyancy_source_s3,(self.nz,)+self.shape,'physical cell buoyancy source')
        x=self._pack(state);source=np.r_[np.zeros(self.n_u+self.n_v),(q*self.thermal_scale[:,None,None]).ravel()]
        dt=float(dt_s)
        if dt not in self.factors:self.factors[dt]=splu(self.identity+.5*dt*self.operator)
        new=self.factors[dt].solve(x-.5*dt*(self.operator@x)+dt*source)
        if not np.isfinite(new).all():raise FloatingPointError('Nonfinite all-level thermal wave state')
        mid=.5*(x+new);residual=(new-x)/dt+self.operator@mid-source
        equation_error=float(np.abs(residual).max()*dt)
        if equation_error>1e-9*max(1.,float(np.abs(x).max()),float(np.abs(new).max())):raise RuntimeError('All-level thermal equations failed')
        old_e=.5*np.dot(x,x)/self.n;new_e=.5*np.dot(new,new)/self.n
        work=float(np.dot(mid,source)/self.n)
        loss=float((self.r*np.dot(mid[:self.n_u+self.n_v],mid[:self.n_u+self.n_v])
            +self.rt*np.dot(mid[self.n_u+self.n_v:],mid[self.n_u+self.n_v:]))/self.n)
        balance=float(new_e-old_e-dt*(work-loss))
        relative=abs(balance)/max(abs(old_e),abs(new_e),dt*(abs(work)+loss),1e-30)
        if relative>1e-9:raise RuntimeError('All-level kinetic/thermal energy budget failed')
        result=self._unpack(new,dict(kinetic_plus_thermal_available_energy_m2_s2=float(new_e),
            midpoint_source_work_m2_s3=work,midpoint_damping_m2_s3=loss,
            energy_budget_residual_m2_s2=balance,relative_energy_budget_error=relative,
            maximum_equation_residual_weighted_velocity_ms=equation_error,dt_s=dt,
            scope='All-cell linear dry hydrostatic Lorenz-grid dynamics; null thermal mode retained, no nonlinear moist/radiative/terrain feedback'))
        self._pack(result)
        mass=self.column.cell_mass_kg_m2[:,None,None]
        result.certificate['maximum_column_mass_mean_velocity_ms']=float(max(
            np.max(np.abs(np.sum(mass*a,axis=0)))/self.column.total_mass for a in [result.u_east,result.v_south]))
        result.certificate.update(self.column.energy_partition(result.buoyancy_cells))
        return result
