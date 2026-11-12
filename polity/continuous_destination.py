"""Versioned resident feedback with continuous destination-bin inventories."""
import numpy as np

from harvest.continuous_food_stocks import periodic_continuous_food_year
from .settlement_seeded_dispatch import ThresholdSeededDispatchFeedback


def continuous_food_ceiling(arrivals,*,kcal_day=2500.,store_days=90.,loss_fraction_year=.05,year_days=365.):
    """Display ceiling using the same normalized 42-step search as its parent.

    Per-person physical stores scale with trial residents here. This differs
    from the separate fixed-physical-storage meal-headroom diagnostic.
    """
    food=np.asarray(arrivals,float)
    if food.ndim!=2 or food.shape[0]!=12 or not np.isfinite(food).all() or (food<0).any():raise ValueError('Twelve finite nonnegative destination bins required')
    if not np.isfinite([kcal_day,store_days,loss_fraction_year,year_days]).all() or kcal_day<=0 or year_days<=0 or store_days<0 or not 0<=loss_fraction_year<1:raise ValueError('Invalid food ceiling units')
    annual=food.sum(axis=0)
    if not np.isfinite(annual).all():raise ValueError('Annual supply must remain finite')
    high=annual/(kcal_day*year_days);low=np.zeros_like(high);positive=high>0
    if positive.any():
        selected=food[:,positive]/kcal_day;lo=low[positive];hi=high[positive];need=np.full_like(selected,year_days/12)
        for _ in range(42):
            mid=(lo+hi)/2
            result=periodic_continuous_food_year(selected/mid,need,store_days,loss_fraction_year=loss_fraction_year,step_days=year_days/12)
            feasible=result.unmet<=1e-8
            lo=np.where(feasible,mid,lo);hi=np.where(feasible,hi,mid)
        low[positive]=lo*(1-1e-8)
    return low


class ContinuousDestinationFeedback(ThresholdSeededDispatchFeedback):
    def _food(self,arrivals,target,*,record):
        return periodic_continuous_food_year(arrivals,np.broadcast_to(target*self.kcal_day*self.year_days/12,arrivals.shape),
            target*self.kcal_day*self.destination_store_days,loss_fraction_year=self.loss_fraction_year,step_days=self.year_days/12,record=record)

    def solve(self,*,scan_intervals=64,refinements=24):
        result=super().solve(scan_intervals=scan_intervals,refinements=refinements)
        result['plan'].food_ceiling_people=continuous_food_ceiling(result['flow']['arrivals'],kcal_day=self.kcal_day,
            store_days=self.destination_store_days,loss_fraction_year=self.loss_fraction_year,year_days=self.year_days)
        result['plan'].food_year=result['town_food']
        result['destination_inventory_convention']='Bin-start supply and immediate capacity clip,continuous meals and exponential stored loss;source food stays monthly'
        result['search_scope']+=' Continuous destination-bin food only;collector-return food still requires a new-calendar audit.'
        return result
