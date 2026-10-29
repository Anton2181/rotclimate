"""Verify frozen Earth-input smoke tests without claiming rainfall skill."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def publish(out):
    r=json.loads((out/'verification.json').read_text());plan=json.loads((out/'frozen_plan.json').read_text())
    literal=ROOT/'calibration/pressure_input_pilot_20261029/plan.json'
    if file_hash(literal)!=r['literal_committed_plan_sha256'] or file_hash(out/'frozen_plan.json')!=r['frozen_plan_sha256']:raise ValueError('Changed literal/frozen pilot plan')
    if (r['actual_earth_initialized_integrations_started']!=6 or r['integrations_completed']!=6
            or r['legacy_earth_benchmark_attempts_added']!=0 or r['monthly_rainfall_skill_evaluated'] is not False
            or r['recalibration'] is not False or r['physics_or_atlas_adoption'] is not False
            or r['initial_conversion_rain_in_run_totals'] is not False or plan['observed_fields_used'] is not False):
        raise ValueError('Need all six separate unscored, non-adopted smoke integrations')
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed pilot source/input: '+n)
    edges=np.array(plan['pressure_edges_pa']);p=np.sqrt(edges[:-1]*edges[1:]);m0=-np.diff(edges)/9.80665
    combined={};checks={};max_energy=0.;max_water=0.;fig,axes=plt.subplots(2,3,figsize=(16,8.5))
    def hgas(t,w,m):return (1004*m+1850*w)*t+(2.5e6-1850*273.15)*w
    for col,(region,declared) in enumerate(plan['regions'].items()):
        directory=out/region;init_record=json.loads((directory/'initial.json').read_text())
        if file_hash(directory/'initial.npz')!=init_record['fields_sha256']:raise ValueError('Changed pilot initial fields')
        with np.load(directory/'initial.npz') as data:init={k:data[k] for k in data.files}
        with np.load(ROOT/declared['archive']) as source:
            found=np.flatnonzero(np.isclose(source['days'],declared['model_day'],rtol=0,atol=1e-9))
            if len(found)!=1:raise ValueError('Ambiguous original model day')
            index=int(source['scored_indices'][found[0]]);stride=plan['horizontal_stride']
            if index!=init_record['source_index'] or abs(source['solved_days'][index]-declared['model_day'])>1e-9:raise ValueError('Spinup/calendar mapping changed')
            archived_t=source['closure_T'][index,::stride,::stride];old_w=source['water'][index,:,::stride,::stride]
            np.testing.assert_array_equal(init['archived_surface_temperature_c'],archived_t)
            np.testing.assert_array_equal(init['archived_lower_water'],old_w[0]);np.testing.assert_array_equal(init['archived_upper_water'],old_w[1])
        mass=np.broadcast_to(m0[:,None,None],init['temperature'].shape);face_mass=m0[:,None,None];cells=int(np.prod(init['latitude'].shape))
        sea=archived_t+273.15+plan['lapse_k_m']*init['elevation'];cap=plan['isothermal_cap_k']
        pcap=edges[0]*(cap/sea)**(9.80665/(287.05*plan['lapse_k_m']))
        raw_t=np.where(p[:,None,None]>=pcap[None],sea[None]*(p[:,None,None]/edges[0])**(287.05*plan['lapse_k_m']/9.80665),cap)
        np.testing.assert_allclose(raw_t,init['raw_temperature'],rtol=1e-12,atol=1e-10)
        np.testing.assert_allclose(init['raw_vapor'][:1].sum(0),old_w[0],rtol=1e-12,atol=1e-10)
        np.testing.assert_allclose(init['raw_vapor'][1:].sum(0),old_w[1],rtol=1e-12,atol=1e-10)
        es=611.2*np.exp(17.67*(raw_t-273.15)/(raw_t-29.65));capacity=mass*.622*es/(p[:,None,None]-es)
        expected=np.empty_like(raw_t);expected[:1]=old_w[:1]*capacity[:1]/capacity[:1].sum(0);expected[1:]=old_w[1:]*capacity[1:]/capacity[1:].sum(0)
        np.testing.assert_allclose(init['raw_vapor'],expected,rtol=1e-12,atol=1e-10)
        initial_h=hgas(init['temperature'],init['vapor'],mass).sum();raw_h=hgas(init['raw_temperature'],init['raw_vapor'],mass).sum()
        np.testing.assert_allclose(initial_h+init['initial_conversion_rain_enthalpy'].sum(),raw_h,rtol=1e-12)
        combined.update({region+'_initial_'+k:v for k,v in init.items()});region_checks={};runs={}
        for dt in plan['timesteps_s']:
            key=str(dt);row=json.loads((directory/(key+'.json')).read_text())
            if row['status']!='completed' or row['started'] is not True or row['steps']!=plan['duration_s']//dt:raise ValueError('Missing/failed planned pilot run')
            if file_hash(directory/(key+'.npz'))!=row['fields_sha256']:raise ValueError('Changed final pilot fields')
            with np.load(directory/(key+'.npz')) as data:a={k:data[k] for k in data.files}
            if np.any(a['u'][:,:,[0,-1]]) or np.any(a['v'][:,[0,-1]]):raise ValueError('Pilot exterior flow changed')
            ke=.5*(np.sum(face_mass*a['u'][:,:,1:-1]**2)+np.sum(face_mass*a['v'][:,1:-1]**2))
            final_h=hgas(a['temperature'],a['vapor'],mass).sum()
            error=float(abs(final_h+ke+a['rain_enthalpy'].sum()-initial_h)/abs(initial_h))
            water_error=float(abs(a['vapor'].sum()+a['rain'].sum()-init['vapor'].sum())/max(float(init['vapor'].sum()),1.))
            full_error=float(abs(final_h+ke+a['rain_enthalpy'].sum()+init['initial_conversion_rain_enthalpy'].sum()-raw_h)/abs(raw_h))
            full_water=float(abs(a['vapor'].sum()+a['rain'].sum()+init['initial_conversion_rain'].sum()-old_w.sum())/max(float(old_w.sum()),1.))
            max_energy=max(max_energy,error,full_error);max_water=max(max_water,water_error,full_water)
            np.testing.assert_allclose(row['mean_run_rain_mm'],a['rain'].mean(),rtol=1e-12)
            np.testing.assert_allclose(row['peak_level_velocity_ms'],max(abs(a['u']).max(),abs(a['v']).max()),rtol=1e-12)
            if not np.isfinite(a['temperature']).all() or a['temperature'].min()<180 or a['temperature'].max()>330:raise ValueError('Pilot thermal domain failed')
            es=611.2*np.exp(17.67*(a['temperature']-273.15)/(a['temperature']-29.65));sat=mass*.622*es/(p[:,None,None]-es)
            if np.any(a['vapor']>sat*(1+1e-9)):raise ValueError('Pilot phase saturation failed')
            region_checks[key]=dict(actual_relative_run_energy_error=error,actual_relative_run_water_error=water_error,
                actual_relative_raw_to_final_energy_error=full_error,actual_relative_raw_to_final_water_error=full_water,
                mean_run_rain_mm=float(a['rain'].mean()),mean_initial_conversion_rain_mm=float(init['initial_conversion_rain'].mean()),
                peak_level_velocity_ms=float(max(abs(a['u']).max(),abs(a['v']).max())))
            boundary=np.zeros(a['rain'].shape,bool);boundary[[0,-1]]=True;boundary[:,[0,-1]]=True
            region_checks[key]['outer_grid_cell_rain_fraction']=float(a['rain'][boundary].sum()/max(float(a['rain'].sum()),1e-30))
            region_checks[key]['maximum_absolute_temperature_adjustment_k']=float(np.max(abs(a['temperature']-init['temperature'])))
            runs[key]=a;combined.update({region+'_'+key+'_'+k:v for k,v in a.items()})
        fine,coarse=runs['900'],runs['1800'];region_checks['timestep_difference']={k:float(np.sqrt(np.mean((fine[k]-coarse[k])**2))) for k in ['temperature','vapor','u','v','rain']}
        region_checks['relative_mean_rain_difference']=float(abs(fine['rain'].mean()-coarse['rain'].mean())/max(float(fine['rain'].mean()),1e-12))
        checks[region]=region_checks
        for row,field,title,cmap in [(0,fine['rain'],region.replace('_',' ')+' — 6 h run rain','YlGnBu'),
            (1,fine['temperature'][0]-init['temperature'][0],region.replace('_',' ')+' — lowest-cell ΔT','RdBu_r')]:
            ax=axes[row,col];limit=max(float(abs(field).max()),1e-10)
            im=ax.pcolormesh(init['longitude'],init['latitude'],field,shading='nearest',cmap=cmap,vmin=0 if row==0 else -limit,vmax=limit)
            coast=ax.contour(init['longitude'],init['latitude'],init['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.)
            coast.set_path_effects([path_effects.withStroke(linewidth=2.5,foreground='white')])
            fig.colorbar(im,ax=ax,shrink=.8,label='Run rain (mm)' if row==0 else 'Temperature change (K)')
            ax.set_title(title,fontsize=11);ax.set_xlabel('Longitude');ax.set_ylabel('Latitude')
    if max(max_energy,max_water)>1e-10:raise ValueError('Pilot actual initialization/run full budgets failed')
    fig.suptitle('Earth-input smoke tests: boundary-dominated rain in closed, flattened domains',fontsize=15)
    fig.text(.5,.012,'Archived simulated inputs • 224 km point sampling • initially resting/unbalanced • no sustained forcing • initial conversion rain excluded • no climate skill score',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'pressure_input_pilot.png',dpi=155);plt.close(fig)
    np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='verified_six_earth_input_smoke_runs',actual_earth_initialized_integrations_started=6,integrations_completed=6,
        legacy_earth_benchmark_attempts_added=0,monthly_rainfall_skill_evaluated=False,recalibration=False,physics_or_atlas_adoption=False,
        maximum_actual_energy_relative_error=max_energy,maximum_actual_water_relative_error=max_water,cases=checks,
        source_receipt_sha256=file_hash(out/'verification.json'),literal_plan_sha256=file_hash(literal),
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),image_sha256=file_hash(out/'pressure_input_pilot.png'),publisher_sha256=file_hash(Path(__file__)),
        scope='Six Earth-initialized smoke integrations counted separately from legacy benchmark attempts. Initial phase rain excluded from run rain; no observed fields, monthly skill comparison or physics adoption.')
    dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'publication_fields.npz',dest/'pressure_input_pilot_fields.npz');shutil.copyfile(out/'pressure_input_pilot.png',dest/'pressure_input_pilot.png')
    write_json(dest/'pressure_input_pilot.json',dict(pilot=r,frozen_plan=plan,independent_publication_checks=result))
    with Image.open(out/'pressure_input_pilot.png') as im:width,height=im.size
    rows=''.join(f'<tr><td>{name.replace("_"," ")}</td><td>{v["900"]["mean_initial_conversion_rain_mm"]:.6f}</td><td>{v["900"]["mean_run_rain_mm"]:.6f}</td><td>{v["900"]["peak_level_velocity_ms"]:.2f}</td><td>{100*v["relative_mean_rain_difference"]:.1f}%</td><td>{100*v["900"]["outer_grid_cell_rain_fraction"]:.1f}%</td></tr>' for name,v in checks.items())
    section=f'''<!--pressure-input-pilot-start--><section aria-labelledby="pressure-input-pilot-h"><h2 id="pressure-input-pilot-h">Six fixed Earth-input smoke integrations</h2>
<p><strong>The coupled pressure/convection prototype now runs on archived model inputs for India, Mexico and the Pacific Northwest.</strong> All six planned runs completed. The literal input declaration was committed before integration. Simulated temperature, the two simulated vapor reservoirs, geography and the scored-day mapping are used; observed rainfall/temperature and archived/reference winds are not inputs. No coefficients are fitted.</p>
<p>These are six-hour initialization and numerical-admissibility tests, with terrain flattened by one declared6 K/km lapse, zero initial wind, closed boundaries and no sustained solar, evaporation or lateral forcing. The cases are initially unbalanced and are not weather forecasts or monthly climate validation. Exact lower/upper water integrals survive the pressure-grid transfer; initial conversion rain is booked separately and excluded from plotted run rain.</p>
<figure><a href="data/pressure_input_pilot.png"><img src="data/pressure_input_pilot.png" width="{width}" height="{height}" loading="lazy" alt="Earth geography with six-hour smoke-test rain and lowest-cell temperature change for India, Mexico and Pacific Northwest; flattened terrain and no climate skill claim"></a><figcaption>Finest15-minute runs on a224 km sampled grid. Coastlines show geography, not resolved terrain forcing. Different regional color scales; new run rainfall is tiny and does not measure Earth monthly skill.</figcaption></figure>
<div class="table"><table><caption>Regional means from15-minute integrations; initial conversion separated from run rain. Difference compares30-minute versus15-minute mean run rain</caption><thead><tr><th>Region</th><th>Initial conversion mm</th><th>6 h run rain mm</th><th>Peak wind m/s</th><th>Relative mean-rain step difference</th><th>Rain in outer grid cells</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><strong>The closed/unbalanced setup fails the physical-use gate for rainfall fitting.</strong> Between99.5% and100% of run rain lies in the outermost grid cells. Temperature adjustments reach7.5–12.9 K somewhere in each partial column over six hours. Boundary treatment and initial dynamical balance must be investigated before tuning rainfall coefficients around these artifacts. Water and gas/kinetic/rain energy still close near1e-15 relative, including the initial conversion; conservation alone is insufficient.</p>
<p>Relative rain differences can be large when rain is extremely small: the tropical means differ by roughly0.0001 mm between timesteps. These tests do not establish temporal convergence of climate rainfall, and the dry result depends on the reconstructed humidity, absent sustained forcing and flattened terrain. Seven new transfer/calendar tests bring the focused suite to300 passes.</p>
<p class="note">Six new Earth-initialized integrations are counted here separately from the unchanged legacy1934 benchmark attempts /1929 strict passes /four historical failures /one historical interruption. No new legacy strict passes, recalibration or measured rainfall gain is claimed. The source is a prior experimental model archive, not independent validation. Uniform RH within each source water reservoir, a partial pressure column, liquid-only/dry-dilute physics, omitted terrain/nonlinear and barotropic dynamics, and absent sustained regional forcing limit interpretation. The next requirement for meaningful rainfall fitting is a declared forcing/boundary and climate-observation comparison, with fixed Earth-like priors and numerical guards. Earthr39 and all normal world/biome/population fields remain unchanged.</p>
<p><a href="data/pressure_input_pilot.json" download>Download frozen declaration, six runs, conversion and numerical checks</a> · <a href="data/pressure_input_pilot_fields.npz">Raw Earth-input initial/final states and separately booked rain</a> · <a href="../../reports/PRESSURE_INPUT_PILOT_20261029.md">Initialization assumptions, counts and calibration limits</a></p></section><!--pressure-input-pilot-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--pressure-input-pilot-start-->' in text:
        before,tail=text.split('<!--pressure-input-pilot-start-->',1);_,after=tail.split('<!--pressure-input-pilot-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);write_json(out/'publication.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
