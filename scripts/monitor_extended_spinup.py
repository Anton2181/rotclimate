"""Read-only daily water/energy checks and plots for the frozen fourteen-day runs."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json


def load(path):
    with np.load(path) as f:return {k:f[k] for k in f.files}


def energy(a,mass):
    gas=((1004*mass[:,None,None]+1850*a['vapor'])*a['temperature']+(2.5e6-1850*273.15)*a['vapor']).sum()
    surface=((a['substrate_capacity']+4186*a['surface_liquid'])*(a['surface_temperature']-273.15)).sum()
    kinetic=.5*((mass[:,None,None]*a['u'][:,:,1:-1]**2).sum()+(mass[:,None,None]*a['v'][:,1:-1]**2).sum())
    return float(gas+surface+kinetic)


def monitor(wet,dry,out):
    out.mkdir(parents=True,exist_ok=True);checks={};all_rows={};reproduction={};counts={}
    for name,folder in [('wet',wet),('dry',dry)]:
        plan=json.loads((folder/'frozen_plan.json').read_text())
        literal=ROOT/f'calibration/extended_surface_spinup_20261029/{name}_plan.json'
        assert literal.read_bytes()==(folder/'frozen_plan.json').read_bytes()
        for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
        progress=json.loads((folder/'progress.json').read_text())
        receipt=folder/'verification.json'
        counts[name]=dict(started=progress['started'],completed=progress['completed'],active=progress['active'])
        if receipt.exists():
            r=json.loads(receipt.read_text());counts[name]=dict(started=r['actual_earth_initialized_integrations_started'],completed=r['integrations_completed'],active=None)
        for region in plan['regions']:
            init_path=folder/region/'initial.npz'
            if not init_path.exists():continue
            initial=load(init_path);land=initial['land'].astype(bool);m=-np.diff(initial['pressure_edges'])/9.80665
            e0=energy(initial,m);w0=float(initial['vapor'].sum()+initial['surface_liquid'].sum());cells=land.size;previous=initial;rows=[]
            for day in range(1,15):
                stem=folder/region/'forced'/f'day_{day}_900';jp=stem.with_suffix('.json');npz=stem.with_suffix('.npz')
                if not jp.exists():break
                d=json.loads(jp.read_text());assert file_hash(npz)==d['fields_sha256'];a=load(npz)
                ee=abs(energy(a,m)-e0-d['net_external_energy_j_m2']*cells)/abs(e0)
                we=abs(a['vapor'].sum()+a['surface_liquid'].sum()-w0+d['net_outward_water_kg_m2']*cells)/w0
                assert max(ee,we)<1e-10,(name,region,day,ee,we)
                evaporation=a['day_rain']-(a['surface_liquid']-previous['surface_liquid'])
                imported=(a['vapor']-previous['vapor']).sum(0)+a['surface_liquid']-previous['surface_liquid']
                assert abs(evaporation.mean()-d['net_evaporation_kg_m2'])<1e-9
                prior_port=rows[-1]['cumulative_outward_water_kg_m2'] if rows else 0.
                assert abs(imported.mean()+d['net_outward_water_kg_m2']-prior_port)<1e-9
                row=dict(day=day,land_rain_mm=float(a['day_rain'][land].mean()),land_evaporation_mm=float(evaporation[land].mean()),land_net_horizontal_import_mm=float(imported[land].mean()),land_liquid_mm=float(a['surface_liquid'][land].mean()),land_temperature_k=float(a['surface_temperature'][land].mean()),actual_energy_relative_error=float(ee),actual_water_relative_error=float(we),cumulative_outward_water_kg_m2=d['net_outward_water_kg_m2'],fields_sha256=d['fields_sha256'])
                rows.append(row)
                if day<=3:
                    old=ROOT/f'output/surface_spinup_{name}_20261029'/region/'forced'/f'day_{day}_900.npz';b=load(old)
                    differences={k:float(abs(a[k]-b[k]).max()) for k in b}
                    for k,error in differences.items():assert error<=(.1 if k=='rain_enthalpy' else 1e-6),(name,region,day,k,error)
                    reproduction[f'{name}_{region}_day{day}']=dict(maximum_absolute_differences=differences,prior_sha256=file_hash(old),new_sha256=file_hash(npz))
                previous=a
            all_rows[name+'_'+region]=rows
    fig,axes=plt.subplots(4,3,figsize=(14,11),sharex=True)
    for col,region in enumerate(['north_india','mexico','pacific_nw']):
        matched={}
        for name,color in [('wet','#187aa7'),('dry','#ad6a36')]:
            rows=all_rows.get(name+'_'+region,[]);days=[r['day'] for r in rows];matched[name]=len(rows)
            for row,key in enumerate(['land_rain_mm','land_liquid_mm','land_temperature_k','land_evaporation_mm']):
                axes[row,col].plot(days,[r[key] for r in rows],marker='.',color=color,label=name)
        axes[0,col].set_title(region.replace('_',' '));axes[0,col].legend()
        for ax in axes[:,col]:ax.set_xlim(.5,14.5);ax.grid(alpha=.2)
        axes[-1,col].set_xlabel('Model day since initialization')
        if not any(matched.values()):
            for ax in axes[:,col]:
                ax.text(.5,.5,'Awaiting first daily checkpoint',ha='center',va='center',transform=ax.transAxes)
                ax.set_axis_off()
        common=min(matched.values());checks[region]=dict(completed_days=matched,latest_matched_day=common)
        if common:
            w=all_rows['wet_'+region][common-1];d=all_rows['dry_'+region][common-1]
            checks[region]['latest_wet_minus_dry']={k:w[k]-d[k] for k in ['land_rain_mm','land_liquid_mm','land_temperature_k']}
    for ax,label in zip(axes[:,0],['Land rain (mm/day)','Land liquid (kg/m²)','Land surface T (K)','Land net evaporation (mm/day)']):ax.set_ylabel(label)
    fig.suptitle('Fourteen-day wet/dry experiment: available daily checkpoints',fontsize=14)
    fig.text(.5,.01,'Same physics and forcing • all completed days shown • initial-state sensitivity, not rainfall skill or equilibria',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(out/'extended_spinup_progress.png',dpi=150);plt.close(fig)
    maps,axes=plt.subplots(4,3,figsize=(15,13))
    for col,region in enumerate(['north_india','mexico','pacific_nw']):
        day=checks[region]['latest_matched_day']
        if not day:
            for ax in axes[:,col]:ax.text(.5,.5,'Awaiting matched checkpoint',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off()
            continue
        geo=load(wet/region/'initial.npz');fields={}
        for name,folder in [('wet',wet),('dry',dry)]:
            a=load(folder/region/'forced'/f'day_{day}_900.npz')
            before=load(folder/region/'forced'/f'day_{day-1}_900.npz') if day>1 else load(folder/region/'initial.npz')
            fields[name]=dict(rain=a['day_rain'],evap=a['day_rain']-a['surface_liquid']+before['surface_liquid'],imported=(a['vapor']-before['vapor']).sum(0)+a['surface_liquid']-before['surface_liquid'])
        arrays=[fields['wet']['rain'],fields['dry']['rain'],fields['wet']['evap']-fields['dry']['evap'],fields['wet']['imported']-fields['dry']['imported']]
        rainmax=max(float(arrays[0].max()),float(arrays[1].max()),1e-10)
        for row,field in enumerate(arrays):
            ax=axes[row,col];limit=max(float(abs(field).max()),1e-10);delta=row>=2
            plot=ax.pcolormesh(geo['longitude'],geo['latitude'],field,shading='nearest',cmap='RdBu_r' if delta else 'YlGnBu',vmin=-limit if delta else 0,vmax=limit if delta else rainmax)
            coast=ax.contour(geo['longitude'],geo['latitude'],geo['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.)
            coast.set_path_effects([pe.withStroke(linewidth=2.6,foreground='white')])
            ax.set_title(region.replace('_',' ')+f' day {day}: '+['wet-start rain','dry-start rain','wet − dry evaporation','wet − dry column import'][row],fontsize=10)
            ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');maps.colorbar(plot,ax=ax,shrink=.8,label='mm/day')
    maps.suptitle('Available matched daily rain and water budgets',fontsize=14)
    maps.text(.5,.01,'Day shown per region • same rain scale within each region • net import is a storage identity, not a water-origin tracer',ha='center',fontsize=9)
    maps.tight_layout(rect=(0,.035,1,.97));maps.savefig(out/'extended_spinup_water.png',dpi=140);plt.close(maps)
    result=dict(status='available_daily_checkpoints_verified',counts=counts,checks=checks,daily=all_rows,first_three_day_reproduction=reproduction,figure_sha256=file_hash(out/'extended_spinup_progress.png'),water_figure_sha256=file_hash(out/'extended_spinup_water.png'),monitor_sha256=file_hash(Path(__file__)),scope='Read-only snapshot. Empty future days are not outcomes; no replacement or fitted initialization. Daily budgets reconstructed from saved fields and actual recorded supplies. No monthly skill or physical adoption.')
    write_json(out/'progress_verification.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['daily','first_three_day_reproduction']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wet',type=Path,required=True);p.add_argument('--dry',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();monitor(a.wet,a.dry,a.out)
