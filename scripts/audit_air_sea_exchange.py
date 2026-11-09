"""Record actual surface relaxation on spent regions; no physics fit/adoption.

python -I scripts/audit_air_sea_exchange.py --workers 3 --out output/air_sea_audit_20261109
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from multiprocessing import Pool
import os
from pathlib import Path
import sys
import urllib.request

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
import numpy as np
from scipy import ndimage as ndi
from rotclimate import earth, joint
from rotclimate.config import Params
from rotclimate.koppen import monthly_stats, monthly_weights
from rotclimate.model import ClimateModel
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json

DAY = 86400.
PLAN = ROOT/'calibration/air_sea_audit_20261109/plan.json'
REFERENCE = ROOT/'data/cache/air_sea_audit_20261109'


def slab_flux_wm2(rate_s, contrast_c, depth_m):
    """Conditional slab sensible flux, not an observed or COARE flux."""
    return 1.225 * 1004. * depth_m * np.asarray(rate_s) * np.asarray(contrast_c)


def equivalent_depth_m(rate_s, speed_ms, coefficient=.001):
    rate, speed = np.broadcast_arrays(np.asarray(rate_s, float), np.asarray(speed_ms, float))
    if np.any(rate <= 0) or np.any(speed < 0):
        raise ValueError('Positive rate and nonnegative wind required')
    return coefficient * speed / rate


def prepare_reference():
    REFERENCE.mkdir(exist_ok=True, parents=True)
    archive = REFERENCE/'sigma995.npz'; receipt = REFERENCE/'reference.json'
    if archive.exists():
        r = json.loads(receipt.read_text())
        if r['archive_sha256'] != file_hash(archive):
            raise ValueError('Changed reference cache')
        return archive, r
    import h5py  # diagnostic-only dependency for NOAA's static netCDF4 files
    sources, arrays = {}, {}
    for key, prefix in [('air', 'air'), ('u', 'uwnd'), ('v', 'vwnd')]:
        filename = prefix + '.sig995.mon.ltm.nc'
        url = 'https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface/' + filename
        path = REFERENCE/filename
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'rotclimate-diagnostic/1.0'}), timeout=30) as response:
                payload = response.read()
            temporary = path.with_suffix('.part'); temporary.write_bytes(payload); temporary.replace(path)
        text = lambda value: value.decode() if isinstance(value, bytes) else str(value)
        with h5py.File(path, 'r') as nc:
            period = text(nc['time'].attrs['climo_period'])
            level = text(nc[prefix].attrs['level_desc'])
            units = text(nc[prefix].attrs['units'])
            if period != '1991/01/01 - 2020/12/31' or level != '0.995 sigma':
                raise ValueError('Unexpected NCEP period or vertical reference')
            if units != ('degC' if key == 'air' else 'm/s'):
                raise ValueError('Unexpected '+prefix+' units')
            scale = np.asarray(nc[prefix].attrs.get('scale_factor',1.)).item()
            offset = np.asarray(nc[prefix].attrs.get('add_offset',0.)).item()
            arrays[key] = np.asarray(nc[prefix],dtype=np.float32) * scale + offset
            if (arrays[key].shape != (12,73,144) or not np.isfinite(arrays[key]).all()
                    or np.max(np.abs(arrays[key])) > 1000
                    or not np.allclose(nc['lat'][:],90-2.5*np.arange(73))
                    or not np.allclose(nc['lon'][:],2.5*np.arange(144))):
                raise ValueError('Unexpected NCEP coordinates or missing fields')
        sources[key] = dict(url=url,sha256=file_hash(path),period=period,level=level,units=units)
        print('Reference ready:', key, flush=True)
    np.savez_compressed(archive, **arrays)
    r = dict(period='1991-2020', level='sigma0.995', air_units='degC', wind_units='m/s', sources=sources,
             archive_sha256=file_hash(archive))
    write_json(receipt, r)
    return archive, r


def reference_at(case, reference):
    south = earth.REGIONS[case.name]['lat0'] < 0
    lat = -case.grid.lat if south else case.grid.lat
    i, j = (90-lat)/2.5, (case.lon % 360)/2.5
    out = {}
    for key, array in reference.items():
        a = np.concatenate([array,array[:,:,:1]],axis=2)
        sampled = np.stack([ndi.map_coordinates(a[m],[i,j],order=1,mode='nearest') for m in range(12)])
        out[key] = np.roll(sampled,6,axis=0) if south else sampled
    if south: out['v'] *= -1
    return out


def one(job):
    region, config, params_path, output, specs, run_id = job
    output = Path(output); path = output/(config+'__'+region+'.json')
    if path.exists():
        row=json.loads(path.read_text())
        if row['identity'] != run_id: raise ValueError('Changed audit inputs')
        if row['status']=='passed': return row
    earth.REGIONS.update(specs)
    case = earth.region_case(region,56.); g=case.grid
    p = earth.earth_params(joint.earth_profile(Params.from_json(ROOT/params_path)),case)
    model = ClimateModel(p,g); model.heat_record = {}
    result = model.run()
    if not result.numerics['all_checks_passed']: raise ValueError('Unverified solver: '+region)
    records = [model.heat_record[round(float(d),6)] for d in result.days]
    fields = {key:np.stack([r[key] for r in records]) for key in records[0]}
    land = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    sea = ~g.land & (ndi.distance_transform_edt(~land)*g.cell_km <= 300.)
    if not sea.any(): raise ValueError('No coastal diagnostic sea: '+region)
    obs = reference_at(case,dict(np.load(REFERENCE/'sigma995.npz')))
    W = monthly_weights(result.days,p.year_days)
    mean = lambda a: (W @ np.asarray(a).reshape(len(result.days),-1)[:,sea.ravel()]).mean(1).tolist()
    st = monthly_stats(result.T,result.P,result.days,p.year_days,summer_solstice=p.winter_solstice_day+p.year_days/2)
    contrast = fields['surface_c']-fields['air_c']
    tendency = fields['lambda_s']*contrast*DAY
    speed = np.hypot(fields['u_ms'],fields['v_ms'])
    depth = equivalent_depth_m(fields['lambda_s'],speed)
    cold = (fields['surface_c']-fields['rate_state_c']) >= 2.
    # Only cold-air states engage the unstable cap; positive tendencies elsewhere
    # are not cap violations. The baseline rate floor is explicitly disclosed.
    capped_cold = cold & (p.ocean_unstable_cap > 0)
    exceed = capped_cold & (tendency > p.ocean_unstable_cap+1e-6)
    row = dict(status='passed',identity=run_id,region=region,config=config,
        params=asdict(p),case_sha256=case_hash(case,observed_sea=True),numerics=result.numerics,
        cells=dict(scored_land=int(land.sum()),mapped_sea=int((g.inmap & ~g.land).sum()),coastal_sea=int(sea.sum())),
        monthly=dict(land_bias_c=(st['Tm'][:,land]-case.obs_T[:,land]).mean(1).tolist(),
            land_temperature_mae_c=np.abs(st['Tm'][:,land]-case.obs_T[:,land]).mean(1).tolist(),
            land_rain_model_mm=st['Pm'][:,land].mean(1).tolist(),land_rain_obs_mm=case.obs_P[:,land].mean(1).tolist(),
            surface_c=mean(fields['surface_c']),air_c=mean(fields['air_c']),
            woa_surface_c=np.asarray(g.obs_sst)[:,sea].mean(1).tolist(),ncep_air_c=obs['air'][:,sea].mean(1).tolist(),
            wind_ms=mean(speed),ncep_wind_ms=np.hypot(obs['u'],obs['v'])[:,sea].mean(1).tolist(),
            surface_tendency_k_day=mean(tendency),warm_air_share=mean(contrast<0),cold_air_share=mean(cold),
            flux_1000m_wm2=mean(slab_flux_wm2(fields['lambda_s'],contrast,1000.)),
            equivalent_depth_proxy_m=mean(depth),cap_exceedance_share=mean(exceed)),
        distributions=dict(tendency_k_day=np.percentile(tendency[:,sea],[0,5,50,95,100]).tolist(),
            equivalent_depth_proxy_m=np.percentile(depth[:,sea],[5,50,95]).tolist(),
            nominal_cap_exceedance_fraction_cold=float(exceed[:,sea].sum()/max(1,capped_cold[:,sea].sum()))),
        references='Separate WOA18 SST and NCEP sigma0.995 air/winds. Mixed periods; no observed flux inferred.')
    write_json(path,row)
    print(config,region,'T MAE',round(np.mean(row['monthly']['land_temperature_mae_c']),3),
          'cap exceed',round(row['distributions']['nominal_cap_exceedance_fraction_cold'],3),flush=True)
    return row


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workers',type=int,default=3)
    ap.add_argument('--out',type=Path,default=ROOT/'output/air_sea_audit_20261109');a=ap.parse_args()
    a.out.mkdir(exist_ok=True,parents=True);plan=json.loads(PLAN.read_text());_,reference=prepare_reference()
    sources={str(p.relative_to(ROOT)):file_hash(p) for p in [PLAN,Path(__file__).resolve(),*sorted((ROOT/'rotclimate').glob('*.py'))]}
    for config,path in plan['configs'].items():
        if file_hash(ROOT/path)!=plan['params_sha256'][config]: raise ValueError('Changed fixed candidate')
    specs={}
    for path in ['calibration/local_accuracy_20261023/regions_dev12.json','calibration/sealed_20261107h/regions.json']:
        specs.update(json.loads((ROOT/path).read_text()));sources[path]=file_hash(ROOT/path)
    protocol=dict(plan=plan,sources_sha256=sources,reference=reference,scope='Development diagnosis; all h regions already spent; no fit/adoption/new sealed pool')
    run_id=freeze(a.out/'protocol.json',protocol)
    jobs=[(r,n,p,str(a.out),specs,run_id) for n,p in plan['configs'].items() for r in plan['regions']]
    with Pool(a.workers) as pool: rows=list(pool.imap_unordered(one,jobs))
    if any(file_hash(ROOT/p)!=h for p,h in sources.items()): raise ValueError('Sources changed during audit')
    write_json(a.out/'summary.json',dict(status='passed',identity=run_id,rows=sorted(rows,key=lambda r:(r['region'],r['config']))))


if __name__=='__main__':main()
