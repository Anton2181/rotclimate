"""Frozen native PNW circulation audit; no new forcing, fitting or adoption."""
from dataclasses import asdict
from pathlib import Path
import argparse,json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rotclimate import earth,joint
from rotclimate.model import ClimateModel
from rotclimate.koppen import monthly_stats
from earth_benchmark import load_params
from benchmark_local import DEV12_SPECS,temperature_metrics
from circulation_reference import acquire,diagnose_model
from local_benchmark_protocol import freeze,file_hash,case_hash,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'calibration/pnw_transport_20261027/plan.json')
    parser.add_argument('--out',type=Path,default=ROOT/'output/pnw_transport_20261027')
    args=parser.parse_args();path=args.plan.resolve();plan=json.loads(path.read_text());out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    parent=ROOT/plan['parent'];parent_review=json.loads((parent/'review.json').read_text())
    if not parent_review['complete']:raise ValueError('Finish frozen parent campaign first')
    parent_protocol=json.loads((parent/'protocol.json').read_text());parent_plan=parent_protocol['plan']
    fields,references=acquire(ROOT,plan)
    sources=[path,Path(__file__),ROOT/plan['physics'],DEV12_SPECS,parent/'review.json',parent/'protocol.json',
        ROOT/'scripts/circulation_reference.py',ROOT/'scripts/earth_calendar.py',ROOT/'scripts/benchmark_local.py',
        ROOT/'scripts/earth_benchmark.py',ROOT/'scripts/local_benchmark_protocol.py',ROOT/'experiments/v10_forcing_audit.py',
        ROOT/'experiments/v10_thermodynamics.py',earth.WOA_SST]
    sources+=list((ROOT/'rotclimate').glob('*.py'))+list((ROOT/'rotclimate_v10').glob('*.py'))+[ROOT/n for n in references]
    sources+=[earth.WORLDCLIM/f'wc2.1_5m_{k}.zip' for k in ['tavg','prec','elev','vapr']]
    sources+=[ROOT/plan['archive']/'cases/pacific_nw.json',ROOT/plan['archive']/'cells/pacific_nw.npz']
    for name in plan['profiles']:sources +=[parent/name/'pacific_nw.json',parent/name/'pacific_nw.npz']
    for n,h in parent_protocol['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed parent scientific epoch: '+n)
    identity=freeze(out/'protocol.json',dict(plan=plan,sources={str(p.relative_to(ROOT)):file_hash(p) for p in sources},references=references))
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()));case=earth.region_case('pacific_nw',plan['cell_km']);g=case.grid
    land=g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    domain=np.ones_like(g.land);domain[[0,-1]]=False;domain[:,[0,-1]]=False
    rows={};saved={};started=time.monotonic()
    for name in plan['profiles']:
        output=out/(name+'.json');npz=out/(name+'.npz')
        if output.exists():raise ValueError('Preserve existing audit runs; choose fresh output')
        prior=json.loads((parent/name/'pacific_nw.json').read_text())
        row=dict(name=name,identity=identity,case_identity=case_hash(case,observed_sea=True),status='started')
        try:
            theta=joint.update_block(load_params(ROOT/plan['physics']),'physics',parent_plan['profiles'][name])
            theta=joint.update_block(theta,'numerics',parent_plan.get('profile_numerics',{}).get(name,{}))
            p=earth.earth_params(joint.earth_profile(theta),case)
            model=ClimateModel(p,grid=g);model.trace_cells=np.nonzero(domain);result=model.run(diagnose_moisture=True)
            if not result.numerics['all_checks_passed']:raise ValueError('Strict numerical check failed')
            st=monthly_stats(result.T,result.P,result.days,p.year_days,summer_solstice=p.winter_solstice_day+p.year_days/2)
            if prior['status']!='passed' or row['case_identity']!=prior['case_identity']:raise ValueError('Unpaired parent inputs')
            if file_hash(parent/name/'pacific_nw.npz')!=prior['arrays_sha256']:raise ValueError('Changed parent arrays')
            with np.load(parent/name/'pacific_nw.npz') as old:
                if not np.array_equal(st['Pm'][(slice(None),)+g.map_slice()],old['simulated'],equal_nan=True):raise ValueError('Parent rainfall cells changed')
            temperature=temperature_metrics(st['Tm'][:,land],case.obs_T[:,land])
            if temperature!=prior['temperature']:raise ValueError('Parent temperature scores changed')
            if name=='reference':
                with np.load(ROOT/plan['archive']/'cells/pacific_nw.npz') as old:
                    for key,value in [('Ts',st['Tm'][:,land]),('Ps',st['Pm'][:,land]),('To',case.obs_T[:,land]),('Po',case.obs_P[:,land])]:
                        if not np.array_equal(value.astype(np.float32),old[key]):raise ValueError('Original r39 cells changed: '+key)
            circulation,native=diagnose_model(case,p,model,result,fields);saved[name]=native
            with npz.open('wb') as stream:np.savez_compressed(stream,**native)
            row.update(status='passed',params=asdict(p),parent_climate_exact=True,temperature=temperature,
                rain=prior['rain'],monthly_rain=prior['monthly_rain'],circulation=circulation,numerics=result.numerics,arrays_sha256=file_hash(npz))
        except Exception as error:row.update(status='failed',error=repr(error))
        write_json(output,row);rows[name]=row;print(name+': '+row['status'],flush=True)
    if any(r['status']!='passed' for r in rows.values()):
        write_json(out/'review.json',dict(complete=True,all_checks_passed=False,climate_integrations=len(rows),rows=rows,physics_or_atlas_adoption=False))
        raise SystemExit('Preserve failed audit runs')
    field=fields['pacific_nw','shum'];lon,lat=np.meshgrid(field.longitude,field.latitude)
    sample=saved[plan['profiles'][0]];valid=sample['circulation_mask_land']|sample['circulation_mask_ocean']
    for n in plan['profiles']:
        for k in ['circulation_mask_land','circulation_mask_ocean','circulation_area']:
            if not np.array_equal(saved[n][k],sample[k]):raise ValueError('Changed native geometry')
    native_reference=sample['circulation_reference_q925_300']
    plot_names=['NCEP/NCAR',*plan['profiles']];labels=dict(reference='r39',reservoir_control='Previous reservoirs',column_no_mix='Corrected rain/recycling')
    fig,axes=plt.subplots(2,4,figsize=(14,8),constrained_layout=True)
    for i,(season,months) in enumerate([('Winter (DJF)',[11,0,1]),('Summer (JJA)',[5,6,7])]):
        days=np.array([31,28,31,30,31,30,31,31,30,31,30,31])[months]
        for ax,name in zip(axes[i],plot_names):
            values=native_reference if name=='NCEP/NCAR' else saved[name]['circulation_model']
            vector=np.average(values[months],axis=0,weights=days)
            ax.pcolormesh((case.lon+360)%360,g.lat,g.land.astype(float),shading='nearest',cmap='Greys',vmin=0,vmax=2,alpha=.4)
            selection=valid.reshape(lon.shape)
            qv=ax.quiver(lon[selection],lat[selection],vector[0,valid],vector[1,valid],angles='uv',scale=70,width=.007,color='#265b8a')
            ax.quiverkey(qv,.82,1.02,10,'10 m/s',labelpos='E',coordinates='axes')
            ax.set(xlim=(230,250),ylim=(40,53),xlabel='Longitude (°E)',ylabel='Latitude (°N)',title=f'{season} · {labels.get(name,name)}')
            ax.set_aspect(1/np.cos(np.radians(46)))
    fig.suptitle('Pacific Northwest · matched native partial-column circulation',fontsize=16)
    fig.supxlabel('Only covered ocean/land footprints above modeled terrain. Identical masks, true-area aggregation and geographic vectors.\nMonthly q-weighted925–300hPa reference omits transient moisture covariance; model vectors are moisture-weighted column diagnostics.',fontsize=9)
    first=out/'native_vectors.png';fig.savefig(first,dpi=145);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,5.4),constrained_layout=True)
    colors=['#466d96','#888888','#b16e37']
    ocean=sample['circulation_mask_ocean'];area=sample['circulation_area'][ocean]
    for name,color in zip(plan['profiles'],colors):
        vectors=np.average(saved[name]['circulation_model'][:,:,ocean],axis=2,weights=area)
        axes[0].plot(vectors[0],label=labels[name],color=color)
        axes[1].plot(rows[name]['monthly_rain']['simulated'],label=labels[name],color=color)
        humidity=rows[name]['circulation'].get('humidity',{}).get('scores',{}).get('ocean')
        if humidity:axes[2].plot(humidity['monthly_model_q_ratio'],label=labels[name],color=color)
    reference=np.average(native_reference[:,:,ocean],axis=2,weights=area)
    axes[0].plot(reference[0],label='NCEP/NCAR',color='#222',lw=2.5)
    axes[1].plot(rows['reference']['monthly_rain']['observed'],label='WorldClim',color='#222',lw=2.5)
    humidity=rows['reservoir_control']['circulation']['humidity']['scores']['ocean']
    axes[2].plot(humidity['monthly_reference_q_ratio'],label='NCEP/NCAR',color='#222',lw=2.5)
    axes[0].set(title='Native ocean · eastward moisture wind',ylabel='Eastward speed (m/s)')
    axes[1].set(title='Regional scored land · monthly rainfall',ylabel='Rain (mm / equal model month)')
    axes[2].set(title='Native ocean · partial humidity shape',ylabel='Mean q700–300 / mean q925–700')
    for ax in axes:ax.set(xticks=range(12),xticklabels=list('JFMAMJJASOND'));ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Pacific Northwest · transport, rainfall and vertical humidity',fontsize=16)
    fig.supxlabel('Three actual climate reruns reproduce prior rainfall cells and temperature scores; r39 also reproduces archived monthlyT/P.\nCoarse1981–2010 reanalysis and1970–2000 rainfall periods differ. Association is not causal attribution; no fit or climate adoption.',fontsize=9)
    second=out/'monthly_diagnostics.png';fig.savefig(second,dpi=145);plt.close(fig)
    final=dict(complete=True,identity=identity,all_checks_passed=True,climate_integrations=3,rows=rows,
        references=references,seconds=time.monotonic()-started,images_sha256={p.name:file_hash(p) for p in [first,second]},physics_or_atlas_adoption=False)
    write_json(out/'review.json',final);print(json.dumps({k:v for k,v in final.items() if k not in ['rows','references']},indent=2),flush=True)


if __name__=='__main__':main()
