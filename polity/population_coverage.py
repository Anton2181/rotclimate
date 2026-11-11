"""Keep missing Earth population input distinct from an ecological zero."""
import numpy as np


def population_coverage(lat,lon,source_lat,source_lon):
    lat,lon=np.broadcast_arrays(np.asarray(lat,float),np.asarray(lon,float))
    a,b=np.asarray(source_lat,float),np.asarray(source_lon,float)
    if a.ndim!=1 or b.ndim!=1 or len(a)<2 or len(b)<2:
        raise ValueError('Source axes need at least two cells')
    step=a[0]-a[1]
    if step<=0 or not np.isfinite(a).all() or not np.isfinite(b).all() or not np.allclose(np.diff(a),-step) or not np.allclose(np.diff(b),step):
        raise ValueError('Expected regular descending latitude/ascending longitude axes')
    r=(a[0]-lat)/step;c=(lon-b[0])/step
    return np.isfinite(lat)&np.isfinite(lon)&(r>=-.5)&(r<=len(a)-.5)&(c>=-.5)&(c<=len(b)-.5)


def require_population_coverage(covered,required):
    covered,required=np.asarray(covered,bool),np.asarray(required,bool)
    if covered.shape!=required.shape:raise ValueError('Coverage and required mask must match')
    missing=int((required&~covered).sum())
    if missing:raise ValueError(f'Missing population input in {missing} required cells; unknown is not zero')
