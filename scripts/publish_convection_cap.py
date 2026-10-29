"""Publish every full fine-grid work-cap attempt, with old failures retained."""
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
from monitor_extended_spinup import load
from publish_lower_cell_resolution import stats,comparison


def publish(out):
    literal=ROOT/'calibration/convection_cap_20261029/plan.json';plan=json.loads(literal.read_text());receipt=json.loads((out/'verification.json').read_text());assert literal.read_bytes()==(out/'frozen_protocol.json').read_bytes() and file_hash(literal)==receipt['literal_plan_sha256']
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    assert len(receipt['results'])==3
    traces=json.loads((out/'coupled_timings.json').read_text());combined={};checks={};states={};differences={};prefix={};cases={};table=[];started=completed=0
    for spec in plan['cases']:
        region=spec['region'];folder=out/spec['name'];p=json.loads((ROOT/spec['plan']).read_text());r=json.loads((folder/'verification.json').read_text());assert (ROOT/spec['plan']).read_bytes()==(folder/'frozen_plan.json').read_bytes() and file_hash(ROOT/spec['plan'])==r['literal_plan_sha256'];top=next(x for x in receipt['results'] if x['name']==spec['name']);assert file_hash(folder/'verification.json')==top['receipt_sha256'];cases[region]=dict(protocol=p,run=r)
        started+=r['actual_earth_initialized_integrations_started'];completed+=r['integrations_completed'];initial=load(folder/region/'initial.npz');old_folder=ROOT/'output/lower_cell_resolution_20261029'/(region+'_split16')/region;old_initial=load(old_folder/'initial.npz')
        initial_exact={k:initial[k].dtype==old_initial[k].dtype and initial[k].tobytes()==old_initial[k].tobytes() for k in old_initial};assert all(initial_exact.values());combined.update({region+'_initial_'+k:v for k,v in initial.items()})
        old_row=json.loads((old_folder/'forced/900.json').read_text());assert old_row['status']=='failed'
        old_partial=load(old_folder/'forced/900_partial.npz');assert file_hash(old_folder/'forced/900_partial.npz')==old_row['partial_fields_sha256'];combined.update({region+'_old_failed_partial_'+k:v for k,v in old_partial.items()})
        for row in r['results']:
            dt=row['dt_s'];key=region+'_'+str(dt);stem=folder/region/'forced'/str(dt);path=stem.with_suffix('.npz') if row['status']=='completed' else stem.with_name(str(dt)+'_partial').with_suffix('.npz');expected=row['fields_sha256'] if row['status']=='completed' else row['partial_fields_sha256'];assert file_hash(path)==expected;a=load(path);c=stats(initial,a,row,initial['pressure_edges'])
            calls=[x for x in traces['calls'] if x['region']==region and x['dt_s']==dt];accepted=[x for x in calls if x['completed']];assert len(accepted)==c['steps'] and all(x['target_converged'] and x['remaining_target_interfaces']==0 for x in accepted)
            timing=dict(calls=len(calls),accepted=len(accepted),failed=len(calls)-len(accepted),total_seconds=float(sum(x['seconds'] for x in calls)),maximum_target_sweeps=max([x['convective_sweeps'] for x in accepted],default=0),median_target_sweeps=float(np.median([x['convective_sweeps'] for x in accepted])) if accepted else None)
            c.update(dt_s=dt,region=region,timing=timing,fields_sha256=file_hash(path));checks[key]=c;states[key]=(initial,a);combined.update({key+'_final_'+k:v for k,v in a.items()})
            if dt==900:
                exact=row['history'][:len(old_row['history'])]==old_row['history'];prefix[region]=dict(initial_arrays_byte_exact=initial_exact,original_accepted_scalar_history_exact=exact,old_accepted_steps=old_row['completed_steps']);assert exact
            table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{dt}</td><td>{row["status"]} ({c["steps"]} steps)</td><td>{c["land_rain_mm"]:.3f}</td><td>{c["land_evaporation_mm"]:.3f}</td><td>{c["land_surface_temperature_change_k"]:.2f}</td><td>{timing["maximum_target_sweeps"]}</td></tr>')
    assert started==receipt['actual_earth_initialized_integrations_started'] and completed==receipt['integrations_completed']
    baseline={};regions=['north_india','mexico','pacific_nw']
    for region in regions:
        baseline[region]={};land=states[region+'_900'][0]['land'].astype(bool)
        for name,folder in [('six',ROOT/'output/shared_transport_20261029'/(region+'_candidate')/region),('nine',ROOT/'output/lower_cell_resolution_20261029'/(region+'_split4')/region)]:
            i=load(folder/'initial.npz');a=load(folder/'forced/900.npz');r=json.loads((folder/'forced/900.json').read_text());assert r['status']=='completed' and file_hash(folder/'forced/900.npz')==r['fields_sha256'];baseline[region][name]=stats(i,a,r,i['pressure_edges']);states[region+'_'+name]=(i,a);combined.update({region+'_'+name+'_initial_'+k:v for k,v in i.items()});combined.update({region+'_'+name+'_final_'+k:v for k,v in a.items()})
        comparisons={}
        if checks[region+'_900']['status']==checks[region+'_450']['status']=='completed':comparisons['fine450_vs_900']=comparison(states[region+'_450'][1],states[region+'_900'][1],states[region+'_450'][0]['pressure_edges'],states[region+'_900'][0]['pressure_edges'],land)
        if checks[region+'_900']['status']=='completed':
            for name in ['six','nine']:comparisons['fine900_vs_'+name]=comparison(states[region+'_900'][1],states[region+'_'+name][1],states[region+'_900'][0]['pressure_edges'],states[region+'_'+name][0]['pressure_edges'],land)
        differences[region]=comparisons
    fig,axes=plt.subplots(1,3,figsize=(14,4.8));x=np.arange(3)
    for i,(label,key,color) in enumerate([('6 levels 900s','six','#777b81'),('9 levels 900s','nine','#1685ac'),('21 levels 900s','900','#ad6838'),('21 levels 450s','450','#4b9b6c')]):
        rows=[baseline[r][key] if key in ['six','nine'] else checks[r+'_'+key] for r in regions]
        for ax,field in zip(axes,['land_rain_mm','land_evaporation_mm','land_surface_temperature_change_k']):ax.bar(x+(i-1.5)*.19,[c[field] if c['status']=='completed' else np.nan for c in rows],.19,label=label,color=color)
    for ax,title,unit in zip(axes,['Run rainfall','Net evaporation','Land surface temperature change'],['mm in 24 h','mm in 24 h','K over 24 h']):ax.set_xticks(x,[r.replace('_',' ') for r in regions]);ax.set_title(title);ax.set_ylabel(unit);ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=8);fig.suptitle('Full finer-grid controls: same physics and tolerance, larger solver work allowance',fontsize=13);fig.text(.5,.01,'Original failed attempts remain retained • initial conversion rain excluded • resolution response is not observational accuracy',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'convection_cap.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(3,3,figsize=(14,10))
    for col,region in enumerate(regions):
        geo,coarse=states[region+'_nine'];fine=states[region+'_900'][1];status=checks[region+'_900']['status'];arrays=[coarse['rain'],fine['rain'],fine['rain']-coarse['rain']];scale=max(float(arrays[0].max()),float(arrays[1].max()),1e-10)
        for row,a in enumerate(arrays):
            ax=axes[row,col]
            if status!='completed' and row>0:ax.text(.5,.5,'Incomplete case; retained raw state',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
            delta=row==2;limit=max(float(abs(a).max()),1e-10);im=ax.pcolormesh(geo['longitude'],geo['latitude'],a,shading='nearest',cmap='RdBu_r' if delta else 'YlGnBu',vmin=-limit if delta else 0,vmax=limit if delta else scale);coast=ax.contour(geo['longitude'],geo['latitude'],geo['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.);coast.set_path_effects([pe.withStroke(linewidth=2.6,foreground='white')]);ax.set_title(region.replace('_',' ')+': '+['9-level run rain','21-level run rain','21 minus 9 levels'][row],fontsize=10);fig.colorbar(im,ax=ax,shrink=.8,label='mm in 24 h')
    fig.suptitle('First-day rainfall: shallower first air cell under unchanged physical closures',fontsize=14);fig.text(.5,.01,'Same rain scale within each region • dark coasts with white halo • no monthly accuracy claim',ha='center',fontsize=9);fig.tight_layout(rect=(0,.035,1,.96));fig.savefig(out/'convection_cap_maps.png',dpi=140);plt.close(fig);np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='full_fixed_cap_attempts_independently_checked',new_earth_integrations=started,integrations_completed=completed,new_failures=started-completed,cumulative_prototype_starts=103+started,cumulative_prototype_completions=95+completed,cumulative_retained_failures=8+started-completed,legacy_benchmark_attempts_added=0,checks=checks,baselines=baseline,comparisons=differences,old_failure_prefix_reproduction=prefix,all_saved_budgets_pass=all(c['independent_budget_pass'] for c in checks.values()),maximum_actual_energy_relative_error=max(c['actual_energy_relative_error'] for c in checks.values()),maximum_actual_water_relative_error=max(c['actual_water_relative_error'] for c in checks.values()),physical_adoption=False,recalibration=False,monthly_skill=False,publisher_sha256=file_hash(Path(__file__)),raw_fields_sha256=file_hash(out/'publication_fields.npz'),timings_sha256=file_hash(out/'coupled_timings.json'),figures_sha256={n:file_hash(out/n) for n in ['convection_cap.png','convection_cap_maps.png']},scope='All declared full fine-grid cases, original64-cap failures and scalar accepted prefixes retained. Fixed1024 cap permits more work without changing closure tolerance or physical parameters. Day-one spatial/grid response only; next observed-month benchmark uses fixed working nine-level grid and wet/dry ensemble.')
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data';write_json(dest/'convection_cap.json',dict(protocol=plan,receipt=receipt,cases=cases,all_coupled_calls=traces,publication=result));shutil.copyfile(out/'publication_fields.npz',dest/'convection_cap_fields.npz');figures=[]
    for name in result['figures_sha256']:
        shutil.copyfile(out/name,dest/name)
        with Image.open(out/name) as im:w,h=im.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="Complete fine-grid rainfall, evaporation and temperature comparison, with spatial rain response and visible coasts"></a></figure>')
    section=f'''<!--convection-cap-start--><section aria-labelledby="convection-cap-h"><h2 id="convection-cap-h">Full finer-grid controls with a larger fixed solver allowance</h2>
<p>{completed} of {started} new 24-hour integrations complete. The 21-level grid places the first exchange reference near 42–43 m. Only maximum convection work changes from 64 to 1024 sweeps; target tolerance remains 0.01 K, relaxation remains 3600 s, and all physical inputs and planetary parameters stay fixed.</p>
{figures[0]}
<div class="table"><table><caption>Every new outcome; partial accumulations are labelled if a case fails</caption><thead><tr><th>Region</th><th>Step s</th><th>Outcome</th><th>Land rain mm</th><th>Land evap mm</th><th>Land ΔT K</th><th>Max target sweeps</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
{figures[1]}
<p>Initial arrays exactly reproduce the original finer-grid cases. Every recorded accepted scalar history through the old rejected step also reproduces exactly; the old three failed cases remain retained in the prior study. The new runs proceed beyond those rejection points by allowing more iterations, without loosening the stopping tolerance.</p>
<p>All final and partial saved water and gas/kinetic/surface energy budgets are reconstructed independently. Downloads retain every coupled-call time, successful target sweep count and failed attempt. Spatial timestep comparisons use matching horizontal fields; pressure-overlap thermal diagnostics preserve gas enthalpy and vapor without adding diagnostic condensation. Regional mean agreement alone is not local convergence.</p>
<p class="note">These are resolution/stability results, not observed rainfall accuracy or physical-model adoption. Prototype record through this study: {103+started} starts /{95+completed} completions /{8+started-completed} retained failures. This study adds no legacy benchmark attempts. The committed next benchmark tests complete WorldClim calendar months using the working nine-level grid, explicit wet/dry starts and fixed common footprints; refinement work will not indefinitely postpone that comparison. Normal atlas climate, biome and population fields remain unchanged.</p>
<p><a href="data/convection_cap.json" download>Download fixed protocol, all outcomes, timing/sweep traces and budget/grid checks</a> · <a href="data/convection_cap_fields.npz">Initial, final and original failed state arrays</a> · <a href="../../reports/CONVECTION_CAP_20261029.md">Full-run results</a> · <a href="../../reports/REGIONAL_RAINFALL_BENCHMARK_DECLARATION_20261029.md">Next observed-rainfall benchmark</a></p></section><!--convection-cap-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--convection-cap-start-->','<!--convection-cap-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps({k:v for k,v in result.items() if k not in ['checks','baselines','comparisons','old_failure_prefix_reproduction']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);publish(p.parse_args().out.resolve())
