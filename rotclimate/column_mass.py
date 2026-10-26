"""Minimum-change stationary column mass constraint for a regional wind.

This is a kinematic, equivalent-barotropic diagnostic closure. Open-border
velocities may change. It does not solve momentum, vertical return, transient
storage, or the difference between dry-mass and humidity-weighted winds.
"""
import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import splu


class ColumnMassProjection:
    """Project cell velocities with the same arithmetic face average as vapor.

    Minimize sum M |delta U|² subject to div(M_face U_face)=0 in the
    interior. M=p0/g exp(-z/8km) is a fixed hydrostatic column approximation.
    D includes the open-border velocities; no hidden compatibility correction
    or fixed-throughflow assumption is needed. Border mass flux is diagnosed.
    """
    def __init__(self, elevation_m, cell_m):
        elevation_m = np.asarray(elevation_m, float)
        if (elevation_m.ndim != 2 or min(elevation_m.shape) < 3
                or not np.isfinite(elevation_m).all() or (elevation_m < 0).any()
                or not np.isfinite(cell_m) or cell_m <= 0):
            raise ValueError('Need finite nonnegative2-D terrain and positive cell spacing')
        self.shape = elevation_m.shape
        self.cell_m = cell_m
        self.mass0 = 101325/9.80665
        self.mass = np.exp(-elevation_m/8000.)
        if self.mass.min() < .01:
            raise ValueError('Column mass outside the supported terrestrial terrain range')
        ny, nx = self.shape
        count = ny*nx
        center = np.arange(count).reshape(self.shape)[1:-1, 1:-1].ravel()
        self.xmass = .5*(self.mass[:, 1:]+self.mass[:, :-1])
        self.ymass = .5*(self.mass[1:, :]+self.mass[:-1, :])
        west, east = self.xmass[1:-1, :-1].ravel(), self.xmass[1:-1, 1:].ravel()
        north, south = self.ymass[:-1, 1:-1].ravel(), self.ymass[1:, 1:-1].ravel()
        rows = np.tile(np.arange(len(center)), 6)
        columns = np.concatenate([center-1, center, center+1, count+center-nx, count+center, count+center+nx])
        values = .5*np.concatenate([-west, east-west, east, north, north-south, -south])
        self.divergence = coo_matrix((values, (rows, columns)), shape=(len(center), 2*count)).tocsr()
        self.inverse_metric = np.tile(1/self.mass.ravel(), 2)
        self.gradient = diags(self.inverse_metric)@self.divergence.T
        self.factor = splu((self.divergence@self.gradient).tocsc())

    def project(self, u, v):
        u, v = np.asarray(u, float), np.asarray(v, float)
        if u.shape != self.shape or v.shape != self.shape or not np.isfinite(u).all() or not np.isfinite(v).all():
            raise ValueError('Need finite matched column velocity fields')
        original = np.concatenate([u.ravel(), v.ravel()])
        rhs = self.divergence@original
        correction = self.gradient@self.factor.solve(rhs)
        projected = original-correction
        residual = self.divergence@projected
        scale = max(float(np.max(np.abs(original)))*float(self.mass.max()), 1.)
        relative = float(np.max(np.abs(residual)))/scale
        if not np.isfinite(projected).all() or relative > 1e-10:
            raise RuntimeError('Column mass constraint failed: '+str(relative))
        count = u.size
        east, north = projected[:count].reshape(self.shape), projected[count:].reshape(self.shape)
        # Exactly the faces enclosing the solved interior, not outside borders.
        fx = self.xmass*.5*(east[:, 1:]+east[:, :-1])
        fy = self.ymass*.5*(north[1:, :]+north[:-1, :])
        net = (fx[1:-1, -1].sum()-fx[1:-1, 0].sum()+fy[0, 1:-1].sum()-fy[-1, 1:-1].sum())
        info = dict(max_scaled_mass_divergence=relative,
            max_mass_divergence_kgm2s=float(np.max(np.abs(residual)))*self.mass0/self.cell_m,
            original_max_mass_divergence_kgm2s=float(np.max(np.abs(rhs)))*self.mass0/self.cell_m,
            boundary_net_dry_air_kg_s=float(net)*self.mass0*self.cell_m,
            velocity_correction_rms_ms=float(np.sqrt(np.mean(correction[:count]**2+correction[count:]**2))),
            velocity_correction_max_ms=float(np.hypot(correction[:count], correction[count:]).max()))
        return east, north, info
