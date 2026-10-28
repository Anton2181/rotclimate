"""Isolated steady forced/damped baroclinic shallow-water mode, periodic C-grid.

Solves momentum AND thermal-thickness adjustment rather than prescribing a
nondivergent shear. This is not yet a coupled Earth climate model. Planar,
constant-depth periodic geometry; no terrain, moisture, latent heating budget,
vertical energy solution, open boundaries or spherical metric is supplied.
Rows point south: v_south has the opposite sign to the climate model's map-up v.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix,eye,bmat
from scipy.sparse.linalg import spsolve


@dataclass
class BaroclinicMode:
    u_east: np.ndarray
    v_south: np.ndarray
    geopotential: np.ndarray
    certificate: dict


def solve_mode(heating,cell_m,coriolis,*,wave_speed_ms,momentum_drag_s,thermal_drag_s):
    """Solve r*u+F*v+grad_x(phi)=0; r*v-F.T*u+grad_s(phi)=0;
    c² div(U)+rT*phi=Q, where Q has units m²/s³ and phi m²/s².

    Q is thermal-mode forcing, NOT external dry-air mass injection. A later
    two-layer embedding must conserve total dry mass and diagnose actual donor
    exchange from wind divergence. Positive drags make the symmetric matrix
    part strictly positive. Skew Coriolis and adjoint grad/div give the exact
    discrete modal energy identity: r|U|²+rT*(phi/c)² = phi*Q/c² on average.
    Faces use one value per periodic cell: u on its east face, v on south face.
    """
    q=np.asarray(heating,float);c=float(wave_speed_ms);r=float(momentum_drag_s);rt=float(thermal_drag_s)
    if (q.ndim!=2 or min(q.shape)<3 or not np.isfinite(q).all() or not np.isfinite(cell_m) or cell_m<=0
            or not np.isfinite([c,r,rt]).all() or min(c,r,rt)<=0):
        raise ValueError('Need finite2D heating, positive spacing, wave speed and both damping rates')
    f=np.broadcast_to(np.asarray(coriolis,float),q.shape)
    if not np.isfinite(f).all():raise ValueError('Need finite matching Coriolis field')
    ny,nx=q.shape;n=q.size;ids=np.arange(n).reshape(q.shape);row=ids.ravel()
    def gradient(neighbor):
        return coo_matrix((np.r_[-np.ones(n),np.ones(n)]/cell_m,
            (np.r_[row,row],np.r_[row,neighbor.ravel()])),shape=(n,n)).tocsr()
    gx=gradient(np.roll(ids,-1,axis=1));gy=gradient(np.roll(ids,-1,axis=0))
    fu=.5*(f+np.roll(f,-1,axis=1));fv=.5*(f+np.roll(f,-1,axis=0))
    columns=[];values=[]
    for di,dj in [(0,0),(-1,0),(0,1),(-1,1)]:
        columns.append(np.roll(np.roll(ids,-di,axis=0),-dj,axis=1).ravel())
        neighbor_f=np.roll(np.roll(fv,-di,axis=0),-dj,axis=1)
        values.append((.125*(fu+neighbor_f)).ravel())
    rotation=coo_matrix((np.concatenate(values),(np.tile(row,4),np.concatenate(columns))),shape=(n,n)).tocsr()
    # Unknown is(u,v,phi/c); equal velocity units avoid arbitrary row rescaling.
    identity=eye(n,format='csr')
    operator=bmat([[r*identity,rotation,c*gx],[-rotation.T,r*identity,c*gy],
                   [-c*gx.T,-c*gy.T,rt*identity]],format='csc')
    rhs=np.r_[np.zeros(2*n),q.ravel()/c];solution=spsolve(operator,rhs)
    if not np.isfinite(solution).all():raise FloatingPointError('Nonfinite baroclinic mode')
    residual=operator@solution-rhs
    scaled=float(np.abs(residual).max()/min(r,rt))
    speed_scale=max(1.,float(np.abs(solution).max()))
    if scaled>1e-8*speed_scale:raise RuntimeError('Baroclinic momentum/thermal equations failed')
    u,v,height=solution.reshape(3,ny,nx);phi=c*height
    input_rate=float(np.mean(phi*q/c**2));dissipation=float(np.mean(r*(u*u+v*v)+rt*height*height))
    energy_error=abs(input_rate-dissipation)/max(abs(input_rate),abs(dissipation),1e-30)
    if energy_error>1e-9:raise RuntimeError('Discrete modal energy identity failed')
    div=(-gx.T@u.ravel()-gy.T@v.ravel()).reshape(q.shape)
    cert=dict(maximum_equation_residual_velocity_ms=scaled,modal_energy_input_m2_s3=input_rate,
        modal_energy_dissipation_m2_s3=dissipation,relative_modal_energy_error=energy_error,
        thermal_balance_residual_m2_s3=float(np.abs(c*c*div+rt*phi-q).max()),
        mean_divergence_per_s=float(div.mean()),mean_geopotential_m2_s2=float(phi.mean()),
        maximum_speed_ms=float(np.hypot(u,v).max()),wave_speed_ms=c,momentum_drag_s=r,thermal_drag_s=rt,
        scope='Isolated periodic flat-grid dry thermal mode; no coupled climate or forcing/energy closure')
    return BaroclinicMode(u,v,phi,cert)
