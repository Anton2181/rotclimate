"""Explicit zonal-background exterior for a finite thermal-anomaly pressure field."""
import numpy as np
from scipy.ndimage import gaussian_filter


def pressure_field(anomaly,large_sigma,local_sigma,large_coefficient,local_coefficient):
    """Diagnosed Pa, with anomaly ZERO outside the actual padded grid.

    The exterior assumption is the intervention. This is not normalization by
    available domain mass, an observed pressure field or a claim that the real
    off-domain atmosphere has zero anomaly. Every other coefficient is retained.
    """
    anomaly=np.asarray(anomaly,float)
    large=gaussian_filter(anomaly,large_sigma,mode='constant',cval=0.)
    local=gaussian_filter(anomaly,local_sigma,mode='constant',cval=0.)-large
    return -100.*(large_coefficient*large+local_coefficient*local)
