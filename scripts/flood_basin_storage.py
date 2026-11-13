"""Declared fixed-calendar field storage feasibility on two development regions."""
import argparse,csv,gzip,hashlib,io,itertools,json,subprocess,sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import land_people_earth as L
from arable_slope_earth import etopo_window
from land_people import CROPS,DAYS,hargreaves,sunlight_top
from harvest.flood_storage import periodic_storage
from settlement_locations_earth import write,sha
PLAN=ROOT/'calibration/flood_basin_storage_20261114/plan.json'
OUT=ROOT/'output/flood_basin_storage_20261114'
MONTHS=np.array([10,11,0,1,2])


def terrain_fields(boxes,nav,z):
    records=[];constant=0;fine_count=0;nx=1644
    for la0,la1,lo0,lo1 in boxes:
        r0,r1=int((56-la1)*60),int((56-la0)*60);c0,c1=int((lo0+12)*60),int((lo1+12)*60)
        rs=slice(max(0,r0-60),r1+60);cs=slice(max(0,c0-60),c1+60)
        lat=56-(np.arange(rs.start,rs.stop)+.5)/60
        spacing=(L.KM_DEG/60,L.KM_DEG*np.cos(np.deg2rad(lat.mean()))/60)
        river=nav[rs,cs];zz=z[rs,cs]
        dist,(iy,ix)=ndi.distance_transform_edt(~river,sampling=spacing,return_indices=True)
        inner=(slice(r0-rs.start,r1-rs.start),slice(c0-cs.start,c1-cs.start))
        mask=(zz[inner]>0)&((zz-zz[iy,ix])[inner]<=5)&(dist[inner]<=30)
        yy,xx=np.nonzero(mask);yy+=r0;xx+=c0
        area=(L.KM_DEG/60)**2*np.cos(np.deg2rad(56-(yy+.5)/60))
        records.extend(zip((yy//5)*nx+xx//5,area));fine_count+=len(yy);constant+=len(yy)*spacing[0]*spacing[1]
    ids=np.asarray([v[0] for v in records],dtype=int);unique,inverse=np.unique(ids,return_inverse=True)
    area=np.bincount(inverse,weights=[v[1] for v in records]);count=np.bincount(inverse)
    row,col=unique//nx,unique%nx
    return dict(row=row,col=col,lat=56-(row+.5)/12,lon=-12+(col+.5)/12,area_km2=area,fine_count=count),dict(fine_cells=fine_count,candidate_area_km2=float(area.sum()),previous_constant_area_method_km2=float(constant))


def eligible(T,crop):
    c=CROPS[crop];Ts=T[MONTHS]
    return np.isfinite(T).all(0)&np.all((Ts>=c['window'][0])&(Ts<=c['window'][1]),axis=0)&(Ts.max(0)>=c['need_warm'])&((np.maximum(Ts-c['base'],0).sum(0)*DAYS)>=c['heat'])


def main(out=OUT):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());out.mkdir(parents=True,exist_ok=True)
    controls=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_flood_storage.py','tests/test_flood_water.py','tests/test_flood_timing.py','tests/test_flood_gauge_quality.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    write(out/'controls.json',dict(status='passed_before_field_outputs',stdout=controls.stdout))
    phase=json.loads((ROOT/'output/flood_basin_seasonality_20261113/results.json').read_text())
    for name,digest in phase['unchanged_atlas_sha256'].items():assert sha(ROOT/name)==digest,name
    sources={str(PLAN.relative_to(ROOT)):sha(PLAN)}
    pins=json.loads((ROOT/'data/earth_harvest_public_sources_20261113.json').read_text())
    for source in pins['sources']:
        path=ROOT/source['path'];assert sha(path)==source['sha256'];sources[source['path']]=source['sha256']
    for name in ['output/flood_basin_seasonality_20261113/results.json','output/flood_basin_irrigation_20261113/groundwork.json','data/cache/arable_slope_earth/etopo60_window.npy']:
        sources[name]=sha(ROOT/name)
    z=etopo_window();nav,_=L.river_masks((672,1644));static={};meta={};fields={}
    for basin,spec in plan['regions'].items():
        static[basin],meta[basin]=terrain_fields(spec['boxes'],nav,z)
    del z,nav
    for basin,f in static.items():
        for name in ('T','P','D'):f[name]=np.empty((12,len(f['row'])))
    for month in range(1,13):
        for var,key in [('tavg','T'),('prec','P'),('tmax','D')]:
            a=L.wc(var,month)[L.window_slices()]
            if key=='D':a=a-L.wc('tmin',month)[L.window_slices()]
            for f in static.values():f[key][month-1]=a[f['row'],f['col']]
    rows=[];csv_buffer=io.StringIO(newline='');csv_writer=csv.writer(csv_buffer)
    csv_writer.writerow(['case','field','latitude','longitude','candidate_area_km2','climate_qualified','crop_eligible','crop_et_coverage','annual_delivered_mm','annual_crop_et_mm','annual_bare_et_mm','initial_mm','final_mm'])
    for basin,f in static.items():
        f['qualified']=np.isfinite(f['T']).all(0)&np.isfinite(f['P']).all(0)&np.isfinite(f['D']).all(0)&(f['P']>=0).all(0)
        f['PET']=hargreaves(f['T'],f['D'],sunlight_top(f['lat'],L.TILT,L.WS_DAY))
        for name,value in f.items():fields[basin+'__'+name]=value
        gauge=next(r for r in phase['rows'] if r['id']==plan['regions'][basin]['gauge']);q=np.asarray(gauge['mean_monthly_flow_m3s'])
        source=np.maximum(q-q.mean(),0)[:,None]*DAYS*86400;fields[basin+'__source_m3']=source
        for crop,capacity,bare_frac,eff,capture_name in itertools.product(['barley','wheat'],[100,300,600],[0,1],[.5,1.],['none','pre_sowing_three_months']):
            case=f'{basin}__{crop}__s{capacity}_b{bare_frac}_e{eff:g}_{capture_name}'
            ok=f['qualified']&eligible(f['T'],crop);idx=np.flatnonzero(ok);area=f['area_km2'][idx]*1e6;pet=f['PET'][:,idx]
            crop_et=np.zeros_like(pet);crop_et[MONTHS]=CROPS[crop]['kc']*pet[MONTHS]
            bare=bare_frac*pet;bare[MONTHS]=0;capture=np.zeros_like(pet,dtype=bool)
            if capture_name!='none':capture[[7,8,9]]=True
            r=periodic_storage(f['P'][:,idx],crop_et,bare,area,np.zeros(len(idx),dtype=int),source,[0],[-1],capacity_mm=capacity,capture_mask=capture,efficiency=eff)
            fields[case+'__field_index']=idx;fields[case+'__crop_et_demand_mm']=crop_et;fields[case+'__bare_et_demand_mm']=bare
            for name,value in r.items():fields[case+'__'+name]=np.asarray(value)
            demand=crop_et.sum(0);coverage=np.divide(r['crop_et_actual_mm'].sum(0),demand,out=np.zeros(len(idx)),where=demand>0)
            fields[case+'__coverage']=coverage
            eligible_area=float(area.sum()/1e6);adequate=float(area[coverage>=.95].sum()/1e6) if r['periodic'] else None
            row=dict(case=case,region=basin,crop=crop,capacity_mm=capacity,bare_ET_fraction=bare_frac,efficiency=eff,capture=capture_name,**meta[basin],climate_missing_area_km2=float(f['area_km2'][~f['qualified']].sum()),eligible_fields=len(idx),eligible_area_km2=eligible_area,periodic=r['periodic'],spinup_years=r['years'],periodic_residual_mm=r['periodic_residual_mm'],adequate_area_km2=adequate,adequate_share_eligible=adequate/eligible_area if adequate is not None and eligible_area>0 else None,mean_crop_ET_coverage=float(np.average(coverage,weights=area)) if r['periodic'] and area.sum()>0 else None,source_m3=float(source.sum()),delivered_m3=float(r['river_delivered_m3'].sum()),loss_m3=float(r['river_loss_m3'].sum()),outlet_m3=float(r['river_outlet_m3'].sum()))
            rows.append(row);where={int(v):j for j,v in enumerate(idx)}
            for i in range(len(f['row'])):
                j=where.get(i);values=['']*6 if j is None or not r['periodic'] else [coverage[j],r['delivered_mm'][:,j].sum(),r['crop_et_actual_mm'][:,j].sum(),r['bare_et_actual_mm'][:,j].sum(),r['initial_mm'][j],r['final_mm'][j]]
                csv_writer.writerow([case,i,f['lat'][i],f['lon'][i],f['area_km2'][i],int(f['qualified'][i]),int(ok[i]),*values])
    np.savez_compressed(out/'fields.npz',**fields)
    with (out/'fields.csv.gz').open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as stream:stream.write(csv_buffer.getvalue().encode())
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'harvest/flood_storage.py',ROOT/'harvest/flood_water.py',ROOT/'scripts/land_people.py',ROOT/'scripts/land_people_earth.py',ROOT/'scripts/arable_slope_earth.py']}
    write(out/'results.json',dict(status='development_storage_feasibility_only',rows=rows,sources=sources,producers=producers,files_sha256={name:sha(out/name) for name in ['fields.npz','fields.csv.gz']},unchanged_atlas_sha256=phase['unchanged_atlas_sha256'],heldout_qualified=False,irrigated_area_or_harvest_calibrated=False,adopt=False,limits=plan['next']))
    print('Wrote',len(rows),'rows;',sum(v['periodic'] for v in rows),'periodic; all scenario members retained')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
