"""Prescribed regional baroclinic boundary ports for the pressure prototype.

Incoming gas enthalpy/vapor, boundary geopotential work and work exchanged
with prescribed Coriolis-coupled boundary velocities are explicitly booked.
Exterior velocities have no kinetic storage degrees of freedom. This is a
conditional regional boundary, not transparent radiation or full nonlinear
momentum/kinetic-energy advection. Zero-boundary controls recover the closed
prototype without modifying its frozen source.
"""
import numpy as np
from .pressure_moist import PressureMoistModel,PressureMoistState,gas_energy,enthalpy_phase
from .multilevel_transport import _field,solve_multilevel
from .column_thermodynamics import CP,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K
from scipy.sparse.linalg import splu
from .convective_adjustment import adjust_convection,_flags


def baroclinic_lower_wind_seed(lower_right_ms,lower_up_ms,layer_mass_kg_m2):
    """Stagger an archived lower projected wind; diagnose upper mass return.

    The source lower wind is retained at exterior faces and averaged between
    cells internally. Upper cells share the compensating mass-mean return.
    This does not preserve an archived upper/barotropic wind or guarantee
    geostrophic balance. Source projected-up is converted to grid-south.
    """
    u,v,m=np.asarray(lower_right_ms,float),np.asarray(lower_up_ms,float),np.asarray(layer_mass_kg_m2,float)
    if (u.ndim!=2 or min(u.shape)<2 or v.shape!=u.shape or m.ndim!=1 or len(m)<2
            or not all(np.isfinite(a).all() for a in [u,v,m]) or np.any(m<=0)):
        raise ValueError('Need finite matching lower wind fields and positive vertical masses')
    uf=np.concatenate([u[:,:1],.5*(u[:,:-1]+u[:,1:]),u[:,-1:]],axis=1)
    south=-v;vf=np.concatenate([south[:1],.5*(south[:-1]+south[1:]),south[-1:]],axis=0)
    coefficients=np.r_[1.,np.full(len(m)-1,-m[0]/m[1:].sum())]
    return coefficients[:,None,None]*uf[None],coefficients[:,None,None]*vf[None]


