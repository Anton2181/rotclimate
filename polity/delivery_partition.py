"""Account for packed AND missing cargo without dropping an incomplete source."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CargoPartition:
    packed_cargo: np.ndarray
    missing_origin: np.ndarray
    missing_serial: np.ndarray
    missing_cargo: np.ndarray


def partition_trip_cargo(departures,counts,owner,origin,serial,site,*,provider_count,load=120000.):
    """Partition original unretained cargo by exact origin/trip serial IDs."""
    departures,counts,owner,origin,serial,site=map(np.asarray,(departures,counts,owner,origin,serial,site))
    if departures.ndim!=1 or counts.shape!=departures.shape or owner.shape!=departures.shape or any(a.ndim!=1 or a.shape!=origin.shape for a in (origin,serial,site)):
        raise ValueError('Invalid cargo/record shapes')
    if any(a.dtype.kind not in 'iu' for a in (counts,owner,origin,serial,site)) or isinstance(provider_count,bool) or not isinstance(provider_count,int) or provider_count<0:
        raise ValueError('Trip counts,IDs and provider count must be integers')
    if not np.isfinite(load) or load<=0 or not np.isfinite(departures).all() or (departures<0).any():raise ValueError('Invalid planned cargo or load')
    if (counts<0).any() or not np.array_equal(counts,np.ceil(departures/load)):
        raise ValueError('Planned serial count must exactly cover original cargo')
    if (owner<0).any() or (owner>=provider_count).any() or (origin<0).any() or (origin>=len(departures)).any() or (serial<0).any() or (site<0).any() or (site>=provider_count).any():
        raise ValueError('Out-of-range original trip/provider IDs')
    if not np.array_equal(site,owner[origin]) or (serial>=counts[origin]).any():raise ValueError('Wrong original owner or serial')
    offsets=np.cumsum(counts,dtype='i8')-counts;identities=offsets[origin]+serial
    if len(np.unique(identities))!=len(identities):raise ValueError('Duplicate packed original trip serial')
    total=int(counts.sum());packed=np.zeros(total,bool);packed[identities]=True;missing=np.flatnonzero(~packed)
    missing_origin=np.searchsorted(np.cumsum(counts,dtype='i8'),missing,side='right');missing_serial=missing-offsets[missing_origin]
    packed_cargo=np.minimum(load,departures[origin]-load*serial);missing_cargo=np.minimum(load,departures[missing_origin]-load*missing_serial)
    if (packed_cargo<=0).any() or (missing_cargo<=0).any():raise ValueError('Recorded serial has no cargo')
    combined=np.bincount(origin,weights=packed_cargo,minlength=len(departures))+np.bincount(missing_origin,weights=missing_cargo,minlength=len(departures))
    if not np.allclose(combined,departures,rtol=1e-12,atol=1e-7):raise ValueError('Packed plus missing cargo does not match original departures')
    return CargoPartition(packed_cargo,missing_origin.astype('i8'),missing_serial.astype('i8'),missing_cargo)


def lagged_return_times(end_hours,month,*,year_days=365.,walking_hours_day=7.):
    """Return phase inside the original ONE-bin-lagged destination bin."""
    ends=np.asarray(end_hours,float)
    if ends.ndim!=1 or isinstance(month,bool) or not isinstance(month,int) or not 0<=month<12 or not np.isfinite([year_days,walking_hours_day]).all() or year_days<=0 or walking_hours_day<=0:
        raise ValueError('Invalid lagged clock units')
    if not np.isfinite(ends).all() or (ends<0).any() or (ends>=year_days*walking_hours_day/12).any():raise ValueError('Return lies outside its declared arrival bin')
    return np.mod((month+1)*year_days/12+ends/walking_hours_day,year_days)
