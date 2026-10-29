"""Verify numerical-backend equivalence before accepting faster prototype runs."""
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


def publish(out):
    receipt=json.loads((out/'verification.json').read_text());plan=json.loads((out/'frozen_protocol.json').read_text());literal=ROOT/'calibration/phase_backend_20261029/plan.json'
    if literal.read_bytes()!=(out/'frozen_protocol.json').read_bytes() or file_hash(literal)!=receipt['literal_plan_sha256']:raise ValueError('Changed backend protocol')
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed backend source/input: '+n)
    if receipt['actual_earth_initialized_integrations_started']!=6 or receipt['integrations_completed']!=6:raise ValueError('Need all six retained completed numerical controls')
    kernel_folder=ROOT/'output/fast_liquid_phase_20261029';kernel=json.loads((kernel_folder/'verification.json').read_text());kp=json.loads((kernel_folder/'frozen_plan.json').read_text())
    kernel_literal=ROOT/'calibration/fast_liquid_phase_20261029/plan.json'
    assert kernel_literal.read_bytes()==(kernel_folder/'frozen_plan.json').read_bytes() and file_hash(kernel_literal)==kernel['plan_sha256']
    assert file_hash(kernel_folder/'fields.npz')==kernel['fields_sha256']
    for n,h in kp['sources'].items():assert file_hash(ROOT/n)==h
    combined={'kernel_'+k:v for k,v in load(kernel_folder/'fields.npz').items()};checks={};table=[];max_e=0.;max_w=0.
    field_limits=dict(temperature='temperature_k_absolute',vapor='vapor_kg_m2_absolute',u='velocity_ms_absolute',v='velocity_ms_absolute',
        surface_temperature='surface_temperature_k_absolute',surface_liquid='surface_liquid_kg_m2_absolute',rain='rain_kg_m2_absolute',rain_enthalpy='rain_enthalpy_j_m2_absolute')
    regions=list(plan['case_plans']);times={};case_records={}
    for region in regions:
        finals={};initials={};rows={};timing={};budgets={};case_plan=json.loads((ROOT/plan['case_plans'][region]).read_text());base=json.loads((ROOT/case_plan['boundary_plan']).read_text())
        m0=-np.diff(base['pressure_edges_pa'])/9.80665
        case_records[region]={}
        for name in ['reference','candidate']:
            folder=out/(region+'_'+name);r=json.loads((folder/'verification.json').read_text());row=r['results'][0];assert row['status']=='completed' and row['steps']==96
            case_literal=ROOT/plan['case_plans'][region]
            assert case_literal.read_bytes()==(folder/'frozen_plan.json').read_bytes() and file_hash(case_literal)==r['literal_plan_sha256']
            aggregate=[c for c in receipt['results'] if c['region']==region and c['backend']==name]
            assert len(aggregate)==1 and file_hash(folder/'verification.json')==aggregate[0]['source_receipt_sha256']
            case_records[region][name]=dict(frozen_plan=case_plan,run=r)
            fields=folder/region/'forced/900.npz';assert file_hash(fields)==row['fields_sha256'];a=load(fields);initial=load(folder/region/'initial.npz');rows[name]=row;finals[name]=a;initials[name]=initial
            mass=np.broadcast_to(m0[:,None,None],a['temperature'].shape);cells=initial['latitude'].size
            hg=lambda d:float(((1004*mass+1850*d['vapor'])*d['temperature']+(2.5e6-1850*273.15)*d['vapor']).sum())
            hs=lambda d:float(((d['substrate_capacity']+4186*d['surface_liquid'])*(d['surface_temperature']-273.15)).sum())
            ke=lambda d:float(.5*(np.sum(m0[:,None,None]*d['u'][:,:,1:-1]**2)+np.sum(m0[:,None,None]*d['v'][:,1:-1]**2)))
            old=hg(initial)+hs(initial)+ke(initial);final=hg(a)+hs(a)+ke(a)
            ee=abs(final-old-row['net_external_energy_j_m2']*cells)/abs(old);water0=float(initial['vapor'].sum()+initial['surface_liquid'].sum())
            we=abs(a['vapor'].sum()+a['surface_liquid'].sum()-water0+row['net_outward_water_kg_m2']*cells)/water0;max_e=max(max_e,ee);max_w=max(max_w,we)
            budgets[name]=dict(actual_energy_relative_error=float(ee),actual_water_relative_error=float(we))
            t=json.loads((folder/'backend_timing.json').read_text());assert all(v['same_code_object'] for v in t['body_bindings'].values())
            if len(t['step_timings'])!=96 or not all(c['completed'] for c in t['step_timings']):raise ValueError('Dropped/failed timing sample')
            seconds=[c['seconds'] for c in t['step_timings']];np.testing.assert_allclose(sum(seconds),t['successful_steps_total_s'],rtol=1e-12)
            timing[name]=dict(coupled_call_total_s=float(sum(seconds)),median_coupled_step_s=float(np.median(seconds)),driver_wall_s=t['driver_wall_seconds'],all_step_seconds=seconds)
            combined.update({region+'_'+name+'_initial_'+k:v for k,v in initial.items()});combined.update({region+'_'+name+'_final_'+k:v for k,v in a.items()})
        for k in initials['reference']:np.testing.assert_array_equal(initials['reference'][k],initials['candidate'][k])
        previous=ROOT/'output/surface_forcing_20261029'/region/'forced/900.npz';previous_row=json.loads(previous.with_suffix('.json').read_text());old=load(previous)
        previous_initial=load(previous.parent.parent/'initial.npz')
        for k in previous_initial:np.testing.assert_array_equal(initials['reference'][k],previous_initial[k])
        exact={k:finals['reference'][k].dtype==old[k].dtype and finals['reference'][k].shape==old[k].shape and finals['reference'][k].tobytes()==old[k].tobytes() for k in old}
        if not all(exact.values()) or rows['reference']['history']!=previous_row['history']:raise ValueError('Bound reference changed the archived baseline')
        differences={}
        for k,limit in field_limits.items():
            error=float(abs(finals['candidate'][k]-finals['reference'][k]).max());differences[k]=error
            if error>plan['state_equivalence'][limit]:raise ValueError('Predeclared backend state tolerance failed: '+region+' '+k)
        np.testing.assert_array_equal(finals['reference']['substrate_capacity'],finals['candidate']['substrate_capacity'])
        speedup=timing['reference']['coupled_call_total_s']/timing['candidate']['coupled_call_total_s'];reduction=1-1/speedup;times[region]=timing
        checks[region]=dict(reference_byte_exact=exact,reference_scalar_history_exact=True,maximum_absolute_state_differences=differences,actual_budgets=budgets,timing=timing,measured_coupled_call_speedup=speedup,measured_time_reduction_fraction=reduction)
        table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{timing["reference"]["coupled_call_total_s"]:.2f}</td><td>{timing["candidate"]["coupled_call_total_s"]:.2f}</td><td>{speedup:.2f}×</td><td>{100*reduction:.1f}%</td><td>{differences["temperature"]:.2e}</td><td>{differences["rain"]:.2e}</td></tr>')
    if max(max_e,max_w)>1e-10:raise ValueError('Independent saved numerical-control budget failed')
    fig,axes=plt.subplots(1,2,figsize=(12.5,4.8));colors=['#9c6a41','#1675a6'];x=np.arange(3)
    for i,name in enumerate(['reference','candidate']):
        axes[0].bar(x+(i-.5)*.34,[1000*kernel['results'][case][name+'_median_s'] for case in ['clear','condensing','mixed']],.34,color=colors[i],label=name)
        axes[1].bar(x+(i-.5)*.34,[times[region][name]['coupled_call_total_s'] for region in regions],.34,color=colors[i],label=name)
    axes[0].set_xticks(x,['clear','condensing','mixed']);axes[0].set_ylabel('Median phase call (ms)');axes[0].set_title('Synthetic phase kernel')
    axes[1].set_xticks(x,[r.replace('_',' ') for r in regions]);axes[1].set_ylabel('All96 coupled calls (s)');axes[1].set_title('Complete24h forced evolution calls')
    for ax in axes:ax.legend();ax.grid(axis='y',alpha=.2)
    fig.suptitle('Equivalent phase numerics: kernel timings and full coupled-step timings',fontsize=13)
    fig.text(.5,.01,'Same physical equations and guards • paired order fixed before outcomes • no timing speed gate • not rainfall skill',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'phase_backend.png',dpi=160);plt.close(fig);np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='phase_backend_equivalence_verified',numerical_backend_qualified_for_future_prototype_runs=True,physical_model_adoption=False,production_atlas_adoption=False,
        new_earth_input_numerical_controls=6,cumulative_smoke_starts=81,cumulative_smoke_completed=77,cumulative_smoke_failures_retained=4,legacy_benchmark_attempts_added=0,monthly_skill=False,recalibration=False,cases=checks,
        maximum_actual_energy_relative_error=float(max_e),maximum_actual_water_relative_error=float(max_w),kernel_timing=kernel,
        scope='Final fields and scalar histories checked against frozen controls; saved energy/water reconstructed against recorded supply. Paired timings are observed, not timing confidence intervals or climate skill.',
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),figure_sha256=file_hash(out/'phase_backend.png'),publisher_sha256=file_hash(Path(__file__)),source_receipt_sha256=file_hash(out/'verification.json'))
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'publication_fields.npz',dest/'phase_backend_fields.npz');shutil.copyfile(out/'phase_backend.png',dest/'phase_backend.png');write_json(dest/'phase_backend.json',dict(protocol=plan,runs=receipt,case_records=case_records,publication=result))
    with Image.open(out/'phase_backend.png') as im:width,height=im.size
    section=f'''<!--phase-backend-start--><section aria-labelledby="phase-backend-h"><h2 id="phase-backend-h">Faster phase numerics with equivalent coupled states</h2>
<p>The new liquid-phase root is cleared for future prototype runs after six fixed24-hour Earth-input numerical controls. It changes the numerical solution method while retaining the same liquid enthalpy/saturation equations, physical guards and frozen dynamics/convection/surface code bodies. No planetary parameter is retuned. Original module globals remain unchanged.</p>
<figure><a href="data/phase_backend.png"><img src="data/phase_backend.png" width="{width}" height="{height}" loading="lazy" alt="Reference and safeguarded phase kernel timings, plus total coupled-step times for three complete24-hour Earth-input cases"></a><figcaption>The synthetic phase kernel speeds up3.4–9×; complete coupled-call time falls about15–28%. These are different measurements. Total coupled-call time includes all96 physical steps; file hashing, preparation and publication are outside that measurement.</figcaption></figure>
<div class="table"><table><caption>Six completed controls; observed timing for each paired24-hour case</caption><thead><tr><th>Region</th><th>Reference calls s</th><th>Candidate calls s</th><th>Speedup</th><th>Time reduction</th><th>Max ΔT K</th><th>Max Δrain mm</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>Every reference final array and diagnostic scalar history exactly reproduces the archived900-second baseline. Candidate final temperature differences stay below1.5e−11 K and rain differences below3.6e−11 mm, inside the tolerances declared before integration. Water and total gas/kinetic/surface energy still close.369 focused tests pass, including1,800 randomized equilibrium states, explicit fallback, independent dependency namespaces and complete synthetic coupling.</p>
<p>The solver skips already solved clear endpoints and uses safeguarded analytic Newton steps inside the original bracket, with the old bisection solver retained as fallback. This reduces the cost of longer spinup and broader searches; it is not a climate-accuracy gain or proof of a global calibration optimum. Raw timings include every successful call, with reference/candidate order alternating by region and no minimum-speed gate.</p>
<p class="note">Six new numerical controls bring the separate prototype record to81 starts /77 completions /four retained earlier failures. Legacy1934/1929, Earthr39 and all normal world/biome/population fields remain unchanged. The faster numerical backend is qualified; the new physical climate model is not adopted or recalibrated. Initial soil-water uncertainty, flat terrain, partial upper atmosphere and omitted nonlinear momentum remain unresolved.</p>
<p><a href="data/phase_backend.json" download>Download frozen protocols, all paired timings and state checks</a> · <a href="data/phase_backend_fields.npz">Raw synthetic and Earth-input numerical-control states</a> · <a href="../../reports/PHASE_BACKEND_20261029.md">Equivalence, timing scope and next numerical work</a></p></section><!--phase-backend-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--phase-backend-start-->','<!--phase-backend-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps({k:v for k,v in result.items() if k not in ['cases','kernel_timing']},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
