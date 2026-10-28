"""Transient pressure/momentum/buoyancy feedback for one vertical eigenmode.

Closed Cartesian horizontal C-grid, rigid-lid anelastic vertical state. This
does not add a second adiabatic update to the earlier two-box moisture model;
it evolves one internally consistent linear dry thermal/momentum state.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import bmat,coo_matrix,eye
from scipy.sparse.linalg import splu


@dataclass
class WaveState:
    u_east: np.ndarray
    v_south: np.ndarray
    pressure_amplitude: np.ndarray
    certificate: dict


class HydrostaticWave:
    def __init__(self,vertical,mode_index,shape,cell_m,coriolis,*,momentum_drag_s=0.,buoyancy_drag_s=0.):
        if (not isinstance(mode_index,int) or isinstance(mode_index,bool)
                or not 0<=mode_index<len(vertical.phase_speeds_ms)
                or len(shape)!=2 or any(not isinstance(n,int) or isinstance(n,bool) or n<2 for n in shape)):
            raise ValueError('Need valid vertical mode index and at least two horizontal cells per axis')
        if (not np.isfinite([cell_m,momentum_drag_s,buoyancy_drag_s]).all() or cell_m<=0
                or momentum_drag_s<0 or buoyancy_drag_s<0):
            raise ValueError('Need positive spacing and finite nonnegative damping')
        self.vertical,self.mode_index,self.shape=vertical,mode_index,tuple(shape)
        self.dx=float(cell_m);self.c=float(vertical.phase_speeds_ms[mode_index])
        self.r=float(momentum_drag_s);self.rt=float(buoyancy_drag_s)
        ny,nx=self.shape;self.n=ny*nx;self.nu=ny*(nx-1);self.nv=(ny-1)*nx
        self.f=self._field(coriolis,self.shape,'Coriolis')
        ids=np.arange(self.n).reshape(self.shape)
        iu=np.arange(self.nu).reshape(ny,nx-1);iv=np.arange(self.nv).reshape(ny-1,nx)
        def gradient(left,right):
            nf=left.size;row=np.arange(nf)
            return coo_matrix((np.r_[-np.ones(nf),np.ones(nf)]/self.dx,
                (np.tile(row,2),np.r_[left.ravel(),right.ravel()])),shape=(nf,self.n)).tocsr()
        self.gx=gradient(ids[:,:-1],ids[:,1:]);self.gy=gradient(ids[:-1],ids[1:])
        rows=[];cols=[];values=[]
        for j in range(ny):
            for i in range(nx):
                for k in [i-1,i]:
                    if not 0<=k<nx-1:continue
                    for l in [j-1,j]:
                        if not 0<=l<ny-1:continue
                        rows.append(iu[j,k]);cols.append(iv[l,i]);values.append(.25*self.f[j,i])
        rotation=coo_matrix((values,(rows,cols)),shape=(self.nu,self.nv)).tocsr()
        cx,cy=self.c*self.gx,self.c*self.gy
        self.operator=bmat([[self.r*eye(self.nu),rotation,cx],[-rotation.T,self.r*eye(self.nv),cy],
                             [-cx.T,-cy.T,self.rt*eye(self.n)]],format='csc')
        self.identity=eye(self.nu+self.nv+self.n,format='csc');self.factors={}

    @staticmethod
    def _field(value,shape,name):
        try:value=np.broadcast_to(np.asarray(value,float),shape).copy()
        except ValueError as exc:raise ValueError('Need matching '+name) from exc
        if not np.isfinite(value).all():raise ValueError('Need finite '+name)
        return value

    def _pack(self,state):
        ny,nx=self.shape
        u=self._field(state.u_east,(ny,nx+1),'east face velocity')
        v=self._field(state.v_south,(ny+1,nx),'south face velocity')
        phi=self._field(state.pressure_amplitude,self.shape,'pressure amplitude')
        if np.any(u[:,[0,-1]]) or np.any(v[[0,-1]]):raise ValueError('Closed walls require exactly zero exterior normal flow')
        return np.r_[u[:,1:-1].ravel(),v[1:-1].ravel(),phi.ravel()/self.c]

    def _unpack(self,vector,certificate):
        ny,nx=self.shape;u=np.zeros((ny,nx+1));v=np.zeros((ny+1,nx))
        u[:,1:-1]=vector[:self.nu].reshape(ny,nx-1)
        v[1:-1]=vector[self.nu:self.nu+self.nv].reshape(ny-1,nx)
        return WaveState(u,v,self.c*vector[self.nu+self.nv:].reshape(self.shape),certificate)

    def initial_state(self,pressure_amplitude,u_east=0.,v_south=0.):
        ny,nx=self.shape
        state=WaveState(self._field(u_east,(ny,nx+1),'east face velocity'),
            self._field(v_south,(ny+1,nx),'south face velocity'),
            self._field(pressure_amplitude,self.shape,'pressure amplitude'),{})
        x=self._pack(state)
        state.certificate=dict(modal_energy_m2_s2=float(.5*np.dot(x,x)/self.n),
            wave_speed_ms=self.c,scope='One hydrostatic vertical mode, closed horizontal walls, linear dry state')
        return state

    def from_buoyancy(self,buoyancy):
        b=np.asarray(buoyancy,float)
        if b.shape!=(len(self.vertical.centers_m)-1,)+self.shape or not np.isfinite(b).all():
            raise ValueError('Need matching finite interface buoyancy')
        pressure=self.vertical.pressure_from_buoyancy(b)
        amplitudes=self.vertical.project_pressure(pressure)
        state=self.initial_state(amplitudes[self.mode_index])
        weight=self.vertical.interface_energy_weight[:,None,None]
        full=float(.5*np.sum(weight*b*b)/(self.vertical.total_mass*self.n))
        retained=float(.5*np.mean((amplitudes[self.mode_index]/self.c)**2))
        state.certificate.update(initial_full_buoyancy_available_energy_m2_s2=full,
            initial_retained_available_energy_m2_s2=retained,
            initial_excluded_available_energy_m2_s2=max(0.,full-retained))
        return state

    def pressure_levels(self,state):
        self._pack(state)
        return self.vertical.pressure_modes[:,self.mode_index,None,None]*state.pressure_amplitude

    def buoyancy_interfaces(self,state):
        self._pack(state)
        return self.vertical.buoyancy_modes[:,self.mode_index,None,None]*state.pressure_amplitude

    def vertical_velocity(self,state):
        self._pack(state)
        div=(np.diff(state.u_east,axis=1)+np.diff(state.v_south,axis=0))/self.dx
        return self.vertical.vertical_velocity(self.vertical.pressure_modes[:,self.mode_index,None,None]*div)

    def advance(self,state,dt_s,*,forcing_m2_s3=0.):
        """Crank-Nicolson coupled state; pressure work and adiabatic work paired.

