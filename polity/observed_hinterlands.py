"""Joint population accounting for supplied fractional diagnostic centre points.

This does not predict sites, urban residents or demographic growth.
"""
import numpy as np


def grid_points(latitude,longitude,grid):
    """Source coordinates to fractional native AEQD grid indices, not affine degrees."""
    from rotclimate.earth import forward
    x,y=np.asarray(grid['x'],float),np.asarray(grid['y'],float);cell=float(grid['cell_km'])
    if x.ndim!=2 or x.shape!=y.shape or min(x.shape)<2 or not np.isfinite(cell) or cell<=0:
        raise ValueError('Native rectangular x/y grid and positive cell size required')
    if not (np.allclose(x,x[0],atol=1e-9,rtol=0) and np.allclose(y,y[:,0,None],atol=1e-9,rtol=0) and np.allclose(np.diff(x[0]),cell,atol=1e-9,rtol=0) and np.allclose(np.diff(y[:,0]),-cell,atol=1e-9,rtol=0)):
        raise ValueError('Native grid must have constant eastward x and southward row spacing')
    xx,yy=forward(np.asarray(latitude,float),np.asarray(longitude,float),float(grid['lat0']),float(grid['lon0']))
    return np.column_stack([(y[0,0]-yy)/cell,(xx-x[0,0])/cell])


def hinterland_people(density,land,centres_rc,cell_km,max_km=60.):
    density=np.asarray(density,float);land=np.asarray(land,bool);centres=np.asarray(centres_rc,float).reshape(-1,2)
    if land.ndim!=2 or density.shape!=land.shape:raise ValueError('Matching two-dimensional density/land arrays required')
    if not np.isfinite(density[land]).all() or np.any(density[land]<0):raise ValueError('Finite nonnegative people density required')
    if not np.isfinite(centres).all():raise ValueError('Finite supplied coordinates required')
    if not np.isfinite(cell_km) or cell_km<=0 or not np.isfinite(max_km) or max_km<0:raise ValueError('Positive cell size and nonnegative finite radius required')
    total=np.zeros(len(centres))
    if not len(centres):return total
    yy,xx=np.nonzero(land);mass=density[yy,xx]*cell_km**2
    for start in range(0,len(yy),4096):
        pts=np.column_stack([yy[start:start+4096],xx[start:start+4096]])
        d2=np.sum((pts[:,None,:]-centres[None,:,:])**2,axis=2);nearest=d2.min(1)
        tie=d2==nearest[:,None];share=tie/tie.sum(1)[:,None]
        share[nearest*cell_km**2>max_km**2]=0
        total+=np.sum(mass[start:start+4096,None]*share,axis=0)
    return total
