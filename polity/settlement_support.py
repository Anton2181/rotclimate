"""Seasonal food → settlement allocation → institutional source availability.

The allocation is a declared scenario, not an observed population or proof of
sovereignty. One finite food pool supports civilian and institutional residents;
institutional availability changes sources, never a travel-strength multiplier.
"""
from dataclasses import dataclass
import numpy as np
from harvest.food_stocks import periodic_food_year


@dataclass
class SettlementPlan:
    food_ceiling_people: np.ndarray
    civilian_people: np.ndarray
    institutional_people: np.ndarray
    total_people: np.ndarray
    institutional_active: np.ndarray
    community_viable: np.ndarray
    food_year: object


def permanent_food_ceiling(arrivals,*,kcal_day=2500.,store_days=90.,loss_fraction_year=.05,year_days=365.):
    """Largest constant resident group meeting EVERY bin in a repeating year.

    Storage scales in demand-days per resident. Dividing energy by resident
    ration makes feasibility monotone: more people reduce supply per person,
    with the same reserve capacity per person. Annual energy is only a search
    upper bound, not the seasonal answer. The returned ceiling errs downward.
    """
    food=np.asarray(arrivals,float)
    if food.ndim!=2 or food.shape[0]!=12 or not np.isfinite(food).all() or np.any(food<0):raise ValueError('Twelve finite nonnegative arrival bins by settlement required')
    if not np.isfinite([kcal_day,store_days,year_days]).all() or min(kcal_day,year_days)<=0 or store_days<0:raise ValueError('Positive ration/year and nonnegative stores required')
    high=food.sum(0)/(kcal_day*year_days);low=np.zeros_like(high);positive=high>0
    if positive.any():
        selected=food[:,positive]/kcal_day;lo=low[positive];hi=high[positive]
        need=np.full_like(selected,year_days/12)
        for _ in range(42):
            mid=(lo+hi)/2
            year=periodic_food_year(selected/mid,need,store_days,loss_fraction_year=loss_fraction_year,step_days=year_days/12)
            feasible=year.unmet<=1e-8
            lo=np.where(feasible,mid,lo);hi=np.where(feasible,hi,mid)
        low[positive]=lo*(1-1e-8)
    return low


def allocate_settlement(arrivals,civilian_request,affiliated,*,institutional_request=100.,minimum_community=50.,
                        kcal_day=2500.,store_days=90.,loss_fraction_year=.05,year_days=365.):
    """Reserve a declared cohort only where a civilian community can coexist.

    The institutional cohort receives first reservation if the combined
    minimum is feasible. Remaining food caps the requested civilian group.
    Otherwise the settlement can persist without an assigned institution.
    Unresolved affiliation never becomes a new actor. Unknown real populations
    and rights remain outside this scenario. Staff are eaten-for ONCE, inside
    the total resident food ledger rather than in an extra support overlay.
    """
    food=np.asarray(arrivals,float);request=np.asarray(civilian_request,float);affiliated=np.asarray(affiliated,bool)
    if food.ndim!=2 or request.shape!=(food.shape[1],) or affiliated.shape!=request.shape:raise ValueError('One resident request and affiliation flag per settlement required')
    if not np.isfinite(request).all() or np.any(request<0) or not np.isfinite([institutional_request,minimum_community]).all() or institutional_request<=0 or minimum_community<0:raise ValueError('Nonnegative civilian budgets and positive institutional request required')
    ceiling=permanent_food_ceiling(food,kcal_day=kcal_day,store_days=store_days,loss_fraction_year=loss_fraction_year,year_days=year_days)
    active=affiliated&(request>=minimum_community)&(ceiling>=institutional_request+minimum_community)
    staff=np.where(active,institutional_request,0.)
    civilian=np.minimum(request,np.maximum(ceiling-staff,0));total=civilian+staff
    need=np.broadcast_to(total*kcal_day*year_days/12,food.shape)
    year=periodic_food_year(food,need,total*kcal_day*store_days,loss_fraction_year=loss_fraction_year,step_days=year_days/12,record=True)
    if np.any(year.unmet>1e-6*np.maximum(1,year.needed)):raise RuntimeError('Allocated settlement exceeds its repeating seasonal food support')
    if np.any(total>ceiling+1e-7) or np.any(civilian>request+1e-7):raise RuntimeError('Population/food allocation failed')
    return SettlementPlan(ceiling,civilian,staff,total,active,civilian>=minimum_community,year)


def paired_reach(outward,inward,*,leg_days=2.,ration_days=4.):
    """Both legs use the same staffed origin; round-trip meals must fit its pack."""
    out,back=np.broadcast_arrays(np.asarray(outward,float),np.asarray(inward,float))
    if np.isnan(out).any() or np.isnan(back).any() or np.any(out<0) or np.any(back<0) or not np.isfinite([leg_days,ration_days]).all() or min(leg_days,ration_days)<=0:raise ValueError('Nonnegative travel and positive finite patrol budgets required')
    return (out<=leg_days)&(back<=leg_days)&(out+back<=ration_days)
