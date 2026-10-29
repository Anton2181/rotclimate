"""Publish completed and failed24h surface-forcing attempts with actual budgets."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from surface_forcing_pilot import prepare


def load(path):
    with np.load(path) as f:return {k:f[k] for k in f.files}


def publish(out):
    receipt=json.loads((out/'verification.json').read_text());plan=json.loads((out/'frozen_plan.json').read_text());base=json.loads((ROOT/plan['boundary_plan']).read_text())
    literal=ROOT/'calibration/surface_forcing_20261029/plan.json'
    if file_hash(literal)!=receipt['literal_plan_sha256'] or literal.read_bytes()!=(out/'frozen_plan.json').read_bytes():raise ValueError('Changed forcing declaration')
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed frozen forcing source: '+n)
    if receipt['actual_earth_initialized_integrations_started']!=12 or receipt['adoption']:raise ValueError('Need every declared unadopted attempt')
    hgas=lambda t,w,m:float(((1004*m+1850*w)*t+(2.5e6-1850*273.15)*w).sum())
    hsurf=lambda a:float(((a['substrate_capacity']+4186*a['surface_liquid'])*(a['surface_temperature']-273.15)).sum())
    m0=-np.diff(base['pressure_edges_pa'])/9.80665
    ke=lambda a:float(.5*(np.sum(m0[:,None,None]*a['u'][:,:,1:-1]**2)+np.sum(m0[:,None,None]*a['v'][:,1:-1]**2)))
    combined={};checks={};table=[];max_e=0.;max_w=0.;max_surface_water=0.;failures=[]
    fig,axes=plt.subplots(3,3,figsize=(15,11));series,saxes=plt.subplots(3,3,figsize=(15,10))
    for col,region in enumerate(plan['regions']):
        init=load(out/region/'initial.npz');_,a,model,initial,surface,_,_,_,_,_=prepare(plan,region)
        for k,v in [('temperature',initial.temperature_k),('vapor',initial.vapor_kg_m2),('u',initial.u_east),('v',initial.v_south),('surface_temperature',surface.temperature_k),('surface_liquid',surface.liquid_kg_m2),('substrate_capacity',surface.substrate_capacity_j_m2_k)]:
            np.testing.assert_array_equal(init[k],v)
        combined.update({region+'_initial_'+k:v for k,v in init.items()});mass=np.broadcast_to(m0[:,None,None],init['temperature'].shape);cells=init['latitude'].size
        initial_e=hgas(init['temperature'],init['vapor'],mass)+ke(init)+hsurf(init);initial_w=float(init['vapor'].sum()+init['surface_liquid'].sum());regional={};runs={};records={}
        for scenario in plan['scenarios']:
            for dt in plan['timesteps_s']:
                folder=out/region/scenario;row=json.loads((folder/(str(dt)+'.json')).read_text());complete=row['status']=='completed'
                path=folder/(str(dt)+('.npz' if complete else '_partial.npz'));assert file_hash(path)==row['fields_sha256' if complete else 'partial_fields_sha256']
                final=load(path);history=row['history'];steps=row['steps'] if complete else row['completed_steps'];assert len(history)==steps
                if complete and steps!=plan['duration_s']//dt:raise ValueError('Wrong completed duration')
                external=history[-1]['cumulative_net_external_energy_j_m2'] if history else 0.;water_out=history[-1]['cumulative_outward_water_kg_m2'] if history else 0.;evap=history[-1]['cumulative_net_evaporation_kg_m2'] if history else 0.
                energy=hgas(final['temperature'],final['vapor'],mass)+ke(final)+hsurf(final);water=float(final['vapor'].sum()+final['surface_liquid'].sum())
                ee=abs(energy-initial_e-external*cells)/abs(initial_e);we=abs(water-initial_w+water_out*cells)/initial_w
                swe=abs(float((final['surface_liquid']-init['surface_liquid']).mean()-final['rain'].mean()+evap))
                max_e=max(max_e,ee);max_w=max(max_w,we);max_surface_water=max(max_surface_water,swe)
                edge=np.zeros(model.shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True;land=init['land'].astype(bool);interior_land=land&~edge
                c=dict(status=row['status'],completed_hours=steps*dt/3600,energy_relative_error=float(ee),water_relative_error=float(we),surface_rain_evap_identity_error_kg_m2=swe,
                    mean_run_rain_mm=float(final['rain'].mean()),land_mean_run_rain_mm=float(final['rain'][land].mean()),interior_land_mean_run_rain_mm=float(final['rain'][interior_land].mean()) if interior_land.any() else None,
                    outer_grid_rain_fraction=float(final['rain'][edge].sum()/final['rain'].sum()) if final['rain'].sum()>0 else None,
                    mean_net_evaporation_kg_m2=evap,maximum_atmospheric_temperature_change_k=float(abs(final['temperature']-init['temperature']).max()),
                    maximum_surface_temperature_change_k=float(abs(final['surface_temperature']-init['surface_temperature']).max()))
                if not complete:c['error']=row['error'];failures.append(dict(region=region,scenario=scenario,dt_s=dt,completed_hours=c['completed_hours'],error=row['error']))
                key=scenario+'_'+str(dt);regional[key]=c;runs[key]=final;records[key]=row;combined.update({region+'_'+key+'_'+k:v for k,v in final.items()})
                outer='—' if c['outer_grid_rain_fraction'] is None else f'{100*c["outer_grid_rain_fraction"]:.1f}%'
                table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{scenario}</td><td>{dt}</td><td>{row["status"]}, {c["completed_hours"]:.2f} h</td><td>{c["mean_run_rain_mm"]:.4f}</td><td>{c["land_mean_run_rain_mm"]:.4f}</td><td>{outer}</td><td>{evap:.3f}</td><td>{c["maximum_surface_temperature_change_k"]:.2f}</td></tr>')
                if history:
                    time=np.array([r['time_s'] for r in history])/3600;style='-' if scenario=='forced' else '--';color='#1675a6' if dt==450 else '#ca7729';label=f'{scenario}, {dt}s'
                    for i,field in enumerate(['mean_rain_mm','mean_surface_temperature_k','cumulative_net_evaporation_kg_m2']):saxes[i,col].plot(time,[r[field] for r in history],linestyle=style,color=color,label=label)
        for scenario in plan['scenarios']:
            if all(records[scenario+'_'+str(dt)]['status']=='completed' for dt in plan['timesteps_s']):
                fine,coarse=runs[scenario+'_450'],runs[scenario+'_900'];regional[scenario+'_timestep_rms']={k:float(np.sqrt(np.mean((fine[k]-coarse[k])**2))) for k in ['temperature','vapor','u','v','rain','surface_temperature','surface_liquid']}
        checks[region]=regional;closed,forced=runs['unforced_450'],runs['forced_450'];rainmax=max(float(closed['rain'].max()),float(forced['rain'].max()),1e-10)
        fields=[closed['rain'],forced['rain'],forced['surface_temperature']-init['surface_temperature']]
        for i,field in enumerate(fields):
            ax=axes[i,col];delta=i==2;limit=max(float(abs(field).max()),1e-10)
            im=ax.pcolormesh(init['longitude'],init['latitude'],field,shading='nearest',cmap='RdBu_r' if delta else 'YlGnBu',vmin=-limit if delta else 0,vmax=limit if delta else rainmax)
            coast=ax.contour(init['longitude'],init['latitude'],init['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.);coast.set_path_effects([pe.withStroke(linewidth=2.6,foreground='white')])
            key='unforced_450' if i==0 else 'forced_450';c=regional[key];title=['unforced rain','forced rain','forced surface ΔT'][i]
            ax.set_title(region.replace('_',' ')+f' — {title}, {c["completed_hours"]:g} h'+(' PARTIAL' if c['status']!='completed' else ''),fontsize=10)
            fig.colorbar(im,ax=ax,shrink=.8,label='Temperature change (K)' if delta else 'Run rain (mm)');ax.set_xlabel('Longitude');ax.set_ylabel('Latitude')
        for i in range(3):
            ax=saxes[i,col];ax.set_xlabel('Hours');ax.set_ylabel(['Cumulative rain (mm)','Mean surface temperature (K)','Cumulative net evaporation (kg/m²)'][i]);ax.grid(alpha=.2)
        saxes[0,col].set_title(region.replace('_',' '));saxes[0,col].legend(fontsize=8)
    if max(max_e,max_w)>1e-10 or max_surface_water>1e-8:raise ValueError('Saved air/surface/kinetic/radiation/port budgets failed')
    fig.suptitle('Sustained surface and radiative forcing: fixed day-long Earth-input controls',fontsize=14)
    fig.text(.5,.01,'Finite surface water and heat • explicit partial upper boundary, not TOA • all rain returned with enthalpy • no monthly accuracy score',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(out/'surface_forcing_maps.png',dpi=145);plt.close(fig)
    series.suptitle('Day-long rain and surface response: both fixed timesteps and both forcing controls',fontsize=14)
    series.tight_layout(rect=(0,0,1,.96));series.savefig(out/'surface_forcing_series.png',dpi=145);plt.close(series);np.savez_compressed(out/'publication_fields.npz',**combined)
    completed=receipt['integrations_completed'];result=dict(status='verified_all_twelve_forcing_attempts',new_earth_input_smoke_starts=12,new_completed=completed,new_failures=12-completed,
        cumulative_smoke_starts=66,cumulative_smoke_completed=50+completed,cumulative_smoke_failures=4+12-completed,legacy_benchmark_attempts_added=0,monthly_skill=False,recalibration=False,adoption=False,cases=checks,failures=failures,
        maximum_actual_energy_relative_error=float(max_e),maximum_actual_water_relative_error=float(max_w),maximum_surface_rain_evap_identity_error_kg_m2=max_surface_water,
        scope='Inputs checked against frozen preparation; actual saved gas/kinetic/surface budgets reconstructed against separately recorded net radiation/port supply. Not independent flux discretization or monthly climate validation.',
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),maps_sha256=file_hash(out/'surface_forcing_maps.png'),series_sha256=file_hash(out/'surface_forcing_series.png'),publisher_sha256=file_hash(Path(__file__)),receipt_sha256=file_hash(out/'verification.json'))
    dest=ROOT/'atlases/climate_accuracy/data'
    for source,name in [('publication_fields.npz','surface_forcing_fields.npz'),('surface_forcing_maps.png','surface_forcing_maps.png'),('surface_forcing_series.png','surface_forcing_series.png')]:shutil.copyfile(out/source,dest/name)
    write_json(dest/'surface_forcing.json',dict(plan=plan,runs=receipt,publication=result))
    figures=''
    for name,alt in [('surface_forcing_maps.png','Unforced and forced day-long rainfall and surface temperature change in three Earth regions'),('surface_forcing_series.png','Rain, surface temperature and net evaporation through the full run, both timesteps and forcing controls')]:
        with Image.open(out/name) as im:width,height=im.size
        figures+=f'<figure><a href="data/{name}"><img src="data/{name}" width="{width}" height="{height}" loading="lazy" alt="{alt}"></a></figure>'
    section=f'''<!--surface-forcing-start--><section aria-labelledby="surface-forcing-h"><h2 id="surface-forcing-h">Day-long surface heat, water and radiation coupling</h2>
<p>The regional prototype now has a finite surface liquid/heat reservoir and sustained grey radiation plus neutral surface exchange. Evaporation and dew transfer actual vapor enthalpy; rain returns mass and actual liquid enthalpy exactly once, changing surface heat capacity. The fixed24-hour controls share initial T/water, model-assisted wind, surface state and lateral boundaries; no observed fields or rainfall targets are used.</p>
{figures}
<div class="table"><table><caption>Every declared forcing attempt, with actual duration; partial cases must not be read as24-hour rainfall</caption><thead><tr><th>Region</th><th>Forcing</th><th>Step s</th><th>Outcome</th><th>Mean rain mm</th><th>Land rain mm</th><th>Outer-cell rain</th><th>Net evaporation kg/m²</th><th>Max surface |ΔT| K</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>Six-hour smoke rainfall was a startup diagnostic, not a steady climate pattern: India's unforced24-hour finer control alone produces about0.50 mm with roughly28% falling inside the perimeter. Longer forcing comparisons should separate spinup behavior from later rainfall rather than treating early edge concentration as a climate skill score. More rainfall under forcing does not by itself mean greater accuracy.</p>
<p class="note">Grey optical depths, surface storage and neutral roughness are declared exploratory choices. The380hPa top has explicitly prescribed radiation from omitted upper air and is not called TOA. No temperature restoration, spectral/cloud/stability/gust/ice/runoff/deep-ocean closure, resolved terrain or nonlinear momentum. All {completed} completed and {12-completed} failed new cases are retained. The separate prototype totals are66 starts /{50+completed} completions /{4+12-completed} retained failures, including four earlier numerical failures; legacy1934/1929 and normal Earthr39/world/biome/population fields remain unchanged. No monthly climate calibration or production adoption.</p>
<p><a href="data/surface_forcing.json" download>Download frozen forcing declaration, all attempts and budgets</a> · <a href="data/surface_forcing_fields.npz">Raw atmospheric/surface initial and final states</a> · <a href="../../reports/SURFACE_FORCING_20261029.md">Forcing assumptions, surface response and rainfall interpretation</a></p></section><!--surface-forcing-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--surface-forcing-start-->','<!--surface-forcing-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);write_json(out/'publication.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['cases','failures']},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
