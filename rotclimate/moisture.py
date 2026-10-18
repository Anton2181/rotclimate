"""Damped moisture iteration with an optional discrete-equation stopping test."""
from dataclasses import dataclass

import numpy as np

from .transport import moisture_terms

DAY = 86400.


def rain_coefficient(W, saturation, dynamics, instability, rh_threshold, tau_days, closure=None):
    rh = W / saturation
    gate = np.clip((rh - rh_threshold) / (1 - rh_threshold), 0, 2) ** 1.5
    rate = dynamics * gate * instability / (tau_days * DAY)
    if closure is not None:
        # physics e2: convective rain rising exponentially with column relative
        # humidity, P = conv * exp(11.4 (r - r0)) * fT mm/day (Bretherton et al.
        # 2004), and rain lost on the way down below high cloud bases,
        # x exp(-evap * z_LCL / 3 km) with z_LCL = (20 + T/5)(100 - RH%) m
        # (Lawrence 2005); the evaporated water stays in the column
        if closure["conv"] > 0:
            rate = rate + (closure["conv"] * np.exp(11.4 * (np.minimum(rh, 1.5) - closure["r0"])) * closure["fT"]
                           / (np.maximum(W, 0.1) * DAY))
        if closure["evap"] > 0:
            z_lcl = (20.0 + closure["T"] / 5.0) * (100.0 - 100.0 * np.clip(rh, 0.0, 1.0))
            rate = rate * np.exp(-closure["evap"] * np.maximum(z_lcl, 0.0) / 3000.0)
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
                   dynamics, instability, boundary, guess, exchange=0., mix=None, sink=None, closure=None):
    """Legacy fixed sweeps unless moisture_residual_tol > 0.

    The optional criterion is max |equation residual| / max(P+|E|,0.1)
    on the full interior, with all rates in mm/day. This is an actual local
    equation check, not the size of the artificially damped update.

    `sink` (1/s, optional): water removed from the column without raining
    (subsidence drying); it enters the equation check as negative evaporation.
    """
    W = guess
    converged = None if p.moisture_residual_tol == 0 else False
    residual = None
    lamE_all = lamE
    for n in range(p.picard_iters):
        lamE = ocean_rate(p, lamE_all, W, ocean_water)
        lamP = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days, closure)
        if sink is not None:
            lamP = lamP + sink
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
            P = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days, closure) * W * DAY
            E = (lamE * (ocean_water - W) + land_source) * DAY
            if sink is not None:
                E = E - sink * W * DAY
            terms = moisture_terms(W, u, v, solver.dx, p.moisture_diffusion, E, P,
                                   exchange, mix(W) if mix is not None else W)
            residual = float(np.max((terms['absolute_residual'] / np.maximum(P + np.abs(E), 0.1))[1:-1, 1:-1]))
            if not np.isfinite(residual):
                raise FloatingPointError('Nonfinite moisture-equation residual')
            converged = residual <= p.moisture_residual_tol
            if converged:
                break
    P = rain_coefficient(W, saturation, dynamics, instability, p.rh_threshold, p.precip_tau_days, closure) * W * DAY
    return MoistureSolution(W, P, n+1, converged, residual)


def ocean_rate(p, lamE, W, ocean_water):
    """Sea-surface exchange rate (1/s); e11 weakens uptake where W exceeds the sea's equilibrium."""
    if p.ocean_sink == 1.0:
        return lamE
    return np.where(W > ocean_water, p.ocean_sink * lamE, lamE)
