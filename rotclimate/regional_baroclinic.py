"""Mass-weighted regional dry mode; an isolated circulation foundation.

Cell geopotential and internal face velocities use a Cartesian C-grid. Column
mass may vary, but the mode speed and layer fractions are constant. This handles
the *mass weighting* of topography, not full terrain-following dynamics. No
moisture or physical heating budget is coupled here. Rows increase southward.
"""
from dataclasses import dataclass

import numpy as np
from scipy.sparse import bmat, coo_matrix, diags, eye
from scipy.sparse.linalg import spsolve


@dataclass
class RegionalMode:
    u_east: np.ndarray  # (ny, nx+1), including both exterior faces
    v_south: np.ndarray  # (ny+1, nx), including both exterior faces
    geopotential: np.ndarray
    divergence_per_s: np.ndarray  # div(mass * U) / mass
    certificate: dict


def _field(value, shape, name, *, positive=False):
    try:
        result = np.broadcast_to(np.asarray(value, dtype=float), shape).copy()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Need a matching {name} field") from exc
    if not np.isfinite(result).all() or (positive and np.any(result <= 0)):
        raise ValueError(f"Need finite {'positive ' if positive else ''}{name}")
    return result


def mass_divergence(u_east, v_south, column_mass, cell_m):
    """Conservative divergence with arithmetic face mass and exterior cell mass.

Mass can be kg/m² or relative mass; a uniform change of units cancels. Exterior
fluxes are counted with outward signs. There is no wrap across regional edges.
"""
    mass = np.asarray(column_mass, dtype=float)
    if mass.ndim != 2 or min(mass.shape) < 2 or not np.isfinite(mass).all() or np.any(mass <= 0):
        raise ValueError("Need finite positive 2D column mass")
    ny, nx = mass.shape
    u = _field(u_east, (ny, nx + 1), "east-face velocity")
    v = _field(v_south, (ny + 1, nx), "south-face velocity")
    if not np.isfinite(cell_m) or cell_m <= 0:
        raise ValueError("Need positive finite grid spacing")
    mu = np.column_stack((mass[:, 0], .5 * (mass[:, :-1] + mass[:, 1:]), mass[:, -1]))
    mv = np.vstack((mass[0], .5 * (mass[:-1] + mass[1:]), mass[-1]))
    return (np.diff(mu * u, axis=1) + np.diff(mv * v, axis=0)) / (mass * cell_m)


