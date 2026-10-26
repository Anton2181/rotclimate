"""Opt-in pressure-driven shear between surface and moisture-column flow.

The Rayleigh/Coriolis balance is the existing surface closure. Changing its
effective drag turns the flow as well as changing speed; it is not a resolved
vertical boundary layer or a conservation fix for concentration advection.
"""
import numpy as np


def frictional_response(px, py, coriolis, drag, density=1.2):
    """Solve eps*u - f*v = -px/rho, f*u + eps*v = -py/rho.

    Pressure gradients use map-right/map-up coordinates in Pa/m, f and drag
    are in 1/s. Positive finite drag keeps the equatorial response regular.
    """
    px, py, f, eps = np.broadcast_arrays(px, py, coriolis, drag)
    if (not all(np.isfinite(a).all() for a in [px, py, f, eps]) or (eps <= 0).any()
            or not np.isfinite(density) or density <= 0):
        raise ValueError('Need finite pressure/Coriolis fields and positive drag/density')
    denominator = density*(eps**2+f**2)
    return -(eps*px+f*py)/denominator, (f*px-eps*py)/denominator


def pressure_shear(pressure, cell_m, coriolis, surface_drag, ratio):
    """Column-minus-surface pressure flow, retaining the same pressure gradient.

    Ratio is the column's effective Rayleigh drag relative to the surface.
    The zero-shear endpoint returns exact zeros without subtractive roundoff.
    """
    if not np.isfinite(ratio) or not 0.25 <= ratio <= 1:
        raise ValueError('Column pressure drag ratio must be in [0.25, 1]')
    pressure = np.asarray(pressure, float)
    if pressure.ndim != 2 or min(pressure.shape) < 2 or not np.isfinite(pressure).all():
        raise ValueError('Need a finite 2-D pressure field')
    if not np.isfinite(cell_m) or cell_m <= 0:
        raise ValueError('Need positive finite cell spacing')
    if ratio == 1:
        return np.zeros_like(pressure), np.zeros_like(pressure)
    px = np.gradient(pressure, axis=1)/cell_m
    py = -np.gradient(pressure, axis=0)/cell_m
    us, vs = frictional_response(px, py, coriolis, surface_drag)
    uc, vc = frictional_response(px, py, coriolis, np.asarray(surface_drag)*ratio)
    return uc-us, vc-vs


def thermal_shear(temperature_c, cell_m, coriolis, height_km):
    """Hydrostatic/geostrophic shear for a representative moist-layer height.

    With horizontally varying layer-mean T and small vertical lapse variation,
    du/dz = -g/(f*T) dT/dnorth, dv/dz = g/(f*T) dT/deast.
    The input is a smooth common-height temperature, never raw terrain-cooled
    surface temperature. Map rows increase southward. A fixed smooth10-degree
    equatorial taper regularizes1/f; it is not an equatorial momentum solution.
    This does not resolve vertical mass return or transient moisture covariance.
    """
    temperature_c = np.asarray(temperature_c, float)
    if (temperature_c.ndim != 2 or min(temperature_c.shape) < 2
            or not np.isfinite(temperature_c).all() or (temperature_c <= -173.15).any()
            or not np.isfinite(cell_m) or cell_m <= 0
            or not np.isfinite(height_km) or not 0 <= height_km <= 4):
        raise ValueError('Need a finite2-D physical layer temperature, cell spacing and height in[0,4]km')
    f = np.broadcast_to(np.asarray(coriolis, float), temperature_c.shape)
    if not np.isfinite(f).all():
        raise ValueError('Need finite Coriolis field')
    if height_km == 0:
        return np.zeros_like(temperature_c), np.zeros_like(temperature_c)
    log_temperature = np.log(temperature_c+273.15)
    tx = np.gradient(log_temperature, axis=1)/cell_m
    ty = -np.gradient(log_temperature, axis=0)/cell_m
    equatorial_f = 2*7.292e-5*np.sin(np.radians(10))
    inverse_f = f/(f*f+equatorial_f**2)
    factor = 9.80665*height_km*1000*inverse_f
    return -factor*ty, factor*tx
