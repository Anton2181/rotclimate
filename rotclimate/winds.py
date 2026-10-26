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
