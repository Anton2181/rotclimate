"""Rigid-lid pressure dynamics retaining divergence-free vertically mean flow.

An exact discrete pressure constraint replaces the stronger old restriction
that every face have zero depth-mean wind. The pressure multiplier does no
work on an admissible midpoint velocity. Nonlinear momentum advection and
surface-pressure evolution are still absent; this is not a free-surface core.
"""
import numpy as np
from scipy.sparse import coo_matrix,kron,bmat,csc_matrix
from scipy.sparse.linalg import splu
from .pressure_boundary import BoundaryPressureMoistModel
from .pressure_moist import PressureMoistState,gas_energy,enthalpy_phase
from .multilevel_transport import _field,solve_multilevel
from .column_thermodynamics import CP,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K


def stagger_two_reservoir_wind(lower_right,lower_up,upper_right,upper_up,levels):
    """Retain both archived model winds; pressure cell0 lower, others upper.

    Source up is grid-up, not geographic north. Arithmetic face averages
    include nearest-cell exterior values; boundary conditions are set later.
    """
    fields=[np.asarray(a,float) for a in [lower_right,lower_up,upper_right,upper_up]]
    if (not isinstance(levels,int) or isinstance(levels,bool) or levels<2 or fields[0].ndim!=2
            or min(fields[0].shape)<2 or any(a.shape!=fields[0].shape or not np.isfinite(a).all() for a in fields)):
        raise ValueError('Need four matching finite wind fields and at least two pressure cells')
    right=np.stack([fields[0]]+[fields[2]]*(levels-1));south=-np.stack([fields[1]]+[fields[3]]*(levels-1))
    u=np.concatenate([right[:,:,:1],.5*(right[:,:,:-1]+right[:,:,1:]),right[:,:,-1:]],axis=2)
    v=np.concatenate([south[:,:1],.5*(south[:,:-1]+south[:,1:]),south[:,-1:]],axis=1)
    return u,v