def solve_regional_mode(heating, cell_m, coriolis, *, column_mass=1.,
                        wave_speed_ms, momentum_drag_s, thermal_drag_s,
                        boundaries=None):
    """Solve damped momentum + c² div(M U)/M + rT phi = Q.

Q is modal heating (m²/s³), not external dry mass. Internal pressure force is
grad(phi). Mass-weighted Coriolis work cancels pairwise. Boundaries is a mapping
of west/east/north/south to 'wall' (default) or 'impedance'. A passive impedance
imposes outward U = phi/c using adjacent-cell pressure. Its energy export is
M phi²/(c dx); there is no incoming characteristic forcing. This is a first-order
normal-wave approximation, NOT a transparent rotating/spherical open boundary.
Exterior velocities have no momentum degrees of freedom or kinetic storage.

All norms include mass. In square-root mass coordinates, pressure/transport and
Coriolis are skew, and positive drags plus passive edges give a positive definite
symmetric part. Energy input = internal drag + thermal drag + boundary export.
"""
    q = np.asarray(heating, dtype=float)
    rates = np.asarray([cell_m, wave_speed_ms, momentum_drag_s, thermal_drag_s], dtype=float)
    if q.ndim != 2 or min(q.shape) < 2 or not np.isfinite(q).all():
        raise ValueError("Need finite 2D heating with at least two cells per axis")
    if not np.isfinite(rates).all() or np.any(rates <= 0):
        raise ValueError("Need positive finite spacing, mode speed and both drags")
    dx, c, r, rt = rates
    mass = _field(column_mass, q.shape, "column mass", positive=True)
    f = _field(coriolis, q.shape, "Coriolis")
    edges = dict(west="wall", east="wall", north="wall", south="wall")
    if boundaries is not None:
        if not isinstance(boundaries, dict) or set(boundaries) - set(edges):
            raise ValueError("Boundary names must be west/east/north/south")
        edges.update(boundaries)
    if any(value not in ("wall", "impedance") for value in edges.values()):
        raise ValueError("Boundary types must be wall or impedance")

    ny, nx = q.shape
    n = q.size
    ids = np.arange(n).reshape(q.shape)
    nu, nv = ny * (nx - 1), (ny - 1) * nx
    iu = np.arange(nu).reshape(ny, nx - 1)
    iv = np.arange(nv).reshape(ny - 1, nx)
    wu = .5 * (mass[:, :-1] + mass[:, 1:])
    wv = .5 * (mass[:-1] + mass[1:])
    root_m = np.sqrt(mass.ravel())
    root_u, root_v = np.sqrt(wu.ravel()), np.sqrt(wv.ravel())

    def gradient(left, right):
        nf = left.size
        face = np.arange(nf)
        return coo_matrix((np.r_[-np.ones(nf), np.ones(nf)] / dx,
                           (np.tile(face, 2), np.r_[left.ravel(), right.ravel()])),
                          shape=(nf, n)).tocsr()

    gx = gradient(ids[:, :-1], ids[:, 1:])
    gy = gradient(ids[:-1], ids[1:])
    ax = c * diags(root_u) @ gx @ diags(1 / root_m)
    ay = c * diags(root_v) @ gy @ diags(1 / root_m)

    # Each cell contributes M*f/4 to every incident internal u/v face pair.
    # Missing exterior velocities are zero in this rotation interpolation.
    # Multiplying by +/- transpose ensures zero *weighted* Coriolis work even
    # with variable mass/f; merely skewing unweighted velocity would be wrong.
    rows, cols, vals = [], [], []
    for j in range(ny):
        for i in range(nx):
            us = [iu[j, k] for k in (i - 1, i) if 0 <= k < nx - 1]
            vs = [iv[k, i] for k in (j - 1, j) if 0 <= k < ny - 1]
            for u in us:
                for v in vs:
                    rows.append(u)
                    cols.append(v)
                    vals.append(.25 * mass[j, i] * f[j, i] / (root_u[u] * root_v[v]))
    rotation = coo_matrix((vals, (rows, cols)), shape=(nu, nv)).tocsr()

    # Passive outward impedance contributes a positive thermal diagonal.
    damping = np.zeros(q.shape)
    if edges["west"] == "impedance": damping[:, 0] += c / dx
    if edges["east"] == "impedance": damping[:, -1] += c / dx
    if edges["north"] == "impedance": damping[0] += c / dx
    if edges["south"] == "impedance": damping[-1] += c / dx
    operator = bmat([[r * eye(nu), rotation, ax],
                     [-rotation.T, r * eye(nv), ay],
                     [-ax.T, -ay.T, diags(rt + damping.ravel())]], format="csc")
    rhs = np.r_[np.zeros(nu + nv), root_m * q.ravel() / c]
    solution = spsolve(operator, rhs)
    if not np.isfinite(solution).all():
        raise FloatingPointError("Nonfinite regional mode")
    residual = operator @ solution - rhs
    # Report residual in physical velocity units, independent of mass units.
    weights = np.r_[root_u, root_v, root_m]
    error_ms = float(np.max(np.abs(residual) / weights) / min(r, rt))
    velocity_scale = max(1., float(np.max(np.abs(solution) / weights)))
    if error_ms > 1e-8 * velocity_scale:
        raise RuntimeError("Regional momentum/thermal equation check failed")
    u = np.zeros((ny, nx + 1))
    v = np.zeros((ny + 1, nx))
    u[:, 1:-1] = (solution[:nu] / root_u).reshape(wu.shape)
    v[1:-1] = (solution[nu:nu + nv] / root_v).reshape(wv.shape)
    phi = (c * solution[nu + nv:] / root_m).reshape(q.shape)
    if edges["west"] == "impedance": u[:, 0] = -phi[:, 0] / c
    if edges["east"] == "impedance": u[:, -1] = phi[:, -1] / c
    if edges["north"] == "impedance": v[0] = -phi[0] / c
    if edges["south"] == "impedance": v[-1] = phi[-1] / c
    div = mass_divergence(u, v, mass, dx)
    total_mass = float(mass.sum())
    supply = float(np.sum(mass * phi * q / c**2) / total_mass)
    drag = float(r * (np.sum(wu * u[:, 1:-1]**2) + np.sum(wv * v[1:-1]**2)) / total_mass)
    relaxation = float(np.sum(mass * rt * (phi / c)**2) / total_mass)
    export = float(np.sum(mass * damping * (phi / c)**2) / total_mass)
    relative_error = abs(supply - drag - relaxation - export) / max(abs(supply), drag + relaxation + export, 1e-30)
    if relative_error > 1e-9:
        raise RuntimeError("Regional modal energy check failed")
    boundary_mass_flux = float((np.sum(mass[:, -1] * u[:, -1]) - np.sum(mass[:, 0] * u[:, 0])
                               + np.sum(mass[-1] * v[-1]) - np.sum(mass[0] * v[0])) / dx)
    certificate = dict(
        maximum_equation_residual_velocity_ms=error_ms,
        modal_energy_input_m2_s3=supply, momentum_dissipation_m2_s3=drag,
        thermal_dissipation_m2_s3=relaxation, boundary_energy_export_m2_s3=export,
        relative_modal_energy_error=relative_error,
        thermal_balance_residual_m2_s3=float(np.abs(c*c*div + rt*phi - q).max()),
        mass_weighted_divergence_per_s=float(np.sum(mass * div) / total_mass),
        boundary_mass_flux_per_total_mass_s=boundary_mass_flux / total_mass,
        divergence_theorem_error_per_s=float(abs(np.sum(mass * div) - boundary_mass_flux) / total_mass),
        integrated_thermal_balance_residual_m2_s3=float(abs(np.sum(mass * (q-rt*phi)) - c*c*boundary_mass_flux) / total_mass),
        mass_weighted_geopotential_m2_s2=float(np.sum(mass * phi) / total_mass),
        minimum_relative_column_mass=float(mass.min() / mass.max()),
        maximum_face_component_ms=float(max(np.abs(u).max(), np.abs(v).max())),
        boundaries=edges, wave_speed_ms=float(c), momentum_drag_s=float(r), thermal_drag_s=float(rt),
        scope="Isolated regional dry mode with variable column mass and passive boundaries; no climate, terrain metric or physical heating coupling")
    return RegionalMode(u, v, phi, div, certificate)


def embed_two_layers(mode, *, lower_fraction=.25):
    """Opposing mass-balanced winds and diagnosed upward dry-air exchange.

Both layers must share the supplied total face-mass pattern and have *constant*
fractions a,1-a. Upward exchange is per local total-column mass per second.
It must later carry water from the actual donor; this helper moves no moisture.
"""
    a = float(lower_fraction)
    if not np.isfinite(a) or not 0 < a < 1:
        raise ValueError("Need a constant lower mass fraction strictly between zero and one")
    return dict(lower_u_east=-(1-a) * mode.u_east, lower_v_south=-(1-a) * mode.v_south,
                upper_u_east=a * mode.u_east, upper_v_south=a * mode.v_south,
                upward_exchange_per_total_column_s=a*(1-a)*mode.divergence_per_s)
