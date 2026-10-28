"""Pressure- and footprint-matched native diagnostics, never model forcing."""
from functools import lru_cache
from pathlib import Path
import json
import numpy as np
from rotclimate import earth
from rotclimate.numerics import matrix_product
from scripts.circulation_reference import (projection_jacobian,geographic_wind,
    native_aggregation,column_targets,vector_scores,layer_partial_water)
from scripts.earth_calendar import observation_weights

ROOT=Path(__file__).resolve().parents[1]
G=9.80665


def partial_flux(water,winds,pressure,bottom=92500.,top=30000.):
    """Exact two-box pressure overlap of simultaneous q and geographic wind.

    Returns partial water and water-weighted vector numerators, not velocities.
    A column's below-ground interval is excluded separately by the native mask.
    """
    partial=layer_partial_water(water,pressure,bottom,top)
    split=.75*pressure
    dp=np.stack([np.maximum(np.minimum(pressure,bottom)-np.maximum(split,top),0),
                 np.maximum(np.minimum(split,bottom)-top,0)])
    mass=np.stack([.25*pressure,.75*pressure])/G
    amount=water/mass*dp/G
    wind=np.asarray(winds)
    if wind.shape!=water.shape[:2]+(2,)+pressure.shape:
        raise ValueError('Expected time/layer/component/grid geographic winds')
    return partial,np.sum(amount[:,:,None]*wind,axis=1)


@lru_cache(maxsize=1)
def references(plan_path):
    from scripts.transport_reference import acquire
    return acquire(ROOT,json.loads((ROOT/plan_path).read_text()))[0]


def diagnose(case,p,arrays,plan):
    g=case.grid;spec=earth.REGIONS[case.name]
    if spec['lat0']<0:raise ValueError('This fixed diagnostic declares northern regions only')
    ref=references(plan['transport_reference_plan']);fields={v:ref[case.name,v] for v in ('uwnd','vwnd','shum','hgt')}
    targets,refwater,height=column_targets(fields)
    scored=arrays['scored_indices'];days=arrays['days'];n=len(days)
    weights,durations,order=observation_weights(days)
    geo=projection_jacobian(g.lat,case.lon,spec['lat0'],spec['lon0']);area=g.cell_km**2/geo[-1]
    water=arrays['water'][scored];wind=arrays['winds'][scored]
    east,north=geographic_wind(wind[:,:,0],wind[:,:,1],geo)
    winds=np.stack([east,north],axis=2)
    pressure=101325*np.exp(-g.elev/8000)
    partial,flux=partial_flux(water,winds,pressure)
    monthly=lambda a:matrix_product(weights,a.reshape(n,-1)).reshape((12,)+a.shape[1:])
    interior=np.ones_like(g.land);interior[[0,-1],:]=False;interior[:,[0,-1]]=False
    observed_valid=np.isfinite(case.obs_P).all(0)
    report={};saved=dict(native_month_days=durations,native_month_order=order,native_latitude=fields['shum'].latitude,
        native_longitude=fields['shum'].longitude)
    for kind in ('land','ocean'):
        # For land, every variable uses the very same observed-rain land pixels;
        # no mixing rain on land with humidity/wind averaged over nearby sea.
        own=g.inmap&interior&((g.land&observed_valid) if kind=='land' else ~g.land)
        aggregate,masks,native_area,coverage=native_aggregation(g.lat,case.lon,area,own,g.land,g.elev,fields['shum'],height)
        above=aggregate((pressure>=92500).astype(float))>=1-1e-12
        mask=masks[kind]&above
        mw=aggregate(monthly(partial));mf=aggregate(monthly(flux))
        velocity=np.divide(mf,mw[:,None],out=np.zeros_like(mf),where=mw[:,None]>0)
        rw=refwater[order].reshape(12,-1);rv=targets['q925_300'][order].reshape(12,2,-1)
        prefix='native_'+kind+'_'
        rain=aggregate(monthly(arrays['rain'][scored].sum(1)))*durations[:,None]
        obs=aggregate(np.nan_to_num(case.obs_P))
        # Compare both rainfall and water under identical calendar and weights.
        saved.update({prefix+'mask':mask,prefix+'area':native_area,prefix+'water':mw,
            prefix+'flux':mf,prefix+'wind':velocity,prefix+'reference_water':rw,
            prefix+'reference_wind':rv,prefix+'rain':rain,prefix+'observed_rain':obs})
        coverage.update(pressure925_excluded=int(np.sum(masks[kind]&~above)),matched_cells=int(mask.sum()))
        row=dict(coverage=coverage,wind=None,monthly=None)
        if mask.any():
            a=native_area[mask];avg=lambda x:np.average(x[...,mask],axis=-1,weights=a).tolist()
            row['wind']=vector_scores(velocity[:,:,mask],rv[:,:,mask],a,durations)
            row['monthly']=dict(water_mm=avg(mw),reference_water_mm=avg(rw),rain_mm=avg(rain),
                observed_rain_mm=avg(obs) if kind=='land' else None)
            row['area_km2']=float(a.sum())
            # Components and budgets are averaged after forming their per-step products.
            for key in ('evaporation','drying','storm','rain_dynamic','rain_convective','rain_overflow'):
                values=aggregate(monthly(arrays[key][scored].sum(1)))*durations[:,None]
                saved[prefix+key]=values;row['monthly'][key+'_mm']=avg(values)
            branch=aggregate(monthly(winds))
            saved[prefix+'branch_wind']=branch
            row['monthly']['branch_wind_ms']=avg(branch)
        report[kind]=row
    report['definition']='Pressure925–300hPa; per-step q*u, then Gregorian and same native footprint aggregation. Land variables use identical observed-rain land pixels with >=80% native area coverage; reference and modeled925hPa must be above ground. No fallback for empty masks.'
    report['limitations']=['Observed q*u is product of monthly reanalysis means, missing submonthly covariance.',
        'Two-box model q and wind are piecewise constant in pressure; no resolved vertical momentum or energy.',
        'WorldClim rain and NCEP climatology have different observational periods and construction.',
        'These reused development regions and new Mexico fields are diagnostics, not independent held-out validation.']
    return report,saved
