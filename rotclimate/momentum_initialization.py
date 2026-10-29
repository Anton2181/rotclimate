"""A convex initial-momentum diagnostic, not a coupled balanced initialization.

Minimize ||A x + b||² + ||x - x_ref||²/tau² in dry-mass-weighted
face velocities x. A is the prototype's actual Coriolis/drag operator.
This changes only the proposed initial winds, never f, drag, T or water.
Stationary momentum does not imply stationary thermodynamics or moist balance.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import eye
from scipy.sparse.linalg import spsolve


@dataclass
class MomentumInitialization:
    u_east: np.ndarray
    v_south: np.ndarray
    certificate: dict


def initial_transport_tendency(model,temperature_k,vapor_kg_m2,u_east,v_south):
    """Actual instantaneous donor/adiabatic tendencies, before liquid phase.

    No timestep or coupled integration is performed. This reveals thermal
    adjustment that a momentum-only initialization can leave unresolved.
    Vapor heat capacity and source enthalpy follow the existing prototype.
    """
    from .pressure_moist import gas_energy
    t,w=np.asarray(temperature_k,float),np.asarray(vapor_kg_m2,float)
    if (t.shape!=model.mass.shape or w.shape!=t.shape or not np.isfinite(t).all()
            or not np.isfinite(w).all() or np.any((t<180)|(t>330)) or np.any(w<0)):
        raise ValueError('Need matching terrestrial temperature and nonnegative water')
    x=model._velocity(u_east,v_south);u,v=model._unpack(x);m=model.mass;dx=model.dx
    fx=m[:,:,:1]*u;fy=m[:,:1]*v
    horizontal=(np.diff(fx,axis=2)+np.diff(fy,axis=1))/dx
    up=-np.cumsum(horizontal,axis=0)[:-1]
    def tendency(q,outside):
        qx=np.concatenate([outside[:,:,:1],q,outside[:,:,-1:]],axis=2)
        qy=np.concatenate([outside[:,:1],q,outside[:,-1:]],axis=1)
        tx=fx*np.where(fx>=0,qx[:,:,:-1],qx[:,:,1:]);ty=fy*np.where(fy>=0,qy[:,:-1],qy[:,1:])
        tz=up*np.where(up>=0,q[:-1],q[1:]);tz=np.concatenate([np.zeros_like(q[:1]),tz,np.zeros_like(q[:1])],axis=0)
        result=-(np.diff(tx,axis=2)+np.diff(ty,axis=1))/dx-np.diff(tz,axis=0)
        boundary=float((tx[:,:,-1].sum()-tx[:,:,0].sum()+ty[:,-1].sum()-ty[:,0].sum())/dx)
        return result,boundary
    q=w/m;h=gas_energy(t,w,m)/m
    ext_t=getattr(model,'external_t',t);ext_q=getattr(model,'external_q',q)
    ext_h=1004*ext_t+ext_q*(2.5e6+1850*(ext_t-273.15))
    dwater,boundary_water=tendency(q,ext_q);dh,boundary_h=tendency(h,ext_h)
    compression=model.column.compression_power_w_m2(t,(np.diff(u,axis=2)+np.diff(v,axis=1))/dx)
    drag=np.zeros_like(t);fu=model.r*m[:,:,:1]*u[:,:,1:-1]**2;fv=model.r*m[:,:1]*v[:,1:-1]**2
    drag[:,:,:-1]+=.5*fu;drag[:,:,1:]+=.5*fu;drag[:,:-1]+=.5*fv;drag[:,1:]+=.5*fv
    dh+=compression+drag
    dt=(dh-(2.5e6+1850*(t-273.15))*dwater)/(1004*m+1850*w)
    return dict(temperature_k_s=dt,vapor_kg_m2_s=dwater,gas_enthalpy_w_m2=dh,
        outward_vapor_kg_m2_s=boundary_water/model.n,outward_gas_enthalpy_w_m2=boundary_h/model.n,
        scope='Instantaneous actual donor/compression/drag tendency before phase or convection; no time integration and no thermal balance guarantee.')


def least_acceleration_wind(model,temperature_k,reference_u,reference_v,*,correction_time_s):
    """Propose initial winds with a finite, explicitly declared correction prior.

    tau is a regularization timescale, not an atmospheric parameter. Longer
    tau favors smaller momentum residuals at the cost of larger wind changes.
    No observations, pressure/temperature changes or speed clipping are used.
    """
    if not np.isfinite(correction_time_s) or correction_time_s<=0:
        raise ValueError('Need a finite positive correction timescale')
    t=np.asarray(temperature_k,float)
    if t.shape!=model.mass.shape or not np.isfinite(t).all() or np.any((t<180)|(t>330)):
        raise ValueError('Need matching terrestrial temperature')
    ref=model._velocity(reference_u,reference_v)
    a=model.momentum;b=model._pressure_force(t)+getattr(model,'boundary_rotation_force',0.)
    tau=float(correction_time_s);scaled=tau*a
    normal=eye(len(ref),format='csc')+scaled.T@scaled
    x=spsolve(normal,ref-tau*(scaled.T@b))
    if not np.isfinite(x).all():raise RuntimeError('Initial momentum solve failed')
    u,v=model._unpack(x);model._velocity(u,v)
    old=a@ref+b;residual=a@x+b;change=x-ref
    stationarity=change+tau*tau*(a.T@residual)
    scale=max(float(np.max(abs(ref))),float(np.max(abs(x))),float(np.max(abs(tau*tau*(a.T@b)))),1.)
    if np.max(abs(stationarity))>1e-9*scale:raise RuntimeError('Convex initialization optimality failed')
    def maximum_acceleration(y):
        return float(max(np.max(abs(y[:model.n_u].reshape(model.nz,model.shape[0],model.shape[1]-1)/model.sqrt_mass[:,None,None])),
            np.max(abs(y[model.n_u:].reshape(model.nz,model.shape[0]-1,model.shape[1])/model.sqrt_mass[:,None,None]))))
    return MomentumInitialization(u,v,dict(correction_time_s=tau,
        initial_mass_weighted_acceleration_norm=float(np.linalg.norm(old)),
        final_mass_weighted_acceleration_norm=float(np.linalg.norm(residual)),
        initial_maximum_acceleration_ms2=maximum_acceleration(old),final_maximum_acceleration_ms2=maximum_acceleration(residual),
        velocity_correction_mass_weighted_norm=float(np.linalg.norm(change)),
        old_objective=float(np.dot(old,old)),new_objective=float(np.dot(residual,residual)+np.dot(change,change)/tau**2),
        relative_optimality_residual=float(np.max(abs(stationarity))/scale),
        peak_level_velocity_ms=float(max(abs(u).max(),abs(v).max())),
        kinetic_energy_change_j_m2=float(.5*(np.dot(x,x)-np.dot(ref,ref))/model.n),
        scope='Unique convex momentum-only initial-wind diagnostic. No thermal/moist balance, normal-mode filtering, integration or physics adoption.'))
