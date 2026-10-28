"""Native-face donor tracer for the isolated regional dry circulation mode.

This is a passive water/tracer equation, not a rainfall/latent-heating model.
It preserves actual staggered air fluxes rather than recentering the winds.
"""
from dataclasses import dataclass
import warnings

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from .regional_baroclinic import embed_two_layers, mass_divergence


@dataclass
class ModeTracer:
    water: np.ndarray
    removal: np.ndarray
    east_water_flux: np.ndarray
    south_water_flux: np.ndarray
    upward_water_flux: np.ndarray
    certificate: dict


def _layers(value, shape, name, *, positive=False):
    array = np.asarray(value, dtype=float)
    if array.shape == (2,):
        array = array[:, None, None]
    try:
        array = np.broadcast_to(array, (2,) + shape).copy()
    except ValueError as exc:
        raise ValueError(f"Need scalar, two layer values, or matching 2D/3D {name}") from exc
    if not np.isfinite(array).all() or np.any(array <= 0 if positive else array < 0):
        raise ValueError(f"Need finite {'positive' if positive else 'nonnegative'} {name}")
    return array


def solve_mode_tracer(mode, column_mass, cell_m, source, removal_rate,
                      external_mixing_ratio, *, lower_fraction=.25):
    """Steady upwind tracer with dry-continuity-diagnosed vertical donor flux.

Water and source are kg/m² and kg/m²/s if column_mass is kg/m²; mixing ratio is
kg/kg. Relative mass units work too if all tracer supplies use consistent units.
Source/removal are supplied, not predicted evaporation/rain. Strictly positive
removal makes this isolated steady system nonsingular even at stagnant cells.
No arbitrary humidity profile, clipping or saturation reset is imposed.

Every exterior face uses actual diagnosed velocity. Incoming air carries the
specified external layer mixing ratio; outgoing air carries local donor water.
Vertical exchange has the same donor rule and cancels exactly in the column.
Boundary mixing ratio is a local edge field, not a globally fixed water amount.
"""
    mass = np.asarray(column_mass, dtype=float)
    if mass.ndim != 2 or min(mass.shape) < 2 or not np.isfinite(mass).all() or np.any(mass <= 0):
        raise ValueError("Need finite positive 2D total dry mass")
    if not np.isfinite(cell_m) or cell_m <= 0:
        raise ValueError("Need positive finite grid spacing")
    ny, nx = mass.shape
    n = mass.size
    shape = mass.shape
    # Independently recompute dry divergence; reject a stale/mismatched mode.
    div = mass_divergence(mode.u_east, mode.v_south, mass, cell_m)
    if (np.shape(mode.divergence_per_s) != shape or not np.isfinite(mode.divergence_per_s).all()
            or not np.allclose(div, mode.divergence_per_s, rtol=1e-10, atol=1e-18)):
        raise ValueError("Mode divergence is inconsistent with supplied face mass/spacing")
    layers = embed_two_layers(mode, lower_fraction=lower_fraction)
    a = float(lower_fraction)
    layer_mass = np.stack([a * mass, (1-a) * mass])
    supply = _layers(source, shape, "source")
    loss = _layers(removal_rate, shape, "removal rate", positive=True)
    external = _layers(external_mixing_ratio, shape, "external mixing ratio")
    mu = np.column_stack((mass[:, 0], .5*(mass[:, :-1]+mass[:, 1:]), mass[:, -1]))
    mv = np.vstack((mass[0], .5*(mass[:-1]+mass[1:]), mass[-1]))
    # One shared flux and its opposite avoid independently rounded products
    # creating a tiny artificial net dry-column source.
    lower_x = a*mu*layers['lower_u_east']
    lower_y = a*mv*layers['lower_v_south']
    fx = np.stack([lower_x, -lower_x])
    fy = np.stack([lower_y, -lower_y])
    upward = mass * layers['upward_exchange_per_total_column_s']
    ids = np.arange(n).reshape(shape)
    rows, cols, values = [], [], []
    rhs = supply.copy()

    def add(row, col, value):
        rows.extend(np.asarray(row).ravel().tolist())
        cols.extend(np.asarray(col).ravel().tolist())
        values.extend(np.asarray(value).ravel().tolist())

    def interior_flux(left, right, flux, mleft, mright):
        pos, neg = np.maximum(flux, 0)/cell_m, np.minimum(flux, 0)/cell_m
        add(left, left, pos/mleft)
        add(right, left, -pos/mleft)
        add(left, right, neg/mright)
        add(right, right, -neg/mright)

    for k in range(2):
        off = k*n
        m = layer_mass[k]
        add(off+ids, off+ids, loss[k])
        interior_flux(off+ids[:, :-1], off+ids[:, 1:], fx[k, :, 1:-1], m[:, :-1], m[:, 1:])
        interior_flux(off+ids[:-1], off+ids[1:], fy[k, 1:-1], m[:-1], m[1:])
        # Boundary normal signs: west/north are opposite grid-positive flow.
        for index, flux, local_m, ext in [
                (ids[:, 0], -fx[k, :, 0], m[:, 0], external[k, :, 0]),
                (ids[:, -1], fx[k, :, -1], m[:, -1], external[k, :, -1]),
                (ids[0], -fy[k, 0], m[0], external[k, 0]),
                (ids[-1], fy[k, -1], m[-1], external[k, -1])]:
            add(off+index, off+index, np.maximum(flux, 0)/(cell_m*local_m))
            rhs[k].ravel()[index] += -np.minimum(flux, 0)*ext/cell_m
    up_pos, up_neg = np.maximum(upward, 0), np.minimum(upward, 0)
    add(ids, ids, up_pos/layer_mass[0])
    add(n+ids, ids, -up_pos/layer_mass[0])
    add(ids, n+ids, up_neg/layer_mass[1])
    add(n+ids, n+ids, -up_neg/layer_mass[1])
    operator = coo_matrix((values, (rows, cols)), shape=(2*n, 2*n)).tocsc()
    with warnings.catch_warnings():
        warnings.simplefilter('error', MatrixRankWarning)
        water = spsolve(operator, rhs.ravel()).reshape((2,)+shape)
    if not np.isfinite(water).all() or np.any(water < 0):
        raise FloatingPointError("Invalid regional donor tracer state")
    residual = operator @ water.ravel()-rhs.ravel()
    scaled_error = float(np.max(np.abs(residual)/operator.diagonal()))
    if scaled_error > 1e-10*max(1.,float(water.max())):
        raise RuntimeError("Regional tracer linear equations failed")
    mixing = water/layer_mass
    qx = np.concatenate((external[:, :, :1], mixing, external[:, :, -1:]), axis=2)
    qy = np.concatenate((external[:, :1], mixing, external[:, -1:]), axis=1)
    water_x = fx*np.where(fx >= 0, qx[:, :, :-1], qx[:, :, 1:])
    water_y = fy*np.where(fy >= 0, qy[:, :-1], qy[:, 1:])
    water_up = up_pos*mixing[0]+up_neg*mixing[1]
    horizontal_out = (np.diff(water_x,axis=2)+np.diff(water_y,axis=1))/cell_m
    vertical_out = np.stack([water_up, -water_up])
    removal = loss*water
    actual_residual = supply-removal-horizontal_out-vertical_out
    actual_scaled = float(np.max(np.abs(actual_residual)/operator.diagonal().reshape((2,)+shape)))
    if actual_scaled > 1e-10*max(1.,float(water.max())):
        raise RuntimeError("Regional tracer actual face equation failed")
    boundary_out = (water_x[:, :, -1].sum(axis=1)-water_x[:, :, 0].sum(axis=1)
                    +water_y[:, -1].sum(axis=1)-water_y[:, 0].sum(axis=1))/cell_m
    budget = supply.sum(axis=(1,2))-removal.sum(axis=(1,2))-boundary_out
    vertical_net = np.array([water_up.sum(), -water_up.sum()])
    certificate = dict(diagonal_scaled_linear_error_water=scaled_error,
        diagonal_scaled_actual_face_error_water=actual_scaled,
        source_water_per_cell_s=supply.sum(axis=(1,2)).tolist(),
        removal_water_per_cell_s=removal.sum(axis=(1,2)).tolist(),
        outward_boundary_water_per_cell_s=boundary_out.tolist(),
        upward_water_transfer_per_cell_s=float(water_up.sum()),
        layer_integrated_budget_error_water_per_cell_s=(budget-vertical_net).tolist(),
        column_integrated_budget_error_water_per_cell_s=float(budget.sum()),
        minimum_water=float(water.min()), maximum_water=float(water.max()),
        minimum_mixing_ratio=float(mixing.min()), maximum_mixing_ratio=float(mixing.max()),
        maximum_dry_column_face_flux_residual=float(max(np.abs(fx.sum(axis=0)).max(),np.abs(fy.sum(axis=0)).max())),
        scope="Isolated passive donor tracer driven by native regional mode faces; supplied sources/removal, no rainfall or latent heating feedback")
    return ModeTracer(water, removal, water_x, water_y, water_up, certificate)
