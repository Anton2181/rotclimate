"""Energy-skew transport of reconstructed native terrain velocities.

Central finite-volume cell transport is mapped to mass-weighted native port
velocities with adjoint interpolation. This is a momentum operator diagnostic,
not yet selected by the qualified dry time integrator or rainfall forecasts.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix,bmat,csc_matrix
from .terrain_apertures import horizontal_apertures
from .terrain_transport import TerrainTransport


@dataclass(frozen=True)
class TerrainMomentumTransport:
    weighted_operator_s: object
    weighted_velocity: np.ndarray
    east_interpolation: object
    south_interpolation: object
    face_mass_kg_m2: np.ndarray
    east_indices: tuple
    south_indices: tuple
    east_count: int

    def acceleration(self):
        weighted=-self.weighted_operator_s@self.weighted_velocity;velocity=weighted/np.sqrt(self.face_mass_kg_m2)
        return velocity[:self.east_count],velocity[self.east_count:]


def projected_central_operator(native_transport,east_interpolation,south_interpolation):
    """Project the same native scalar fluxes onto reconstructed momentum."""
    central=.5*(native_transport.matrix-native_transport.matrix.T)
    cx,cy=east_interpolation,south_interpolation
    if cx.shape[0]!=native_transport.mass.size or cy.shape[0]!=native_transport.mass.size:raise ValueError('Interpolation and native transport cells differ')
    east=cx.T@central@cx;south=cy.T@central@cy;nu,nv=cx.shape[1],cy.shape[1]
    operator=bmat([[east,csc_matrix((nu,nv))],[csc_matrix((nv,nu)),south]],format='csc')
    return .5*(operator-operator.T)


def momentum_transport(grid,east_speed_ms,south_speed_ms,cell_m):
    a=horizontal_apertures(grid);u=np.asarray(east_speed_ms,float);v=np.asarray(south_speed_ms,float);transport=TerrainTransport(grid,u,v,cell_m,1.)
    ex=np.nonzero(a.east_kg_m2);sy=np.nonzero(a.south_kg_m2);mu=np.r_[a.east_kg_m2[ex],a.south_kg_m2[sy]];root=np.sqrt(mu);nu=len(ex[0]);ids=np.arange(grid.dry_mass_kg_m2.size).reshape(grid.dry_mass_kg_m2.shape);mass=grid.dry_mass_kg_m2.ravel()
    def interpolate(index,kind,offset):
        k,l,j,i=index;jr,ir=(j,i+1) if kind=='east' else (j+1,i);first=ids[k,j,i];second=ids[l,jr,ir];columns=np.arange(len(k));r=root[offset:offset+len(k)]
        return coo_matrix((np.r_[.5*r/mass[first],.5*r/mass[second]],(np.r_[first,second],np.r_[columns,columns])),shape=(len(mass),len(k))).tocsc()
    cx=interpolate(ex,'east',0);cy=interpolate(sy,'south',nu);operator=projected_central_operator(transport,cx,cy);x=root*np.r_[u[ex],v[sy]]
    return TerrainMomentumTransport(operator,x,cx,cy,mu,ex,sy,nu)
