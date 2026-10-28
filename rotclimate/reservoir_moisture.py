"""Independent layer water with actual surface/storm/rain equation checks.

Steady moisture states per seasonal step, not a vertically resolved momentum
or energy model. Total calibrated saturation may remain legacy; a moist
hydrostatic profile partitions capacity without resetting actual humidity.
"""
from dataclasses import dataclass
import numpy as np
from .moisture import rain_coefficient,ocean_rate
from .reservoir_transport import ReservoirTransport,solve_block

DAY=86400.


@dataclass
class ReservoirMoistureSolution:
    water: np.ndarray
    rain: np.ndarray
    iterations: int
    converged: bool
    scaled_residual: float
    layer_water: np.ndarray
    layer_rain: np.ndarray
    evaporation: np.ndarray
    certificate: dict


def reservoir_rain_partition(water,fractions,saturation,dynamics,instability,p,closure=None):
    """Local dynamic rain/saturation, with an optional column convective law.

    Bretherton's exponential is calibrated against whole-column humidity;
    applying it separately to different layer humidities adds a convexity
    amplification. The opt-in scheme evaluates that component once on total
    water. All falling dynamic/convective rain sees the same lower-air cloud
    base evaporation; local supersaturation removal stays unevaporated.
    Returns ground-rain coefficients and the coefficient of upper rain that
    evaporates into the lower layer. This transfer is separately booked in
    both layer equations. At a proportional humidity profile the ground-rain
    sum recovers the column law, without imposing that profile dynamically.
    """
    equivalent=water/fractions
    if p.moisture_reservoir_rain_scheme=='layer':
        return (rain_coefficient(equivalent,saturation,dynamics,instability,
            p.rh_threshold,p.precip_tau_days,closure,spread=p.rh_spread),0.)
    if p.moisture_reservoir_rain_scheme!='column-convection':
        raise ValueError('Unknown independent-reservoir rainfall scheme')
    rh=equivalent/saturation
    overflow=np.divide(np.maximum(rh-1,0),rh,out=np.zeros_like(rh),where=rh>0)/DAY
    # Without an empirical closure the existing dynamic rain remains local.
    # Remove its independently returned overflow before applying evaporation.
    dynamic=rain_coefficient(equivalent,saturation,dynamics,instability,
        p.rh_threshold,p.precip_tau_days,spread=p.rh_spread)-overflow
    convective=0.;evaporation=1.
    if closure is not None:
        if closure['conv']>0:
            total=water.sum(0);column_rh=total/saturation
            convective=(closure['conv']*np.exp(11.4*(np.minimum(column_rh,1.5)-closure['r0']))
                *closure['fT']/(np.maximum(total,.1)*DAY))
        if closure['evap']>0:
            lower_rh=rh[0]
            lcl=(20.+closure['T']/5.)*(100.-100.*np.clip(lower_rh,0.,1.))
            evaporation=np.exp(-closure['evap']*np.maximum(lcl,0.)/3000.)
    gross=dynamic+convective
    return gross*evaporation+overflow,(1-evaporation)*gross[1]


def reservoir_rain_coefficients(water,fractions,saturation,dynamics,instability,p,closure=None):
    """Ground-rain rates; matrix loss also includes evaporated upper rain."""
    return reservoir_rain_partition(water,fractions,saturation,dynamics,instability,p,closure)[0]