class RigidLidMoistModel(BoundaryPressureMoistModel):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        ny,nx=self.shape;ids=np.arange(self.n).reshape(self.shape)
        def divergence(left,right):
            size=left.size;cols=np.arange(size)
            return coo_matrix((np.r_[np.ones(size),-np.ones(size)]/self.dx,
                (np.r_[left.ravel(),right.ravel()],np.tile(cols,2))),shape=(self.n,size)).tocsc()
        dx=divergence(ids[:,:-1],ids[:,1:]);dy=divergence(ids[:-1],ids[1:])
        # x contains sqrt(M)*velocity; D*x is column dry-mass divergence.
        self.column_divergence=bmat([[kron(self.sqrt_mass[None,:],dx),kron(self.sqrt_mass[None,:],dy)]],format='csc')
        # Drop the redundant last cell equation; set its multiplier to zero.
        self.constraint=self.column_divergence[:-1].tocsc()
        self.constraint_gradient=-self.constraint.T
        self.projection_factor=splu((self.constraint@self.constraint.T).tocsc())

    def _pack_unchecked(self,u,v):
        ny,nx=self.shape;u=_field(u,(self.nz,ny,nx+1),'east velocity');v=_field(v,(self.nz,ny+1,nx),'south velocity')
        if not np.array_equal(u[:,:,[0,-1]],self.u_boundary[:,:,[0,-1]]) or not np.array_equal(v[:,[0,-1]],self.v_boundary[:,[0,-1]]):
            raise ValueError('Exterior velocities differ from prescribed regional ports')
        return np.r_[(self.sqrt_mass[:,None,None]*u[:,:,1:-1]).ravel(),(self.sqrt_mass[:,None,None]*v[:,1:-1]).ravel()]

    def _velocity(self,u,v):
        x=self._pack_unchecked(u,v);div=self.column_divergence@x
        scale=max(float(np.max(abs(self.column_divergence)@abs(x))),1e-12)
        if np.max(abs(div))>1e-10*scale+1e-13:raise ValueError('Rigid-lid winds must close column dry mass; project initial wind first')
        return x

    def project_initial_wind(self,u,v):
        """Mass-orthogonal projection; disclose the kinetic energy removed.

        Only the vertically averaged component changes. This is an initial
        state conversion, not a dynamical energy-conserving step. Temperature
        and vapor are untouched; callers must record conversion separately.
        """
        raw=self._pack_unchecked(u,v)
        x=raw-self.constraint.T@self.projection_factor.solve(self.constraint@raw)
        u1,v1=self._unpack(x);self._velocity(u1,v1)
        cross=float(np.dot(x,raw-x));removed=float(.5*(np.dot(raw,raw)-np.dot(x,x))/self.n)
        if removed < -1e-9 or abs(cross)>1e-10*max(float(np.dot(raw,raw)),1.):raise RuntimeError('Initial wind projection lost orthogonality')
        return u1,v1,dict(removed_kinetic_energy_j_m2=removed,
            maximum_column_mass_divergence_kg_m2_s=float(abs(self.column_divergence@x).max()),
            scope='Initial mass-orthogonal rigid-lid projection; removed kinetic energy explicitly separate, no hidden heat addition or physics adoption.')

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
        if dt not in self.factors:
            block=bmat([[self.identity+.5*dt*self.momentum,dt*self.constraint_gradient],
                [self.constraint,csc_matrix((self.n-1,self.n-1))]],format='csc')
            self.factors[dt]=splu(block)
        guess=t0.copy();previous_velocity=None
        for iteration in range(1,max_iterations+1):
            midpoint_t=.5*(t0+guess)
            force=self._pressure_force(midpoint_t)+self.boundary_rotation_force
            solution=self.factors[dt].solve(np.r_[x0-.5*dt*(self.momentum@x0)-dt*force,np.zeros(self.n-1)])
            x=solution[:len(x0)];constraint_pressure=solution[len(x0):]
            constraint_force=self.constraint_gradient@constraint_pressure
            mid=.5*(x+x0);u,v=self._unpack(mid)
            div=(np.diff(u,axis=2)+np.diff(v,axis=1))/self.dx
            compression=self.column.compression_power_w_m2(midpoint_t,div)
            drag_heat=np.zeros_like(t0);mu=self.mass[:,0,0,None,None]
            fu=self.r*mu*u[:,:,1:-1]**2;fv=self.r*mu*v[:,1:-1]**2
            drag_heat[:,:,:-1]+=.5*fu;drag_heat[:,:,1:]+=.5*fu
            drag_heat[:,:-1]+=.5*fv;drag_heat[:,1:]+=.5*fv
            enthalpy_source=old_h/dt+compression+drag_heat+external
            if np.any(enthalpy_source<0):raise ValueError('Timestep/cooling produces a negative gas-enthalpy source')
            water=solve_multilevel(self.mass,u,v,self.dx,w0/dt+evap,1/dt,self.external_q)
            external_h=CP*self.external_t+self.external_q*(LV+CP_VAPOR*(self.external_t-REFERENCE_K))
            enthalpy=solve_multilevel(self.mass,u,v,self.dx,enthalpy_source,1/dt,external_h)
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
        boundary_h=float(sum(enthalpy.certificate['outward_boundary_per_layer_cell_s']))
        boundary_w=float(sum(water.certificate['outward_boundary_per_layer_cell_s']))
        boundary_phi=self._geopotential_boundary_flux(midpoint_t)
        boundary_rotation_work=float(-np.dot(mid,self.boundary_rotation_force))
        energy_error=float((new_h-old_h).sum()+rain_h.sum()+dk-dt*external.sum()+dt*(boundary_h+boundary_phi-boundary_rotation_work))
        water_error=float((new_w-w0).sum()+rain.sum()-dt*evap.sum()+dt*boundary_w)
        tolerance=1000*np.finfo(float).eps*max(float(np.sum(abs(old_h))),1.)
        if abs(energy_error)>tolerance or abs(water_error)>1e-10*max(float(w0.sum()+dt*evap.sum()),1.):
            raise RuntimeError('Coupled actual gas/kinetic/rain or water/source budget failed')
        pressure_work=float(-np.dot(mid,force-self.boundary_rotation_force));compression_sum=float(compression.sum())
        work_error=pressure_work+compression_sum+boundary_phi
        if abs(work_error)>1e-10*max(abs(pressure_work),float(abs(compression).sum()),1.):raise RuntimeError('Actual pressure/compression work failed')
        u1,v1=self._unpack(x);self._velocity(u1,v1)
        final_mid=.5*(t0+new_t)
        momentum_residual=(x-x0)/dt+self.momentum@mid+self._pressure_force(final_mid)+self.boundary_rotation_force+constraint_force
        constraint_work=float(-np.dot(mid,constraint_force))
        if abs(constraint_work)>1e-9*max(float(abs(mid*constraint_force).sum()),1.):raise RuntimeError('Rigid-lid constraint pressure did work')
        cert=dict(iterations=iteration,
            maximum_column_mass_divergence_kg_m2_s=float(abs(self.column_divergence@x).max()),
            rigid_lid_constraint_pressure_work_w_m2=constraint_work/self.n,
            maximum_constraint_pressure_potential_m2_s2=float(abs(constraint_pressure).max()),maximum_temperature_fixed_point_residual_k=error,
            maximum_velocity_iteration_difference_ms=velocity_error,
            maximum_actual_midpoint_momentum_residual_weighted_ms2=float(np.max(abs(momentum_residual))),
            maximum_midpoint_hydrostatic_geopotential_residual_m2_s2=float(np.max(abs(np.einsum('ij,j...->i...',self.column.hydrostatic_matrix,final_mid-midpoint_t)))),
            actual_gas_plus_kinetic_plus_rain_energy_residual_j_m2=energy_error/self.n,
            relative_total_energy_budget_error=abs(energy_error)/max(float(abs(old_h).sum()),1.),
            actual_vapor_plus_rain_source_residual_kg_m2=water_error/self.n,
            pressure_work_w_m2=pressure_work/self.n,compression_work_w_m2=compression_sum/self.n,
            actual_pressure_compression_cancellation_error_w_m2=work_error/self.n,
            drag_heat_w_m2=float(drag_heat.sum()/self.n),external_power_w_m2=float(external.sum()/self.n),
            outward_boundary_gas_enthalpy_w_m2=boundary_h/self.n,outward_boundary_geopotential_work_w_m2=boundary_phi/self.n,
            prescribed_boundary_rotation_work_w_m2=boundary_rotation_work/self.n,outward_boundary_vapor_kg_m2_s=boundary_w/self.n,
            gas_enthalpy_plus_kinetic_energy_j_m2=float((new_h.sum()+.5*np.dot(x,x))/self.n),
            kinetic_energy_j_m2=float(.5*np.dot(x,x)/self.n),
            transport_water=water.certificate,transport_enthalpy=enthalpy.certificate,
            scope='Rigid-lid divergence-free mean flow with prescribed zero-mean regional ports: incoming gas/vapor, geopotential flux and external boundary-rotation work booked. No exterior kinetic storage, nonlinear momentum advection, transparent radiation, terrain or Earth adoption.')
        return PressureMoistState(new_t,new_w,u1,v1,rain,rain_h,cert)

