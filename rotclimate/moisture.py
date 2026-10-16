"""Damped moisture iteration with an optional discrete-equation stopping test."""
from dataclasses import dataclass

import numpy as np

from .transport import moisture_terms

DAY = 86400.


def rain_coefficient(W, saturation, dynamics, instability, rh_threshold, tau_days):
    rh = W / saturation
    gate = np.clip((rh - rh_threshold) / (1 - rh_threshold), 0, 2) ** 1.5
    rate = dynamics * gate * instability / (tau_days * DAY)
    # The supersaturation term is zero at RH=0; avoid the legacy 0/0 there.
    overflow = np.divide(np.maximum(rh - 1, 0), rh, out=np.zeros_like(rh), where=rh > 0)
    return rate + overflow / DAY


@dataclass
class MoistureSolution:
    water: np.ndarray
    rain: np.ndarray
    iterations: int
    converged: bool | None
    scaled_residual: float | None


def solve_moisture(solver, p, u, v, lamE, ocean_water, land_source, saturation,
                   dynamics, instability, boundary, guess, exchange=0., mix=None):
    """Legacy fixed sweeps unless moisture_residual_tol > 0.

    The optional criterion is max |equation residual| / max(P+|E|,0.1)
    on the full interior, with all rates in mm/day. This is an actual local
    equation check, not the size of the artificially damped update.
    """
    W = guess
    converged = None if p.moisture_residual_tol == 0 else False
    residual = None
    for n in range(p.picard_iters):
        lamP = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days)
        if mix is not None:
            mixed = mix(W)
            new = solver.solve(u, v, p.moisture_diffusion, lamE + lamP + exchange,
                               lamE * ocean_water + land_source + exchange * mixed, boundary, guess=W)
        else:
            new = solver.solve(u, v, p.moisture_diffusion, lamE + lamP,
                               lamE * ocean_water + land_source, boundary, guess=W)
        if p.moisture_relaxation == 0.5:
            W = 0.5 * (W + np.maximum(new, 0))  # exact legacy arithmetic
        else:
            W = (1-p.moisture_relaxation) * W + p.moisture_relaxation * np.maximum(new, 0)
        if p.moisture_residual_tol > 0:
            W[solver.border] = boundary[solver.border]
            P = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days) * W * DAY
            E = (lamE * (ocean_water - W) + land_source) * DAY
            terms = moisture_terms(W, u, v, solver.dx, p.moisture_diffusion, E, P,
                                   exchange, mix(W) if mix is not None else W)
            residual = float(np.max((terms['absolute_residual'] / np.maximum(P + np.abs(E), 0.1))[1:-1, 1:-1]))
            if not np.isfinite(residual):
                raise FloatingPointError('Nonfinite moisture-equation residual')
            converged = residual <= p.moisture_residual_tol
            if converged:
                break
    P = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days) * W * DAY
    return MoistureSolution(W, P, n+1, converged, residual)
