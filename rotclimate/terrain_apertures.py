"""Common-pressure openings between neighboring terrain-following columns.

Cross-level overlaps avoid treating air below the neighboring ground as an
open horizontal port. These are geometry/flux-divergence primitives, not a
complete terrain-following momentum or thermodynamic solver.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import G
from .terrain_hydrostatics import TerrainPressureGrid


@dataclass(frozen=True)
class TerrainApertures:
    east_kg_m2: np.ndarray  # source level, east level, y, east face
    south_kg_m2: np.ndarray  # north level, south level, south face, x
    layer_mass_kg_m2: np.ndarray


def horizontal_apertures(grid):
    if not isinstance(grid,TerrainPressureGrid):raise TypeError('Need an explicit terrain pressure grid')
    p=np.asarray(grid.edges_pa,float)
    if p.ndim!=3 or min(p.shape[1:])<2 or not np.isfinite(p).all() or np.any(np.diff(p,axis=0)>=0):raise ValueError('Need positive pressure layers on a two-dimensional grid')
    def overlap(left,right):
        bottom=np.minimum(left[:-1,None],right[None,:-1]);top=np.maximum(left[1:,None],right[None,1:])
        return np.maximum(bottom-top,0.)/G
    east=overlap(p[:,:,:-1],p[:,:,1:]);south=overlap(p[:,:-1],p[:,1:])
    # The union of level-pair intersections is exactly the shared column.
    np.testing.assert_allclose(east.sum((0,1)),(np.minimum(p[0,:,:-1],p[0,:,1:])-np.maximum(p[-1,:,:-1],p[-1,:,1:]))/G,rtol=3e-14,atol=1e-10)
    np.testing.assert_allclose(south.sum((0,1)),(np.minimum(p[0,:-1],p[0,1:])-np.maximum(p[-1,:-1],p[-1,1:]))/G,rtol=3e-14,atol=1e-10)
    return TerrainApertures(east,south,grid.dry_mass_kg_m2.copy())


def mass_flux_divergence(apertures,east_speed_ms,south_speed_ms,cell_m):
    """Layer dry-mass divergence with pairwise canceling interior face fluxes.

    Velocities are explicit per open level pair. All exterior faces are closed.
    Positive divergence is outward; vertical exchange and a compatible pressure
    constraint are still needed before this can advance a fixed-mass atmosphere.
    """
    if not isinstance(apertures,TerrainApertures) or not np.isfinite(cell_m) or cell_m<=0:raise ValueError('Need terrain openings and positive grid spacing')
    u,v=np.asarray(east_speed_ms,float),np.asarray(south_speed_ms,float)
    if u.shape!=apertures.east_kg_m2.shape or v.shape!=apertures.south_kg_m2.shape or not np.isfinite(u).all() or not np.isfinite(v).all():raise ValueError('Need finite velocities on every explicit level-pair face')
    east=apertures.east_kg_m2*u/cell_m;south=apertures.south_kg_m2*v/cell_m;div=np.zeros_like(apertures.layer_mass_kg_m2)
    div[:,:,:-1]+=east.sum(1);div[:,:,1:]-=east.sum(0)
    div[:,:-1]+=south.sum(1);div[:,1:]-=south.sum(0)
    return div
