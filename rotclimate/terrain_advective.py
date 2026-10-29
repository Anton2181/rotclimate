"""Nonlinear momentum transport candidate for the closed dry terrain core.

Reference dry dynamics stay untouched. This candidate iterates midpoint native
velocity as well as temperature, using energy-skew projected central momentum
transport and the same conservative enthalpy/pressure/Coriolis discretizations.
It remains a closed dry subsystem, without rainfall or Earth climate adoption.
"""
import numpy as np
from scipy.sparse import bmat,eye,csc_matrix
from .column_thermodynamics import CP,G
from .terrain_dry import TerrainDryModel,TerrainDryState
from .terrain_momentum_transport import momentum_transport,projected_central_operator
from .terrain_pressure_gradient import common_pressure_force
from .terrain_pressure_work import compression_power
from .terrain_apertures import mass_flux_divergence
from .terrain_transport import TerrainTransport
from .open_mean_boundary import OpenMeanSaddleSolve


class TerrainAdvectiveModel(TerrainDryModel):
    def __init__(self,*args,advect_momentum=True,**kwargs):
        if not isinstance(advect_momentum,bool):raise ValueError('Momentum transport flag must be explicit boolean')
        self.advect_momentum=advect_momentum
        super().__init__(*args,**kwargs)
        geometry=momentum_transport(self.grid,np.zeros_like(self.apertures.east_kg_m2),np.zeros_like(self.apertures.south_kg_m2),self.dx)
        self.east_interpolation=geometry.east_interpolation;self.south_interpolation=geometry.south_interpolation

    def _advection(self,transport):
        if not self.advect_momentum:return csc_matrix((len(self.mu),len(self.mu)))
        return projected_central_operator(transport,self.east_interpolation,self.south_interpolation)

    def _heat_transport(self,transport,t0,power,um,vm):
        # Affine centering is applied before time/mass and flux terms are
        # assembled together. The native reference divergence is evaluated
        # directly from fluxes, avoiding loss of its low bits in M@1-m/dt.
        temperature_reference=float(t0.flat[0]);reference=CP*temperature_reference
        native_divergence=mass_flux_divergence(self.apertures,um,vm,self.dx)
        # Only interior vertical ports exist. Boundary omega is a residual
        # diagnostic, never an actual flux through the rigid ground/top.
        vertical=transport.interface_omega_pa_s[1:-1]/G
        native_divergence[1:]+=vertical;native_divergence[:-1]-=vertical
        centered_source=power-reference*native_divergence
        centered,receipt=transport.advance(CP*(t0-temperature_reference),source_per_area_s=centered_source,nonnegative=False)
        temperature=temperature_reference+centered/CP
        receipt.update(reference_specific_enthalpy_j_kg=reference,affine_reference_flux_term_w_m2_sum=float((reference*native_divergence).sum()),actual_full_enthalpy_source_residual_j_m2_sum=float((CP*self.mass*(temperature-t0)).sum()-transport.dt*power.sum()),scope='Affine-centered native enthalpy equation; explicit reference flux divergence, no energy-residual feedback, clipping or renormalization.')
        return temperature,receipt

    def advance(self,state,dt_s,*,temperature_tolerance_k=1e-10,velocity_tolerance_ms=1e-9,max_iterations=80):
        if not np.isfinite([dt_s,temperature_tolerance_k,velocity_tolerance_ms]).all() or min(dt_s,temperature_tolerance_k,velocity_tolerance_ms)<=0 or not isinstance(max_iterations,int) or max_iterations<1:raise ValueError('Need positive time step/tolerances and iteration budget')
        state=self.initial_state(state.temperature_k,state.east_speed_ms,state.south_speed_ms);dt=float(dt_s);x0=self._pack(state.east_speed_ms,state.south_speed_ms);t0=state.temperature_k;guess=t0.copy();guess_x=x0.copy();n=len(x0);constraint=self.constraint
        for iteration in range(1,max_iterations+1):
            ug,vg=self._unpack(.5*(x0+guess_x));old_mid_transport=TerrainTransport(self.grid,ug,vg,self.dx,dt);advection=self._advection(old_mid_transport);operator=self.rotation+advection
            midpoint_t=.5*(t0+guess);force=common_pressure_force(self.grid,self.h,midpoint_t-self.reference_mean,self.dx,**self.reference);acceleration=self._pack(force.east_ms2,force.south_ms2)-self.reference_barotropic
            matrix=bmat([[eye(n,format='csc')+.5*dt*operator,dt*constraint.T],[constraint,csc_matrix((constraint.shape[0],constraint.shape[0]))]],format='csc');solver=OpenMeanSaddleSolve(matrix,n)
            solution=solver.solve(np.r_[x0-.5*dt*(operator@x0)+dt*acceleration,np.zeros(constraint.shape[0])]);x=solution[:n];u,v=self._unpack(x);mid=.5*(x0+x);um,vm=self._unpack(mid)
            compression=compression_power(self.grid,um,vm,self.dx,midpoint_t-self.reference_mean,**self.reference);transport=TerrainTransport(self.grid,um,vm,self.dx,dt);candidate,thermal=self._heat_transport(transport,t0,compression.layer_power_w_m2,um,vm)
            temperature_error=float(abs(candidate-guess).max());velocity_error=float(np.max(abs(x-guess_x)/self.root));guess=candidate;guess_x=x
            if temperature_error<=temperature_tolerance_k and velocity_error<=velocity_tolerance_ms:break
        else:raise RuntimeError('Advective terrain velocity/temperature coupling did not converge')
        if np.any((guess<180)|(guess>330)):raise ValueError('Advective terrain step leaves supported temperature domain')
        # Final native midpoint powers are evaluated again independently. The
        # operator is skew for every iterate; no energy error repairs heat.
        final_mid=.5*(t0+guess);force=common_pressure_force(self.grid,self.h,final_mid-self.reference_mean,self.dx,**self.reference);acceleration=self._pack(force.east_ms2,force.south_ms2)-self.reference_barotropic;compression=compression_power(self.grid,um,vm,self.dx,final_mid-self.reference_mean,**self.reference);final_advection=self._advection(transport)
        kinetic_change=float(.5*((x@x)-(x0@x0)));gas_change=float((CP*self.mass*(guess-t0)).sum());residual=gas_change+kinetic_change;scale=max(abs(gas_change),abs(kinetic_change),1.)
        if abs(residual)>1e-7*scale+1e-5:raise RuntimeError('Actual advective terrain gas/kinetic budget failed')
        momentum=x-x0+dt*((self.rotation+final_advection)@mid+constraint.T@solution[n:]-acceleration)
        certificate=dict(nonlinear_momentum_transport_enabled=self.advect_momentum,iterations=iteration,temperature_fixed_point_residual_k=temperature_error,velocity_fixed_point_residual_ms=velocity_error,gas_enthalpy_change_j_m2_sum=gas_change,kinetic_energy_change_j_m2_sum=kinetic_change,actual_energy_residual_j_m2_sum=residual,normalized_actual_energy_error=abs(residual)/scale,mechanical_pressure_power_w_m2_sum=float(mid@acceleration),compression_power_w_m2_sum=float(compression.layer_power_w_m2.sum()),constraint_work_w_m2_sum=float(mid@(constraint.T@solution[n:])),coriolis_work_w_m2_sum=float(mid@(self.rotation@mid)),advective_kinetic_work_w_m2_sum=float(mid@(final_advection@mid)),maximum_constraint_potential_m2_s2=float(abs(solution[n:]).max()),maximum_actual_midpoint_momentum_residual_weighted_ms=float(abs(momentum).max()),maximum_advective_acceleration_ms2=float(np.max(abs(final_advection@mid)/self.root)),maximum_native_dry_mass_residual_kg_m2_s=thermal['maximum_native_dry_mass_residual_kg_m2_s'],thermal_transport=thermal,energy_residual_heat_correction_j_m2=0.,reference_column_potential_absorbed_in_constraint_gauge=True,scope='Closed dry terrain candidate with native projected central nonlinear momentum transport; no moisture/phase, open boundaries, surface/radiative forcing or Earth climate adoption.')
        return TerrainDryState(guess,u,v,certificate)