def solve_reservoir_moisture(solver,p,u,v,lamE,ocean_water,land_source,saturation,dynamics,instability,
        boundary,guess,exchange=0.,mix=None,*,sink=None,closure=None,gain=None,condensate=None,
        lower_capacity_fraction=None,ocean_lower_fraction=None):
    if (gain is not None or condensate is not None or solver.column_mass is None or len(solver.layers)!=2
            or p.moisture_residual_tol<=0 or not 0<p.moisture_relaxation<=1):
        raise ValueError('Independent reservoirs require conservative two-branch mass transport, strict residuals and no extra import/rainout')
    shape=solver.column_mass.shape
    lower=np.broadcast_to(np.asarray(lower_capacity_fraction,float),shape)
    ocean_fraction=np.broadcast_to(np.asarray(ocean_lower_fraction,float),shape)
    if any(not np.isfinite(f).all() or (f<=0).any() or (f>=1).any() for f in [lower,ocean_fraction]):
        raise ValueError('Need finite layer capacity and ocean boundary fractions strictly in(0,1)')
    fractions=np.stack([lower,1-lower]);winds=[(a,b) for _,a,b in solver.layers]
    rate=0. if p.moisture_reservoir_mixing_days==0 else 1/(p.moisture_reservoir_mixing_days*DAY)
    op=ReservoirTransport(solver.column_mass,*winds,solver.dx,mixing_rate=rate)
    bfrac=np.where(lamE>0,ocean_fraction,lower)
    bnd=np.stack([bfrac*boundary,(1-bfrac)*boundary])
    previous=getattr(solver,'reservoir_water',None)
    if previous is None:water=fractions*guess
    else:
        previous_total=previous.sum(0)
        weights=np.divide(previous,previous_total,out=fractions.copy(),where=previous_total>0)
        water=weights*guess
    water[:,op.border]=bnd[:,op.border]
    drying=np.zeros(shape) if sink is None else np.broadcast_to(sink,shape)
    exchange=np.broadcast_to(exchange,shape)
    partition=lambda w:reservoir_rain_partition(w,fractions,saturation,dynamics,instability,p,closure)
    mixed=lambda w:np.stack([mix(a) for a in w]) if mix is not None else w
    max_linear_error=0.;recoveries=0
    for iteration in range(p.picard_iters):
        surface_rate=ocean_rate(p,lamE,water[0]/ocean_fraction,ocean_water)
        coefficients,recycling=partition(water)
        reaction=coefficients+drying+exchange
        # Upper rain evaporating below removes upper water and supplies lower
        # vapor; only its surviving fraction is ground precipitation.
        reaction[1]+=recycling
        reaction[0]+=surface_rate/ocean_fraction
        source=exchange*mixed(water)
        source[0]+=recycling*water[1]
        source[0]+=surface_rate*ocean_water+land_source
        new,linear=solve_block(op,source,reaction,bnd,diffusion=p.moisture_diffusion,guess=water,
            rtol=solver.rtol,max_iter=solver.max_iter,recover=solver.recover)
        solver.iterations.append(linear['iterations']);solver.converged.append(True)
        solver.final_updates.append(linear['diagonal_scaled_residual_mm']);solver.methods.append(linear['method'])
        max_linear_error=max(max_linear_error,linear['diagonal_scaled_residual_mm'])
        recoveries+=linear['method']=='sparse_recovery'
        water=(1-p.moisture_relaxation)*water+p.moisture_relaxation*new
        water[:,op.border]=bnd[:,op.border]
        # Evaluate the ACTUAL updated state, including the sea uptake switch.
        surface_rate=ocean_rate(p,lamE,water[0]/ocean_fraction,ocean_water)
        evaporation=np.zeros_like(water)
        evaporation[0]=(surface_rate*(ocean_water-water[0]/ocean_fraction)+land_source)*DAY
        net=evaporation-drying*water*DAY
        coefficients,recycling=partition(water)
        rain=coefficients*water*DAY
        recycled=recycling*water[1]*DAY
        internal=np.stack([recycled,-recycled])
        horizontal_vertical,boundary_supply=op.terms(water,diffusion=p.moisture_diffusion)
        storm=exchange*(mixed(water)-water)*DAY
        residual=net[:,1:-1,1:-1]+internal[:,1:-1,1:-1]+horizontal_vertical*DAY+storm[:,1:-1,1:-1]-rain[:,1:-1,1:-1]
        layer_scale=np.maximum(rain[:,1:-1,1:-1]+np.abs(net[:,1:-1,1:-1]),.05)
        layer_residual=float(np.max(np.abs(residual)/layer_scale))
        column_scale=np.maximum(rain[:,1:-1,1:-1].sum(0)+np.abs(net[:,1:-1,1:-1].sum(0)),.1)
        column_residual=float(np.max(np.abs(residual.sum(0))/column_scale))
        scaled=max(layer_residual,column_residual)
        if not np.isfinite(scaled):raise FloatingPointError('Nonfinite independent-reservoir water residual')
        if scaled<=p.moisture_residual_tol:break
    total=water.sum(0)
    actual_fractions=np.divide(water,total,out=fractions.copy(),where=total>0)
    solver.set_layers(tuple((actual_fractions[i],*winds[i]) for i in range(2)))
    solver.reservoir_water=water.copy()
    q=water/op.layer_mass
    ratio=np.divide(q[1],q[0],out=np.zeros_like(total),where=q[0]>0)
    certificate=dict(all_layer_checks_passed=scaled<=p.moisture_residual_tol,
        rain_scheme=p.moisture_reservoir_rain_scheme,
        maximum_recycled_precipitation_mm_day=float(recycled[1:-1,1:-1].max()),
        mean_recycled_precipitation_mm_day=float(recycled[1:-1,1:-1].mean()),
        maximum_internal_precipitation_transfer_residual_mm_day=float(np.abs(internal.sum(0)).max()),
        max_scaled_layer_residual=layer_residual,max_scaled_column_residual=column_residual,
        maximum_absolute_layer_residual_mm_day=float(np.abs(residual).max()),
        minimum_upper_lower_q_ratio=float(ratio[1:-1,1:-1].min()),maximum_upper_lower_q_ratio=float(ratio[1:-1,1:-1].max()),
        minimum_lower_water_fraction=float(actual_fractions[0,1:-1,1:-1].min()),maximum_lower_water_fraction=float(actual_fractions[0,1:-1,1:-1].max()),
        max_scaled_dry_column_residual=op.dry_residual,max_linear_equation_error_mm=max_linear_error,
        sparse_recoveries=recoveries,iterations=iteration+1,
        boundary_advective_diffusive_supply_cell_mm_day=float(boundary_supply.sum())*DAY,
        scope='Independent steady layer water; donor vertical exchange cancels; surface exchange below, layer rain/storms/drying accounted separately')
    observer=getattr(solver,'reservoir_observer',None)
    if observer is not None:
        # Observe only the final solved equation. Isolated copies prevent a
        # diagnostic callback from changing this or the next seasonal state.
        fields=dict(water=water,layer_mass=op.layer_mass,winds=np.asarray(winds),
            upward_air=op.upward_air,lower_out=op.lower_out,upper_out=op.upper_out,
            evaporation=evaporation,drying_rate=drying,storm=storm,rain=rain,
            recycled=recycled,residual=residual,saturation=saturation,fractions=fractions,
            dynamics=dynamics,instability=instability,boundary_water=bnd,
            ocean_water=ocean_water,ocean_fraction=ocean_fraction)
        observer(dict(fields={key:np.array(value,copy=True) for key,value in fields.items()},
            closure=None if closure is None else {key:np.array(value,copy=True) for key,value in closure.items()},
            dx=op.dx,diffusion=p.moisture_diffusion))
    return ReservoirMoistureSolution(total,rain.sum(0),iteration+1,scaled<=p.moisture_residual_tol,scaled,
        water,rain,evaporation.sum(0),certificate)
