"""Separate ageostrophic dry return from rotational thermal shear.

Kinematic closure only: lower convergence is retained, not derived from a new
energy/momentum equation. No humidity ratio, region fit or observed forcing.
"""
import numpy as np
from .thermal_layer_winds import ThermalLayerWinds


def divergent_thermal_branches(projector,lower,shear):
    shape=projector.shape
    if len(lower)!=2 or len(shear)!=2:raise ValueError('Need two-component lower wind and shear')
    if any(np.shape(a)!=shape or not np.isfinite(a).all() for a in (*lower,*shear)):
        raise ValueError('Need finite matching wind fields')
    # P is the exact existing dry-mass projection. P(S) adds rotational
    # thermal flow without prescribing the divergent part of the return.
    su,sv,thermal_projection=projector.project(*shear)
    mean_u,mean_v,mean_projection=projector.project(*lower)
    upper=((mean_u-.25*lower[0])/.75+su,(mean_v-.25*lower[1])/.75+sv)
    target_shear=((mean_u-lower[0])/.75+su,(mean_v-lower[1])/.75+sv)
    decomposition_error=max(float(np.abs(upper[i]-lower[i]-target_shear[i]).max()) for i in range(2))
    actual_mean=(.25*lower[0]+.75*upper[0],.25*lower[1]+.75*upper[1])
    residual=projector.divergence@np.r_[actual_mean[0].ravel(),actual_mean[1].ravel()]
    thermal_div=projector.divergence@np.r_[su.ravel(),sv.ravel()]
    scale=max(1.,float(np.hypot(*lower).max()),float(np.hypot(*upper).max()))
    scaled=float(np.abs(residual).max())/scale
    if scaled>1e-10 or np.abs(thermal_div).max()/scale>1e-10:
        raise RuntimeError('Separated divergent/rotational branches violate dry continuity')
    cert=dict(projection=mean_projection,thermal_projection=thermal_projection,
        max_scaled_dry_column_residual=scaled,maximum_shear_error_ms=decomposition_error,
        shear_constraint='mass-divergent historical return plus mass-balanced thermal rotation',
        maximum_total_thermal_shear_departure_ms=float(np.hypot(upper[0]-lower[0]-shear[0],upper[1]-lower[1]-shear[1]).max()),
        maximum_common_correction_ms=0.,lower_dry_mass_fraction=.25,pressure_centroid_ratio=7/3,
        lower_wind_exact=True,divergent_return_retained=True,
        maximum_thermal_projection_change_ms=float(np.hypot(su-shear[0],sv-shear[1]).max()),
        scope='Original lower convergence and dry return retained; only mass-balanced thermal rotation added above; no new energy/momentum solution')
    return ThermalLayerWinds(tuple(np.array(a,copy=True) for a in lower),upper,cert)
