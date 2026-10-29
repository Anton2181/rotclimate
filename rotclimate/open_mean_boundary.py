"""Prescribed globally mass-balanced mean throughflow for the rigid-lid core.

Boundary pressure work includes the diagnosed constraint geopotential. The
regional model rejects net dry-mass sources; any preparation correction is
explicit, separate and never performed silently inside the model.
"""
import numpy as np
from scipy.sparse import bmat,csc_matrix
from .rigid_lid_refined import RefinedRigidLidMoistModel,RefinedSaddleSolve
from .pressure_moist import PressureMoistState,gas_energy,enthalpy_phase
from .multilevel_transport import _field,solve_multilevel
from .column_thermodynamics import CP,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K


class OpenMeanSaddleSolve(RefinedSaddleSolve):
    """Refine and check rows with separate velocity/pressure reference scales.

    Pure throughflow can have exactly zero transverse momentum/pressure.
    A componentwise relative error then divides residual roundoff by roundoff.
    Block reference norms retain physical units and make the zero-mode limit
    meaningful. Native dry-mass and actual energy checks remain unchanged.
    """
    def __init__(self,matrix,momentum_size):
        super().__init__(matrix);self.momentum_size=momentum_size

    def solve(self,rhs):
        rhs=np.asarray(rhs,float);x=self.factor.solve(rhs);b=rhs.astype(np.longdouble)
        def residual():
            xe=x.astype(np.longdouble);r=b-self.extended@xe;n=self.momentum_size
            reference=np.r_[np.full(n,np.max(abs(xe[:n]))),np.full(len(xe)-n,np.max(abs(xe[n:])))]
            scale=abs(b)+self.absolute@reference
            return r,float(np.max(abs(r)/np.maximum(scale,np.finfo(np.longdouble).tiny)))
        _,initial=residual()
        for _ in range(3):
            r,_=residual();x+=self.factor.solve(np.asarray(r,float))
        _,final=residual()
        if final>8*np.finfo(float).eps:raise RuntimeError('Refined open-boundary block-scaled row error exceeds8eps')
        self.calls.append(dict(initial_rowwise_backward_error=initial,final_rowwise_backward_error=final,refinement_rounds=3,
            scale='Separate mass-weighted velocity and constraint-potential infinity norms; rowwise mixed-unit normwise backward error.'))
        return x


def balance_normal_ports(u_boundary,v_boundary,layer_mass_kg_m2,cell_m):
    """Explicit minimum-kinetic barotropic correction to globally balance ports.

    Equal-width perimeter faces receive one constant outward-speed correction
    at every level, preserving each face's vertical shear. Inputs are copied.
    """
    u,v,m=np.asarray(u_boundary,float).copy(),np.asarray(v_boundary,float).copy(),np.asarray(layer_mass_kg_m2,float)
    if (u.ndim!=3 or v.ndim!=3 or m.ndim!=1 or len(m)!=len(u) or v.shape!=(len(m),u.shape[1]+1,u.shape[2]-1)
            or min(u.shape[1],u.shape[2]-1)<2 or not all(np.isfinite(a).all() for a in [u,v,m]) or np.any(m<=0)
            or not np.isfinite(cell_m) or cell_m<=0 or np.any(u[:,:,1:-1]) or np.any(v[:,1:-1])):
        raise ValueError('Need finite matching perimeter-only ports, positive masses and spacing')
    net=lambda:float(np.sum(m[:,None]*(u[:,:,-1]-u[:,:,0]))+np.sum(m[:,None]*(v[:,-1]-v[:,0])))
    before=net();faces=2*(u.shape[1]+v.shape[2]);correction=before/(m.sum()*faces)
    u[:,:,0]+=correction;u[:,:,-1]-=correction;v[:,0]+=correction;v[:,-1]-=correction
    return u,v,dict(original_net_outward_dry_mass_kg_s=before*cell_m,
        uniform_outward_speed_correction_ms=correction,corrected_net_outward_dry_mass_kg_s=net()*cell_m,
        scope='Explicit preparation correction only; all levels shift equally, vertical shear unchanged. Model itself never renormalizes incoming dry mass.')


