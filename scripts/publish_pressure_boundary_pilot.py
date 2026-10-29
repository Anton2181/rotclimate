"""Reconstruct state budgets and publish the frozen boundary/initial-wind controls."""
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
    literal=ROOT/'calibration/pressure_boundary_pilot_20261029/plan.json'
    if file_hash(literal)!=receipt['literal_plan_sha256'] or literal.read_bytes()!=(out/'frozen_plan.json').read_bytes():
        raise ValueError('Boundary declaration changed')
    for name,h in plan['sources'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Changed frozen boundary source: '+name)
    if receipt['actual_earth_initialized_integrations_started']!=12 or receipt['integrations_completed']!=12:
        raise ValueError('All declared cases must be retained and completed for this publication')
    if receipt['physics_or_atlas_adoption'] or receipt['monthly_rainfall_skill_evaluated'] or receipt['legacy_earth_benchmark_attempts_added']:
        raise ValueError('Boundary smoke tests are unscored research')
    masses=-np.diff(plan['pressure_edges_pa'])/9.80665
    energy=lambda t,w,m:((1004*m+1850*w)*t+(2.5e6-1850*273.15)*w).sum()
    ke=lambda a:float(.5*(np.sum(masses[:,None,None]*a['u'][:,:,1:-1]**2)+np.sum(masses[:,None,None]*a['v'][:,1:-1]**2)))
    checks={};combined={};all_checks=[];table=[]
    fig,axes=plt.subplots(3,3,figsize=(15,11.5))
    for col,(region,spec) in enumerate(plan['regions'].items()):
        init=load(ROOT/spec['prior_pilot_folder']/'initial.npz');seed=load(out/region/'seed.npz')
        mass=np.broadcast_to(masses[:,None,None],init['temperature'].shape);cells=init['latitude'].size
        initial_h=energy(init['temperature'],init['vapor'],mass);initial_water=float(init['vapor'].sum())
        runs={};regional={};combined.update({region+'_initial_'+k:v for k,v in init.items()})
        combined.update({region+'_seed_'+k:v for k,v in seed.items()})
        for setup,config in plan['setups'].items():
            for dt in config['timesteps_s']:
                folder=out/region/setup;row=json.loads((folder/(str(dt)+'.json')).read_text())
                path=folder/(str(dt)+'.npz')
                if row['status']!='completed' or file_hash(path)!=row['fields_sha256']:raise ValueError('Missing or altered boundary state')
                a=load(path);history=row['history']
                if len(history)!=plan['duration_s']//dt:raise ValueError('Incomplete boundary history')
                assert [h['time_s'] for h in history]==list(range(dt,plan['duration_s']+1,dt))
                initial_ke=0.
                if config['archived_lower_wind_seed']:initial_ke=ke(dict(u=seed['seed_u'],v=seed['seed_v']))
                # Sum the separately recorded port terms, then reconstruct the final
                # gas/kinetic/rain balances. Port flux scalars originate in the solver;
                # this is an accounting check, not independent flux discretization.
                port_energy=dt*sum(h['boundary_rotation_work_w_m2']-h['boundary_gas_enthalpy_w_m2']-h['boundary_geopotential_work_w_m2'] for h in history)
                outward_water=dt*sum(h['boundary_vapor_kg_m2_s'] for h in history)
                np.testing.assert_allclose(port_energy,row['net_port_energy_j_m2'],atol=1e-8,rtol=1e-12)
                np.testing.assert_allclose(outward_water,row['net_outward_port_water_kg_m2'],atol=1e-12,rtol=1e-12)
                error=abs(energy(a['temperature'],a['vapor'],mass)+ke(a)+a['rain_enthalpy'].sum()-initial_h-initial_ke-port_energy*cells)/abs(initial_h+initial_ke)
                water_error=abs(a['vapor'].sum()+a['rain'].sum()-initial_water+outward_water*cells)/initial_water
                for field in ['u','v']:
                    bound=seed[field+'_boundary'] if config['prescribed_ports'] else np.zeros_like(a[field])
                    np.testing.assert_array_equal(a[field][:,:,[0,-1]] if field=='u' else a[field][:,[0,-1]],bound[:,:,[0,-1]] if field=='u' else bound[:,[0,-1]])
                    np.testing.assert_allclose(np.sum(masses[:,None,None]*a[field],axis=0),0,atol=1e-7)
                if np.any(a['vapor']<0) or np.any(a['rain']<0) or not np.isfinite(a['temperature']).all():raise ValueError('Nonphysical boundary state')
                edge=np.zeros(a['rain'].shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True
                c=dict(relative_actual_energy_error=float(error),relative_actual_water_error=float(water_error),
                    mean_run_rain_mm=float(a['rain'].mean()),outer_grid_rain_fraction=float(a['rain'][edge].sum()/a['rain'].sum()) if a['rain'].sum()>0 else None,
                    maximum_temperature_adjustment_k=float(abs(a['temperature']-init['temperature']).max()),
                    peak_level_velocity_ms=float(max(abs(a['u']).max(),abs(a['v']).max())),
                    net_imported_water_kg_m2=float(-outward_water),net_port_energy_j_m2=float(port_energy),
                    initial_maximum_momentum_imbalance_ms2=row['initial_maximum_momentum_imbalance_ms2'])
                np.testing.assert_allclose(c['mean_run_rain_mm'],row['mean_run_rain_mm'],rtol=1e-12)
                key=setup+'_'+str(dt);regional[key]=c;runs[key]=a;all_checks.append(c)
                combined.update({region+'_'+key+'_'+k:v for k,v in a.items()})
                table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{setup.replace("_"," ")}</td><td>{dt}</td><td>{c["mean_run_rain_mm"]:.6f}</td><td>{100*c["outer_grid_rain_fraction"]:.1f}%</td><td>{c["maximum_temperature_adjustment_k"]:.2f}</td><td>{c["net_imported_water_kg_m2"]:.4f}</td></tr>')
        baseline=load(ROOT/spec['prior_pilot_folder']/'900.npz');combined.update({region+'_closed_rest_900_'+k:v for k,v in baseline.items()})
        fine,coarse=runs['ports_seeded_450'],runs['ports_seeded_900']
        regional['seeded_port_timestep_rms']={k:float(np.sqrt(np.mean((fine[k]-coarse[k])**2))) for k in ['temperature','vapor','u','v','rain']}
        checks[region]=regional
        for i,(a,label) in enumerate([(baseline,'closed / rest'),(runs['ports_seeded_900'],'ports / seeded'),(fine,'ports / seeded, finer step')]):
            ax=axes[i,col];im=ax.pcolormesh(init['longitude'],init['latitude'],a['rain'],shading='nearest',cmap='YlGnBu',vmin=0,
                vmax=max(float(baseline['rain'].max()),float(runs['ports_seeded_900']['rain'].max()),float(fine['rain'].max()),1e-10))
            coast=ax.contour(init['longitude'],init['latitude'],init['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.)
            coast.set_path_effects([pe.withStroke(linewidth=2.6,foreground='white')])
            ax.set_title(region.replace('_',' ')+' — '+label,fontsize=10)
            ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');fig.colorbar(im,ax=ax,shrink=.8,label='6 h rain (mm)')
    if max(max(c['relative_actual_energy_error'],c['relative_actual_water_error']) for c in all_checks)>1e-10:raise ValueError('Reconstructed boundary budgets failed')
    fig.suptitle('Prescribed boundary flow and archived initial winds: six-hour rainfall controls',fontsize=14)
    fig.text(.5,.012,'Same initial temperature/water • fixed model-assisted baroclinic ports • no observed wind/rain inputs • not monthly climate skill',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(out/'pressure_boundary_pilot.png',dpi=145);plt.close(fig)
    np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='verified_twelve_boundary_smoke_runs',new_earth_input_smoke_integrations=12,cumulative_earth_input_smoke_integrations=18,
        legacy_benchmark_attempts_added=0,monthly_rainfall_skill_evaluated=False,recalibration=False,adoption=False,cases=checks,
        maximum_reconstructed_energy_relative_error=max(c['relative_actual_energy_error'] for c in all_checks),
        maximum_reconstructed_water_relative_error=max(c['relative_actual_water_error'] for c in all_checks),
        accounting_scope='Final state budgets independently reconstructed against separately summed solver-recorded port scalars; not an independent boundary-flux solver.',
        plan_sha256=file_hash(literal),receipt_sha256=file_hash(out/'verification.json'),publisher_sha256=file_hash(Path(__file__)),
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),figure_sha256=file_hash(out/'pressure_boundary_pilot.png'))
    dest=ROOT/'atlases/climate_accuracy/data'
    shutil.copyfile(out/'publication_fields.npz',dest/'pressure_boundary_pilot_fields.npz');shutil.copyfile(out/'pressure_boundary_pilot.png',dest/'pressure_boundary_pilot.png')
    write_json(dest/'pressure_boundary_pilot.json',dict(frozen_plan=plan,runs=receipt,publication=result))
    with Image.open(out/'pressure_boundary_pilot.png') as im:width,height=im.size
    section=f'''<!--pressure-boundary-pilot-start--><section aria-labelledby="pressure-boundary-pilot-h"><h2 id="pressure-boundary-pilot-h">Regional boundaries and initial-wind controls</h2>
<p>Twelve further six-hour Earth-input runs separate the effects of prescribed regional flow and initial winds. The same initial temperature and water are retained. Initial winds come from the archived <em>simulated lower wind</em>, with a compensating upper return; this does not make the initial state balanced. No observed wind, humidity or rainfall is supplied.</p>
<figure><a href="data/pressure_boundary_pilot.png"><img src="data/pressure_boundary_pilot.png" width="{width}" height="{height}" loading="lazy" alt="India, Mexico and Pacific Northwest six-hour rain comparing closed resting control with prescribed boundaries and archived simulated initial winds"></a><figcaption>Shared rainfall scale within each regional column. Coastlines use a white halo. Initial conversion rain is excluded; no monthly skill comparison.</figcaption></figure>
<div class="table"><table><caption>All twelve declared boundary and initial-wind controls</caption><thead><tr><th>Region</th><th>Setup</th><th>Step s</th><th>Run rain mm</th><th>Outer-cell rain</th><th>Max |ΔT| K</th><th>Net imported water kg/m²</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>Incoming vapor and gas enthalpy, outward geopotential work and work exchanged with the prescribed boundary velocities are explicitly counted. The incoming temperature and humidity remain at the adjacent initial model values; these are conditional boundaries, not transparent wave exits. Prescribed exterior velocities have no kinetic storage degrees of freedom. The budget check reconstructs final gas/kinetic/rain energy and water against separately summed solver-recorded port fluxes.</p>
<p class="note">These twelve runs plus the previous six make eighteen Earth-initialized smoke integrations, separate from the unchanged legacy 1934 attempts /1929 strict passes /four historical failures /one interruption. No calibration or production adoption. Flat terrain, a partial column, omitted barotropic/nonlinear momentum dynamics and absent sustained surface/radiative forcing still limit interpretation. Initial winds alone do not prove dynamical balance, and more rainfall alone does not prove improved accuracy.</p>
<p><a href="data/pressure_boundary_pilot.json" download>Download declaration, twelve runs and budget checks</a> · <a href="data/pressure_boundary_pilot_fields.npz">Raw boundary controls and initial/final states</a> · <a href="../../reports/PRESSURE_BOUNDARY_PILOT_20261029.md">Boundary experiment and physical interpretation</a></p></section><!--pressure-boundary-pilot-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--pressure-boundary-pilot-start-->','<!--pressure-boundary-pilot-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);write_json(out/'publication.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
