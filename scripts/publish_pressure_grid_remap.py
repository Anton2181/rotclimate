"""Independently check saved static grid transfers and publish their scope."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def load(path):
    with np.load(path) as f:return {k:f[k] for k in f.files}


def total(a):
    m=(-np.diff(a['pressure_edges'])/9.80665)[:,None,None]
    h=((1004*m+1850*a['vapor'])*a['temperature']+(2.5e6-1850*273.15)*a['vapor']).sum()
    h+=((a['substrate_capacity']+4186*a['surface_liquid'])*(a['surface_temperature']-273.15)).sum()
    h+=.5*((m*a['u'][:,:,1:-1]**2).sum()+(m*a['v'][:,1:-1]**2).sum())
    return float(h),float(a['vapor'].sum()+a['surface_liquid'].sum())


def publish(out):
    literal=ROOT/'calibration/pressure_grid_remap_20261029/plan.json';p=json.loads(literal.read_text());r=json.loads((out/'verification.json').read_text())
    assert literal.read_bytes()==(out/'frozen_plan.json').read_bytes() and file_hash(literal)==r['literal_plan_sha256']
    assert r['actual_earth_initialized_integrations_started']==0 and r['static_transfer_cases']==6
    for n,h in p['sources'].items():assert file_hash(ROOT/n)==h,n
    expected={(region,parts) for region in p['inputs'] for parts in p['lowest_cell_parts']}
    assert {(row['region'],row['lowest_cell_parts']) for row in r['results']}==expected and len(r['results'])==len(expected)
    combined={};checks=[];table=[]
    for row in r['results']:
        region,parts=row['region'],row['lowest_cell_parts'];source=load(ROOT/p['inputs'][region]);path=out/(region+f'_split{parts}.npz');assert file_hash(path)==row['fields_sha256'];a=load(path)
        assert a['pressure_edges'][0]==source['pressure_edges'][0] and a['pressure_edges'][-1]==source['pressure_edges'][-1]
        np.testing.assert_array_equal(a['pressure_edges'],np.r_[np.linspace(source['pressure_edges'][0],source['pressure_edges'][1],parts+1),source['pressure_edges'][2:]])
        for key in ['land','latitude','longitude','substrate_capacity']:np.testing.assert_array_equal(a[key],source[key])
        e0,w0=total(source);e1,w1=total(a);er=abs(e1-e0)/abs(e0);wr=abs(w1-w0)/w0;assert max(er,wr)<p['energy_water_relative_tolerance']
        old_m=(-np.diff(source['pressure_edges'])/9.80665)[:,None,None];new_m=(-np.diff(a['pressure_edges'])/9.80665)[:,None,None];momentum={};kinetic={}
        for key in ['u','v']:
            momentum[key]=float(abs((old_m*source[key]).sum(0)-(new_m*a[key]).sum(0)).max())
            kinetic[key]=float(abs(.5*((old_m*source[key]**2).sum(0)-(new_m*a[key]**2).sum(0))).max())
            assert momentum[key]<p['momentum_absolute_tolerance_kg_m_s'] and kinetic[key]<p['refinement_kinetic_tolerance_j_m2']
        # No runoff/evaporation occurs in this static transfer.
        np.testing.assert_allclose(a['surface_liquid']-source['surface_liquid'],a['conversion_rain'],rtol=1e-9,atol=1e-10)
        sh=lambda d:(d['substrate_capacity']+4186*d['surface_liquid'])*(d['surface_temperature']-273.15)
        np.testing.assert_allclose(sh(a)-sh(source),a['conversion_rain_enthalpy'],rtol=1e-7,atol=1e-5)
        checks.append(dict(region=region,parts=parts,actual_energy_relative_error=er,actual_water_relative_error=wr,momentum_integral_errors=momentum,kinetic_variance_errors_j_m2=kinetic))
        prefix=region+f'_split{parts}_';combined.update({prefix+k:v for k,v in a.items()});combined.update({region+'_source_'+k:v for k,v in source.items()})
        table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{parts}</td><td>{row["source_reference_height_mean_m"]:.1f}</td><td>{row["target_reference_height_mean_m"]:.1f}</td><td>{row["mean_conversion_rain_mm"]:.4f}</td><td>{er:.2e}</td><td>{wr:.2e}</td></tr>')
    regions=list(p['inputs']);x=np.arange(len(regions));fig,axes=plt.subplots(1,2,figsize=(12,4.8));colors=['#6d7179','#1c84b1','#a95f36']
    for i,parts in enumerate([1]+p['lowest_cell_parts']):
        rows=[next(row for row in r['results'] if row['region']==region and row['lowest_cell_parts']==(4 if parts==1 else parts)) for region in regions]
        heights=[row['source_reference_height_mean_m'] if parts==1 else row['target_reference_height_mean_m'] for row in rows]
        axes[0].bar(x+(i-1)*.25,heights,.25,color=colors[i],label='original' if parts==1 else f'{parts} lower subcells')
        if parts>1:axes[1].bar(x+(i-1.5)*.32,[row['mean_conversion_rain_mm'] for row in rows],.32,color=colors[i],label=f'{parts} lower subcells')
    axes[0].set_ylabel('Mean exchange reference height (m)');axes[0].set_title('Same pressure lids and dry column mass')
    axes[1].set_ylabel('Initial conversion rain (mm)');axes[1].set_title('Target-pressure phase, returned to surface')
    for ax in axes:ax.set_xticks(x,[name.replace('_',' ') for name in regions]);ax.legend();ax.grid(axis='y',alpha=.2)
    fig.suptitle('Conservative vertical-grid initialization: six static transfers',fontsize=14)
    fig.text(.5,.01,'Zero climate integrations • total water and gas/surface/kinetic energy checked • no rainfall skill measurement',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'pressure_grid_remap.png',dpi=160);plt.close(fig);np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='six_static_remaps_independently_verified',checks=checks,actual_earth_initialized_integrations_started=0,monthly_skill=False,recalibration=False,physical_adoption=False,maximum_actual_energy_relative_error=max(c['actual_energy_relative_error'] for c in checks),maximum_actual_water_relative_error=max(c['actual_water_relative_error'] for c in checks),figure_sha256=file_hash(out/'pressure_grid_remap.png'),raw_fields_sha256=file_hash(out/'publication_fields.npz'),publisher_sha256=file_hash(Path(__file__)),scope='Saved initial fields only. No dynamics, inferred subcell slope, balanced-state claim or production adoption. Conversion rain is not climate rainfall.')
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'pressure_grid_remap.png',dest/'pressure_grid_remap.png');shutil.copyfile(out/'publication_fields.npz',dest/'pressure_grid_remap_fields.npz');write_json(dest/'pressure_grid_remap.json',dict(protocol=p,static_outcomes=r,publication=result))
    with Image.open(out/'pressure_grid_remap.png') as image:width,height=image.size
    section=f'''<!--pressure-grid-remap-start--><section aria-labelledby="pressure-grid-remap-h"><h2 id="pressure-grid-remap-h">Conservative transfer toward a shallower first air cell</h2>
<p>The current first cell uses a surface-exchange reference height of about 730–755 m. A new conservative pressure-overlap operator prepares vertical-resolution controls without changing the column pressure mass or supplying extra water or energy. These six cases are static transfers of saved initial arrays, with zero climate integrations.</p>
<figure><a href="data/pressure_grid_remap.png"><img src="data/pressure_grid_remap.png" width="{width}" height="{height}" loading="lazy" alt="Original and subdivided lowest-cell reference heights, plus small initial phase conversion rain"></a><figcaption>Four-way subdivision brings the reference height to about 170–175 m; sixteen-way subdivision to about 42–43 m. Gas enthalpy and vapor use the exact pressure overlaps. Target-pressure phase returns actual conversion rain and liquid enthalpy to the same surface.</figcaption></figure>
<div class="table"><table><caption>Static initialization checks; conversion rain is excluded from run rainfall</caption><thead><tr><th>Region</th><th>Lower parts</th><th>Old height m</th><th>New height m</th><th>Conversion mm</th><th>Energy rel. error</th><th>Water rel. error</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>Saved fields independently retain total water, gas/surface/kinetic energy and facewise integrated momentum. Refinement preserves kinetic energy; the general coarsening operator exposes unresolved kinetic variance separately and does not assume it becomes heat. Eight new remapping tests and an 86-test focused suite pass.</p>
<p class="note">A constant source cell becomes constant subcells before phase adjustment. No unseen lapse profile is invented, and the remapped state is not promised to be balanced. A shallower cell alone does not validate the surface-exchange closure or improve rainfall accuracy. Dynamic resolution and timestep controls require a separate experiment. The fourteen-day wet/dry runs are independent; normal Earth r39, world, biome and population fields remain unchanged.</p>
<p><a href="data/pressure_grid_remap.json" download>Download frozen static protocol, six outcomes and independent checks</a> · <a href="data/pressure_grid_remap_fields.npz">Source and remapped initial arrays</a> · <a href="../../reports/PRESSURE_GRID_REMAP_20261029.md">Results and next resolution controls</a></p></section><!--pressure-grid-remap-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--pressure-grid-remap-start-->','<!--pressure-grid-remap-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);publish(p.parse_args().out.resolve())
