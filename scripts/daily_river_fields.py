"""Declared daily river/pond/soil development cases; no harvest adoption."""
import argparse,csv,gzip,io,itertools,json,subprocess,sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.field_clock import field_clock
from harvest.soil_drying import soil_profile
from harvest.river_fields import periodic_fields,RiverClock
from land_people import CROPS,DAYS
from settlement_locations_earth import sha,write
OUT=ROOT/'output/daily_river_fields_20261114'
PLAN=ROOT/'calibration/daily_river_fields_20261114/plan.json'
OLD=ROOT/'output/flood_basin_storage_20261114/fields.npz'
REGIONS=['nile','mesopotamia_euphrates_only']
STOCKS=['top_mm','deep_mm','bound_mm','pond_mm']
FLUXES=['infiltration_mm','delivered_mm','surface_evap_mm','bare_diffusion_mm','root_uptake_mm','root_potential_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm']
STATIC=None


def load_inputs():
    global STATIC
    with np.load(OLD) as archive:
        STATIC={b:{k:archive[b+'__'+k] for k in ['lat','lon','area_km2','T','P','PET','qualified']} for b in REGIONS}
    phase=json.loads((ROOT/'output/flood_basin_seasonality_20261113/results.json').read_text())
    for region,gauge in [('nile','aswan'),('mesopotamia_euphrates_only','hit')]:
        q=np.array(next(v for v in phase['rows'] if v['id']==gauge)['mean_monthly_flow_m3s'])
        STATIC[region]['source_m3']=np.maximum(q-q.mean(),0)*DAYS*86400
        assert STATIC[region]['qualified'].all(),'Missing climate requires explicit handling before a new run'


def prepare(spec):
    if STATIC is None:load_inputs()
    region,crop,zr,calendar,bg,pondcap,eff,capture=spec;f=STATIC[region];nf=len(f['lat'])
    begin=365*(10 if calendar=='old' else 10.5)/12;end=365*(3 if calendar=='old' else 2.5)/12;flood=365*7/12
    clock=field_clock(np.linspace(0,365,13),event_edges_days=[flood,begin,end]);globalcrop=clock.cyclic_window(begin,end);floodmask=clock.cyclic_window(flood,begin)
    ts=clock.repeat_bin_values(f['T']);c=CROPS[crop]
    therm=np.all((ts[globalcrop]>=c['window'][0])&(ts[globalcrop]<=c['window'][1]),axis=0)&(ts[globalcrop].max(0)>=c['need_warm'])
    therm&=(np.sum(np.maximum(ts-c['base'],0)*clock.step_days[:,None]*globalcrop[:,None],axis=0)>=c['heat'])
    cm=globalcrop[:,None]&therm[None,:];pm=np.broadcast_to(floodmask[:,None],(len(clock.step_days),nf))
    a=dict(profile=soil_profile(.25,.1,zr,.1,9.),area_m2=f['area_km2']*1e6,field_nodes=np.zeros(nf,dtype=int),source_m3=clock.spread_bin_totals(f['source_m3'][:,None]),clock=RiverClock(clock,[0],[-1]),rain_mm=clock.spread_bin_totals(f['P']),eto_mm_day=clock.repeat_bin_values(f['PET']/np.diff(clock.bin_edges_days)[:,None]),crop_mask=cm,capture_mask=pm if capture else np.zeros_like(pm),pond_mask=pm,crop_kcb=c['kc'])
    opts=dict(bare_background=bg,pond_capacity_mm=pondcap,infiltration_mm_day=20.,efficiency=eff,pond_evap_coefficient=1.,crop_exposed_fraction=.25,depletion_fraction=.55)
    return f,clock,therm,a,opts


def run_case(spec):
    f,clock,eligible,a,opts=prepare(spec)
    region,crop,zr,calendar,bg,pondcap,eff,capture=spec
    case=f'{region}__{crop}__z{zr:g}_{calendar}_b{bg:g}_p{pondcap:g}_e{eff:g}_c{int(capture)}'
    r=periodic_fields(**a,**opts)
    area=f['area_km2']*1e6;fields={'eligible':eligible};monthly={};daily={}
    for name in STOCKS:
        fields['initial_'+name]=r['initial'][name];fields['final_'+name]=r[name][-1]
        daily[name]=np.sum(r[name]*area[None,:]/1000.,axis=1)
    for name in FLUXES:
        fields['annual_'+name]=r[name].sum(0)
        flux=np.sum(r[name]*area[None,:]/1000.,axis=1)
        monthly[name]=np.bincount(clock.bin_index,weights=flux,minlength=12)
    for name in ['river_requested_m3','river_delivered_m3','river_loss_m3','river_outlet_m3']:
        monthly[name]=np.bincount(clock.bin_index,weights=r[name][:,0],minlength=12)
    fields['root_coverage']=np.divide(fields['annual_root_uptake_mm'],fields['annual_root_potential_mm'],out=np.zeros_like(area),where=fields['annual_root_potential_mm']>0)
    eligible_area=float(area[eligible].sum()/1e6);adequate=float(area[eligible&(fields['root_coverage']>=.95)].sum()/1e6) if r['periodic'] else None
    row=dict(case=case,region=region,crop=crop,root_depth_m=zr,taw_mm=150*zr,calendar=calendar,bare_background=bg,pond_capacity_mm=pondcap,efficiency=eff,capture=bool(capture),candidate_fields=len(area),eligible_fields=int(eligible.sum()),candidate_area_km2=float(area.sum()/1e6),eligible_area_km2=eligible_area,adequate_root_area_km2=adequate,root_coverage=float(np.average(fields['root_coverage'][eligible],weights=area[eligible])) if r['periodic'] and eligible_area>0 else None,periodic=r['periodic'],spinup_years=r['years'],periodic_residual_mm=r['periodic_residual_mm'],source_m3=float(a['source_m3'].sum()),rain_m3=float(np.sum(a['rain_mm']*area[None,:]/1000.)),delivered_m3=float(r['river_delivered_m3'].sum()),delivery_loss_m3=float(r['river_loss_m3'].sum()),river_outlet_m3=float(r['river_outlet_m3'].sum()))
    for name in ['surface_evap_mm','bare_diffusion_mm','root_uptake_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm']:row[name.replace('_mm','_m3')]=float(monthly[name].sum())
    row['initial_stock_m3']=float(sum(np.sum(r['initial'][name]*area/1000.) for name in STOCKS));row['final_stock_m3']=float(sum(daily[name][-1] for name in STOCKS))
    row['joint_mass_residual_m3']=row['initial_stock_m3']+row['source_m3']+row['rain_m3']-row['final_stock_m3']-row['delivery_loss_m3']-row['river_outlet_m3']-sum(row[k.replace('_mm','_m3')] for k in ['surface_evap_mm','bare_diffusion_mm','root_uptake_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm'])
    return row,fields,monthly,daily


