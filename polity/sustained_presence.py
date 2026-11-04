"""Conditional cereal provisioning, separate from political ownership.

Rural meals precede collection. Only repeating-year overflow may leave a cell;
the legacy capacity denominator (with implicit losses/draft allowance) is never
used. Fixed collection paths and freight limits are supplied, not institutions.
"""
from dataclasses import dataclass
import numpy as np
from harvest.food_stocks import periodic_food_year


@dataclass
class RuralFood:
    harvest: np.ndarray
    need: np.ndarray
    overflow: np.ndarray
    year: object


def rural_cereal(annual, boundaries, *, demand_fraction=.6, reserve_days=180.,
                 loss_fraction_year=.05, calendar='first', year_days=365.):
    annual=np.asarray(annual,float);bits=np.asarray(boundaries)
    if annual.shape!=bits.shape or bits.dtype.kind not in 'ui' or np.any(bits>4095):
        raise ValueError('Annual energy and twelve-bin unsigned calendars required')
    if not np.isfinite(annual).all() or np.any(annual<0) or np.any((annual>0)&(bits==0)):
        raise ValueError('Positive cereal energy requires an explicit calendar')
    if not np.isfinite([demand_fraction,reserve_days,year_days]).all() or not 0<=demand_fraction<=1 or reserve_days<0 or year_days<=0:
        raise ValueError('Fractional rural demand and nonnegative reserve required')
    if calendar not in ('first','last'):raise ValueError('Choose one calendar, never average alternative harvests')
    options=np.stack([((bits>>m)&1)>0 for m in range(12)])
    chosen=options.argmax(0) if calendar=='first' else 11-options[::-1].argmax(0)
    supply=np.zeros((12,)+annual.shape)
    np.put_along_axis(supply,chosen[None],annual[None],axis=0)
    need=np.broadcast_to(annual*demand_fraction/12,supply.shape)
    year=periodic_food_year(supply,need,annual*demand_fraction*reserve_days/year_days,
        loss_fraction_year=loss_fraction_year,step_days=year_days/12,record=True)
    available=year.stock_path[:-1]+supply
    overflow=np.maximum(available-need-annual*demand_fraction*reserve_days/year_days,0)
    np.testing.assert_allclose(overflow.sum(0),year.overflow,rtol=1e-10,atol=1e-5)
    return RuralFood(supply,need,overflow,year)


def fixed_path_days(graph, parents, order):
    """Both directions along ONE fixed parent forest, not two nearest sites.

    `order` lists non-root nodes after their parents. Non-listed nodes retain
    infinity; roots (parent == self) start at zero. Paths may have directional
    weather costs. Missing edges fail rather than becoming free travel.
    """
    parents=np.asarray(parents);order=np.asarray(order)
    if parents.shape!=(graph.shape[0],) or parents.dtype.kind not in 'iu' or order.dtype.kind not in 'iu':raise ValueError('Integer parent forest required')
    roots=np.flatnonzero(parents==np.arange(len(parents)))
    incoming=np.full(len(parents),np.inf);outgoing=incoming.copy();incoming[roots]=0;outgoing[roots]=0
    if np.any((order<0)|(order>=len(parents))) or np.any((parents[order]<0)|(parents[order]>=len(parents))):raise ValueError('Invalid forest nodes')
    forward=np.asarray(graph[order,parents[order]]).ravel()
    back=np.asarray(graph[parents[order],order]).ravel()
    if np.any(forward<=0) or np.any(back<=0):raise ValueError('Collection path edge missing')
    for i,node in enumerate(order):
        parent=parents[node]
        if not np.isfinite(incoming[parent]):raise ValueError('Forest must be acyclic and parent-ordered')
        incoming[node]=incoming[parent]+forward[i];outgoing[node]=outgoing[parent]+back[i]
    return outgoing,incoming


