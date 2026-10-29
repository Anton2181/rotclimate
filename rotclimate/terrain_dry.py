"""Closed dry terrain pressure/Coriolis/enthalpy integration research core.

Fixed hydrostatic reference geometry; staircase pressure-coordinate ground.
No nonlinear momentum advection, open boundaries, radiation, surface forcing,
vapor, phase changes or Earth calibration. Never selected by the normal atlas.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix,diags,bmat,eye,csc_matrix
from .column_thermodynamics import CP,RD,G
from .terrain_apertures import horizontal_apertures,mass_flux_divergence
from .terrain_pressure_gradient import common_pressure_force
from .terrain_pressure_work import compression_power
from .terrain_transport import TerrainTransport
from .open_mean_boundary import OpenMeanSaddleSolve


@dataclass(frozen=True)
class TerrainDryState:
    temperature_k: np.ndarray  # actual dry-mass-weighted layer means
    east_speed_ms: np.ndarray  # explicit common-pressure level-pair ports
    south_speed_ms: np.ndarray
    certificate: dict


class TerrainDryModel:
    def __init__(self,grid,elevation_m,coriolis,cell_m,*,reference_temperature_k=288.15,reference_pressure_pa=101325.,reference_lapse_k_m=.0065):
        self.grid=grid;self.h=np.asarray(elevation_m,float).copy();self.apertures=horizontal_apertures(grid);self.mass=grid.dry_mass_kg_m2.copy();self.shape=self.mass.shape
        if self.h.shape!=self.shape[1:] or not np.isfinite(self.h).all() or not np.isfinite(cell_m) or cell_m<=0:raise ValueError('Need matching ground and positive grid spacing')
        self.dx=float(cell_m);self.reference=dict(reference_temperature_k=reference_temperature_k,reference_pressure_pa=reference_pressure_pa,reference_lapse_k_m=reference_lapse_k_m);p=grid.edges_pa;ratio=(p[:-1]-p[1:])/p[1:];alpha=RD*reference_lapse_k_m/G
        self.reference_mean=reference_temperature_k*(p[1:]/reference_pressure_pa)**alpha*np.expm1((1+alpha)*np.log1p(ratio))/((1+alpha)*ratio)
        a=self.apertures;self.ex=np.nonzero(a.east_kg_m2);self.sy=np.nonzero(a.south_kg_m2);self.nu=len(self.ex[0]);self.mu=np.r_[a.east_kg_m2[self.ex],a.south_kg_m2[self.sy]];self.root=np.sqrt(self.mu);_,ny,nx=self.shape;n=ny*nx
        left=np.r_[self.ex[2]*nx+self.ex[3],self.sy[2]*nx+self.sy[3]];right=np.r_[self.ex[2]*nx+self.ex[3]+1,(self.sy[2]+1)*nx+self.sy[3]];ports=np.arange(len(self.mu));self.constraint=coo_matrix((np.r_[self.root,-self.root]/self.dx,(np.r_[left,right],np.r_[ports,ports])),shape=(n,len(self.mu))).tocsc()[:-1]
        ids=np.arange(self.mass.size).reshape(self.shape)
        def interpolate(index,kind,offset):
            k,l,j,i=index;jr,ir=(j,i+1) if kind=='east' else (j+1,i);first=ids[k,j,i];second=ids[l,jr,ir];columns=np.arange(len(k));root=self.root[offset:offset+len(k)]
            return coo_matrix((np.r_[.5*root/self.mass.ravel()[first],.5*root/self.mass.ravel()[second]],(np.r_[first,second],np.r_[columns,columns])),shape=(self.mass.size,len(k))).tocsc()
        cx=interpolate(self.ex,'east',0);cy=interpolate(self.sy,'south',self.nu);f=np.broadcast_to(np.asarray(coriolis,float),self.shape)
        if not np.isfinite(f).all():raise ValueError('Need finite terrestrial Coriolis field')
        rotation=cx.T@diags((self.mass*f).ravel())@cy
        self.rotation=bmat([[csc_matrix((self.nu,self.nu)),rotation],[-rotation.T,csc_matrix((len(self.mu)-self.nu,len(self.mu)-self.nu))]],format='csc');self.factors={}
        # The column-constant ground/reference potential is entirely in the
        # barotropic constraint's range. Absorb it into the pressure gauge
        # before solving, avoiding cancellation of tiny rest-state terms.
        reference_force=common_pressure_force(grid,self.h,np.zeros_like(self.mass),self.dx,**self.reference)
        self.reference_barotropic=self._pack(reference_force.east_ms2,reference_force.south_ms2)

    def _pack(self,u,v):return self.root*np.r_[u[self.ex],v[self.sy]]

    def _unpack(self,x):
        u=np.zeros_like(self.apertures.east_kg_m2);v=np.zeros_like(self.apertures.south_kg_m2);velocity=x/self.root;u[self.ex]=velocity[:self.nu];v[self.sy]=velocity[self.nu:];return u,v

    def initial_state(self,temperature_k,east_speed_ms,south_speed_ms):
        t=np.asarray(temperature_k,float);u=np.asarray(east_speed_ms,float);v=np.asarray(south_speed_ms,float)
        if t.shape!=self.shape or not np.isfinite(t).all() or np.any((t<180)|(t>330)) or u.shape!=self.apertures.east_kg_m2.shape or v.shape!=self.apertures.south_kg_m2.shape or not np.isfinite(u).all() or not np.isfinite(v).all():raise ValueError('Need supported matching dry temperature and velocities')
        if np.any(u[self.apertures.east_kg_m2==0]) or np.any(v[self.apertures.south_kg_m2==0]):raise ValueError('Closed ports cannot carry wind')
        divergence=mass_flux_divergence(self.apertures,u,v,self.dx).sum(0)
        if abs(divergence).max()>1e-10*max(float(abs(u).max()),float(abs(v).max()),1.)+1e-13:raise ValueError('Initial wind must close actual column dry mass; project explicitly first')
        return TerrainDryState(t.copy(),u.copy(),v.copy(),{})

    def advance(self,state,dt_s,*,temperature_tolerance_k=1e-10,max_iterations=60):
        if not np.isfinite([dt_s,temperature_tolerance_k]).all() or min(dt_s,temperature_tolerance_k)<=0 or not isinstance(max_iterations,int) or max_iterations<1:raise ValueError('Need positive time step/tolerance and iteration budget')
        state=self.initial_state(state.temperature_k,state.east_speed_ms,state.south_speed_ms);dt=float(dt_s);x0=self._pack(state.east_speed_ms,state.south_speed_ms);t0=state.temperature_k;guess=t0.copy();n=len(x0);constraint=self.constraint
        if dt not in self.factors:
            matrix=bmat([[eye(n,format='csc')+.5*dt*self.rotation,dt*constraint.T],[constraint,csc_matrix((constraint.shape[0],constraint.shape[0]))]],format='csc');self.factors[dt]=OpenMeanSaddleSolve(matrix,n)
        solver=self.factors[dt];solver.calls=[]
        for iteration in range(1,max_iterations+1):
            midpoint_t=.5*(t0+guess);force=common_pressure_force(self.grid,self.h,midpoint_t-self.reference_mean,self.dx,**self.reference);acceleration=self._pack(force.east_ms2,force.south_ms2)-self.reference_barotropic
            solution=solver.solve(np.r_[x0-.5*dt*(self.rotation@x0)+dt*acceleration,np.zeros(constraint.shape[0])]);x=solution[:n];u,v=self._unpack(x);mid=.5*(x0+x);um,vm=self._unpack(mid)
            compression=compression_power(self.grid,um,vm,self.dx,midpoint_t-self.reference_mean,**self.reference);transport=TerrainTransport(self.grid,um,vm,self.dx,dt);candidate,thermal=transport.advance(CP*t0,source_per_area_s=compression.layer_power_w_m2);candidate=candidate/CP;error=float(abs(candidate-guess).max());guess=candidate
            if error<=temperature_tolerance_k:break
        else:raise RuntimeError('Dry terrain pressure/enthalpy coupling did not converge')
        if np.any((guess<180)|(guess>330)):raise ValueError('Dry terrain time step leaves supported temperature domain')
        # Re-evaluate physical powers at the returned midpoint; do not feed an
        # energy residual back into temperature, compression, or momentum.
        final_mid=.5*(t0+guess);force=common_pressure_force(self.grid,self.h,final_mid-self.reference_mean,self.dx,**self.reference);acceleration=self._pack(force.east_ms2,force.south_ms2)-self.reference_barotropic;compression=compression_power(self.grid,um,vm,self.dx,final_mid-self.reference_mean,**self.reference)
        kinetic_change=float(.5*((x@x)-(x0@x0)));gas_change=float((CP*self.mass*(guess-t0)).sum());residual=gas_change+kinetic_change;scale=max(abs(gas_change),abs(kinetic_change),1.)
        if abs(residual)>1e-7*scale+1e-5:raise RuntimeError('Actual dry terrain gas/kinetic budget failed')
        pressure=float(mid@acceleration);constraint_work=float(mid@(constraint.T@solution[n:]));rotation_work=float(mid@(self.rotation@mid));momentum=x-x0+dt*(self.rotation@mid+constraint.T@solution[n:]-acceleration)
        certificate=dict(iterations=iteration,temperature_fixed_point_residual_k=error,gas_enthalpy_change_j_m2_sum=gas_change,kinetic_energy_change_j_m2_sum=kinetic_change,actual_energy_residual_j_m2_sum=residual,normalized_actual_energy_error=abs(residual)/scale,mechanical_pressure_power_w_m2_sum=pressure,compression_power_w_m2_sum=float(compression.layer_power_w_m2.sum()),constraint_work_w_m2_sum=constraint_work,coriolis_work_w_m2_sum=rotation_work,maximum_actual_midpoint_momentum_residual_weighted_ms=float(abs(momentum).max()),maximum_native_dry_mass_residual_kg_m2_s=thermal['maximum_native_dry_mass_residual_kg_m2_s'],thermal_transport=thermal,energy_residual_heat_correction_j_m2=0.,reference_column_potential_absorbed_in_constraint_gauge=True,scope='Closed dry pressure/Coriolis and native enthalpy subsystem on staircase terrain; no nonlinear momentum advection, moisture, open boundaries, surface forcing or Earth adoption.')
        return TerrainDryState(guess,u,v,certificate)
