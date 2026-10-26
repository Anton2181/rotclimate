"""Research two-reservoir solve with the existing nonlinear column rain law.

Prescribed temperature/circulation inputs only, not a coupled climate model.
Column rain removes each layer's share of its water; no independent vertical
thermodynamics or saturation is inferred. Surface and external sources must
be provided explicitly, with nonnegative rates and accountable drying.
"""
from dataclasses import dataclass
import numpy as np
from rotclimate.moisture import rain_coefficient

DAY=86400.


@dataclass
class ReservoirSolution:
    water: np.ndarray
    layer_rain: np.ndarray
    iterations: int
    scaled_residual: float
    maximum_absolute_residual_mm_day: float
    linear_certificate: dict
    boundary_supply_cell_mm_day: float


def solve_column_rain(operator,p,source,saturation,dynamics,boundary,*,instability=1.,drying=0.,guess=None,closure=None):
    """Solve each water layer and certify its nonlinear local equation.

    Source is mm/s per layer, prescribed boundary is mm per layer, saturation
    is total-column mm. Drying is an explicitly counted1/s loss. Rain uses
    the unmodified climate column rain_coefficient at W_lower+W_upper, and
    partitions removal in proportion to current layer water. Both layers
    therefore have the same rain loss coefficient, not an imposed humidity
    profile. This isolates transport-state changes from precipitation-law
    changes; it does not represent where within the column clouds form.
    """
    source=operator._field(source,'source');boundary=operator._field(boundary,'boundary')
    if (source<0).any() or (boundary<0).any():raise ValueError('Need nonnegative explicit water supplies')
    saturation=np.broadcast_to(np.asarray(saturation,float),operator.shape)
    dynamics=np.broadcast_to(np.asarray(dynamics,float),operator.shape)
    instability=np.broadcast_to(np.asarray(instability,float),operator.shape)
    drying=np.broadcast_to(np.asarray(drying,float),source.shape)
    if (not np.isfinite(saturation).all() or (saturation<=0).any()
            or any(not np.isfinite(v).all() or (v<0).any() for v in [dynamics,instability,drying])):
        raise ValueError('Need positive saturation and finite nonnegative dynamics, instability and drying')
    if (not np.isfinite(p.moisture_residual_tol) or p.moisture_residual_tol<=0
            or not np.isfinite(p.moisture_relaxation) or not 0<p.moisture_relaxation<=1
            or p.picard_iters<1 or not np.isfinite(p.precip_tau_days) or p.precip_tau_days<=0
            or not np.isfinite(p.rh_threshold) or not 0<=p.rh_threshold<1):
        raise ValueError('Need explicit positive residual tolerance, valid rain parameters and bounded iteration settings')
    water=boundary.copy() if guess is None else operator._field(guess,'guess').copy()
    if (water<0).any():raise ValueError('Need nonnegative initial water')
    water[:,operator.border]=boundary[:,operator.border]
    rate=lambda w:rain_coefficient(w.sum(0),saturation,dynamics,instability,p.rh_threshold,p.precip_tau_days,closure,spread=p.rh_spread)
    for iteration in range(p.picard_iters):
        new,certificate=operator.solve(source,rate(water)+drying,boundary,diffusion=p.moisture_diffusion)
        water=(1-p.moisture_relaxation)*water+p.moisture_relaxation*new
        water[:,operator.border]=boundary[:,operator.border]
        rain=rate(water)*water*DAY
        transport,supply=operator.terms(water,diffusion=p.moisture_diffusion)
        evaporation=(source-drying*water)*DAY
        residual=evaporation[:,1:-1,1:-1]+transport*DAY-rain[:,1:-1,1:-1]
        scale=np.maximum(rain[:,1:-1,1:-1]+np.abs(evaporation[:,1:-1,1:-1]),.05)
        scaled=float(np.max(np.abs(residual)/scale))
        if not np.isfinite(scaled):raise FloatingPointError('Nonfinite reservoir equation residual')
        if scaled<=p.moisture_residual_tol:
            return ReservoirSolution(water,rain,iteration+1,scaled,float(np.abs(residual).max()),certificate,float(supply.sum())*DAY)
    raise RuntimeError(f'Two-reservoir nonlinear equation failed: residual {scaled:g} > {p.moisture_residual_tol:g} after {p.picard_iters} iterations')
