"""Hydrostatic pressure-coordinate temperature and exact compression work.

Fixed descending pressure edges, dry reference masses dp/g, zero pressure
velocity at both lids. This is the dry/dilute coordinate: water loading and
vapor effects on gas volume are not silently included with fixed dry masses.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import G,RD


@dataclass
class PressureCoordinate:
    edges_pa: np.ndarray
    centers_pa: np.ndarray
    cell_mass_kg_m2: np.ndarray
    hydrostatic_matrix: np.ndarray
    interpolation: np.ndarray
    center_log_pressure_distance: np.ndarray

    def _cells(self,value,name):
        a=np.asarray(value,float)
        if a.ndim<1 or a.shape[0]!=len(self.centers_pa) or not np.isfinite(a).all():
            raise ValueError('Need matching finite pressure-cell '+name)
        return a

    def geopotential(self,temperature_k):
        t=self._cells(temperature_k,'temperature')
        if np.any(t<=0):raise ValueError('Need positive physical temperature')
        return np.einsum('ij,j...->i...',self.hydrostatic_matrix,t)

    def upward_mass_flux(self,horizontal_divergence_s):
        div=self._cells(horizontal_divergence_s,'divergence')
        mass=self.cell_mass_kg_m2.reshape((-1,)+(1,)*(div.ndim-1));flux=-np.cumsum(mass*div,axis=0)
        scale=np.sum(np.abs(mass*div),axis=0)
        if np.any(abs(flux[-1])>1e-10*scale+1e-13):raise ValueError('Pressure-lid dry mass continuity failed')
        return flux[:-1]

    def pressure_velocity(self,horizontal_divergence_s):
        return -G*self.upward_mass_flux(horizontal_divergence_s)

    def compression_power_w_m2(self,temperature_k,horizontal_divergence_s):
        """Discrete Rd*T*omega/p times pressure mass, paired with hydrostatics.

        Only this term supplies adiabatic compression to transported gas
        enthalpy. No fixed-height gz/MSE advection or second b_t cooling.
        """
        t=self._cells(temperature_k,'temperature');div=self._cells(horizontal_divergence_s,'divergence')
        if t.shape!=div.shape or np.any(t<=0):raise ValueError('Need positive matching temperature/divergence')
        flux=self.upward_mass_flux(div)
        scale=(RD*self.center_log_pressure_distance).reshape((-1,)+(1,)*(t.ndim-1))
        return -t*np.einsum('ij,i...->j...',self.interpolation,scale*flux)


def pressure_coordinate(pressure_edges_pa):
    p=np.asarray(pressure_edges_pa,float)
    if (p.ndim!=1 or len(p)<3 or not np.isfinite(p).all() or np.any(np.diff(p)>=0)
            or np.any((p<10000)|(p>110000))):raise ValueError('Need descending terrestrial pressure edges')
    centers=np.sqrt(p[:-1]*p[1:]);mass=-np.diff(p)/G;n=len(mass);distance=np.log(centers[:-1]/centers[1:])
    c=np.zeros((n-1,n));i=np.arange(n-1);c[i,i]=.5;c[i,i+1]=.5
    integrate=np.vstack([np.zeros((1,n-1)),np.tril(np.ones((n-1,n-1)))])*(RD*distance)[None,:]
    h=integrate@c;h-=np.sum(mass[:,None]*h,axis=0,keepdims=True)/mass.sum()
    return PressureCoordinate(p.copy(),centers,mass,h,c,distance)
