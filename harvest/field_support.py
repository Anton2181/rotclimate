"""Listed cereal field work constrains complete cropped hectares and net grain.

Annual and reaping budgets refer to the SAME workforce. Reaping is a subset
of total work, not a second labour charge. These are partial field-task tests,
not total household or draft-animal budgets.
"""
from dataclasses import dataclass
import numpy as np
from harvest.food_stocks import periodic_food_year


@dataclass
class FieldSupport:
    retained: np.ndarray
    produced_kcal: np.ndarray
    rural_reference_people: np.ndarray
    workers: np.ndarray
    annual_hours_used: np.ndarray
    reaping_hours_used: np.ndarray
    annual_hours_available: np.ndarray
    reaping_hours_available: np.ndarray


def field_support(annual_kcal,listed_hours_per_million,reaping_hours_per_million,*,
                  rural_need_kcal,worker_fraction=.4,hours_worker_year=600.,harvest_days=30.,
                  hours_worker_day=8.,ration_kcal_day=2500.,year_days=365.):
    """Retain complete annual crop activities under two simultaneous limits.

    Rural meals are an explicit input, independent of realized production.
    Workers are a declared share of that reference food-supported group, not
    inferred actual residents. Non-reaping tasks have no new climate deadlines;
    draft services, processing, care and other household tasks remain omitted.
    Farm hours are already allocated, not otherwise-free household time.
    """
    energy,hours,reap,need=np.broadcast_arrays(*[np.asarray(v,float) for v in [annual_kcal,listed_hours_per_million,reaping_hours_per_million,rural_need_kcal]])
    scalars=[worker_fraction,hours_worker_year,harvest_days,hours_worker_day,ration_kcal_day,year_days]
    if not np.isfinite(scalars).all() or not 0<=worker_fraction<=1 or min(hours_worker_year,harvest_days,hours_worker_day)<0 or min(ration_kcal_day,year_days)<=0 or harvest_days>year_days or hours_worker_year>hours_worker_day*year_days:raise ValueError('Finite compatible workforce and work budgets required')
    if not all(np.isfinite(v).all() for v in [energy,hours,reap,need]) or np.any(energy<0) or np.any(need<0) or np.any(hours<0) or np.any(reap<0) or np.any(reap>hours) or np.any((energy>0)&((hours<=0)|(reap<=0))):raise ValueError('Positive production requires complete finite listed and reaping work')
    people=need/(ration_kcal_day*year_days);workers=people*worker_fraction
    annual=workers*hours_worker_year;peak=np.minimum(annual,workers*hours_worker_day*harvest_days)
    total_req=energy*hours/1e6;reap_req=energy*reap/1e6
    total_ratio=np.divide(annual,total_req,out=np.ones_like(energy),where=total_req>0)
    reap_ratio=np.divide(peak,reap_req,out=np.ones_like(energy),where=reap_req>0)
    retained=np.minimum(1,np.minimum(total_ratio,reap_ratio));retained=np.where(energy>0,retained,0.)
    return FieldSupport(retained,energy*retained,people,workers,total_req*retained,reap_req*retained,annual,peak)


@dataclass
class FixedRuralFood:
    harvest: np.ndarray
    year: object
    need: np.ndarray
    reserve_days: float
    year_days: float

    @property
    def exportable(self):
        protected=self.year.unmet<=1e-8*np.maximum(self.year.needed,1)
        capacity=self.year.needed*self.reserve_days/self.year_days
        available=self.year.stock_path[:-1]+self.harvest
        overflow=np.maximum(available-self.need-capacity,0.)
        return overflow*protected


def fixed_rural_food(produced_kcal,boundaries,rural_need_kcal,*,reserve_days=365.,loss_fraction_year=.05,year_days=365.):
    """A harvest reduction cannot automatically reduce the rural food claim."""
    energy,bits,need=np.asarray(produced_kcal,float),np.asarray(boundaries),np.asarray(rural_need_kcal,float)
    if energy.shape!=bits.shape or energy.shape!=need.shape or bits.dtype.kind not in 'ui' or np.any(bits>4095) or not np.isfinite(energy).all() or not np.isfinite(need).all() or np.any(energy<0) or np.any(need<0) or np.any((energy>0)&(bits==0)):raise ValueError('Explicit calendars, production and fixed rural food needs required')
    if not np.isfinite([reserve_days,year_days]).all() or reserve_days<0 or year_days<=0:raise ValueError('Nonnegative rural store and positive year required')
    options=np.stack([((bits>>m)&1)>0 for m in range(12)]);chosen=options.argmax(0)
    supply=np.zeros((12,)+energy.shape);np.put_along_axis(supply,chosen[None],energy[None],axis=0)
    monthly=np.broadcast_to(need/12,supply.shape)
    year=periodic_food_year(supply,monthly,need*reserve_days/year_days,loss_fraction_year=loss_fraction_year,step_days=year_days/12,record=True)
    return FixedRuralFood(supply,year,monthly,reserve_days,year_days)
