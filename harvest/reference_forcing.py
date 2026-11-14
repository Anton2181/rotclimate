"""Shared reference-weather algebra with explicit world radiation and bin totals.

No Earth calendar, solar geometry, humidity or wind is invented by this adapter.
The caller supplies weather and extraterrestrial radiation with declared units.
"""
import numpy as np

from .reference_eto import penman_monteith,pressure_at_elevation,saturation_vapour_pressure


def daily_from_radiation(tmean_c,tmin_c,tmax_c,ea_kpa,wind2m_ms,pressure_kpa,
                         solar_mj_m2_day,ra_mj_m2_day,elevation_m):
    values=np.broadcast_arrays(*[np.asarray(v,dtype=float) for v in [tmean_c,tmin_c,tmax_c,ea_kpa,wind2m_ms,pressure_kpa,solar_mj_m2_day,ra_mj_m2_day,elevation_m]])
    if not all(np.isfinite(v).all() for v in values):raise ValueError('Every reference-weather input must be finite')
    t,lo,hi,ea,u,p,rs,ra,z=values
    if np.any(lo>t) or np.any(t>hi) or np.any(rs<0) or np.any(ra<=0) or np.any(ea<0):
        raise ValueError('Ordered temperatures, nonnegative solar/vapour and positive supplied extraterrestrial radiation required')
    pressure_at_elevation(z)
    rso=(.75+2e-5*z)*ra;ratio=rs/rso;used=np.clip(ratio,.3,1.)
    rns=.77*rs
    rnl=4.903e-9*((hi+273.16)**4+(lo+273.16)**4)/2*(.34-.14*np.sqrt(ea))*(1.35*used-.35)
    rn=rns-rnl;es=(saturation_vapour_pressure(lo)+saturation_vapour_pressure(hi))/2
    pm=penman_monteith(t,es,ea,u,p,rn)
    har=.0023*np.maximum(t+17.8,0)*np.sqrt(hi-lo)*.408*ra
    return dict(ra_mj_m2_day=ra,rso_mj_m2_day=rso,rs_ratio_raw=ratio,rs_ratio_used=used,rns_mj_m2_day=rns,rnl_mj_m2_day=rnl,rn_mj_m2_day=rn,**pm,hargreaves_mm_day=har)


def mean_year_bin_totals(year_index,bin_index,daily_amounts,*,bin_count=12):
    """Average complete per-year bin sums; never average rates as bin amounts.

    The caller qualifies calendar completeness and supplies each daily amount.
    Every labelled year must contain every bin, including explicitly zero bins.
    """
    year=np.asarray(year_index);bins=np.asarray(bin_index);amount=np.asarray(daily_amounts,float)
    if isinstance(bin_count,bool) or not isinstance(bin_count,int) or bin_count<1:
        raise ValueError('Positive integer bin count required')
    if year.ndim!=1 or bins.shape!=year.shape or year.dtype.kind not in 'iu' or bins.dtype.kind not in 'iu' or not year.size:
        raise ValueError('Nonempty integer year/bin labels of equal length required')
    if amount.ndim<1 or amount.shape[0]!=len(year) or not np.isfinite(amount).all() or np.any(amount<0) or np.any(bins<0) or np.any(bins>=bin_count):
        raise ValueError('Finite nonnegative amounts matching valid bin labels required')
    result=np.zeros((bin_count,)+amount.shape[1:])
    years=np.unique(year)
    for value in years:
        selected=year==value
        if not np.array_equal(np.unique(bins[selected]),np.arange(bin_count)):
            raise ValueError('Each supplied year must contain all bins')
        totals=np.zeros_like(result);np.add.at(totals,bins[selected],amount[selected]);result+=totals
    return result/len(years)


def one_degree_cells(latitude_deg,longitude_deg):
    """Half-open sampling tiles; source resolution and interpolation are separate."""
    lat,lon=np.broadcast_arrays(np.asarray(latitude_deg,float),np.asarray(longitude_deg,float))
    if not np.isfinite(lat).all() or not np.isfinite(lon).all() or np.any((lat<-90)|(lat>=90)) or np.any((lon<-180)|(lon>=180)):
        raise ValueError('Coordinates in half-open latitude[-90,90), longitude[-180,180) required')
    return np.floor(lat).astype(int),np.floor(lon).astype(int)
