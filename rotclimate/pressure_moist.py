"""Repeated dry/dilute hydrostatic pressure-coordinate moist feedback.

Gas enthalpy, vapor, pressure and winds evolve together. Compression work is
the hydrostatic energy adjoint and is included exactly once. Liquid rain
exports actual enthalpy. This reduced coordinate omits water loading, vapor
gas-volume feedback, water potential/fall work and ice; it must not be mixed
with the fixed-height gas+gz phase kernel or called a complete Earth model.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import bmat,coo_matrix,eye,kron
from scipy.sparse.linalg import splu
from .column_thermodynamics import CP,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K,liquid_enthalpy
from .falling_water_energy import _equilibrium
from .multilevel_transport import solve_multilevel,_field
from .pressure_coordinate import pressure_coordinate


@dataclass
class PressureMoistState:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    u_east: np.ndarray
    v_south: np.ndarray
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    certificate: dict


def gas_energy(t,w,m):
    # Positive-reference gas enthalpy. The added cp_d*M*T0 is constant under
    # fixed dry-mass continuity and changes neither phase nor global budgets.
    return (CP*m+CP_VAPOR*w)*t+(LV-CP_VAPOR*REFERENCE_K)*w


def enthalpy_phase(t,w,m,p):
    """Top-down enthalpy-only liquid fall; no unbooked water potential work."""
    nt,nw=np.empty_like(t),np.empty_like(w);incoming=np.zeros_like(t[0]);liquid_t=t[-1]
    for k in range(len(t)-1,-1,-1):
        nt[k],nw[k],incoming,_,_=_equilibrium(t[k],w[k],m[k],p[k],incoming,liquid_t,
            extra_heat=0.,feedback_per_vapor_change=0.)
        liquid_t=nt[k]
    return nt,nw,incoming,liquid_enthalpy(nt[0],incoming)


class PressureMoistModel:
    def __init__(self,pressure_edges_pa,shape,cell_m,coriolis,*,momentum_drag_s=0.,phase_enabled=True):
        self.column=pressure_coordinate(pressure_edges_pa)
        if (len(shape)!=2 or any(not isinstance(n,int) or isinstance(n,bool) or n<2 for n in shape)
                or not np.isfinite([cell_m,momentum_drag_s]).all() or cell_m<=0 or momentum_drag_s<0):
            raise ValueError('Need at least two horizontal cells per axis, positive spacing and nonnegative drag')
        self.shape=tuple(shape);self.nz=len(self.column.centers_pa);self.dx=float(cell_m);self.r=float(momentum_drag_s)
        ny,nx=shape;self.n=ny*nx;self.nu=ny*(nx-1);self.nv=(ny-1)*nx
        self.mass=np.broadcast_to(self.column.cell_mass_kg_m2[:,None,None],(self.nz,ny,nx)).copy()
        self.pressure=np.broadcast_to(self.column.centers_pa[:,None,None],self.mass.shape).copy()
        self.sqrt_mass=np.sqrt(self.column.cell_mass_kg_m2)
        self.phase_enabled=bool(phase_enabled);self.factors={}
        ids=np.arange(self.n).reshape(shape);iu=np.arange(self.nu).reshape(ny,nx-1);iv=np.arange(self.nv).reshape(ny-1,nx)
        def gradient(left,right):
            count=left.size;rows=np.arange(count)
            return coo_matrix((np.r_[-np.ones(count),np.ones(count)]/self.dx,
                (np.tile(rows,2),np.r_[left.ravel(),right.ravel()])),shape=(count,self.n)).tocsr()
        gx,gy=gradient(ids[:,:-1],ids[:,1:]),gradient(ids[:-1],ids[1:])
        f=np.broadcast_to(np.asarray(coriolis,float),shape)
        if not np.isfinite(f).all():raise ValueError('Need finite matching Coriolis')
        rows=[];cols=[];values=[]
        for j in range(ny):
            for i in range(nx):
                for k in [i-1,i]:
                    if not 0<=k<nx-1:continue
                    for ell in [j-1,j]:
                        if 0<=ell<ny-1:rows.append(iu[j,k]);cols.append(iv[ell,i]);values.append(.25*f[j,i])
        rotate=kron(eye(self.nz),coo_matrix((values,(rows,cols)),shape=(self.nu,self.nv)),format='csc')
        self.n_u,self.n_v=self.nz*self.nu,self.nz*self.nv
        self.momentum=bmat([[self.r*eye(self.n_u),rotate],[-rotate.T,self.r*eye(self.n_v)]],format='csc')
        h=self.sqrt_mass[:,None]*self.column.hydrostatic_matrix
        self.pressure_gradient=bmat([[kron(h,gx)],[kron(h,gy)]],format='csc')
        self.identity=eye(self.n_u+self.n_v,format='csc')

    def _velocity(self,u,v):
        ny,nx=self.shape;u=_field(u,(self.nz,ny,nx+1),'east velocity');v=_field(v,(self.nz,ny+1,nx),'south velocity')
        if np.any(u[:,:,[0,-1]]) or np.any(v[:,[0,-1]]):raise ValueError('Need closed exterior normal velocities')
        m=self.column.cell_mass_kg_m2[:,None,None]
        for flow in [u,v]:
            if np.any(abs(np.sum(m*flow,axis=0))>1e-10*np.sum(abs(m*flow),axis=0)+m.sum()*1e-13):
                raise ValueError('This baroclinic prototype excludes depth-mean flow')
        return np.r_[(self.sqrt_mass[:,None,None]*u[:,:,1:-1]).ravel(),(self.sqrt_mass[:,None,None]*v[:,1:-1]).ravel()]

    def _unpack(self,x):
        ny,nx=self.shape;u=np.zeros((self.nz,ny,nx+1));v=np.zeros((self.nz,ny+1,nx))
        u[:,:,1:-1]=x[:self.n_u].reshape(self.nz,ny,nx-1)/self.sqrt_mass[:,None,None]
        v[:,1:-1]=x[self.n_u:].reshape(self.nz,ny-1,nx)/self.sqrt_mass[:,None,None]
        return u,v

    def _pressure_force(self,t):
        # A horizontally uniform reference has exactly zero gradient. Remove
        # that null component before multiplying, avoiding cancellation of
        # large background geopotentials; no physical thermal state is reset.
        anomaly=t-np.mean(t,axis=(1,2),keepdims=True)
        return self.pressure_gradient@anomaly.ravel()

    def initial_state(self,temperature_k,vapor_kg_m2=0.,u_east=0.,v_south=0.):
        t=_field(temperature_k,self.mass.shape,'temperature',minimum=180.)
        w=_field(vapor_kg_m2,self.mass.shape,'vapor',minimum=0.)
        if np.any(t>330) or np.any(w/self.mass>.2):raise ValueError('Need terrestrial dilute thermal state')
        x=self._velocity(u_east,v_south);u,v=self._unpack(x)
        return PressureMoistState(t,w,u,v,np.zeros(self.shape),np.zeros(self.shape),
            dict(gas_enthalpy_plus_kinetic_energy_j_m2=float((gas_energy(t,w,self.mass).sum()+.5*np.dot(x,x))/self.n)))

    def advance(self,state,dt_s,*,heating_w_m2=0.,evaporation_kg_m2_s=0.,vapor_source_temperature_k=None,
                temperature_tolerance_k=1e-8,max_iterations=40):
        if (not np.isfinite([dt_s,temperature_tolerance_k]).all() or dt_s<=0 or temperature_tolerance_k<=0
                or not isinstance(max_iterations,int) or max_iterations<1):raise ValueError('Need positive timestep, tolerance and iteration budget')
        dt=float(dt_s);t0=_field(state.temperature_k,self.mass.shape,'old temperature',minimum=180.)
        w0=_field(state.vapor_kg_m2,self.mass.shape,'old vapor',minimum=0.);x0=self._velocity(state.u_east,state.v_south)
        heat=_field(heating_w_m2,self.mass.shape,'external heating');evap=_field(evaporation_kg_m2_s,self.mass.shape,'vapor source',minimum=0.)
        source_t=t0 if vapor_source_temperature_k is None else _field(vapor_source_temperature_k,self.mass.shape,'source vapor temperature',minimum=180.)
        if np.any(t0>330) or np.any(source_t>330) or np.any(w0/self.mass>.2):raise ValueError('Need supported terrestrial state/source')
        vapor_power=evap*(LV+CP_VAPOR*(source_t-REFERENCE_K));external=heat+vapor_power;old_h=gas_energy(t0,w0,self.mass)
        if dt not in self.factors:self.factors[dt]=splu(self.identity+.5*dt*self.momentum)
        guess=t0.copy();previous_velocity=None
        for iteration in range(1,max_iterations+1):
            midpoint_t=.5*(t0+guess)
            force=self._pressure_force(midpoint_t)
            x=self.factors[dt].solve(x0-.5*dt*(self.momentum@x0)-dt*force)
            mid=.5*(x+x0);u,v=self._unpack(mid)
            div=(np.diff(u,axis=2)+np.diff(v,axis=1))/self.dx
            compression=self.column.compression_power_w_m2(midpoint_t,div)
            drag_heat=np.zeros_like(t0);mu=self.mass[:,0,0,None,None]
            fu=self.r*mu*u[:,:,1:-1]**2;fv=self.r*mu*v[:,1:-1]**2
            drag_heat[:,:,:-1]+=.5*fu;drag_heat[:,:,1:]+=.5*fu
            drag_heat[:,:-1]+=.5*fv;drag_heat[:,1:]+=.5*fv
            enthalpy_source=old_h/dt+compression+drag_heat+external
            if np.any(enthalpy_source<0):raise ValueError('Timestep/cooling produces a negative gas-enthalpy source')
            water=solve_multilevel(self.mass,u,v,self.dx,w0/dt+evap,1/dt,w0/self.mass)
            enthalpy=solve_multilevel(self.mass,u,v,self.dx,enthalpy_source,1/dt,old_h/self.mass)
            moved_w=water.amount;moved_t=(enthalpy.amount-(LV-CP_VAPOR*REFERENCE_K)*moved_w)/(CP*self.mass+CP_VAPOR*moved_w)
            if self.phase_enabled:new_t,new_w,rain,rain_h=enthalpy_phase(moved_t,moved_w,self.mass,self.pressure)
            else:new_t,new_w,rain,rain_h=moved_t,moved_w,np.zeros(self.shape),np.zeros(self.shape)
            if not np.isfinite(new_t).all() or np.any((new_t<180)|(new_t>330)):raise ValueError('Coupled thermal state outside180–330K')
            error=float(np.max(abs(new_t-guess)))
            velocity_error=float(np.max(abs(x-previous_velocity))/max(float(self.sqrt_mass.min()),1.)) if previous_velocity is not None else None
            if error<=temperature_tolerance_k:break
            guess=new_t;previous_velocity=x
        else:raise RuntimeError('Coupled pressure/transport/phase fixed point failed; reduce timestep')
        new_h=gas_energy(new_t,new_w,self.mass);dk=.5*(np.dot(x,x)-np.dot(x0,x0))
        energy_error=float((new_h-old_h).sum()+rain_h.sum()+dk-dt*external.sum())
        water_error=float((new_w-w0).sum()+rain.sum()-dt*evap.sum())
        tolerance=1000*np.finfo(float).eps*max(float(np.sum(abs(old_h))),1.)
        if abs(energy_error)>tolerance or abs(water_error)>1e-10*max(float(w0.sum()+dt*evap.sum()),1.):
            raise RuntimeError('Coupled actual gas/kinetic/rain or water/source budget failed')
        pressure_work=float(-np.dot(mid,force));compression_sum=float(compression.sum())
        work_error=pressure_work+compression_sum
        if abs(work_error)>1e-10*max(abs(pressure_work),float(abs(compression).sum()),1.):raise RuntimeError('Actual pressure/compression work failed')
        u1,v1=self._unpack(x);self._velocity(u1,v1)
        final_mid=.5*(t0+new_t)
        momentum_residual=(x-x0)/dt+self.momentum@mid+self._pressure_force(final_mid)
        cert=dict(iterations=iteration,maximum_temperature_fixed_point_residual_k=error,
            maximum_velocity_iteration_difference_ms=velocity_error,
            maximum_actual_midpoint_momentum_residual_weighted_ms2=float(np.max(abs(momentum_residual))),
            maximum_midpoint_hydrostatic_geopotential_residual_m2_s2=float(np.max(abs(np.einsum('ij,j...->i...',self.column.hydrostatic_matrix,final_mid-midpoint_t)))),
            actual_gas_plus_kinetic_plus_rain_energy_residual_j_m2=energy_error/self.n,
            relative_total_energy_budget_error=abs(energy_error)/max(float(abs(old_h).sum()),1.),
            actual_vapor_plus_rain_source_residual_kg_m2=water_error/self.n,
            pressure_work_w_m2=pressure_work/self.n,compression_work_w_m2=compression_sum/self.n,
            actual_pressure_compression_cancellation_error_w_m2=work_error/self.n,
            drag_heat_w_m2=float(drag_heat.sum()/self.n),external_power_w_m2=float(external.sum()/self.n),
            gas_enthalpy_plus_kinetic_energy_j_m2=float((new_h.sum()+.5*np.dot(x,x))/self.n),
            kinetic_energy_j_m2=float(.5*np.dot(x,x)/self.n),
            transport_water=water.certificate,transport_enthalpy=enthalpy.certificate,
            scope='Repeated dry/dilute pressure-coordinate enthalpy/vapor/phase/wind feedback; compression once. Zero depth-mean flow, fixed pressure bounds; no water loading/volume/potential/fall heat, ice, radiation or terrain.')
        return PressureMoistState(new_t,new_w,u1,v1,rain,rain_h,cert)
