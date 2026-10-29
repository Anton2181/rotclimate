"""Closed-domain terrain mass projection and hydrostatic compression diagnostic.

Interior ports are common-pressure level intersections. The pressure-coordinate
lower boundary is a staircase with blocked underground ports, not a smooth
terrain metric. No time integration or open regional boundary is implemented.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from numpy.polynomial.legendre import leggauss
from .column_thermodynamics import G,RD
from .terrain_apertures import horizontal_apertures,mass_flux_divergence


def _fields(grid,u,v,dx):
    a=horizontal_apertures(grid);u=np.asarray(u,float);v=np.asarray(v,float)
    if u.shape!=a.east_kg_m2.shape or v.shape!=a.south_kg_m2.shape or not np.isfinite(u).all() or not np.isfinite(v).all() or not np.isfinite(dx) or dx<=0:raise ValueError('Need finite native face velocities and positive spacing')
    return a,u,v


def project_column_mass(grid,east_speed_ms,south_speed_ms,cell_m):
    """Minimum-kinetic change to close each fixed column's dry mass.

    Exterior faces are closed. Signed kinetic change is reported separately;
    projection is an initialization diagnostic and does not secretly heat gas.
    """
    a,u,v=_fields(grid,east_speed_ms,south_speed_ms,cell_m);_,ny,nx=grid.dry_mass_kg_m2.shape
    ex=np.nonzero(a.east_kg_m2);sy=np.nonzero(a.south_kg_m2);mx=a.east_kg_m2[ex];my=a.south_kg_m2[sy];mu=np.r_[mx,my];speed=np.r_[u[ex],v[sy]];root=np.sqrt(mu)
    left=np.r_[ex[2]*nx+ex[3],sy[2]*nx+sy[3]];right=np.r_[ex[2]*nx+ex[3]+1,(sy[2]+1)*nx+sy[3]];ports=np.arange(len(mu))
    b=coo_matrix((np.r_[root,-root]/cell_m,(np.r_[left,right],np.r_[ports,ports])),shape=(ny*nx,len(mu))).tocsc();reduced=b[:-1];raw=root*speed
    lagrange=spsolve(reduced@reduced.T,reduced@raw);corrected=raw-reduced.T@lagrange;velocity=corrected/root
    ue=np.zeros_like(u);vs=np.zeros_like(v);ue[ex]=velocity[:len(mx)];vs[sy]=velocity[len(mx):];div=mass_flux_divergence(a,ue,vs,cell_m).sum(0)
    return ue,vs,dict(maximum_actual_column_mass_divergence_kg_m2_s=float(abs(div).max()),kinetic_energy_change_j_m2=float(.5*(corrected@corrected-raw@raw)),original_kinetic_energy_j_m2=float(.5*(raw@raw)),projection_heat_added_j_m2=0.,scope='Closed-domain minimum-kinetic initial projection, not a momentum time step or hidden heat correction.')


@dataclass(frozen=True)
class TerrainCompression:
    layer_power_w_m2: np.ndarray
    interface_omega_pa_s: np.ndarray
    maximum_lower_boundary_omega_pa_s: float


def compression_power(grid,east_speed_ms,south_speed_ms,cell_m,temperature_anomaly_k,*,reference_temperature_k=288.15,reference_pressure_pa=101325.,reference_lapse_k_m=.0065):
    """Integrate Rd*T*omega/p dp/g on exact local pressure subintervals.

    omega(p) comes from continuity of the actual horizontal pressure-port fluxes,
    including neighbors' cross-level interfaces. Eight-point Gauss quadrature
    integrates the declared dry-reference-plus-piecewise-anomaly profile.
    Fixed column masses require closed lower/upper omega boundaries. Gas/kinetic
    pressure-work cancellation must still be checked by the caller; no energy
    residual is fed back into these independently computed physical powers.
    """
    a,u,v=_fields(grid,east_speed_ms,south_speed_ms,cell_m);p=grid.edges_pa;delta=np.asarray(temperature_anomaly_k,float);nz,ny,nx=grid.dry_mass_kg_m2.shape
    if delta.shape!=grid.dry_mass_kg_m2.shape or not np.isfinite(delta).all() or np.ndim(reference_temperature_k) or np.ndim(reference_pressure_pa) or not np.isfinite([reference_temperature_k,reference_pressure_pa,reference_lapse_k_m]).all() or reference_pressure_pa<=0 or not 0<=reference_lapse_k_m<=.012:raise ValueError('Need matching anomalies and a common supported dry reference')
    per_column=[[] for _ in range(ny*nx)]
    for kind,mu,velocity in [('east',a.east_kg_m2,u),('south',a.south_kg_m2,v)]:
        for kl,kr,j,i in zip(*np.nonzero(mu)):
            jr,ir=(j,i+1) if kind=='east' else (j+1,i);bottom=min(p[kl,j,i],p[kr,jr,ir]);top=max(p[kl+1,j,i],p[kr+1,jr,ir]);rate=velocity[kl,kr,j,i]/(G*cell_m)
            per_column[j*nx+i].append((top,bottom,rate));per_column[jr*nx+ir].append((top,bottom,-rate))
    nodes,weights=leggauss(8);power=np.zeros_like(delta);omega=np.zeros_like(p);alpha=RD*reference_lapse_k_m/G
    for j in range(ny):
        for i in range(nx):
            entries=np.asarray(per_column[j*nx+i]);top,bottom,rate=entries.T
            def w(pressure):return -G*(np.clip(np.asarray(pressure)[...,None]-top,0,bottom-top)*rate).sum(-1)
            omega[:,j,i]=w(p[:,j,i]);breaks=np.unique(np.r_[p[:,j,i],top,bottom]);mid=.5*(breaks[:-1]+breaks[1:]);half=.5*np.diff(breaks);points=mid[:,None]+half[:,None]*nodes
            level=np.searchsorted(-p[:,j,i],-mid)-1;temperature=reference_temperature_k*(points/reference_pressure_pa)**alpha+delta[level,j,i,None]
            if np.any((temperature<180)|(temperature>330)):raise ValueError('Unsupported dry reference/anomaly temperature')
            integral=(RD*temperature/points*w(points)*weights).sum(1)*half/G
            np.add.at(power[:,j,i],level,integral)
    boundary=float(abs(omega[0]).max());scale=max(float(abs(omega).max()),1e-8)
    if boundary>1e-9*scale+1e-12:raise ValueError('Horizontal ports do not close fixed column mass at the ground')
    return TerrainCompression(power,omega,boundary)
