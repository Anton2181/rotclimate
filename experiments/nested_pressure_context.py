"""A finite native parent supplies ONLY the exterior thermal-pressure context.

The child replaces the parent's anomaly in its ENTIRE padded rectangle on
every pressure coupling call. Outer parent continuation and planar projection
remain approximations. This is one-way nesting, not a global atmosphere.
"""
import numpy as np


def insert_child(parent_anomaly, child_anomaly, offset):
    parent=np.asarray(parent_anomaly,float)
    child=np.asarray(child_anomaly,float)
    if (parent.ndim!=2 or child.ndim!=2 or not isinstance(offset,int) or offset<0
            or parent.shape!=(child.shape[0]+2*offset,child.shape[1]+2*offset)
            or not np.isfinite(parent).all() or not np.isfinite(child).all()):
        raise ValueError('Need finite, equally resolved centered nested arrays and integral offset')
    combined=parent.copy()
    crop=(slice(offset,offset+child.shape[0]),slice(offset,offset+child.shape[1]))
    combined[crop]=child
    return combined,crop


def nested_pressure(parent_anomaly,child_anomaly,offset,broad_sigma,local_sigma,
                    broad_hpa_K,local_hpa_K,gaussian):
    """Original pressure algebra/filter with actual finite parent exterior.

    gaussian is the original model.gauss, including its original nearest
    continuation at the OUTER parent boundary. No observed T or fit is supplied.
    """
    if not np.isfinite([broad_sigma,local_sigma,broad_hpa_K,local_hpa_K]).all() or min(broad_sigma,local_sigma)<=0:
        raise ValueError('Need finite coefficients and positive kernel scales')
    combined,crop=insert_child(parent_anomaly,child_anomaly,offset)
    broad=gaussian(combined,broad_sigma)
    local=gaussian(combined,local_sigma)-broad
    return (-100.*(broad_hpa_K*broad+local_hpa_K*local))[crop]