def main(out=OUT,workers=4):
    for path in [PLAN,PLAN.parent/'geometry_policy.json']:assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    core=OUT/'core/review.json';audit=json.loads(core.read_text());assert audit['status']=='passed_before_earth_outputs' and '105 passed' in audit['controls_stdout']
    for name,digest in audit['producers'].items():assert sha(ROOT/name)==digest,name
    base=json.loads((ROOT/'output/flood_basin_storage_20261114/results.json').read_text());protected=base['unchanged_atlas_sha256'].copy()
    for folder in ['flood_basin_storage_20261114','soil_drying_20261114']:
        for name,digest in json.loads((ROOT/f'output/{folder}/review.json').read_text())['fresh_byte_exact'].items():protected[f'output/{folder}/'+name]=digest
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    specs=list(itertools.product(REGIONS,['barley','wheat'],[1.,1.5],['old','fractional'],[0.,.15],[0.,200.],[.5,1.],[False,True]));assert len(specs)==256
    out.mkdir(parents=True,exist_ok=True);rows=[];fields={};load_inputs()
    for region,f in STATIC.items():
        for name,value in f.items():fields[region+'__'+name]=value
    def records():
        if workers==1:
            for spec in specs:yield run_case(spec)
        else:
            with ProcessPoolExecutor(max_workers=workers,initializer=load_inputs) as pool:yield from pool.map(run_case,specs,chunksize=1)
    buffer=io.StringIO(newline='');writer=csv.writer(buffer);columns=['case','field','latitude','longitude','area_km2','eligible','root_coverage',*['initial_'+k for k in STOCKS],*['final_'+k for k in STOCKS],*['annual_'+k for k in FLUXES]];writer.writerow(columns)
    for number,(row,values,monthly,daily) in enumerate(records(),1):
        case=row['case'];region=row['region'];rows.append(row)
        for name,value in values.items():fields[case+'__'+name]=value
        for name,value in monthly.items():fields[case+'__monthly_'+name]=value
        for name,value in daily.items():fields[case+'__daily_'+name]=value
        for i in range(row['candidate_fields']):writer.writerow([case,i,STATIC[region]['lat'][i],STATIC[region]['lon'][i],STATIC[region]['area_km2'][i],int(values['eligible'][i]),values['root_coverage'][i] if values['eligible'][i] and row['periodic'] else '',*[values[k][i] for k in columns[7:]]])
        if number%16==0:print('Completed',number,'/256; maxcycles',max(v['spinup_years'] for v in rows),flush=True)
    np.savez_compressed(out/'fields.npz',**fields)
    with (out/'fields.csv.gz').open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,filename='',mode='wb',mtime=0) as stream:stream.write(buffer.getvalue().encode())
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'harvest/river_fields.py',ROOT/'harvest/soil_drying.py',ROOT/'harvest/field_clock.py',ROOT/'harvest/flood_water.py',ROOT/'scripts/land_people.py',PLAN,PLAN.parent/'geometry_policy.json']}
    sources={str(p.relative_to(ROOT)):sha(p) for p in [OLD,ROOT/'output/flood_basin_seasonality_20261113/results.json',core]}
    write(out/'results.json',dict(status='daily_development_coupling_only',rows=rows,producers=producers,sources=sources,files_sha256={name:sha(out/name) for name in ['fields.npz','fields.csv.gz']},unchanged_sha256=protected,all_candidates_consume_water=True,heldout_qualified=False,harvest_or_population_scored=False,adopt=False))
    print('Wrote256development cases;',sum(v['periodic'] for v in rows),'periodic; maxmassresidual',max(abs(v['joint_mass_residual_m3']) for v in rows))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT);parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();main(args.out,args.workers)
