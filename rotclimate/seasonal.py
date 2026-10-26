"""Calendar-safe spin-up and diagnostics of a repeated forced annual cycle.

The fixed limits are numerical repeatability criteria, not fitted climate
targets or estimates of real interannual variability.
"""
from numbers import Integral
import numpy as np

LIMITS = dict(temperature=.05, rain=.01, water=.05, soil_water=.1,
              recycled_rain=.01, snow_water=.1)
UNITS = dict(temperature='degC', rain='mm/day', water='mm', soil_water='mm',
             recycled_rain='mm/day', snow_water='mm')


def integration_order(steps,primer,extra_years):
    for name,value,minimum in [('steps',steps,1),('primer',primer,0),('extra_years',extra_years,0)]:
        if isinstance(value,bool) or not isinstance(value,Integral) or value<minimum:
            raise ValueError(name+' must be an integer >= '+str(minimum))
    # Keep the exact historical ordering for ordinary primers. Longer ones
    # wrap the calendar instead of indexing past the start of the year.
    prefix=list(range(steps-primer,steps)) if primer<=steps else [k%steps for k in range(steps-primer,steps)]
    return prefix+list(range(steps))*(extra_years+1),primer+steps*extra_years


class CycleMonitor:
    def __init__(self,steps,land_mask):
        self.steps=steps;self.land=np.asarray(land_mask,bool)
        self.interior=np.ones_like(self.land);self.interior[[0,-1],:]=False;self.interior[:,[0,-1]]=False
        if not self.interior.any():raise ValueError('Need an interior climate grid')
        self.previous={};self.seasons=0;self.comparisons=[];self.current={}

    def update(self,season,fields):
        if season!=self.seasons%self.steps or set(fields)!=set(LIMITS):
            raise ValueError('Need complete, sequential annual diagnostic fields')
        year=self.seasons//self.steps
        if season==0:
            self.current={key:dict(domain_max_abs=0.,map_land_max_abs=0. if self.land.any() else None,
                                  map_land_mean_abs=0. if self.land.any() else None) for key in fields}
        for key,field in fields.items():
            field=np.asarray(field,float)
            if field.shape!=self.land.shape or not np.isfinite(field).all():raise ValueError('Invalid annual-cycle field: '+key)
            if key not in self.previous:self.previous[key]=np.empty((self.steps,)+field.shape)
            if year:
                delta=np.abs(field-self.previous[key][season]);record=self.current[key]
                record['domain_max_abs']=max(record['domain_max_abs'],float(delta[self.interior].max()))
                if self.land.any():
                    record['map_land_max_abs']=max(record['map_land_max_abs'],float(delta[self.land].max()))
                    record['map_land_mean_abs']+=float(delta[self.land].mean())/self.steps
            self.previous[key][season]=field
        self.seasons+=1
        if season==self.steps-1 and year:
            self.comparisons.append(dict(year=year+1,previous_year=year,fields=self.current,
                domain_repeats=all(self.current[key]['domain_max_abs']<=LIMITS[key] for key in LIMITS),
                map_land_repeats=all(self.current[key]['map_land_max_abs']<=LIMITS[key] for key in LIMITS) if self.land.any() else None))

    def report(self):
        return dict(complete_years=self.seasons//self.steps,checked=bool(self.comparisons),
            limits=LIMITS.copy(),units=UNITS.copy(),comparisons=list(self.comparisons),
            domain_repeats=bool(self.comparisons and self.comparisons[-1]['domain_repeats']))
