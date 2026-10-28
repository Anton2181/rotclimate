"""Energy-paired anelastic hydrostatic vertical state, rigid top/bottom lids.

Reduced pressure and horizontal velocity live at cell centers, buoyancy and
vertical mass flux at interior interfaces. Positive reference density and N²
define the discrete energy inner products. This is a linear anelastic column,
not a compressible moist prognostic atmosphere or terrain-following grid.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import eigh_tridiagonal

from .column_thermodynamics import CP,G,RD,EPSILON


@dataclass
class ReferenceColumn:
    height_m: np.ndarray
    temperature_k: np.ndarray
    pressure_pa: np.ndarray
    density_kg_m3: np.ndarray
    potential_temperature_k: np.ndarray


def stable_reference(height_m,*,surface_potential_temperature_k=300.,
                     surface_pressure_pa=101325.,buoyancy_frequency_s=.01,
                     reference_pressure_pa=100000.):
    """Dry hydrostatic ideal gas, theta=theta_surface exp(N²*z/g).

Exner(p) integrates dPi/dz=-g/(cp theta) analytically. N is prescribed and
stable; no temperature floor or stability clipping changes the reference.
"""
    z=np.asarray(height_m,float)
    theta0,ps,n,pref=map(float,[surface_potential_temperature_k,surface_pressure_pa,buoyancy_frequency_s,reference_pressure_pa])
    if (not np.isfinite(z).all() or np.any(z<0) or not np.isfinite([theta0,ps,n,pref]).all()
            or not 180<=theta0<=330 or not 40000<=ps<=110000 or n<=0 or pref<=0
            or not np.isfinite(n*n) or n*n==0):
        raise ValueError('Need nonnegative finite height and terrestrial positive stable reference scales')
    exponent=n*n*z/G
    theta=theta0*np.exp(exponent)
    pi=(ps/pref)**(RD/CP)+G*G/(CP*theta0*n*n)*np.expm1(-exponent)
    if not np.isfinite(theta).all() or np.any(pi<=0):
        raise ValueError('Reference height exceeds positive hydrostatic Exner domain')
    temperature=theta*pi;pressure=pref*pi**(CP/RD);density=pressure/(RD*temperature)
    return ReferenceColumn(z.copy(),temperature,pressure,density,theta)


def virtual_potential_buoyancy(temperature_k,pressure_pa,vapor_dry_mixing_ratio,
                               reference_potential_temperature_k,*,reference_pressure_pa=100000.):
    """Dry-exponent virtual-potential-temperature buoyancy g*(theta_v/theta0-1).

Mixing ratio is vapor/dry air. Exact ideal-gas virtual-temperature factor is
(1+r/epsilon)/(1+r). The potential-temperature exponent is dry Rd/cp; no moist
entropy approximation is silently substituted into the phase energy ledger.
"""
    t,p,r,theta0=np.broadcast_arrays(*map(lambda a:np.asarray(a,float),
        [temperature_k,pressure_pa,vapor_dry_mixing_ratio,reference_potential_temperature_k]))
    if (not all(np.isfinite(a).all() for a in [t,p,r,theta0]) or np.any(t<=0)
            or np.any(p<=0) or np.any(r<0) or np.any(theta0<=0)
            or not np.isfinite(reference_pressure_pa) or reference_pressure_pa<=0):
        raise ValueError('Need finite positive thermodynamic scales and nonnegative dry vapor ratio')
    tv=t*(1+r/EPSILON)/(1+r)
    theta_v=tv*(reference_pressure_pa/p)**(RD/CP)
    return G*(theta_v/theta0-1)


@dataclass
class VerticalState:
    edges_m: np.ndarray
    centers_m: np.ndarray
    cell_mass_kg_m2: np.ndarray
    interface_density_kg_m3: np.ndarray
    interface_stability_s2: np.ndarray
    interface_energy_weight: np.ndarray  # rho*distance/N²
    pressure_modes: np.ndarray  # level, mode; mean(M*F²)=1, mean(M*F)=0
    buoyancy_modes: np.ndarray  # dF/dz on interior interfaces
    phase_speeds_ms: np.ndarray
    certificate: dict

    @property
    def total_mass(self):return float(self.cell_mass_kg_m2.sum())

    def _levels(self,value,count,name):
        value=np.asarray(value,float)
        if value.ndim<1 or value.shape[0]!=count or not np.isfinite(value).all():
            raise ValueError('Need matching finite vertical '+name)
        return value

    def pressure_from_buoyancy(self,buoyancy):
        b=self._levels(buoyancy,len(self.centers_m)-1,'interface buoyancy')
        d=np.diff(self.centers_m).reshape((-1,)+(1,)*(b.ndim-1))
        increments=b*d
        pressure=np.concatenate([np.zeros_like(b[:1]),np.cumsum(increments,axis=0)],axis=0)
        weights=self.cell_mass_kg_m2.reshape((-1,)+(1,)*(b.ndim-1))
        pressure-=np.sum(weights*pressure,axis=0,keepdims=True)/self.total_mass
        return pressure

    def buoyancy_from_pressure(self,pressure):
        p=self._levels(pressure,len(self.centers_m),'cell pressure')
        d=np.diff(self.centers_m).reshape((-1,)+(1,)*(p.ndim-1))
        return np.diff(p,axis=0)/d

    def vertical_velocity(self,layer_horizontal_divergence):
        div=self._levels(layer_horizontal_divergence,len(self.centers_m),'layer horizontal divergence')
        weights=self.cell_mass_kg_m2.reshape((-1,)+(1,)*(div.ndim-1))
        flux=np.cumsum(weights*div,axis=0)
        scale=np.sum(np.abs(weights*div),axis=0)
        if np.any(np.abs(flux[-1])>1e-11*np.maximum(scale,1e-30)):
            raise ValueError('Horizontal flow violates the rigid-lid column mass constraint')
        rho=self.interface_density_kg_m3.reshape((-1,)+(1,)*(div.ndim-1))
        return -flux[:-1]/rho

    def project_pressure(self,pressure):
        p=self._levels(pressure,len(self.centers_m),'cell pressure')
        weights=self.cell_mass_kg_m2.reshape((-1,)+(1,)*(p.ndim-1))
        return np.einsum('km,k...->m...',self.pressure_modes,weights*p)/self.total_mass

    def pressure_from_amplitudes(self,amplitudes):
        a=self._levels(amplitudes,len(self.phase_speeds_ms),'mode amplitudes')
        return np.einsum('km,m...->k...',self.pressure_modes,a)

    def project_buoyancy_source(self,buoyancy_source):
        q=self._levels(buoyancy_source,len(self.centers_m)-1,'buoyancy source')
        weight=self.interface_energy_weight.reshape((-1,)+(1,)*(q.ndim-1))
        projected=np.einsum('km,k...->m...',self.buoyancy_modes,weight*q)/self.total_mass
        c2=self.phase_speeds_ms.reshape((-1,)+(1,)*(q.ndim-1))**2
        return c2*projected


def build_vertical_state(edges_m,cell_density_kg_m3,interface_stability_s2):
    """Solve -d/dz[rho/N² dF/dz]=rho F/c² with zero end gradients.