class BoundaryPressureMoistModel(PressureMoistModel):
    def __init__(self,pressure_edges_pa,shape,cell_m,coriolis,*,u_boundary=0.,v_boundary=0.,
                 external_temperature_k=280.,external_mixing_ratio=0.,momentum_drag_s=0.,phase_enabled=True):
        super().__init__(pressure_edges_pa,shape,cell_m,coriolis,momentum_drag_s=momentum_drag_s,phase_enabled=phase_enabled)
        ny,nx=self.shape
        self.u_boundary=_field(u_boundary,(self.nz,ny,nx+1),'prescribed east boundary')
        self.v_boundary=_field(v_boundary,(self.nz,ny+1,nx),'prescribed south boundary')
        if np.any(self.u_boundary[:,:,1:-1]) or np.any(self.v_boundary[:,1:-1]):raise ValueError('Boundary arrays must have zero interior entries')
        m=self.column.cell_mass_kg_m2[:,None,None]
        for flow in [self.u_boundary,self.v_boundary]:
            if np.any(abs(np.sum(m*flow,axis=0))>1e-11*np.sum(abs(m*flow),axis=0)+m.sum()*1e-13):raise ValueError('Boundary ports must have zero depth-mass-mean normal flow')
        self.external_t=_field(external_temperature_k,self.mass.shape,'incoming temperature',minimum=180.)
        self.external_q=_field(external_mixing_ratio,self.mass.shape,'incoming vapor ratio',minimum=0.)
        if np.any(self.external_t>330) or np.any(self.external_q>.2):raise ValueError('Incoming states outside terrestrial dilute domain')
        f=np.broadcast_to(np.asarray(coriolis,float),shape);ue=np.zeros((self.nz,ny,nx-1));ve=np.zeros((self.nz,ny-1,nx))
        for j in range(ny):
            for i in range(nx):
                for k in [i-1,i]:
                    if 0<=k<nx-1:
                        if j==0:ue[:,j,k]+=.25*f[j,i]*self.v_boundary[:,0,i]
                        if j==ny-1:ue[:,j,k]+=.25*f[j,i]*self.v_boundary[:,-1,i]
                for ell in [j-1,j]:
                    if 0<=ell<ny-1:
                        if i==0:ve[:,ell,i]-=.25*f[j,i]*self.u_boundary[:,j,0]
                        if i==nx-1:ve[:,ell,i]-=.25*f[j,i]*self.u_boundary[:,j,-1]
        self.boundary_rotation_force=np.r_[(self.sqrt_mass[:,None,None]*ue).ravel(),(self.sqrt_mass[:,None,None]*ve).ravel()]

    def _velocity(self,u,v):
        ny,nx=self.shape;u=_field(u,(self.nz,ny,nx+1),'east velocity');v=_field(v,(self.nz,ny+1,nx),'south velocity')
        if not np.array_equal(u[:,:,[0,-1]],self.u_boundary[:,:,[0,-1]]) or not np.array_equal(v[:,[0,-1]],self.v_boundary[:,[0,-1]]):
            raise ValueError('Exterior velocities differ from declared ports')
        m=self.column.cell_mass_kg_m2[:,None,None]
        for flow in [u,v]:
            if np.any(abs(np.sum(m*flow,axis=0))>1e-10*np.sum(abs(m*flow),axis=0)+m.sum()*1e-13):raise ValueError('Regional prototype excludes depth-mean flow')
        return np.r_[(self.sqrt_mass[:,None,None]*u[:,:,1:-1]).ravel(),(self.sqrt_mass[:,None,None]*v[:,1:-1]).ravel()]

    def _unpack(self,x):
        ny,nx=self.shape;u=self.u_boundary.copy();v=self.v_boundary.copy()
        u[:,:,1:-1]=x[:self.n_u].reshape(self.nz,ny,nx-1)/self.sqrt_mass[:,None,None]
        v[:,1:-1]=x[self.n_u:].reshape(self.nz,ny-1,nx)/self.sqrt_mass[:,None,None]
        return u,v

    def initial_state(self,temperature_k,vapor_kg_m2=0.,u_east=None,v_south=None):
        return super().initial_state(temperature_k,vapor_kg_m2,self.u_boundary if u_east is None else u_east,self.v_boundary if v_south is None else v_south)

    def _geopotential_boundary_flux(self,temperature):
        phi=self.column.geopotential(temperature);m=self.column.cell_mass_kg_m2[:,None]
        return float((np.sum(m*(phi[:,:,-1]*self.u_boundary[:,:,-1]-phi[:,:,0]*self.u_boundary[:,:,0]))
            +np.sum(m*(phi[:,-1]*self.v_boundary[:,-1]-phi[:,0]*self.v_boundary[:,0])))/self.dx)

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
            force=self._pressure_force(midpoint_t)+self.boundary_rotation_force
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
        momentum_residual=(x-x0)/dt+self.momentum@mid+self._pressure_force(final_mid)+self.boundary_rotation_force
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
            outward_boundary_gas_enthalpy_w_m2=boundary_h/self.n,outward_boundary_geopotential_work_w_m2=boundary_phi/self.n,
            prescribed_boundary_rotation_work_w_m2=boundary_rotation_work/self.n,outward_boundary_vapor_kg_m2_s=boundary_w/self.n,
            gas_enthalpy_plus_kinetic_energy_j_m2=float((new_h.sum()+.5*np.dot(x,x))/self.n),
            kinetic_energy_j_m2=float(.5*np.dot(x,x)/self.n),
            transport_water=water.certificate,transport_enthalpy=enthalpy.certificate,
            scope='Prescribed regional baroclinic ports: incoming gas/vapor, geopotential flux and external boundary-rotation work booked. No exterior kinetic storage, nonlinear momentum advection, transparent radiation, terrain or Earth adoption.')
        return PressureMoistState(new_t,new_w,u1,v1,rain,rain_h,cert)


