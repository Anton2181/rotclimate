"""Bounded source/runtime identity checks after the preserved annual mismatch."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request

import h5py
import numpy as np
import scipy
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import urban_seasonal_transfer_controls as C
from rotclimate.earth import _wc

OUT=C.OUT;PLAN=C.PLAN.parent/'seasonal_transfer_annual_diagnosis.json'


def native(var):
    url=f'https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface/{var}.sig995.mon.ltm.nc'
    path=ROOT/'data/cache/ncep_ltm'/f'native_{var}.nc'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as response:data=response.read()
        partial=path.with_suffix('.part');partial.write_bytes(data)
        with h5py.File(partial) as f:assert f[var].shape==(12,73,144)
        partial.replace(path)
    with h5py.File(path) as f:
        a=np.array(f[var],float);lat=np.array(f['lat']);lon=np.array(f['lon'])
        period=str(f['time'].attrs.get('climo_period'));scale=str(f[var].attrs.get('scale_factor'))
    fallback,la,lo=C.G.S.E._ncep(var)
    np.testing.assert_array_equal(lat,la);np.testing.assert_array_equal(lon,lo)
    return dict(variable=var,path=str(path.relative_to(ROOT)),url=url,sha256=C.sha(path),
                period=period,scale_factor=scale,exact_array_equal=bool(np.array_equal(a,fallback)),
                different_values=int((a!=fallback).sum()),max_absolute_array_difference=float(abs(a-fallback).max()))


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    failure=json.loads((OUT/'greek/failure.json').read_text());assert failure['status']=='preserved_failed_annual_control'
    for name,digest in failure['sources_sha256'].items():assert C.sha(ROOT/name)==digest,name
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:natives=list(pool.map(native,['uwnd','vwnd','wspd']))
    E,N,T,P=C.G.S.E,C.G.S.N,C.G.S.T,C.G.S.P
    u,la,lo=E._ncep('uwnd');v,*_=E._ncep('vwnd');wind,*_=E._ncep('wspd')
    sigma=np.sqrt(np.maximum(wind**2-u**2-v**2,0))
    lat,lon=np.meshgrid(la,lo,indexing='ij')
    land=np.isfinite(E.sample_global(_wc('elev'),lat,np.where(lon>180,lon-360,lon)))
    table=np.array([[np.median(sigma[m][~land&(lat>=b)&(lat<b+5)]) for m in range(12)] for b in range(15,50,5)])
    reference=json.loads((ROOT/'calibration/polity_20261025/sea.json').read_text())
    np.testing.assert_array_equal(table,reference['F6_sigma_table']['sigma'])
    g=dict(np.load(OUT/'prepared/greek_transport_world.npz'));a=dict(np.load(OUT/'prepared/greek_control.npz'))
    med=(~g['land'])&(g['lon']>-5.6)&(g['lon']<36.5)&(g['lat']>30)&(g['lat']<46.5)&~((g['lon']>26.5)&(g['lat']>40.8))
    for key in ['wind','sigma']:
        np.testing.assert_array_equal([v[med].mean() for v in g[key]],reference['F5_closure']['med_'+key])
    pool=dict(np.load(C.G.S.PILOT.POOL));g.update(cell_km=float(pool['cell_km']),lat0=C.G.S.PILOT.WINDOW['lat0'],lon0=C.G.S.PILOT.WINDOW['lon0'])
    from rotclimate import biomes
    g['biome']=biomes.classify(g['tavg'].mean(0),g['prec'].sum(0),g['land'])
    P.apply_sea();world=P.world_of(g,pool['road']);st=N.statics(world);cl=N.climate(world,st)
    width=g['land'].shape[1];places=[(int(n//width),int(n%width)) for n in a['nodes']]
    ports=C.G.S.X.ports_of(places,st['water']);near=ndi.binary_dilation(st['basin']>0,iterations=1)
    net=T.cost_network(world,st,cl,0,ports,[p for p in places if near[p]])
    nodes,costs=next(T.costs_from(net,a['nodes'],limit=540,batch=48))
    projected=C.CityColumns(costs,a['nodes'])[:,a['nodes']]
    np.testing.assert_array_equal(projected,costs[:,a['nodes']])
    np.testing.assert_array_equal(projected.astype(np.float32),a['between'][0,:len(nodes)])
    rejected=False
    try:C.CityColumns(costs,a['nodes'])[:,a['nodes'][:1]]
    except ValueError:rejected=True
    assert rejected
    dependencies=['polity/control.py','polity/network.py','polity/earth.py','polity/trade.py','polity/seasons.py','polity/transport.py',
                  'rotclimate/earth.py','rotclimate/biomes.py','harvest/field_support.py','harvest/work_maps.py',
                  'scripts/settlement_supply_calibration.py','scripts/settlement_supply_earth.py','scripts/greek_walls.py']
    changed=[]
    for path in dependencies:
        old=subprocess.check_output(['git','show','ea2c77524:'+path],cwd=ROOT)
        if hashlib.sha256(old).hexdigest()!=C.sha(ROOT/path):changed.append(path)
    receipt=dict(status='bounded_identity_diagnosis_annual_mismatch_unresolved',producer_sha256=C.sha(Path(__file__)),
                 plan_sha256=C.sha(PLAN),failure_sha256=C.sha(OUT/'greek/failure.json'),
                 native_comparisons=natives,F6_scalar_values_exact=84,mediterranean_monthly_means_exact=24,
                 projected_batch_values_exact=int(projected.size),wrong_projection_rejected=True,
                 changed_dependencies_since_original_result=changed,
                 dependency_note='Only optional forest argument/branch and runtime harvest path override changed. No forest field is present in the Earth world. No direct-effect source change identified.',
                 environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
                 isolated_cache_paths=True,seasonal_trial_ready=False,new_fit=False,adopt=False)
    (OUT/'identity_diagnosis.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
