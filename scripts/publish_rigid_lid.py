"""Publish retained mean-flow controls, including the original failed attempts."""
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


def load(path):
    with np.load(path) as f:return {k:f[k] for k in f.files}


def publish(out):
    receipt=json.loads((out/'verification.json').read_text());plan=json.loads((out/'frozen_plan.json').read_text())
    literal=ROOT/'calibration/rigid_lid_refined_20261029/plan.json';prior=ROOT/'output/rigid_lid_20261029'
    first=json.loads((prior/'verification.json').read_text());base=json.loads((ROOT/plan['boundary_plan']).read_text())
    if file_hash(literal)!=receipt['literal_plan_sha256'] or literal.read_bytes()!=(out/'frozen_plan.json').read_bytes():raise ValueError('Changed refined rigid-lid declaration')
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed frozen rigid-lid source: '+n)
    if receipt['actual_earth_initialized_integrations_started']!=12 or receipt['integrations_completed']!=12 or receipt['adoption']:raise ValueError('Need all twelve repeat outcomes')
    if first['actual_earth_initialized_integrations_started']!=12 or first['integrations_completed']!=8:raise ValueError('Original failures lost')
    mass0=-np.diff(base['pressure_edges_pa'])/9.80665;combined={};checks={};rows=[];max_e=0.;max_w=0.;max_mass=0.;max_work=0.;max_backward=0.
    hgas=lambda t,w,m:float(((1004*m+1850*w)*t+(2.5e6-1850*273.15)*w).sum())
    kinetic=lambda u,v:float(.5*(np.sum(mass0[:,None,None]*u[:,:,1:-1]**2)+np.sum(mass0[:,None,None]*v[:,1:-1]**2)))
    fig,axes=plt.subplots(4,3,figsize=(15,14))
    for col,region in enumerate(plan['regions']):
        init=load(ROOT/base['regions'][region]['prior_pilot_folder']/'initial.npz');seed=load(out/region/'initial_winds.npz');oldseed=load(prior/region/'initial_winds.npz')
        for name in seed:np.testing.assert_array_equal(seed[name],oldseed[name])
        cells=init['latitude'].size;mass=np.broadcast_to(mass0[:,None,None],init['temperature'].shape)
        combined.update({region+'_initial_'+k:v for k,v in init.items()});combined.update({region+'_wind_'+k:v for k,v in seed.items()})
        projection=json.loads((out/region/'conversion.json').read_text())
        removed=(kinetic(seed['raw_u'],seed['raw_v'])-kinetic(seed['retained_mean_u'],seed['retained_mean_v']))/cells
        np.testing.assert_allclose(removed,projection['removed_kinetic_energy_j_m2'],rtol=1e-12)
        for component in ['u','v']:
            retained=seed['retained_mean_'+component];deviation=retained-np.sum(mass0[:,None,None]*retained,axis=0,keepdims=True)/mass0.sum()
            np.testing.assert_allclose(deviation,seed['no_mean_'+component],atol=1e-10)
        regional={};runs={}
        for scenario in plan['scenarios']:
            for dt in plan['timesteps_s']:
                folder=out/region/scenario;record=json.loads((folder/(str(dt)+'.json')).read_text());path=folder/(str(dt)+'.npz')
                if record['status']!='completed' or file_hash(path)!=record['fields_sha256']:raise ValueError('Altered or missing repeated state')
                a=load(path);history=record['history'];assert len(history)==plan['duration_s']//dt
                power=dt*sum(r['port_power_w_m2'] for r in history);water_out=dt*sum(r['outward_boundary_vapor_kg_m2_s'] for r in history)
                initial=hgas(init['temperature'],init['vapor'],mass)+kinetic(seed[scenario+'_u'],seed[scenario+'_v'])
                final=hgas(a['temperature'],a['vapor'],mass)+kinetic(a['u'],a['v'])+a['rain_enthalpy'].sum()
                energy_error=float(abs(final-initial-power*cells)/abs(initial));water_error=float(abs(a['vapor'].sum()+a['rain'].sum()-init['vapor'].sum()+water_out*cells)/init['vapor'].sum())
                div=(np.diff(a['u'],axis=2)+np.diff(a['v'],axis=1))/base['cell_m'];native_mass_error=float(abs(np.sum(mass*div,axis=0)).max())
                edge=np.zeros(a['rain'].shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True
                c=dict(mean_run_rain_mm=float(a['rain'].mean()),outer_grid_rain_fraction=float(a['rain'][edge].sum()/a['rain'].sum()) if a['rain'].sum()>0 else None,
                    maximum_temperature_adjustment_k=float(abs(a['temperature']-init['temperature']).max()),
                    peak_depth_mean_velocity_ms=float(max(abs(np.sum(mass0[:,None,None]*f,axis=0)/mass0.sum()).max() for f in [a['u'],a['v']])),
                    reconstructed_energy_relative_error=energy_error,reconstructed_water_relative_error=water_error,native_final_column_mass_residual_kg_m2_s=native_mass_error,
                    net_imported_water_kg_m2=-water_out,maximum_constraint_pressure_work_w_m2=max(abs(r['constraint_pressure_work_w_m2']) for r in history),
                    maximum_refined_rowwise_backward_error=max(r['saddle_refinement']['maximum_final_rowwise_backward_error'] for r in history))
                max_e=max(max_e,energy_error);max_w=max(max_w,water_error);max_mass=max(max_mass,native_mass_error);max_work=max(max_work,c['maximum_constraint_pressure_work_w_m2']);max_backward=max(max_backward,c['maximum_refined_rowwise_backward_error'])
                np.testing.assert_allclose(c['mean_run_rain_mm'],record['mean_run_rain_mm'],rtol=1e-12)
                oldrecord=json.loads((prior/region/scenario/(str(dt)+'.json')).read_text())
                if oldrecord['status']=='completed':
                    oldpath=prior/region/scenario/(str(dt)+'.npz');assert file_hash(oldpath)==oldrecord['fields_sha256'];old=load(oldpath)
                    c['original_completed_repeat_temperature_max_difference_k']=float(abs(a['temperature']-old['temperature']).max())
                else:
                    oldpath=prior/region/scenario/(str(dt)+'_partial.npz');assert file_hash(oldpath)==oldrecord['partial_fields_sha256'];old=load(oldpath)
                combined.update({region+'_first_'+scenario+'_'+str(dt)+'_'+k:v for k,v in old.items()})
                combined.update({region+'_'+scenario+'_'+str(dt)+'_'+k:v for k,v in a.items()});key=scenario+'_'+str(dt);regional[key]=c;runs[key]=a
                rows.append(f'<tr><td>{region.replace("_"," ")}</td><td>{scenario.replace("_"," ")}</td><td>{dt}</td><td>{c["mean_run_rain_mm"]:.6f}</td><td>{100*c["outer_grid_rain_fraction"]:.1f}%</td><td>{c["maximum_temperature_adjustment_k"]:.2f}</td><td>{c["peak_depth_mean_velocity_ms"]:.2f}</td></tr>')
        for scenario in plan['scenarios']:
            fine,coarse=runs[scenario+'_450'],runs[scenario+'_900'];regional[scenario+'_timestep_rms']={k:float(np.sqrt(np.mean((fine[k]-coarse[k])**2))) for k in ['temperature','vapor','u','v','rain']}
        checks[region]=regional;no,yes=runs['no_mean_450'],runs['retained_mean_450']
        uc=.5*(yes['u'][:,:,:-1]+yes['u'][:,:,1:]);vc=.5*(yes['v'][:,:-1]+yes['v'][:,1:]);speed=np.hypot(np.sum(mass*uc,axis=0)/mass0.sum(),np.sum(mass*vc,axis=0)/mass0.sum())
        fields=[no['rain'],yes['rain'],yes['temperature'][0]-no['temperature'][0],speed]
        rainmax=max(float(no['rain'].max()),float(yes['rain'].max()),1e-10)
        for i,field in enumerate(fields):
            ax=axes[i,col];delta=i==2;limit=max(float(abs(field).max()),1e-10)
            image=ax.pcolormesh(init['longitude'],init['latitude'],field,shading='nearest',cmap='RdBu_r' if delta else 'YlGnBu',vmin=-limit if delta else 0,vmax=limit if i>1 else rainmax)
            coast=ax.contour(init['longitude'],init['latitude'],init['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.);coast.set_path_effects([pe.withStroke(linewidth=2.6,foreground='white')])
            ax.set_title(region.replace('_',' ')+' — '+['no mean: rain','retained mean: rain','lowest-cell T difference','retained mean wind speed'][i],fontsize=10)
            ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');fig.colorbar(image,ax=ax,shrink=.8,label=['6 h rain (mm)','6 h rain (mm)','Retained minus no mean (K)','Mean wind (m/s)'][i])
    if max(max_e,max_w)>1e-10 or max_backward>8*np.finfo(float).eps:raise ValueError('Repeated actual budgets/precision failed')
    fig.suptitle('Retaining divergence-free mean circulation: paired six-hour Earth-input controls',fontsize=14)
    fig.text(.5,.01,'Same initial T, water and vertical shear • original four numerical failures retained • refined repeat of all12 cases • no monthly climate skill score',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.97));fig.savefig(out/'rigid_lid.png',dpi=145);plt.close(fig)
    np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='verified_twelve_refined_mean_flow_runs_with_original_failures',new_repeat_earth_integrations=12,
        original_mean_flow_attempts=12,original_mean_flow_completed=8,original_mean_flow_failures_retained=4,
        cumulative_earth_input_smoke_starts=42,cumulative_earth_input_smoke_completed=38,cumulative_earth_input_smoke_failures=4,
        legacy_benchmark_attempts_added=0,monthly_skill=False,recalibration=False,adoption=False,cases=checks,
        maximum_reconstructed_energy_relative_error=max_e,maximum_reconstructed_water_relative_error=max_w,
        maximum_native_final_column_mass_residual_kg_m2_s=max_mass,maximum_constraint_pressure_work_w_m2=max_work,maximum_refined_rowwise_backward_error=max_backward,
        budget_scope='Final energy/water independently reconstructed against summed solver-recorded port scalars; not independent flux discretization. Projection KE removal separate from integration budgets.',
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),figure_sha256=file_hash(out/'rigid_lid.png'),publisher_sha256=file_hash(Path(__file__)),receipt_sha256=file_hash(out/'verification.json'))
    dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'publication_fields.npz',dest/'rigid_lid_fields.npz');shutil.copyfile(out/'rigid_lid.png',dest/'rigid_lid.png');write_json(dest/'rigid_lid.json',dict(plan=plan,original_attempts=first,refined_repeat=receipt,publication=result))
    with Image.open(out/'rigid_lid.png') as im:width,height=im.size
    section=f'''<!--rigid-lid-start--><section aria-labelledby="rigid-lid-h"><h2 id="rigid-lid-h">Retaining the vertically averaged circulation</h2>
<p>The pressure prototype now permits a divergence-free vertically averaged wind instead of forcing that wind to zero everywhere. A constraint pressure enforces fixed-column mass without doing work. The paired controls retain identical initial temperature, water and vertical wind shear; only the nondivergent mean circulation differs. Both archived <em>simulated</em> lower and upper winds are used, with no observed wind or rain input.</p>
<figure><a href="data/rigid_lid.png"><img src="data/rigid_lid.png" width="{width}" height="{height}" loading="lazy" alt="Three Earth regions comparing six-hour rain with and without retained mean circulation, temperature differences and final mean wind speed"></a><figcaption>Finer450-second runs. Rain scales match within each region. Initial projection's removed kinetic energy is recorded separately; no hidden heat compensation or balanced-initialization claim.</figcaption></figure>
<div class="table"><table><caption>All twelve refined paired runs</caption><thead><tr><th>Region</th><th>Initial mean flow</th><th>Step s</th><th>Rain mm</th><th>Outer-cell rain</th><th>Max |ΔT| K</th><th>Peak mean wind m/s</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p><strong>The first attempt remains part of the record.</strong> Eight of twelve original cases completed; four finer-step cases stopped on the unchanged native pressure-lid mass check. A complete twelve-case repeat uses the same equations, inputs, parameters, steps and physical tolerances, with three residual-correction solves evaluated at higher precision. All repeated cases completed. The old failed histories and partial fields are downloadable; the repeat does not erase them.</p>
<p class="note">This is a rigid-lid mean-flow extension, not variable surface pressure, nonlinear momentum advection or full thermal/moist balance. The prescribed boundary mean flow is still closed, so no free barotropic inflow is claimed. Constraint pressure work, native column mass, gas/kinetic/rain energy and water are checked. Forty-two separate prototype smoke starts comprise38 completions and four numerical failures. The legacy1934/1929 benchmark, Earthr39 and normal world/biome/population fields remain unchanged; no monthly rainfall skill or calibration gain is claimed.</p>
<p><a href="data/rigid_lid.json" download>Download both attempts, all outcomes and precision checks</a> · <a href="data/rigid_lid_fields.npz">Raw paired states and original failed partial states</a> · <a href="../../reports/RIGID_LID_20261029.md">Mean-flow physics, numerical failures and interpretation</a></p></section><!--rigid-lid-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--rigid-lid-start-->','<!--rigid-lid-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);write_json(out/'publication.json',result);print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
