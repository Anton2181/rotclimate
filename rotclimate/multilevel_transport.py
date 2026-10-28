"""Conservative native-face donor transport over any fixed dry-air layers.

Vertical mass exchange is diagnosed from actual horizontal dry divergence.
No arbitrary humidity partition, source from convergence, condensation or
heat law is supplied. Positive reaction permits steady and backward-Euler
linear equations; reaction1/dt is time tendency, not rainfall.
"""
from dataclasses import dataclass
import warnings
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning,spsolve


@dataclass
class MultilevelTracer:
    amount: np.ndarray
    reaction_loss: np.ndarray
    east_tracer_flux: np.ndarray
    south_tracer_flux: np.ndarray
    upward_tracer_flux: np.ndarray
    upward_dry_mass_flux: np.ndarray
    certificate: dict


def _field(value,shape,name,*,minimum=None):
    a=np.asarray(value,float)
    if a.ndim==1 and a.shape[0]==shape[0]:a=a[:,None,None]
    try:a=np.broadcast_to(a,shape).copy()
    except ValueError as exc:raise ValueError('Need matching '+name) from exc
    if not np.isfinite(a).all() or (minimum is not None and np.any(a<minimum)):
        raise ValueError('Need finite valid '+name)
    return a


def solve_multilevel(layer_mass,u_east,v_south,cell_m,source,reaction_rate,external_mixing_ratio):
    """Solve reaction*amount + div(actual donor fluxes)=source.

All layer masses are positive and fixed. Internal/interface/exterior fluxes
retain their actual staggered representation. Positive upward air uses the
lower donor; negative uses upper. Surface/top dry mass flux is zero. Total
horizontal column divergence must match that constraint to roundoff tolerance.
External incoming air carries supplied layer mixing ratio; outward carries
local donor. Source/reaction are explicit, never inferred from observed rain.
"""
    mass=np.asarray(layer_mass,float)
    if (mass.ndim!=3 or min(mass.shape)<2 or not np.isfinite(mass).all() or np.any(mass<=0)
            or not np.isfinite(cell_m) or cell_m<=0):
        raise ValueError('Need finite positive level/row/column masses and grid spacing')
    nz,ny,nx=mass.shape;count=mass.size;dx=float(cell_m)
    u=_field(u_east,(nz,ny,nx+1),'east face velocity')
    v=_field(v_south,(nz,ny+1,nx),'south face velocity')
    supplied=_field(source,mass.shape,'source',minimum=0.)
    rate=_field(reaction_rate,mass.shape,'reaction rate',minimum=0.)
    if np.any(rate<=0):raise ValueError('Strictly positive reaction/time rate required for a nonsingular fixed-mass problem')
    outside=_field(external_mixing_ratio,mass.shape,'external mixing ratio',minimum=0.)
    mx=np.concatenate([mass[:,:,:1],.5*(mass[:,:,:-1]+mass[:,:,1:]),mass[:,:,-1:]],axis=2)
    my=np.concatenate([mass[:,:1],.5*(mass[:,:-1]+mass[:,1:]),mass[:,-1:]],axis=1)
    fx,fy=mx*u,my*v
    horizontal_div=(np.diff(fx,axis=2)+np.diff(fy,axis=1))/dx
    cumulative=-np.cumsum(horizontal_div,axis=0)
    speed=max(1.,float(np.abs(u).max()),float(np.abs(v).max()))
    scale=float(mass.sum(0).max())*speed/dx
    dry_error=float(np.abs(cumulative[-1]).max()/scale)
    if dry_error>1e-10:raise ValueError('Layer winds do not close stationary dry-column mass with rigid top/surface')
    up=cumulative[:-1]
    # Top/surface fluxes are exactly zero; the diagnosed roundoff residual is
    # exposed above rather than exported as an artificial dry mass source.
    ids=np.arange(count).reshape(mass.shape);rows=[];cols=[];values=[];rhs=supplied.copy()
    def add(row,col,value):
        rows.extend(np.asarray(row).ravel().tolist());cols.extend(np.asarray(col).ravel().tolist())
        values.extend(np.asarray(value).ravel().tolist())
    def transfer(left,right,flux,ml,mr):
        pos=np.maximum(flux,0);neg=np.minimum(flux,0)
        add(left,left,pos/ml);add(right,left,-pos/ml)
        add(left,right,neg/mr);add(right,right,-neg/mr)
    add(ids,ids,rate)
    transfer(ids[:,:,:-1],ids[:,:,1:],fx[:,:,1:-1]/dx,mass[:,:,:-1],mass[:,:,1:])
    transfer(ids[:,:-1],ids[:,1:],fy[:,1:-1]/dx,mass[:,:-1],mass[:,1:])
    transfer(ids[:-1],ids[1:],up,mass[:-1],mass[1:])
    for index,normal,own,out in [
            (ids[:,:,0],-fx[:,:,0]/dx,mass[:,:,0],outside[:,:,0]),
            (ids[:,:,-1],fx[:,:,-1]/dx,mass[:,:,-1],outside[:,:,-1]),
            (ids[:,0],-fy[:,0]/dx,mass[:,0],outside[:,0]),
            (ids[:,-1],fy[:,-1]/dx,mass[:,-1],outside[:,-1])]:
        add(index,index,np.maximum(normal,0)/own)
        rhs.ravel()[index]+= -np.minimum(normal,0)*out
    matrix=coo_matrix((values,(rows,cols)),shape=(count,count)).tocsc()
    with warnings.catch_warnings():
        warnings.simplefilter('error',MatrixRankWarning)
        amount=spsolve(matrix,rhs.ravel()).reshape(mass.shape)
    if not np.isfinite(amount).all() or np.any(amount<0):raise FloatingPointError('Invalid multilevel donor state')
    diagonal=matrix.diagonal().reshape(mass.shape)
    linear_error=float(np.max(np.abs((matrix@amount.ravel()).reshape(mass.shape)-rhs)/diagonal))
    q=amount/mass
    qx=np.concatenate([outside[:,:,:1],q,outside[:,:,-1:]],axis=2)
    qy=np.concatenate([outside[:,:1],q,outside[:,-1:]],axis=1)
    water_x=fx*np.where(fx>=0,qx[:,:,:-1],qx[:,:,1:])
    water_y=fy*np.where(fy>=0,qy[:,:-1],qy[:,1:])
    water_up=up*np.where(up>=0,q[:-1],q[1:])
    vertical=np.concatenate([np.zeros_like(q[:1]),water_up,np.zeros_like(q[:1])],axis=0)
    outflow=(np.diff(water_x,axis=2)+np.diff(water_y,axis=1))/dx+np.diff(vertical,axis=0)
    loss=rate*amount
    actual_error=float(np.max(np.abs(supplied-loss-outflow)/diagonal))
    tolerance=1e-10*max(1.,float(amount.max()))
    if max(actual_error,linear_error)>tolerance:raise RuntimeError('Multilevel matrix/actual donor face equation failed')
    boundary=(water_x[:,:,-1].sum(1)-water_x[:,:,0].sum(1)+water_y[:,-1].sum(1)-water_y[:,0].sum(1))/dx
    vertical_out=np.diff(vertical,axis=0).sum((1,2))
    budgets=supplied.sum((1,2))-loss.sum((1,2))-boundary-vertical_out
    cert=dict(levels=nz,maximum_relative_dry_column_mass_residual=dry_error,
        diagonal_scaled_matrix_error=linear_error,diagonal_scaled_actual_face_error=actual_error,
        source_per_layer_cell_s=supplied.sum((1,2)).tolist(),reaction_per_layer_cell_s=loss.sum((1,2)).tolist(),
        outward_boundary_per_layer_cell_s=boundary.tolist(),upward_interface_transfer_cell_s=water_up.sum((1,2)).tolist(),
        actual_layer_budget_errors_cell_s=budgets.tolist(),actual_column_budget_error_cell_s=float(budgets.sum()),
        minimum_amount=float(amount.min()),maximum_amount=float(amount.max()),
        scope='Fixed-mass multilevel conservative donor scalar; explicit reaction/supply, no phase or momentum/thermodynamic feedback')
    return MultilevelTracer(amount,loss,water_x,water_y,water_up,up,cert)
