"""Verify and publish the fixed three-day soil-water sensitivity experiment."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from surface_spinup_pilot import prepare
from monitor_surface_spinup import monitor,load


def publish(wet,dry,out):
    out.mkdir(parents=True,exist_ok=True);folders=dict(wet=wet,dry=dry);receipts={};plans={};checks={};combined={};table=[];max_e=0.;max_w=0.;max_evap=0.
    fig,axes=plt.subplots(4,3,figsize=(15,12));regions=['north_india','mexico','pacific_nw'];timesteps={}
    for kind,folder in folders.items():
        receipt=json.loads((folder/'verification.json').read_text());plan=json.loads((folder/'frozen_plan.json').read_text());literal=ROOT/'calibration/surface_spinup_20261029'/(kind+'_plan.json')
        expected=6 if kind=='wet' else 3
        if literal.read_bytes()!=(folder/'frozen_plan.json').read_bytes() or file_hash(literal)!=receipt['literal_plan_sha256']:raise ValueError('Changed literal spinup declaration')
        if receipt['actual_earth_initialized_integrations_started']!=expected or receipt['integrations_completed']!=expected or receipt['adoption']:raise ValueError('Need every declared completed spinup case')
        for n,h in plan['sources'].items():
            if file_hash(ROOT/n)!=h:raise ValueError('Changed frozen spinup source: '+n)
        plans[kind]=plan;receipts[kind]=receipt
        base=json.loads((ROOT/plan['boundary_plan']).read_text());m0=-np.diff(base['pressure_edges_pa'])/9.80665
        hgas=lambda a,m:float(((1004*m+1850*a['vapor'])*a['temperature']+(2.5e6-1850*273.15)*a['vapor']).sum())
        hs=lambda a:float(((a['substrate_capacity']+4186*a['surface_liquid'])*(a['surface_temperature']-273.15)).sum())
        ke=lambda a:float(.5*(np.sum(m0[:,None,None]*a['u'][:,:,1:-1]**2)+np.sum(m0[:,None,None]*a['v'][:,1:-1]**2)))
        kind_checks={}
        for col,region in enumerate(regions):
            init=load(folder/region/'initial.npz');_,a,model,initial,surface,*_=prepare(plan,region)
            for k,v in [('temperature',initial.temperature_k),('vapor',initial.vapor_kg_m2),('u',initial.u_east),('v',initial.v_south),('surface_temperature',surface.temperature_k),('surface_liquid',surface.liquid_kg_m2)]:np.testing.assert_array_equal(init[k],v)
            combined.update({kind+'_'+region+'_initial_'+k:v for k,v in init.items()});mass=np.broadcast_to(m0[:,None,None],init['temperature'].shape);cells=init['latitude'].size
            e0=hgas(init,mass)+hs(init)+ke(init);w0=float(init['vapor'].sum()+init['surface_liquid'].sum());land=init['land'].astype(bool)
            for dt in plan['timesteps_s']:
                path=folder/region/'forced'/f'{dt}.npz';row=json.loads((folder/region/'forced'/f'{dt}.json').read_text());assert file_hash(path)==row['fields_sha256']
                if row['status']!='completed' or row['steps']!=259200//dt or len(row['daily'])!=3:raise ValueError('Incomplete spinup state')
                final=load(path);daily=[];previous=init;previous_out=0.;evap_total=0.
                for day in [1,2,3]:
                    f=folder/region/'forced'/f'day_{day}_{dt}.npz';record=json.loads((folder/region/'forced'/f'day_{day}_{dt}.json').read_text());assert file_hash(f)==record['fields_sha256'];current=load(f)
                    np.testing.assert_allclose(current['day_rain'],current['rain']-previous.get('rain',np.zeros_like(current['rain'])),atol=1e-12)
                    energy=hgas(current,mass)+hs(current)+ke(current);water=float(current['vapor'].sum()+current['surface_liquid'].sum())
                    ee=abs(energy-e0-record['net_external_energy_j_m2']*cells)/abs(e0);we=abs(water-w0+record['net_outward_water_kg_m2']*cells)/w0
                    evap=current['day_rain']-(current['surface_liquid']-previous['surface_liquid']);evap_error=float(abs(evap.mean()-record['net_evaporation_kg_m2']));evap_total+=record['net_evaporation_kg_m2']
                    convergence=(current['vapor']-previous['vapor']).sum(0)+current['surface_liquid']-previous['surface_liquid']
                    np.testing.assert_allclose(convergence.mean(),-(record['net_outward_water_kg_m2']-previous_out),atol=1e-8)
                    max_e=max(max_e,ee);max_w=max(max_w,we);max_evap=max(max_evap,evap_error)
                    daily.append(dict(day=day,land_rain_mm=float(current['day_rain'][land].mean()),land_net_evaporation_kg_m2=float(evap[land].mean()),
                        mean_land_liquid_kg_m2=float(current['surface_liquid'][land].mean()),mean_land_temperature_k=float(current['surface_temperature'][land].mean()),
                        mean_net_column_water_import_kg_m2=float(convergence.mean()),reconstructed_energy_relative_error=float(ee),reconstructed_water_relative_error=float(we)))
                    combined.update({kind+'_'+region+'_'+str(dt)+'_day_'+str(day)+'_'+k:v for k,v in current.items()});previous=current;previous_out=record['net_outward_water_kg_m2']
                for k in final:np.testing.assert_array_equal(final[k],previous[k])
                key=region+'_'+str(dt);kind_checks[key]=dict(daily=daily,final_cumulative_rain_mm=float(final['rain'].mean()),final_mean_atmospheric_water_kg_m2=float(final['vapor'].sum(0).mean()),cumulative_net_evaporation_kg_m2=evap_total)
                if kind=='wet':timesteps[region+'_'+str(dt)]=final
                last=daily[-1];table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{kind}</td><td>{dt}</td>'+''.join(f'<td>{d["land_rain_mm"]:.3f}</td>' for d in daily)+f'<td>{last["mean_land_liquid_kg_m2"]:.2f}</td><td>{last["mean_land_temperature_k"]:.2f}</td></tr>')
                color='#ca7729' if kind=='dry' else ('#1675a6' if dt==450 else '#65a8bb');style='--' if dt==900 and kind=='wet' else '-';label=f'{kind}, {dt}s'
                for i,field in enumerate(['land_rain_mm','land_net_evaporation_kg_m2','mean_land_liquid_kg_m2','mean_land_temperature_k']):axes[i,col].plot([1,2,3],[d[field] for d in daily],style+'o',color=color,label=label)
        checks[kind]=kind_checks
    if max(max_e,max_w)>1e-10 or max_evap>1e-8:raise ValueError('Saved spinup energy/water/surface budget failed')
    differences={}
    for col,region in enumerate(regions):
        fine,coarse=timesteps[region+'_450'],timesteps[region+'_900']
        differences[region]={k:float(np.sqrt(np.mean((fine[k]-coarse[k])**2))) for k in ['temperature','vapor','u','v','rain','surface_temperature','surface_liquid']}
        fine_day=combined['wet_'+region+'_450_day_3_day_rain'];coarse_day=combined['wet_'+region+'_900_day_3_day_rain']
        differences[region]['day3_rain_rms_mm']=float(np.sqrt(np.mean((fine_day-coarse_day)**2)))
        for i in range(4):axes[i,col].set_xlabel('Completed day');axes[i,col].set_xticks([1,2,3]);axes[i,col].grid(alpha=.2);axes[i,col].set_ylabel(['Land daily rain (mm)','Land daily net evaporation (kg/m²)','Land liquid storage (kg/m²)','Land surface temperature (K)'][i])
        axes[0,col].set_title(region.replace('_',' '));axes[0,col].legend(fontsize=8)
    fig.suptitle('Three-day spinup: initial land water changes the rain and heat cycle',fontsize=14);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/'surface_spinup_series.png',dpi=145);plt.close(fig)
    monitored=monitor(wet,dry,out/'monitor',final=True);shutil.copyfile(ROOT/monitored['figure'],out/'surface_spinup_water.png')
    reproduction=monitored['wet_first_day_reproduction'];assert len(reproduction)==6
    np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='verified_nine_three_day_spinup_cases',new_earth_input_smoke_starts=9,new_completed=9,new_failures=0,cumulative_smoke_starts=75,cumulative_smoke_completed=71,cumulative_smoke_failures_retained=4,
        legacy_benchmark_attempts_added=0,monthly_skill=False,recalibration=False,adoption=False,cases=checks,wet_timestep_rms=differences,
        maximum_actual_energy_relative_error=float(max_e),maximum_actual_water_relative_error=float(max_w),maximum_daily_surface_rain_evap_identity_error_kg_m2=max_evap,wet_first_day_reproduction=reproduction,
        scope='Frozen inputs checked; saved daily energy/water budgets reconstructed against recorded net exterior supply. Day-three48–72h window, not equilibrium or monthly skill. Dry900 is a coarse initial-condition screen; wet900/450 quantify timestep sensitivity.',
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),series_sha256=file_hash(out/'surface_spinup_series.png'),water_map_sha256=file_hash(out/'surface_spinup_water.png'),publisher_sha256=file_hash(Path(__file__)),receipts_sha256={n:file_hash(p/'verification.json') for n,p in folders.items()})
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data'
    for source,name in [('publication_fields.npz','surface_spinup_fields.npz'),('surface_spinup_series.png','surface_spinup_series.png'),('surface_spinup_water.png','surface_spinup_water.png')]:shutil.copyfile(out/source,dest/name)
    write_json(dest/'surface_spinup.json',dict(plans=plans,runs=receipts,publication=result,water_budget_maps=monitored))
    figures=''
    for name,alt in [('surface_spinup_series.png','Land rain, evaporation, liquid storage and temperature over three days for wet and dry initial land'),('surface_spinup_water.png','Day-three wet and dry rainfall, inferred evaporation and net horizontal column-water convergence')]:
        with Image.open(out/name) as im:width,height=im.size
        figures+=f'<figure><a href="data/{name}"><img src="data/{name}" width="{width}" height="{height}" loading="lazy" alt="{alt}"></a></figure>'
    section=f'''<!--surface-spinup-start--><section aria-labelledby="surface-spinup-h"><h2 id="surface-spinup-h">Three-day spinup and initial land-water uncertainty</h2>
<p>Nine fixed72-hour Earth-input smoke runs compare initially dry land with the50 kg/m² wet baseline, while keeping the source atmosphere, wind, forcing physics and boundary fields fixed. Wet cases use900 and450 seconds; the dry900-second branch is a coarse sensitivity screen. Initial pressure-conversion rain is credited before the run in both cases.</p>
{figures}
<div class="table"><table><caption>All nine completed cases; daily land means, not monthly rainfall estimates</caption><thead><tr><th>Region</th><th>Initial land</th><th>Step s</th><th>Day1 rain mm</th><th>Day2 rain mm</th><th>Day3 rain mm</th><th>Final land liquid kg/m²</th><th>Final land T K</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p><strong>The initial land-water store still strongly controls rainfall after three days.</strong> At900 seconds, day-three land rain is1.318 versus0.065 mm in India,1.353 versus0.403 mm in Mexico and1.635 versus0.183 mm in the Pacific Northwest (wet versus dry). Wet storage remains about40–46 kg/m² while dry land contains only about0.3–2.4 kg/m². Wet land is roughly4–6 K cooler. These are transient initial-state differences, not proof of multiple stable climates or an optimizer trap.</p>
<p>The water maps use actual daily identities: evaporation equals rain minus surface-water change, and net horizontal column-water input equals the change in total atmospheric plus surface water. These are integrated net budgets, not moisture-origin tags. Six wet first-day checkpoints reproduce the preceding24-hour experiment at the same timestep. Mean rainfall sensitivity to initial water is much greater than the wet-branch timestep difference, while local rain still requires numerical assessment.</p>
<p class="note">356 focused physics tests remain valid; no physical source changed for this longer test. All nine attempts completed, retaining the four earlier failures in the separate75 starts /71 completions /four-failure prototype record. Legacy1934/1929 and normal Earthr39/world/biome/population fields remain unchanged. No steady-state guarantee, monthly climate score, calibration or adoption. Land-water availability and heat capacity both change with the initial storage; grey radiation, partial upper atmosphere, neutral exchange, flat terrain and omitted nonlinear momentum remain approximations.</p>
<p><a href="data/surface_spinup.json" download>Download both frozen plans, nine runs and daily budget checks</a> · <a href="data/surface_spinup_fields.npz">Raw daily atmospheric/surface states</a> · <a href="../../reports/SURFACE_SPINUP_20261029.md">Initial-state uncertainty, reproducibility and next steps</a></p></section><!--surface-spinup-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--surface-spinup-start-->','<!--surface-spinup-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps({k:v for k,v in result.items() if k not in ['cases','wet_timestep_rms','wet_first_day_reproduction']},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--wet',type=Path,required=True);ap.add_argument('--dry',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();publish(a.wet.resolve(),a.dry.resolve(),a.out.resolve())
