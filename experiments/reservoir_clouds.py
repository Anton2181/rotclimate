"""Isolated layer-capacity rain closure; no independent vertical temperature."""
import numpy as np
from rotclimate.moisture import rain_coefficient
from experiments.condensing_reservoirs import ReservoirSolution

DAY=86400.


def layer_rain_rate(water,saturation,fractions,p,dynamics,instability=1.,closure=None):
    """Apply the existing column law to layer-equivalent column amounts.

    f_i*Ws is each layer's capacity. Evaluating the unchanged law at W_i/f_i
    preserves the numerical water floor and scales convective rain correctly:
    at W_i=f_i*W, both layer loss rates equal the original column loss rate.
    This imposes a capacity profile, not an actual humidity profile. It does
    not infer layer temperatures or latent heating from this approximation.
    """
    water=np.asarray(water,float);fractions=np.asarray(fractions,float)
    if (water.ndim!=3 or water.shape[0]!=2 or fractions.shape!=(2,)
            or not np.isfinite(fractions).all() or (fractions<=0).any()
            or abs(float(fractions.sum())-1)>1e-12):raise ValueError('Need two positive capacity fractions summing to1')
    return np.stack([rain_coefficient(water[i]/fractions[i],saturation,dynamics,instability,
        p.rh_threshold,p.precip_tau_days,closure,spread=p.rh_spread) for i in range(2)])


def solve_layer_rain(operator,p,source,saturation,dynamics,boundary,fractions,*,instability=1.,drying=0.,guess=None,closure=None):
    """Solve two independent nonlinear layer rain sinks and full local ledgers."""
    source=operator._field(source,'source');boundary=operator._field(boundary,'boundary')
    saturation=np.broadcast_to(np.asarray(saturation,float),operator.shape)
    drying=np.broadcast_to(np.asarray(drying,float),source.shape)
    if ((source<0).any() or (boundary<0).any() or not np.isfinite(saturation).all() or (saturation<=0).any()
            or not np.isfinite(drying).all() or (drying<0).any() or p.moisture_residual_tol<=0
            or not 0<p.moisture_relaxation<=1 or p.picard_iters<1):raise ValueError('Need positive capacities, valid explicit supplies and strict iteration settings')
    water=boundary.copy() if guess is None else operator._field(guess,'guess').copy()
    if (water<0).any():raise ValueError('Need nonnegative initial water')
    water[:,operator.border]=boundary[:,operator.border]
    rate=lambda w:layer_rain_rate(w,saturation,fractions,p,dynamics,instability,closure)
    for iteration in range(p.picard_iters):
        new,certificate=operator.solve(source,rate(water)+drying,boundary,diffusion=p.moisture_diffusion)
        water=(1-p.moisture_relaxation)*water+p.moisture_relaxation*new
        water[:,operator.border]=boundary[:,operator.border]
        rain=rate(water)*water*DAY;transport,supply=operator.terms(water,diffusion=p.moisture_diffusion)
        evaporation=(source-drying*water)*DAY
        residual=evaporation[:,1:-1,1:-1]+transport*DAY-rain[:,1:-1,1:-1]
        scaled=float(np.max(np.abs(residual)/np.maximum(rain[:,1:-1,1:-1]+np.abs(evaporation[:,1:-1,1:-1]),.05)))
        if not np.isfinite(scaled):raise FloatingPointError('Nonfinite layer rain residual')
        if scaled<=p.moisture_residual_tol:
            return ReservoirSolution(water,rain,iteration+1,scaled,float(np.abs(residual).max()),certificate,float(supply.sum())*DAY)
    raise RuntimeError(f'Layer-capacity rain equation failed: residual {scaled:g} after {p.picard_iters} iterations')