Q is mode-projected physical buoyancy heating (phi units/s), constant over
the step. It is not a prescribed target temperature. With zero damping/source,
modal kinetic+available energy is conserved; positive damping dissipates it.
"""
        if not np.isfinite(dt_s) or dt_s<=0:raise ValueError('Need positive finite timestep')
        x=self._pack(state);q=self._field(forcing_m2_s3,self.shape,'mode heating')
        source=np.r_[np.zeros(self.nu+self.nv),q.ravel()/self.c]
        dt=float(dt_s)
        if dt not in self.factors:self.factors[dt]=splu(self.identity+.5*dt*self.operator)
        rhs=x-.5*dt*(self.operator@x)+dt*source
        new=self.factors[dt].solve(rhs)
        if not np.isfinite(new).all():raise FloatingPointError('Nonfinite hydrostatic wave state')
        mid=.5*(x+new)
        residual=(new-x)/dt+self.operator@mid-source
        residual_ms=float(np.abs(residual).max()*dt)
        scale=max(1.,float(np.abs(x).max()),float(np.abs(new).max()))
        if residual_ms>1e-9*scale:raise RuntimeError('Transient momentum/buoyancy equations failed')
        old_e=.5*np.dot(x,x)/self.n;new_e=.5*np.dot(new,new)/self.n
        supply=float(np.dot(mid,source)/self.n)
        loss=float((self.r*np.dot(mid[:self.nu+self.nv],mid[:self.nu+self.nv])
                    +self.rt*np.dot(mid[self.nu+self.nv:],mid[self.nu+self.nv:]))/self.n)
        balance=float(new_e-old_e-dt*(supply-loss))
        relative=abs(balance)/max(abs(old_e),abs(new_e),dt*(abs(supply)+loss),1e-30)
        if relative>1e-9:raise RuntimeError('Transient modal energy balance failed')
        cert=dict(modal_energy_m2_s2=float(new_e),previous_modal_energy_m2_s2=float(old_e),
            midpoint_heating_work_m2_s3=supply,midpoint_damping_m2_s3=loss,
            energy_budget_residual_m2_s2=balance,relative_energy_budget_error=relative,
            maximum_equation_residual_velocity_ms=residual_ms,dt_s=dt,wave_speed_ms=self.c,
            scope='Coupled linear pressure/momentum/buoyancy state; one specified vertical eigenmode, no moisture/terrain/radiation feedback')
        return self._unpack(new,cert)

    def advance_buoyancy_heating(self,state,dt_s,buoyancy_source):
        source=np.asarray(buoyancy_source,float)
        if source.shape!=(len(self.vertical.centers_m)-1,)+self.shape:
            raise ValueError('Need matching interface buoyancy source')
        mode_forcing=self.vertical.project_buoyancy_source(source)[self.mode_index]
        result=self.advance(state,dt_s,forcing_m2_s3=mode_forcing)
        weight=self.vertical.interface_energy_weight[:,None,None]
        full=float(np.sum(weight*source**2)/(self.vertical.total_mass*self.n))
        retained=float(np.mean(mode_forcing**2/self.c**2))
        if retained>full+1e-10*max(full,1e-30):raise RuntimeError('Projected buoyancy source exceeds its actual norm')
        result.certificate.update(full_buoyancy_source_energy_norm_m2_s4=full,
            retained_buoyancy_source_energy_norm_m2_s4=retained,
            excluded_buoyancy_source_energy_norm_m2_s4=max(0.,full-retained))
        return result
