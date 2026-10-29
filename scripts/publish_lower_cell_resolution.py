"""Retain every lower-cell attempt and diagnose budgets and grid/step sensitivity."""
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
from monitor_extended_spinup import load,energy
from rotclimate.pressure_remap import pressure_overlap


def stats(initial,final,row,edges):
    mass=-np.diff(edges)/9.80665;land=initial['land'].astype(bool);edge=np.zeros(land.shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True;interior=land&~edge
    e0=energy(initial,mass);water0=float(initial['vapor'].sum()+initial['surface_liquid'].sum());history=row['history'];last=history[-1] if history else dict(cumulative_net_external_energy_j_m2=0,cumulative_outward_water_kg_m2=0)
    ee=abs(energy(final,mass)-e0-last['cumulative_net_external_energy_j_m2']*land.size)/abs(e0)
    we=abs(final['vapor'].sum()+final['surface_liquid'].sum()-water0+last['cumulative_outward_water_kg_m2']*land.size)/water0
    evap=final['rain']-final['surface_liquid']+initial['surface_liquid']
    return dict(status=row['status'],steps=len(history),actual_energy_relative_error=float(ee),actual_water_relative_error=float(we),independent_budget_pass=bool(max(ee,we)<1e-10),land_rain_mm=float(final['rain'][land].mean()),interior_land_rain_mm=float(final['rain'][interior].mean()),land_evaporation_mm=float(evap[land].mean()),land_surface_temperature_k=float(final['surface_temperature'][land].mean()),land_liquid_kg_m2=float(final['surface_liquid'][land].mean()),land_surface_temperature_change_k=float((final['surface_temperature']-initial['surface_temperature'])[land].mean()),initial_total_energy_j=float(e0),initial_total_water_kg=float(water0))


def comparison(a,b,edges_a,edges_b,land):
    # Coarsen integral quantities only, without a new diagnostic phase adjustment.
    op=pressure_overlap(edges_a,edges_b);ma=(-np.diff(edges_a)/9.80665)[:,None,None];mb=(-np.diff(edges_b)/9.80665)[:,None,None]
    w=op.extensive(a['vapor']);h=op.extensive((1004*ma+1850*a['vapor'])*a['temperature']+(2.5e6-1850*273.15)*a['vapor']);t=(h-(2.5e6-1850*273.15)*w)/(1004*mb+1850*w)
    return dict(land_rain_mean_difference_mm=float((a['rain']-b['rain'])[land].mean()),land_rain_rms_difference_mm=float(np.sqrt(np.mean((a['rain']-b['rain'])[land]**2))),surface_temperature_rms_difference_k=float(np.sqrt(np.mean((a['surface_temperature']-b['surface_temperature'])**2))),coarsened_atmospheric_temperature_rms_difference_k=float(np.sqrt(np.mean((t-b['temperature'])**2))),column_vapor_rms_difference_mm=float(np.sqrt(np.mean((a['vapor'].sum(0)-b['vapor'].sum(0))**2))))


def publish(out):
    plan_path=ROOT/'calibration/lower_cell_resolution_20261029/plan.json';plan=json.loads(plan_path.read_text());receipt=json.loads((out/'verification.json').read_text());assert plan_path.read_bytes()==(out/'frozen_protocol.json').read_bytes() and file_hash(plan_path)==receipt['literal_plan_sha256']
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    assert len(receipt['results'])==len(plan['cases'])
    combined={};checks={};states={};table=[];case_records={};started=completed=0
    for spec in plan['cases']:
        folder=out/spec['name'];literal=ROOT/spec['plan'];p=json.loads(literal.read_text());assert literal.read_bytes()==(folder/'frozen_plan.json').read_bytes()
        r=json.loads((folder/'verification.json').read_text());assert r['literal_plan_sha256']==file_hash(literal)
        top=next(c for c in receipt['results'] if c['name']==spec['name']);assert file_hash(folder/'verification.json')==top['receipt_sha256'];started+=r['actual_earth_initialized_integrations_started'];completed+=r['integrations_completed'];case_records[spec['name']]=dict(protocol=p,run=r)
        region=spec['region'];initial=load(folder/region/'initial.npz');edges=initial['pressure_edges'];combined.update({spec['name']+'_initial_'+k:v for k,v in initial.items()})
        for row in r['results']:
            dt=row['dt_s'];key=spec['name']+'_'+str(dt);stem=folder/region/'forced'/str(dt);path=stem.with_suffix('.npz') if row['status']=='completed' else stem.with_name(str(dt)+'_partial').with_suffix('.npz');expected=row['fields_sha256'] if row['status']=='completed' else row['partial_fields_sha256'];assert file_hash(path)==expected
            a=load(path);c=stats(initial,a,row,edges);c.update(region=region,parts=p['lower_cell_parts'],dt_s=dt,fields_sha256=file_hash(path));checks[key]=c;states[key]=(initial,a);combined.update({key+'_final_'+k:v for k,v in a.items()})
            table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{p["lower_cell_parts"]}</td><td>{dt}</td><td>{row["status"]} ({c["steps"]} steps)</td><td>{c["land_rain_mm"]:.3f}</td><td>{c["land_evaporation_mm"]:.3f}</td><td>{c["land_surface_temperature_change_k"]:.2f}</td></tr>')
    assert started==receipt['actual_earth_initialized_integrations_started'] and completed==receipt['integrations_completed']
    regions=['north_india','mexico','pacific_nw'];baseline={};differences={}
    for region in regions:
        prior=ROOT/'output/shared_transport_20261029'/(region+'_candidate')/region;initial=load(prior/'initial.npz');a=load(prior/'forced/900.npz');row=json.loads((prior/'forced/900.json').read_text());c=stats(initial,a,row,initial['pressure_edges']);baseline[region]=c;states[region+'_coarse_900']=(initial,a)
        combined.update({region+'_coarse_initial_'+k:v for k,v in initial.items()});combined.update({region+'_coarse_final_'+k:v for k,v in a.items()});land=initial['land'].astype(bool);pairs={}
        for key in [f'{region}_split4_900',f'{region}_split4_450',f'{region}_split16_900']:
            i,f=states[key];ee=abs(checks[key]['initial_total_energy_j']-c['initial_total_energy_j'])/abs(c['initial_total_energy_j']);we=abs(checks[key]['initial_total_water_kg']-c['initial_total_water_kg'])/c['initial_total_water_kg'];assert max(ee,we)<1e-11
            checks[key]['initial_coarse_energy_relative_difference']=ee;checks[key]['initial_coarse_water_relative_difference']=we
            if checks[key]['status']=='completed':pairs[key+'_vs_coarse']=comparison(f,a,i['pressure_edges'],initial['pressure_edges'],land)
        k900,k450=f'{region}_split4_900',f'{region}_split4_450'
        if checks[k900]['status']==checks[k450]['status']=='completed':pairs['split4_450_vs_900']=comparison(states[k450][1],states[k900][1],states[k450][0]['pressure_edges'],states[k900][0]['pressure_edges'],land)
        k16=f'{region}_split16_900'
        if checks[k16]['status']==checks[k900]['status']=='completed':pairs['split16_900_vs_split4_900']=comparison(states[k16][1],states[k900][1],states[k16][0]['pressure_edges'],states[k900][0]['pressure_edges'],land)
        differences[region]=pairs
    fig,axes=plt.subplots(1,3,figsize=(14,4.8));variants=[('coarse 900s',None,'#777b81'),('4 parts 900s','split4_900','#1685ac'),('4 parts 450s','split4_450','#4b9b6c'),('16 parts 900s','split16_900','#ad6838')];x=np.arange(3)
    for i,(label,suffix,color) in enumerate(variants):
        values=[baseline[r] if suffix is None else checks[r+'_'+suffix] for r in regions]
        for ax,key in zip(axes,['land_rain_mm','land_evaporation_mm','land_surface_temperature_change_k']):
            ax.bar(x+(i-1.5)*.19,[v[key] if v['status']=='completed' else np.nan for v in values],.19,color=color,label=label)
    for ax,title,label in zip(axes,['Run rainfall','Net evaporation','Land surface temperature change'],['mm in 24 h','mm in 24 h','K over 24 h']):ax.set_title(title);ax.set_ylabel(label);ax.set_xticks(x,[r.replace('_',' ') for r in regions]);ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=8);fig.suptitle('Lower-air-cell resolution: fixed 24-hour physical controls',fontsize=14);fig.text(.5,.01,'Failed runs omitted from 24h bars; partial states retained in table • conversion rain excluded • not monthly skill',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'lower_cell_resolution.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(3,3,figsize=(14,10))
    for col,region in enumerate(regions):
        initial,coarse=states[region+'_coarse_900'];key=region+'_split4_900';fine=states[key][1];status=checks[key]['status'];arrays=[coarse['rain'],fine['rain'],fine['rain']-coarse['rain']];rainmax=max(float(arrays[0].max()),float(arrays[1].max()),1e-10)
        for row,field in enumerate(arrays):
            ax=axes[row,col]
            if status!='completed' and row>0:ax.text(.5,.5,'Failed/partial case: see retained raw state',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
            delta=row==2;limit=max(float(abs(field).max()),1e-10);im=ax.pcolormesh(initial['longitude'],initial['latitude'],field,shading='nearest',cmap='RdBu_r' if delta else 'YlGnBu',vmin=-limit if delta else 0,vmax=limit if delta else rainmax);coast=ax.contour(initial['longitude'],initial['latitude'],initial['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.);coast.set_path_effects([pe.withStroke(linewidth=2.6,foreground='white')]);ax.set_title(region.replace('_',' ')+': '+['coarse run rain','4-part run rain','4-part minus coarse'][row],fontsize=10);fig.colorbar(im,ax=ax,shrink=.8,label='mm in 24 h')
    fig.suptitle('Completed four-part first-cell refinement: first-day rainfall response',fontsize=14);fig.text(.5,.01,'Same rain scale within each region • dark coasts with white halo • resolution response is not accuracy',ha='center',fontsize=9);fig.tight_layout(rect=(0,.035,1,.96));fig.savefig(out/'lower_cell_resolution_maps.png',dpi=140);plt.close(fig)
    np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='all_lower_cell_resolution_attempts_published',new_earth_integrations=started,integrations_completed=completed,failed_cases=started-completed,cumulative_prototype_starts=93+started,cumulative_prototype_completions=89+completed,cumulative_retained_failures=4+started-completed,legacy_benchmark_attempts_added=0,checks=checks,baseline=baseline,comparisons=differences,all_saved_budgets_pass=all(c['independent_budget_pass'] for c in checks.values()),physical_adoption=False,recalibration=False,monthly_skill=False,publisher_sha256=file_hash(Path(__file__)),raw_fields_sha256=file_hash(out/'publication_fields.npz'),figures_sha256={n:file_hash(out/n) for n in ['lower_cell_resolution.png','lower_cell_resolution_maps.png']},scope='All fixed lower-cell grid/step attempts retained. Compatible horizontal fields and pressure-overlap gas enthalpy/vapor diagnostics compared; no diagnostic phase imposed on coarsened fields. Day-one transient resolution response, not climatic skill, spinup convergence, or sixteen-way timestep convergence.')
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data';write_json(dest/'lower_cell_resolution.json',dict(protocol=plan,receipt=receipt,cases=case_records,publication=result));shutil.copyfile(out/'publication_fields.npz',dest/'lower_cell_resolution_fields.npz')
    figures=[]
    for name in result['figures_sha256']:
        shutil.copyfile(out/name,dest/name)
        with Image.open(out/name) as im:w,h=im.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="Lower-cell grid rainfall, evaporation and surface temperature controls; spatial response with visible coasts"></a></figure>')
    section=f'''<!--lower-cell-resolution-start--><section aria-labelledby="lower-cell-resolution-h"><h2 id="lower-cell-resolution-h">Shallower first air cells: physical and numerical sensitivity</h2>
<p>{completed} of {started} new fixed 24-hour integrations complete. Every outcome and partial state is retained. The first old cell is split into four or sixteen constant subcells, with conservative water, gas/surface/kinetic energy and momentum transfer. The surface-exchange reference height falls from about 750 m to 175 or 43 m. No planetary parameter, opacity or exchange coefficient is retuned.</p>
{figures[0]}
<div class="table"><table><caption>Run rain excludes target-pressure initialization conversion; failed cases show partial accumulations</caption><thead><tr><th>Region</th><th>Parts</th><th>Step s</th><th>Outcome</th><th>Land rain mm</th><th>Land evap mm</th><th>Land ΔT K</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
{figures[1]}
<p>Four-way grids have 900/450-second controls; sixteen-way grids have only 900 seconds, so no finer-grid timestep convergence is claimed. Downloadable comparisons include spatial rainfall RMS, surface-temperature RMS, column vapor and pressure-overlap thermodynamic differences. A smaller regional mean difference alone does not establish local convergence.</p>
<p>Saved water and gas/kinetic/surface energy are independently checked against actual recorded sources for every available final/partial state. Coarsened diagnostics retain gas enthalpy and vapor integrals without adding diagnostic condensation. Initial water and total energy match the archived coarse control; no new wind projection or hidden heat is added.</p>
<p class="note">Piecewise-constant subdivision changes the resolved initial stability and flux geometry. This is a physical-resolution experiment, not monthly rainfall skill or model adoption. Fourteen-day runs already show substantial initialization memory. Neutral exchange, flat terrain, partial upper atmosphere and omitted nonlinear momentum remain approximations. Cumulative prototype record through this study: {93+started} starts /{89+completed} completions /{4+started-completed} retained numerical failures. Legacy 1934/1929 and normal Earth r39, world/biome/population fields remain unchanged.</p>
<p><a href="data/lower_cell_resolution.json" download>Download frozen protocol, every attempt, budget checks and resolution comparisons</a> · <a href="data/lower_cell_resolution_fields.npz">All initial, final and partial state arrays</a> · <a href="../../reports/LOWER_CELL_RESOLUTION_20261029.md">Results and interpretation</a></p></section><!--lower-cell-resolution-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--lower-cell-resolution-start-->','<!--lower-cell-resolution-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps({k:v for k,v in result.items() if k not in ['checks','baseline','comparisons']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);publish(p.parse_args().out.resolve())