def collected_supply(overflow, catchments, accessible, sites, *, collection_fraction=.1,
                     freight_capacity=1., retention=.95, delay_bins=1):
    """Each cell goes to at most one site; inaccessible/uncollected food stays unused.

    `freight_capacity` is per-site per-bin departing energy, not a walking
    speed converted into tonnage. No origin depot storage or alternative trade.
    """
    food=np.asarray(overflow,float);ids=np.asarray(catchments);access=np.asarray(accessible,bool)
    if food.shape!=access.shape or food.shape[0]!=12 or food.shape[1:]!=ids.shape or ids.dtype.kind not in 'iu':raise ValueError('Twelve food/access fields and integer catchments required')
    if not np.isfinite(food).all() or np.any(food<0) or np.any((ids<0)|(ids>sites)):raise ValueError('Invalid food or catchments')
    if not np.isfinite([collection_fraction,retention]).all() or not 0<=collection_fraction<=1 or not 0<=retention<=1:raise ValueError('Fractional collection and retention required')
    if isinstance(delay_bins,bool) or not isinstance(delay_bins,(int,np.integer)) or not 0<=delay_bins<12:raise ValueError('Integer delay below a year required')
    cap=np.broadcast_to(np.asarray(freight_capacity,float),(12,sites))
    if not np.isfinite(cap).all() or np.any(cap<0):raise ValueError('Finite freight capacities required')
    eligible=np.stack([np.bincount(ids.ravel(),weights=(f*a*collection_fraction).ravel(),minlength=sites+1)[1:] for f,a in zip(food,access)])
    departure=np.minimum(eligible,cap);arrivals=np.roll(departure,delay_bins,axis=0)*retention
    return dict(eligible=eligible,departures=departure,arrivals=arrivals,
        transport_loss=float(departure.sum()*(1-retention)),
        uncollected=float(food.sum()-departure.sum()))


def site_food(arrivals, *, people=100., kcal_day=2500., reserve_days=90., loss_fraction_year=.05,year_days=365.):
    if not np.isfinite([people,kcal_day,reserve_days,year_days]).all() or people<=0 or kcal_day<=0 or reserve_days<0 or year_days<=0:raise ValueError('Positive group and ration; nonnegative reserve required')
    arrivals=np.asarray(arrivals,float)
    if arrivals.ndim!=2 or arrivals.shape[0]!=12:raise ValueError('Twelve bins by site required')
    need=np.full_like(arrivals,people*kcal_day*year_days/12)
    year=periodic_food_year(arrivals,need,people*kcal_day*reserve_days,
        loss_fraction_year=loss_fraction_year,step_days=year_days/12,record=True)
    return year,1-year.unmet_path/need


def stored_collection(overflow,catchments,accessible,sites,*,collection_fraction=.1,
                      freight_capacity=1.,retention=.95,delay_bins=1,
                      store_days=365.,loss_fraction_year=.05,dispatch_open=None,year_days=365.):
    """On-farm export stores keep grain at its own origin until collection.

    Each site's prescribed freight slots are shared between its fixed cells
    in proportion to their annual exportable supply. No optimization or extra
    freight appears when another cell cannot dispatch. Rural protected food
    is never in this second inventory. This allocation is a scenario rule.
    """
    food=np.asarray(overflow,float);ids=np.asarray(catchments);access=np.asarray(accessible,bool)
    # Shared validation, including capacities/fractions and directed delay.
    checked=collected_supply(food,ids,access,sites,collection_fraction=collection_fraction,
        freight_capacity=freight_capacity,retention=retention,delay_bins=delay_bins)
    if not np.isfinite([store_days,year_days]).all() or store_days<0 or year_days<=0:raise ValueError('Nonnegative export store and positive year required')
    cap=np.broadcast_to(np.asarray(freight_capacity,float),(12,sites))
    opened=np.ones((12,sites),bool) if dispatch_open is None else np.broadcast_to(np.asarray(dispatch_open,bool),(12,sites))
    included=ids>0;production=food*collection_fraction*included
    annual=production.sum(0)
    total=np.bincount(ids.ravel(),weights=annual.ravel(),minlength=sites+1)
    fraction=np.divide(annual,total[ids],out=np.zeros_like(annual),where=total[ids]>0)
    capacity=np.c_[np.zeros(12),cap];allowed=np.c_[np.zeros(12,bool),opened]
    # Do not request above annual supply/12. The explicit decay therefore
    # creates a small export deficit instead of free replacement grain.
    need=np.minimum(capacity[:,ids]*fraction,annual/12)*access*allowed[:,ids]
    year=periodic_food_year(production,need,annual*store_days/year_days,
        loss_fraction_year=loss_fraction_year,step_days=year_days/12,record=True)
    taken=need-year.unmet_path
    departures=np.stack([np.bincount(ids.ravel(),weights=t.ravel(),minlength=sites+1)[1:] for t in taken])
    if np.any(departures>cap+1e-7*np.maximum(cap,1)):raise RuntimeError('Export stores exceeded supplied freight capacity')
    return dict(departures=departures,arrivals=np.roll(departures,delay_bins,axis=0)*retention,
        transport_loss=float(departures.sum()*(1-retention)),collection_storage_loss=float(year.spoiled.sum()),
        uncollected=float(food.sum()-production.sum()+year.overflow.sum()),
        max_collection_ledger_residual=float(np.max(np.abs(year.ledger_residual))))
