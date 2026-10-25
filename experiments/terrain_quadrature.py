"""Exact area quadrature of slopes on a common, finite-resolution DEM.

Only elevation is read from WorldClim. Climate observations do not determine
these samples. The existing regional model uses the same projected metric.
"""
from functools import lru_cache
import numpy as np
from rotclimate import earth
from rotclimate.orography import validate_terrain_samples


def overlap_weights(fine, coarse, fine_step, coarse_step):
    fine=np.asarray(fine,float);coarse=np.asarray(coarse,float)
    if (fine.ndim!=1 or coarse.ndim!=1 or not len(fine) or not len(coarse) or
            not np.isfinite(fine).all() or not np.isfinite(coarse).all() or
            not np.isfinite(fine_step) or fine_step<=0 or not np.isfinite(coarse_step) or coarse_step<=0):
        raise ValueError('Need finite cell centers and positive widths')
    overlap=np.maximum(0.,np.minimum(coarse[:,None]+coarse_step/2,fine[None,:]+fine_step/2)-
                       np.maximum(coarse[:,None]-coarse_step/2,fine[None,:]-fine_step/2))/coarse_step
    if not np.allclose(overlap.sum(1),1.,rtol=0,atol=1e-10):
        raise ValueError('Fine terrain must completely cover each climate cell')
    # Remove roundoff at exactly touching edges, then preserve exact row sums.
    overlap[overlap<1e-13]=0.
    overlap/=overlap.sum(1)[:,None]
    return overlap


def from_terrain(height, fine_x, fine_y, coarse_x, coarse_y, fine_step_km, coarse_step_km):
    height=np.asarray(height,float);fine_x=np.asarray(fine_x,float);fine_y=np.asarray(fine_y,float)
    if (height.shape!=(len(fine_y),len(fine_x)) or min(height.shape)<3 or not np.isfinite(height).all() or
            not np.allclose(np.diff(fine_x),fine_step_km) or not np.allclose(np.diff(fine_y),-fine_step_km)):
        raise ValueError('Need finite north-up terrain on the declared regular fine grid')
    wx=overlap_weights(fine_x,coarse_x,fine_step_km,coarse_step_km)
    wy=overlap_weights(fine_y,coarse_y,fine_step_km,coarse_step_km)
    def sparse(weights):
        count=int((weights>0).sum(1).max());indices=np.zeros((count,len(weights)),int)
        values=np.zeros_like(indices,dtype=float)
        for i,row in enumerate(weights):
            used=np.flatnonzero(row>0);indices[:len(used),i]=used;values[:len(used),i]=row[used]
        return indices,values
    ix,vx=sparse(wx);iy,vy=sparse(wy)
    dy,dx=np.gradient(height,fine_step_km*1000.,edge_order=2)
    extract=lambda a:a[iy[:,None,:,None],ix[None,:,None,:]].reshape(-1,len(coarse_y),len(coarse_x))
    weights=(vy[:,None,:,None]*vx[None,:,None,:]).reshape(-1,len(coarse_y),len(coarse_x))
    return validate_terrain_samples(np.stack([extract(dx),extract(-dy),weights]),weights.shape[1:])


@lru_cache(maxsize=1)
def raw_elevation():
    return earth._wc('elev')


@lru_cache(maxsize=8)
def reference_terrain(name, spacing_km=14., pad_km=1212.):
    """WorldClim pixel-area means in one fixed projected reference frame."""
    spec=earth.REGIONS[name];lat0,lon0=spec['lat0'],spec['lon0']
    hw,hh=spec['width_km']/2+pad_km,spec['height_km']/2+pad_km
    nx,ny=int(np.ceil(2*hw/spacing_km)),int(np.ceil(2*hh/spacing_km))
    elev=raw_elevation();h,w=elev.shape
    plat=90-(np.arange(h)+.5)/12;plon=-180+(np.arange(w)+.5)/12
    span=np.degrees(np.hypot(hw,hh)/earth.R_EARTH_KM)+1
    rows=np.flatnonzero(np.abs(plat-lat0)<=span)
    dlon=span/max(np.cos(np.radians(min(abs(lat0)+span,89))),.05)
    cols=np.flatnonzero(np.abs(((plon-lon0+180)%360)-180)<=dlon)
    lat,lon=np.meshgrid(plat[rows],plon[cols],indexing='ij')
    x,y=earth.forward(lat,lon,lat0,lon0)
    i=np.floor((hh-y)/spacing_km).astype(int);j=np.floor((x+hw)/spacing_km).astype(int)
    values=elev[rows[:,None],cols[None,:]]
    inside=(i>=0)&(i<ny)&(j>=0)&(j<nx);land=inside&np.isfinite(values)
    flat=i*nx+j;area=np.cos(np.radians(lat));size=ny*nx
    all_area=np.bincount(flat[inside],weights=area[inside],minlength=size)
    land_area=np.bincount(flat[land],weights=area[land],minlength=size)
    if (all_area<=0).any():raise ValueError('Fine reference contains unsampled cells')
    total=np.bincount(flat[land],weights=(area*values)[land],minlength=size)
    mean=np.divide(total,land_area,out=np.zeros(size),where=land_area>0)
    height=np.where(land_area/all_area>=.5,np.maximum(mean,1.),0.).reshape(ny,nx)
    xs=-hw+(np.arange(nx)+.5)*spacing_km;ys=hh-(np.arange(ny)+.5)*spacing_km
    if lat0<0:height=height[::-1];ys=-ys[::-1]
    return height,xs,ys


def prepare_case(case, reference_km=14., pad_km=1100.):
    """Attach the same independent fine terrain input to either model scheme."""
    g=case.grid;spec=earth.REGIONS[case.name];step=g.cell_km
    hw,hh=spec['width_km']/2+pad_km,spec['height_km']/2+pad_km
    xs=-hw+(np.arange(g.nx)+.5)*step;ys=hh-(np.arange(g.ny)+.5)*step
    if spec['lat0']<0:ys=-ys[::-1]
    # This padding is fixed across 56/28 km, not recomputed from climate resolution.
    terrain,tx,ty=reference_terrain(case.name,reference_km,pad_km+112.)
    g.terrain_slopes=from_terrain(terrain,tx,ty,xs,ys,reference_km,step)
    return case
