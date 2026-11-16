"""Restore the wind period named by the annual protocol; isolated exact replay."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

import h5py
import numpy as np
from scipy.io import netcdf_file
import urban_seasonal_transfer_controls as C

ROOT=C.ROOT;OUT=C.OUT/'wind_1981';PLAN=C.PLAN.parent/'seasonal_transfer_annual_diagnosis.json'
CACHE=ROOT/'data/cache/ncep_ltm'


def arrays(path,var):
    if h5py.is_hdf5(path):
        with h5py.File(path) as f:
            a,lat,lon=[np.asarray(f[k],float) for k in [var,'lat','lon']]
            period=str(f['time'].attrs.get('climo_period'))
    else:
        with netcdf_file(path,mmap=False) as f:
            a,lat,lon=[np.array(f.variables[k].data,dtype=float) for k in [var,'lat','lon']]
            period=str(getattr(f.variables['time'],'climo_period',None))
    assert a.shape==(12,73,144) and np.isfinite(a).all()
    np.testing.assert_array_equal(lat,90-2.5*np.arange(73));np.testing.assert_array_equal(lon,2.5*np.arange(144))
    assert '1981/01/01 - 2010/12/31' in period
    return a,lat,lon,period


def recover(var):
    url=f'https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface/{var}.sig995.mon.1981-2010.ltm.nc'
    path=CACHE/f'original_period_{var}.nc'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as response:data=response.read()
        partial=path.with_suffix('.part');partial.write_bytes(data);arrays(partial,var);partial.replace(path)
    a,lat,lon,period=arrays(path,var)
    fallback,*_=C.G.S.E._ncep(var)
    return var,dict(path=str(path.relative_to(ROOT)),url=url,sha256=C.sha(path),period=period,
                    different_from_fallback_values=int((a!=fallback).sum()),
                    maximum_absolute_difference=float(abs(a-fallback).max()))


def main(stage):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    OUT.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=dict(pool.map(recover,['uwnd','vwnd','wspd']))
    receipt=dict(status='named_1981_2010_annual_protocol_source_recovered_not_yet_qualified',
                 plan_sha256=C.sha(PLAN),producer_sha256=C.sha(Path(__file__)),sources=records,
                 interpretation='Exactly the period named in the annual protocol. No period fitting or blended winds. Native arrays read verbatim with format-only HDF5/NetCDF3 handling; canonical network/yield/population producers unchanged.',
                 prior_failure_sha256=C.sha(C.OUT/'greek/failure.json'),adopt=False)
    (OUT/'wind_restoration.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def recovered(var):
        source=records[var];path=ROOT/source['path'];assert C.sha(path)==source['sha256']
        return arrays(path,var)[:3]
    C.G.S.E._ncep=recovered;C.OUT=OUT
    C.main(stage)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['greek','low']);a=p.parse_args();main(a.stage)
