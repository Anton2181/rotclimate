"""Cell-centered dry buoyancy and its energy-adjoint hydrostatic column.

This Lorenz-grid alternative shares thermal cell locations with the moist
transport code. It has one pressure-invisible computational thermal mode,
which is exposed rather than filtered or called a physical solution. Linear
dry reference energy is not the nonlinear moist/static-energy budget.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import svd


@dataclass
class CellThermalColumn:
    edges_m: np.ndarray
    centers_m: np.ndarray
    cell_mass_kg_m2: np.ndarray
    cell_stability_s2: np.ndarray
    interface_density_kg_m3: np.ndarray
    thermal_energy_weight: np.ndarray
    interface_interpolation: np.ndarray
    hydrostatic_matrix: np.ndarray
    phase_speeds_ms: np.ndarray
    pressure_modes: np.ndarray
    cell_buoyancy_modes: np.ndarray
    pressure_invisible_thermal_mode: np.ndarray
    certificate: dict

    @property
    def total_mass(self):return float(self.cell_mass_kg_m2.sum())

    def _cells(self,value,name):
        a=np.asarray(value,float)
        if a.ndim<1 or a.shape[0]!=len(self.centers_m) or not np.isfinite(a).all():
            raise ValueError('Need matching finite cell '+name)
        return a

    def pressure_from_buoyancy(self,buoyancy):
        b=self._cells(buoyancy,'buoyancy')
        return np.einsum('ij,j...->i...',self.hydrostatic_matrix,b)

    def vertical_velocity(self,layer_horizontal_divergence):
        div=self._cells(layer_horizontal_divergence,'horizontal divergence')
        m=self.cell_mass_kg_m2.reshape((-1,)+(1,)*(div.ndim-1))
        flux=np.cumsum(m*div,axis=0);scale=np.sum(np.abs(m*div),axis=0)
        if np.any(np.abs(flux[-1])>1e-11*np.maximum(scale,1e-30)):
            raise ValueError('Horizontal flow violates closed-lid column mass')
        rho=self.interface_density_kg_m3.reshape((-1,)+(1,)*(div.ndim-1))
        return -flux[:-1]/rho

    def adiabatic_buoyancy_tendency(self,layer_horizontal_divergence):
        """Thermal tendency paired with actual hydrostatic pressure work.

        On a uniform grid this is -N² times the mean of adjacent interface
        vertical velocities, including exactly zero velocities at both lids.
        On nonuniform grids the density/distance weights follow from the
        pressure-work identity, rather than an independently chosen averaging.
        """
        w=self.vertical_velocity(layer_horizontal_divergence)
        weight=(self.interface_density_kg_m3*np.diff(self.centers_m)).reshape((-1,)+(1,)*(w.ndim-1))
        thermal_velocity=np.einsum('ij,i...->j...',self.interface_interpolation,weight*w)
        factor=(-self.cell_stability_s2/self.cell_mass_kg_m2).reshape((-1,)+(1,)*(w.ndim-1))
        return factor*thermal_velocity

    def project_pressure(self,pressure):
        p=self._cells(pressure,'pressure');m=self.cell_mass_kg_m2.reshape((-1,)+(1,)*(p.ndim-1))
        return np.einsum('km,k...->m...',self.pressure_modes,m*p)/self.total_mass

    def reconstruct_active_buoyancy(self,buoyancy):
        b=self._cells(buoyancy,'buoyancy')
        amplitudes=self.project_pressure(self.pressure_from_buoyancy(b))
        return np.einsum('km,m...->k...',self.cell_buoyancy_modes,amplitudes)

    def energy_partition(self,buoyancy):
        b=self._cells(buoyancy,'buoyancy');active=self.reconstruct_active_buoyancy(b);null=b-active
        weight=self.thermal_energy_weight.reshape((-1,)+(1,)*(b.ndim-1))
        columns=int(np.prod(b.shape[1:]))
        energy=lambda a:float(.5*np.sum(weight*a*a)/(self.total_mass*columns))
        full,physical,invisible=map(energy,[b,active,null])
        return dict(total_thermal_available_energy_m2_s2=full,
            pressure_active_available_energy_m2_s2=physical,
            pressure_invisible_available_energy_m2_s2=invisible,
            partition_residual_m2_s2=full-physical-invisible)


def build_cell_thermal_column(edges_m,cell_density_kg_m3,cell_stability_s2):
    edges=np.asarray(edges_m,float);rho=np.asarray(cell_density_kg_m3,float);n2=np.asarray(cell_stability_s2,float)
    if (edges.ndim!=1 or len(edges)<3 or not np.isfinite(edges).all() or np.any(np.diff(edges)<=0)
            or rho.shape!=(len(edges)-1,) or n2.shape!=rho.shape or not np.isfinite(rho).all()
            or not np.isfinite(n2).all() or np.any(rho<=0) or np.any(n2<=0)):
        raise ValueError('Need ascending edges and matching positive finite cell density/stability')
    dz=np.diff(edges);zc=.5*(edges[:-1]+edges[1:]);distance=np.diff(zc);m=rho*dz;n=len(m)
    interpolation=np.zeros((n-1,n));i=np.arange(n-1)
    interpolation[i,i]=dz[1:]/(dz[:-1]+dz[1:]);interpolation[i,i+1]=dz[:-1]/(dz[:-1]+dz[1:])
    integration=np.vstack([np.zeros((1,n-1)),np.tril(np.ones((n-1,n-1)))])*distance[None,:]
    h=integration@interpolation;h-=np.sum(m[:,None]*h,axis=0,keepdims=True)/m.sum()
    rhof=(rho[:-1]*dz[1:]+rho[1:]*dz[:-1])/(dz[:-1]+dz[1:]);e=m/n2
    # phi_t = -H E^-1 H.T M div. Singular values of sqrt(M) H /sqrt(E)
    # are c. Avoid forming its squared normal matrix: the short vertical
    # modes become poorly conditioned under refinement, contaminating H*b=F.
    a=np.sqrt(m)[:,None]*h/np.sqrt(e)[None,:]
    left,speeds,right=svd(a,full_matrices=False);speeds=speeds[:-1];c2=speeds**2
    if np.any(c2<=0):raise RuntimeError('Cell thermal internal mode speeds must be positive')
    f=left[:,:-1]/np.sqrt(m)[:,None]*np.sqrt(m.sum());sign=np.where(f[0]>0,-1.,1.);f*=sign
    b=right[:-1].T/np.sqrt(e)[:,None]*np.sqrt(m.sum())/speeds[None,:]*sign
    # The interpolation has a one-dimensional checkerboard-like nullspace.
    null=np.linalg.svd(interpolation,full_matrices=True)[2][-1]
    null*=np.sqrt(m.sum()/np.dot(e,null*null))
    identity_error=float(np.max(np.abs(h@b-f)))
    gram_error=float(np.max(np.abs(f.T@(m[:,None]*f)/m.sum()-np.eye(n-1))))
    thermal_error=float(np.max(np.abs(b.T@(e[:,None]*b)/m.sum()-np.diag(1/c2)))/max(1/c2))
    null_error=float(np.max(np.abs(h@null)))
    if max(identity_error,gram_error,thermal_error,null_error)>1e-9:
        raise RuntimeError('Cell thermal hydrostatic/energy/null identities failed')
    cert=dict(levels=n,pressure_active_internal_modes=n-1,pressure_invisible_thermal_modes=1,
        maximum_hydrostatic_mode_error=identity_error,maximum_mass_orthogonality_error=gram_error,
        relative_thermal_energy_mode_error=thermal_error,maximum_null_pressure_residual_m2_s2=null_error,
        first_phase_speed_ms=float(np.sqrt(c2[0])),
        scope='Linear dry fixed-reference Lorenz-grid hydrostatic column; pressure-invisible computational thermal mode exposed, no moist dynamics adoption')
    return CellThermalColumn(edges.copy(),zc,m,n2.copy(),rhof,e,interpolation,h,speeds,f,b,null,cert)
