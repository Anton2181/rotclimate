"""Small-grid reference operator for an explicitly supplied whole-planet field.

No climate integration, parent temperature prediction, momentum solution or
adoption is provided. Dense all-pairs quadrature is intentionally limited to
2048 cells; this is a known-answer reference for a future scalable operator.
"""
import numpy as np


def sphere_grid(nlat, nlon):
    """Global equal-angle cell centers and exact spherical cell area/R**2."""
    if not isinstance(nlat, int) or not isinstance(nlon, int) or nlat < 2 or nlon < 4:
        raise ValueError('Need at least2 latitude bands and4 longitude cells')
    if nlat*nlon > 2048:
        raise ValueError('Dense reference limited to2048 cells; not a production filter')
    edges = np.linspace(-np.pi/2, np.pi/2, nlat+1)
    latitude = np.rad2deg(.5*(edges[:-1]+edges[1:]))
    longitude = -180. + (np.arange(nlon)+.5)*360./nlon
    lat, lon = np.meshgrid(latitude, longitude, indexing='ij')
    area = np.broadcast_to((np.sin(edges[1:])-np.sin(edges[:-1]))[:,None]*2*np.pi/nlon, (nlat,nlon)).copy()
    return lat, lon, area


def spherical_gaussian(field, sigma_km, radius_km=6371.):
    """Area-normalized geodesic Gaussian quadrature over the ENTIRE sphere.

    The supplied field covers every cell. No nearest, zero-anomaly or unseen
    exterior continuation is inferred. sigma is a physical great-circle length.
    A finite grid only approximates the continuous spherical convolution.
    """
    field = np.asarray(field, float)
    if field.ndim != 2 or not np.isfinite(field).all():
        raise ValueError('Need a finite global two-dimensional field')
    if not np.isfinite(sigma_km) or sigma_km <= 0 or not np.isfinite(radius_km) or radius_km <= 0:
        raise ValueError('Need positive finite Gaussian scale and sphere radius in km')
    lat, lon, area = sphere_grid(*field.shape)
    phi, lam = np.deg2rad(lat.ravel()), np.deg2rad(lon.ravel())
    xyz = np.column_stack([np.cos(phi)*np.cos(lam), np.cos(phi)*np.sin(lam), np.sin(phi)])
    cosine = np.clip(xyz@xyz.T, -1., 1.)
    np.fill_diagonal(cosine, 1.)
    distance = radius_km*np.arccos(cosine)
    weight = np.exp(-.5*(distance/sigma_km)**2)*area.ravel()[None,:]
    weight /= weight.sum(axis=1, keepdims=True)
    return (weight@field.ravel()).reshape(field.shape)


def pressure_from_global_anomaly(anomaly_K, broad_km, local_km, broad_hpa_K, local_hpa_K):
    """Existing pressure-anomaly algebra in Pa, with spherical global filters.

    This supplies no value for the unknown parent anomaly field. Coefficients
    are caller-supplied existing physics, not fitted in this prototype.
    """
    if not np.isfinite([broad_hpa_K, local_hpa_K]).all():
        raise ValueError('Need finite pressure coefficients')
    broad = spherical_gaussian(anomaly_K, broad_km)
    local = spherical_gaussian(anomaly_K, local_km)-broad
    return -100.*(broad_hpa_K*broad+local_hpa_K*local)