def advance_boundary_with_convection(model,state,dt_s,*,neutral_tolerance_k=.01,max_sweeps=64,relaxation_s=0.,**kwargs):
    """First-order split dynamics/transport/phase then conservative adjustment.

    The nested dynamical certificate applies before the adjustment. Final
    pressure responds on the next timestep; no final midpoint claim is made.
    """
    if not np.isfinite(relaxation_s) or relaxation_s<0:raise ValueError('Need finite nonnegative convective relaxation time')
    dynamic=model.advance(state,dt_s,**kwargs)
    closure=adjust_convection(dynamic.temperature_k,dynamic.vapor_kg_m2,model.mass,model.column.centers_pa,
        neutral_tolerance_k=neutral_tolerance_k,max_sweeps=max_sweeps)
    if not closure.certificate['converged']:raise RuntimeError('Convective adjustment did not converge; no step accepted')
    fraction=1. if relaxation_s==0 else float(-np.expm1(-dt_s/relaxation_s))
    if fraction==1.:
        final_t,final_w=closure.temperature_k,closure.vapor_kg_m2;extra_rain=closure.ground_rain_kg_m2;extra_h=closure.ground_rain_enthalpy_j_m2
    else:
        # Relax water and gas enthalpy, not temperature. The target's actual
        # exported rain is included in the same convex budget. Homogenizing
        # this mixture can change saturation, so book its phase explicitly.
        final_w=dynamic.vapor_kg_m2+fraction*(closure.vapor_kg_m2-dynamic.vapor_kg_m2)
        h0=gas_energy(dynamic.temperature_k,dynamic.vapor_kg_m2,model.mass)
        h1=gas_energy(closure.temperature_k,closure.vapor_kg_m2,model.mass)
        mixed_h=h0+fraction*(h1-h0)
        mixed_t=(mixed_h-(LV-CP_VAPOR*REFERENCE_K)*final_w)/(CP*model.mass+CP_VAPOR*final_w)
        final_t,final_w,mixed_rain,mixed_rain_h=enthalpy_phase(mixed_t,final_w,model.mass,model.pressure)
        extra_rain=fraction*closure.ground_rain_kg_m2+mixed_rain;extra_h=fraction*closure.ground_rain_enthalpy_j_m2+mixed_rain_h
    rain=dynamic.ground_rain_kg_m2+extra_rain;rain_h=dynamic.ground_rain_enthalpy_j_m2+extra_h
    face_mass=model.mass[:,0,0,None,None]
    kinetic=lambda s:.5*(np.sum(face_mass*s.u_east[:,:,1:-1]**2)+np.sum(face_mass*s.v_south[:,1:-1]**2))
    old=gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+kinetic(state)
    new=gas_energy(final_t,final_w,model.mass).sum()+kinetic(dynamic)
    ports=dynamic.certificate
    boundary_energy=ports['outward_boundary_gas_enthalpy_w_m2']+ports['outward_boundary_geopotential_work_w_m2']-ports['prescribed_boundary_rotation_work_w_m2']
    energy_error=float(new+rain_h.sum()-old-dt_s*ports['external_power_w_m2']*model.n+dt_s*boundary_energy*model.n)
    evap=_field(kwargs.get('evaporation_kg_m2_s',0.),model.mass.shape,'water source',minimum=0.)
    water_error=float(final_w.sum()+rain.sum()-state.vapor_kg_m2.sum()-dt_s*evap.sum()+dt_s*ports['outward_boundary_vapor_kg_m2_s']*model.n)
    if abs(energy_error)>2000*np.finfo(float).eps*max(abs(old),1.) or abs(water_error)>1e-9*max(float(state.vapor_kg_m2.sum()),1.):
        raise RuntimeError('Split coupled convection actual total budget failed')
    cert=dict(dynamics_before_adjustment=dynamic.certificate,convective_adjustment=closure.certificate,
        relaxation_s=relaxation_s,adjusted_fraction=fraction,
        outward_boundary_gas_enthalpy_w_m2=ports['outward_boundary_gas_enthalpy_w_m2'],
        outward_boundary_geopotential_work_w_m2=ports['outward_boundary_geopotential_work_w_m2'],
        prescribed_boundary_rotation_work_w_m2=ports['prescribed_boundary_rotation_work_w_m2'],
        outward_boundary_vapor_kg_m2_s=ports['outward_boundary_vapor_kg_m2_s'],external_power_w_m2=ports['external_power_w_m2'],
        actual_remaining_active_interfaces=int(np.count_nonzero(_flags(final_t,final_w,model.mass,model.column.centers_pa,neutral_tolerance_k))),
        actual_combined_energy_rain_source_residual_j_m2=energy_error/model.n,
        actual_combined_water_rain_source_residual_kg_m2=water_error/model.n,
        gas_enthalpy_plus_kinetic_energy_j_m2=float(new/model.n),kinetic_energy_j_m2=float(kinetic(dynamic)/model.n),
        scope='Prescribed regional ports and split conservative convection; actual incoming gas/vapor, geopotential and boundary-rotation work booked before adjustment. No transparent/nonlinear boundary or Earth adoption.')
    return PressureMoistState(final_t,final_w,dynamic.u_east,dynamic.v_south,rain,rain_h,cert)
