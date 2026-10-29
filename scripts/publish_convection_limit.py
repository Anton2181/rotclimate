"""Verify and publish the rejected-step replay and every frozen static cap."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load


def publish(out):
    literal=ROOT/'calibration/convection_limit_replay_20261029/plan.json';p=json.loads(literal.read_text());r=json.loads((out/'verification.json').read_text());assert literal.read_bytes()==(out/'frozen_protocol.json').read_bytes() and file_hash(literal)==r['literal_plan_sha256']
    for n,h in p['sources'].items():assert file_hash(ROOT/n)==h,n
    assert r['expected_rejection_reproduced'] and all(r['rejected_weather_state_byte_exact'].values())
    assert r['actual_earth_initialized_integrations_started']==1 and r['integrations_completed']==0
    assert [c['maximum_sweeps'] for c in r['static_controls']]==p['static_maximum_sweeps'] and r['captured_nonconverged_targets']==1
    meta=json.load(open(out/'closure_input_0.json'));assert file_hash(out/'closure_input_0.npz')==meta['fields_sha256'];a=load(out/'closure_input_0.npz');combined={'captured_'+k:v for k,v in a.items()};checks=[];converged=[];table=[]
    before=(1004*a['cell_mass']+1850*a['input_vapor'])*a['input_temperature']+(2.5e6-1850*273.15)*a['input_vapor'];w0=a['input_vapor'].sum(0)
    for row in r['static_controls']:
        cap=row['maximum_sweeps'];path=out/f'closure_0_cap{cap}.npz';assert file_hash(path)==row['fields_sha256'];b=load(path);combined.update({f'cap{cap}_'+k:v for k,v in b.items()})
        after=(1004*a['cell_mass']+1850*b['vapor'])*b['temperature']+(2.5e6-1850*273.15)*b['vapor'];er=float(np.max(abs(after.sum(0)+b['rain_enthalpy']-before.sum(0))/np.maximum(abs(before).sum(0),1.)));wr=float(np.max(abs(b['vapor'].sum(0)+b['rain']-w0)/np.maximum(w0,1.)));assert max(er,wr)<1e-11
        if cap==64:
            assert row['byte_exact_to_captured_target']
            for key,old in [('temperature','output_temperature'),('vapor','output_vapor'),('rain','rain'),('rain_enthalpy','rain_enthalpy')]:assert b[key].tobytes()==a[old].tobytes()
        if row['certificate']['converged']:converged.append((cap,b))
        c=dict(maximum_sweeps=cap,converged=row['certificate']['converged'],actual_sweeps=row['certificate']['sweeps'],remaining_interfaces=row['certificate']['remaining_active_interfaces'],actual_energy_relative_error=er,actual_water_relative_error=wr);checks.append(c)
        table.append(f'<tr><td>{cap}</td><td>{c["converged"]}</td><td>{c["actual_sweeps"]}</td><td>{c["remaining_interfaces"]}</td><td>{er:.2e}</td><td>{wr:.2e}</td></tr>')
    same=True
    for _,b in converged[1:]:same=same and all(b[k].tobytes()==converged[0][1][k].tobytes() for k in b)
    assert same and len(converged)==3
    caps=[str(c['maximum_sweeps']) for c in checks];fig,axes=plt.subplots(1,2,figsize=(11,4.5));colors=['#ab6038' if not c['converged'] else '#25875c' for c in checks]
    axes[0].bar(caps,[c['remaining_interfaces'] for c in checks],color=colors);axes[0].set_ylabel('Remaining unstable interfaces');axes[0].set_title('Same captured convection input')
    axes[1].bar(caps,[c['actual_sweeps'] for c in checks],color=colors);axes[1].set_ylabel('Actual sweeps');axes[1].set_title('Converged targets stop at 176 sweeps')
    for ax in axes:ax.set_xlabel('Maximum allowed sweeps');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Fine-grid rejection: insufficient solver work on the captured India step',fontsize=13);fig.text(.5,.01,'Same 0.01 K tolerance and thermodynamics • all caps conserve water/enthalpy • conservation alone does not imply convergence',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'convection_limit.png',dpi=160);plt.close(fig);np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='replayed_rejection_and_static_work_caps_verified',new_earth_integrations=1,integrations_completed=0,expected_replay_numerical_failures=1,static_closure_cases=5,cumulative_prototype_starts=103,cumulative_prototype_completions=95,cumulative_retained_failures=8,rejection_reproduced=True,retained_weather_byte_exact=r['rejected_weather_state_byte_exact'],checks=checks,converged_caps_byte_exact=same,converged_caps=[c for c,_ in converged],physical_adoption=False,numerical_cap_dynamic_adoption=False,recalibration=False,monthly_skill=False,publisher_sha256=file_hash(Path(__file__)),raw_fields_sha256=file_hash(out/'publication_fields.npz'),figure_sha256=file_hash(out/'convection_limit.png'),scope='One rejected Earth-input step repeated and retained; five closure-only work-cap controls add no Earth integrations. A 176-sweep target diagnoses one insufficient work limit, not a new physical law, full-run stability or climate accuracy.')
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data';write_json(dest/'convection_limit.json',dict(protocol=p,replay=r,publication=result));shutil.copyfile(out/'convection_limit.png',dest/'convection_limit.png');shutil.copyfile(out/'publication_fields.npz',dest/'convection_limit_fields.npz')
    with Image.open(out/'convection_limit.png') as im:w,h=im.size
    section=f'''<!--convection-limit-start--><section aria-labelledby="convection-limit-h"><h2 id="convection-limit-h">Reproduced fine-grid rejection: the captured target needs more solver work</h2>
<p>The next rejected India step is replayed once from its retained 19-step checkpoint. The original convergence error reproduces, the last accepted weather remains byte-identical, and a passive observer captures the actual convection input and rejected target without changing the physical equations. This is a new integration attempt and remains a numerical failure in the record.</p>
<figure><a href="data/convection_limit.png"><img src="data/convection_limit.png" width="{w}" height="{h}" loading="lazy" alt="Static convection work-cap tests: 64 and 128 sweeps fail, while 256, 512 and 1024 limits converge at 176 sweeps"></a><figcaption>All five fixed caps use the same captured input, 0.01 K stopping tolerance, phase law and conservative mixing. Budgets close even for nonconverged targets, so conservation alone is insufficient.</figcaption></figure>
<div class="table"><table><caption>Five static closure solves; zero additional dynamics integrations</caption><thead><tr><th>Work cap</th><th>Converged</th><th>Actual sweeps</th><th>Remaining interfaces</th><th>Energy rel. error</th><th>Water rel. error</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>The 64-sweep target exactly reproduces the captured rejected target. Caps 256/512/1024 stop at the same 176 sweeps and produce byte-identical temperature, vapor, rain and liquid enthalpy. This establishes inadequate work allowance for this input; it does not prove that any fixed cap suffices for a full finer-grid run.</p>
<p class="note">One expected rejected replay brings the separate prototype record to 103 starts /95 completions /eight retained numerical failures. The five static solves are not extra Earth integrations. No larger cap is dynamically adopted in this diagnostic. The next frozen six-run protocol tests the full finer-grid day at 900/450 seconds with a fixed 1024-sweep allowance, keeping all physical parameters and the stopping tolerance unchanged. Legacy 1934/1929, Earth r39 and all normal atlas fields remain unchanged; no recalibration or monthly skill improvement.</p>
<p><a href="data/convection_limit.json" download>Download frozen replay, all five static caps and independent checks</a> · <a href="data/convection_limit_fields.npz">Captured inputs and every target array</a> · <a href="../../reports/CONVECTION_LIMIT_20261029.md">Failure diagnosis and full-run follow-up</a></p></section><!--convection-limit-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--convection-limit-start-->','<!--convection-limit-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);publish(p.parse_args().out.resolve())