class OpenMeanRigidLidModel(RefinedRigidLidMoistModel):
    def __init__(self,pressure_edges_pa,shape,cell_m,coriolis,*,u_boundary=0.,v_boundary=0.,**kwargs):
        # Keep the frozen parent's zero-mean boundary contract intact.
        super().__init__(pressure_edges_pa,shape,cell_m,coriolis,u_boundary=0.,v_boundary=0.,**kwargs)
        ny,nx=self.shape
        self.u_boundary=_field(u_boundary,(self.nz,ny,nx+1),'prescribed east boundary')
        self.v_boundary=_field(v_boundary,(self.nz,ny+1,nx),'prescribed south boundary')
        if np.any(self.u_boundary[:,:,1:-1]) or np.any(self.v_boundary[:,1:-1]):raise ValueError('Boundary arrays must have zero interior entries')
        m=self.column.cell_mass_kg_m2[:,None,None]
        boundary_div=(np.diff(m*self.u_boundary,axis=2)+np.diff(m*self.v_boundary,axis=1)).sum(0)/self.dx
        scale=float(np.sum(abs(boundary_div)))
        if abs(boundary_div.sum())>1e-12*scale+1e-13:raise ValueError('Prescribed ports must have globally zero net dry mass; prepare explicitly')
        self.boundary_mass_divergence=boundary_div.ravel()
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
        x=self._pack_unchecked(u,v);div=self.column_divergence@x+self.boundary_mass_divergence
        scale=max(float(np.max(abs(self.column_divergence)@abs(x)+abs(self.boundary_mass_divergence))),1e-12)
        if np.max(abs(div))>1e-10*scale+1e-13:raise ValueError('Open rigid-lid winds must close actual column dry mass; project initial wind first')
        return x

    def project_initial_wind(self,u,v):
        """Nearest mass-weighted wind satisfying the affine regional mass constraint.

        Unlike a projection to a zero-flux subspace, required throughflow may
        increase kinetic energy. Report signed energy change, never hidden heat.
        """
        raw=self._pack_unchecked(u,v)
        x=raw-self.constraint.T@self.projection_factor.solve(self.constraint@raw+self.boundary_mass_divergence[:-1])
        u1,v1=self._unpack(x);self._velocity(u1,v1)
        correction=raw-x;tangent=correction-self.constraint.T@self.projection_factor.solve(self.constraint@correction)
        if np.linalg.norm(tangent)>1e-10*max(np.linalg.norm(correction),1.):raise RuntimeError('Affine projection is not orthogonal to mass-admissible increments')
        return u1,v1,dict(kinetic_energy_change_j_m2=float(.5*(np.dot(x,x)-np.dot(raw,raw))/self.n),
            maximum_column_mass_residual_kg_m2_s=float(abs(self.column_divergence@x+self.boundary_mass_divergence).max()),
            scope='Affine minimum-change initial projection; actual signed kinetic energy change separate, no heat compensation or balance claim.')

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
            self.factors[dt]=OpenMeanSaddleSolve(block,self.n_u+self.n_v)
        self.factors[dt].calls=[]
        guess=t0.copy();previous_velocity=None
        for iteration in range(1,max_iterations+1):
            midpoint_t=.5*(t0+guess)
            force=self._pressure_force(midpoint_t)+self.boundary_rotation_force
            solution=self.factors[dt].solve(np.r_[x0-.5*dt*(self.momentum@x0)-dt*force,-self.boundary_mass_divergence[:-1]])
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
        boundary_constraint=float(np.dot(constraint_pressure,self.boundary_mass_divergence[:-1]))
        energy_error=float((new_h-old_h).sum()+rain_h.sum()+dk-dt*external.sum()+dt*(boundary_h+boundary_phi+boundary_constraint-boundary_rotation_work))
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
        if abs(constraint_work+boundary_constraint)>1e-9*max(float(abs(mid*constraint_force).sum()),abs(boundary_constraint),1.):raise RuntimeError('Actual open-boundary constraint-pressure work failed')
        cert=dict(iterations=iteration,
            maximum_column_mass_divergence_kg_m2_s=float(abs(self.column_divergence@x+self.boundary_mass_divergence).max()),
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
            outward_boundary_gas_enthalpy_w_m2=boundary_h/self.n,outward_boundary_geopotential_work_w_m2=(boundary_phi+boundary_constraint)/self.n,
            outward_boundary_thermal_geopotential_work_w_m2=boundary_phi/self.n,
            outward_boundary_constraint_geopotential_work_w_m2=boundary_constraint/self.n,
            prescribed_boundary_rotation_work_w_m2=boundary_rotation_work/self.n,outward_boundary_vapor_kg_m2_s=boundary_w/self.n,
            gas_enthalpy_plus_kinetic_energy_j_m2=float((new_h.sum()+.5*np.dot(x,x))/self.n),
            kinetic_energy_j_m2=float(.5*np.dot(x,x)/self.n),
            transport_water=water.certificate,transport_enthalpy=enthalpy.certificate,
            scope='Open rigid-lid mean throughflow with globally balanced prescribed dry-mass ports and actual constraint geopotential flux: incoming gas/vapor, geopotential flux and external boundary-rotation work booked. No exterior kinetic storage, nonlinear momentum advection, transparent radiation, terrain or Earth adoption.')
        calls=self.factors[dt].calls
        cert['saddle_refinement']=dict(coupling_solves=len(calls),maximum_initial_rowwise_backward_error=max(c['initial_rowwise_backward_error'] for c in calls),
            maximum_final_rowwise_backward_error=max(c['final_rowwise_backward_error'] for c in calls),refinement_rounds_per_solve=3,
            error_scale='Separate mass-weighted velocity and constraint-potential infinity norms, rowwise. Native mass/energy tolerances unchanged.')
        return PressureMoistState(new_t,new_w,u1,v1,rain,rain_h,cert)


