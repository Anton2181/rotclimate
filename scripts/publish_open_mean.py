"""Publish the fixed open-mean boundary comparison and actual boundary budgets."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe_effect
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def load(path):
    with np.load(path) as f:return {k:f[k] for k in f.files}


def publish(out):
    receipt=json.loads((out/'verification.json').read_text());plan=json.loads((out/'frozen_plan.json').read_text());base=json.loads((ROOT/plan['boundary_plan']).read_text())
    literal=ROOT/'calibration/open_mean_20261029/plan.json'
    if file_hash(literal)!=receipt['literal_plan_sha256'] or literal.read_bytes()!=(out/'frozen_plan.json').read_bytes():raise ValueError('Changed open-mean declaration')
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed frozen open-mean source: '+n)
    if receipt['actual_earth_initialized_integrations_started']!=12 or receipt['integrations_completed']!=12 or receipt['adoption']:raise ValueError('Need all twelve unadopted outcomes')
    m0=-np.diff(base['pressure_edges_pa'])/9.80665;checks={};combined={};table=[];max_e=0.;max_w=0.;max_mass=0.;max_work=0.;max_backward=0.
    hgas=lambda t,w,m:float(((1004*m+1850*w)*t+(2.5e6-1850*273.15)*w).sum())
    ke=lambda u,v:float(.5*(np.sum(m0[:,None,None]*u[:,:,1:-1]**2)+np.sum(m0[:,None,None]*v[:,1:-1]**2)))
    fig,axes=plt.subplots(4,3,figsize=(15,14))
    for col,region in enumerate(plan['regions']):
        init=load(ROOT/base['regions'][region]['prior_pilot_folder']/'initial.npz');seed=load(out/region/'initial_winds.npz');conversion=json.loads((out/region/'conversion.json').read_text());regional=dict(conversion=conversion);runs={}
        cells=init['latitude'].size;mass=np.broadcast_to(m0[:,None,None],init['temperature'].shape)
        combined.update({region+'_initial_'+k:v for k,v in init.items()});combined.update({region+'_wind_'+k:v for k,v in seed.items()})
        for scenario in plan['scenarios']:
            bu,bv=seed[scenario+'_boundary_u'],seed[scenario+'_boundary_v']
            boundary_div=(np.diff(m0[:,None,None]*bu,axis=2)+np.diff(m0[:,None,None]*bv,axis=1)).sum(0)/base['cell_m']
            assert abs(boundary_div.sum())<1e-12
            change=(ke(seed[scenario+'_u'],seed[scenario+'_v'])-ke(seed[scenario+'_raw_u'],seed[scenario+'_raw_v']))/cells
            np.testing.assert_allclose(change,conversion['initial_wind_projection'][scenario]['kinetic_energy_change_j_m2'],rtol=1e-12,atol=1e-9)
            for dt in plan['timesteps_s']:
                folder=out/region/scenario;record=json.loads((folder/(str(dt)+'.json')).read_text());path=folder/(str(dt)+'.npz')
                if record['status']!='completed' or file_hash(path)!=record['fields_sha256']:raise ValueError('Missing or altered open-mean state')
                a=load(path);history=record['history'];assert len(history)==plan['duration_s']//dt
                np.testing.assert_array_equal(a['u'][:,:,[0,-1]],bu[:,:,[0,-1]]);np.testing.assert_array_equal(a['v'][:,[0,-1]],bv[:,[0,-1]])
                power=dt*sum(r['port_power_w_m2'] for r in history);water_out=dt*sum(r['outward_boundary_vapor_kg_m2_s'] for r in history)
                initial=hgas(init['temperature'],init['vapor'],mass)+ke(seed[scenario+'_u'],seed[scenario+'_v']);final=hgas(a['temperature'],a['vapor'],mass)+ke(a['u'],a['v'])+a['rain_enthalpy'].sum()
                ee=float(abs(final-initial-power*cells)/abs(initial));we=float(abs(a['vapor'].sum()+a['rain'].sum()-init['vapor'].sum()+water_out*cells)/init['vapor'].sum())
                div=(np.diff(a['u'],axis=2)+np.diff(a['v'],axis=1))/base['cell_m'];me=float(abs(np.sum(mass*div,axis=0)).max())
                pe=max(abs(r['constraint_pressure_work_w_m2']+r['outward_constraint_geopotential_work_w_m2']) for r in history)
                be=max(r['saddle_refinement']['maximum_final_rowwise_backward_error'] for r in history)
                max_e=max(max_e,ee);max_w=max(max_w,we);max_mass=max(max_mass,me);max_work=max(max_work,pe);max_backward=max(max_backward,be)
                edge=np.zeros(a['rain'].shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True
                c=dict(mean_run_rain_mm=float(a['rain'].mean()),outer_grid_rain_fraction=float(a['rain'][edge].sum()/a['rain'].sum()) if a['rain'].sum()>0 else None,
                    maximum_temperature_adjustment_k=float(abs(a['temperature']-init['temperature']).max()),net_imported_water_kg_m2=-water_out,
                    peak_mean_velocity_ms=float(max(abs(np.sum(m0[:,None,None]*f,axis=0)/m0.sum()).max() for f in [a['u'],a['v']])),
                    reconstructed_energy_relative_error=ee,reconstructed_water_relative_error=we,native_column_mass_residual_kg_m2_s=me,
                    constraint_internal_plus_boundary_work_error_w_m2=pe,block_scaled_rowwise_backward_error=be)
                regional[scenario+'_'+str(dt)]=c;runs[scenario+'_'+str(dt)]=a;combined.update({region+'_'+scenario+'_'+str(dt)+'_'+k:v for k,v in a.items()})
                table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{scenario.replace("_"," ")}</td><td>{dt}</td><td>{c["mean_run_rain_mm"]:.6f}</td><td>{100*c["outer_grid_rain_fraction"]:.1f}%</td><td>{c["maximum_temperature_adjustment_k"]:.2f}</td><td>{c["net_imported_water_kg_m2"]:.4f}</td></tr>')
        for component in ['u','v']:
            left,right=seed['closed_mean_ports_'+component],seed['open_mean_ports_'+component]
            anomaly=lambda q:q-np.sum(m0[:,None,None]*q,axis=0,keepdims=True)/m0.sum()
            np.testing.assert_allclose(anomaly(left),anomaly(right),atol=1e-10)
        for scenario in plan['scenarios']:
            fine,coarse=runs[scenario+'_450'],runs[scenario+'_900'];regional[scenario+'_timestep_rms']={k:float(np.sqrt(np.mean((fine[k]-coarse[k])**2))) for k in ['temperature','vapor','u','v','rain']}
        checks[region]=regional;closed,opened=runs['closed_mean_ports_450'],runs['open_mean_ports_450']
        fields=[closed['rain'],opened['rain'],opened['temperature'][0]-closed['temperature'][0],(opened['vapor']-closed['vapor']).sum(0)]
        rainmax=max(float(closed['rain'].max()),float(opened['rain'].max()),1e-10)
        for i,field in enumerate(fields):
            limit=max(float(abs(field).max()),1e-10);ax=axes[i,col]
            im=ax.pcolormesh(init['longitude'],init['latitude'],field,shading='nearest',cmap='RdBu_r' if i>=2 else 'YlGnBu',vmin=-limit if i>=2 else 0,vmax=limit if i>=2 else rainmax)
            coast=ax.contour(init['longitude'],init['latitude'],init['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.);coast.set_path_effects([pe_effect.withStroke(linewidth=2.6,foreground='white')])
            ax.set_title(region.replace('_',' ')+' — '+['closed mean: rain','open mean: rain','lowest-cell T difference','column water difference'][i],fontsize=10)
            ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');fig.colorbar(im,ax=ax,shrink=.8,label=['6 h rain (mm)','6 h rain (mm)','Open minus closed (K)','Open minus closed (kg/m²)'][i])
    if max(max_e,max_w)>1e-10 or max_backward>8*np.finfo(float).eps:raise ValueError('Open-mean actual budgets/precision failed')
    fig.suptitle('Allowing regional mean throughflow: paired six-hour Earth-input controls',fontsize=14)
    fig.text(.5,.01,'Identical baroclinic shear and initial T/water • explicit global dry-mass correction • actual constraint-pressure boundary work • no monthly skill score',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.97));fig.savefig(out/'open_mean.png',dpi=145);plt.close(fig);np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='verified_twelve_open_mean_boundary_runs',new_earth_input_smoke_integrations=12,cumulative_smoke_starts=54,cumulative_smoke_completed=50,cumulative_smoke_failures_retained=4,
        legacy_benchmark_attempts_added=0,monthly_skill=False,recalibration=False,adoption=False,cases=checks,maximum_reconstructed_energy_relative_error=max_e,maximum_reconstructed_water_relative_error=max_w,
        maximum_native_column_mass_residual_kg_m2_s=max_mass,maximum_constraint_work_plus_boundary_flux_error_w_m2=max_work,maximum_block_scaled_backward_error=max_backward,
        budget_scope='Final-state energy/water reconstructed against summed solver-recorded port scalars; not independent flux discretization. Signed affine projection KE changes separate.',
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),figure_sha256=file_hash(out/'open_mean.png'),publisher_sha256=file_hash(Path(__file__)),receipt_sha256=file_hash(out/'verification.json'))
    dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'publication_fields.npz',dest/'open_mean_fields.npz');shutil.copyfile(out/'open_mean.png',dest/'open_mean.png');write_json(dest/'open_mean.json',dict(plan=plan,runs=receipt,publication=result))
    with Image.open(out/'open_mean.png') as im:width,height=im.size
    section=f'''<!--open-mean-start--><section aria-labelledby="open-mean-h"><h2 id="open-mean-h">Mass-balanced mean flow through regional boundaries</h2>
<p>The regional boundary now permits vertically averaged flow, with globally zero net dry mass and explicit constraint-pressure work. The paired controls retain the same initial temperature, water and source baroclinic shear. Only the boundary mean and the initial mean flow needed to satisfy its mass constraint differ.</p>
<figure><a href="data/open_mean.png"><img src="data/open_mean.png" width="{width}" height="{height}" loading="lazy" alt="Three Earth regions comparing six-hour rainfall, temperature and column-water changes under closed versus open mean boundary flow"></a><figcaption>Finer450-second runs. Rain scales match within each region. Positive differences mean open minus closed. Initial conversion rain is excluded; no monthly rainfall skill evaluation.</figcaption></figure>
<div class="table"><table><caption>All twelve declared regional boundary controls</caption><thead><tr><th>Region</th><th>Boundary mean</th><th>Step s</th><th>Rain mm</th><th>Outer-cell rain</th><th>Max |ΔT| K</th><th>Net imported water kg/m²</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>Maximum startup temperature adjustments fall7.35→7.07 K in India,10.89→9.66 K in Mexico and13.21→10.01 K in the Pacific Northwest. This reduces a startup artifact but does not establish better monthly rainfall accuracy. Rainfall remains tiny and often concentrated at the perimeter. The open-boundary mean winds reach roughly5.5–6.5 m/s.</p>
<p>The archived <em>simulated</em> layer winds require an explicit uniform outward-speed correction of−0.0521/−0.00943/+0.2311 m/s to balance global boundary dry mass, preserving vertical shear. The model itself rejects unbalanced flow. Affine initial projection can add or remove kinetic energy; its signed change is recorded without hidden heat. The constraint pressure exchanges energy with the exterior; total geopotential boundary work includes its thermal and constraint parts. A uniform-throughflow test also checks the exact zero-transverse-mode limit of the mixed-unit linear solver.</p>
<p class="note">All twelve new cases completed;337 focused tests pass. The separate prototype smoke record is54 starts /50 completions /four retained numerical failures. The old1934/1929 benchmark, Earthr39 and normal world/biome/population fields remain unchanged. No recalibration or production adoption. Nonlinear momentum, variable surface pressure, resolved terrain, sustained surface/radiative forcing and balanced initialization remain limitations.</p>
<p><a href="data/open_mean.json" download>Download boundary declaration, twelve outcomes and budgets</a> · <a href="data/open_mean_fields.npz">Raw boundary, initial and final fields</a> · <a href="../../reports/OPEN_MEAN_20261029.md">Mean-flow boundary physics and interpretation</a></p></section><!--open-mean-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--open-mean-start-->','<!--open-mean-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);write_json(out/'publication.json',result);print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