Discrete hydrostatic derivative, vertical continuity and available-energy
weights are paired before computing modes. The zero barotropic eigenvalue is
excluded; all n-1 internal modes are retained. No near-neutral/unstable N² is
clipped into a convenient positive value.
"""
    edges=np.asarray(edges_m,float);rho=np.asarray(cell_density_kg_m3,float)
    n2=np.asarray(interface_stability_s2,float)
    if (edges.ndim!=1 or len(edges)<3 or not np.isfinite(edges).all() or np.any(np.diff(edges)<=0)
            or rho.shape!=(len(edges)-1,) or n2.shape!=(len(edges)-2,)
            or not np.isfinite(rho).all() or np.any(rho<=0) or not np.isfinite(n2).all() or np.any(n2<=0)):
        raise ValueError('Need ascending cell edges, positive matching density and positive interface N²')
    centers=.5*(edges[:-1]+edges[1:]);dz=np.diff(edges);distance=np.diff(centers)
    mass=rho*dz
    # Linear density interpolation from the two cell centers to their shared edge.
    rho_face=(rho[:-1]*dz[1:]+rho[1:]*dz[:-1])/(dz[:-1]+dz[1:])
    energy_weight=rho_face*distance/n2
    conductance=energy_weight/distance**2
    diagonal=np.r_[conductance,0]+np.r_[0,conductance]
    diagonal/=mass
    off=-conductance/np.sqrt(mass[:-1]*mass[1:])
    eigenvalues,vectors=eigh_tridiagonal(diagonal,off,select='i',select_range=(1,len(mass)-1))
    if np.any(eigenvalues<=0):raise RuntimeError('Internal vertical modes must have positive eigenvalues')
    modes=vectors/np.sqrt(mass[:,None])*np.sqrt(mass.sum())
    modes*=np.where(modes[0]>0,-1.,1.)
    buoyancy=np.diff(modes,axis=0)/distance[:,None]
    speeds=1/np.sqrt(eigenvalues)
    gram=modes.T@(mass[:,None]*modes)/mass.sum()
    available=buoyancy.T@(energy_weight[:,None]*buoyancy)/mass.sum()
    orth_error=float(np.abs(gram-np.eye(len(speeds))).max())
    mean_error=float(np.abs(np.sum(mass[:,None]*modes,axis=0)/mass.sum()).max())
    ape_error=float(np.abs(available-np.diag(eigenvalues)).max()/max(eigenvalues))
    if max(orth_error,mean_error,ape_error)>1e-9:
        raise RuntimeError('Vertical eigenmode mass/energy identities failed')
    cert=dict(levels=len(mass),internal_modes=len(speeds),maximum_mass_orthogonality_error=orth_error,
        maximum_mass_mean_mode_error=mean_error,relative_modal_available_energy_error=ape_error,
        first_phase_speed_ms=float(speeds[0]),
        scope='Linear anelastic hydrostatic rigid-lid vertical column; positive supplied N²/density, no moist convection or compressible/terrain evolution')
    return VerticalState(edges,centers,mass,rho_face,n2,energy_weight,modes,buoyancy,speeds,cert)
