"""Independently reconstruct actual rain components from six exact captures."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json
from padding_budget_capture import exact,equation_check,COMPONENTS
from review_padding_sensitivity import validate_state,summarize_state
OUT=ROOT/'output/rain_closure_capture_20261127'
PLAN=ROOT/'calibration/rain_closure_capture_20261127/plan.json'


def main():
    assert not (OUT/'review.json').exists()
    plan=json.loads(PLAN.read_text());protocol=json.loads((OUT/'protocol.json').read_text())
    result=json.loads((OUT/'results.json').read_text())
    assert protocol['plan_sha256']==file_hash(PLAN)
    assert result['protocol_sha256']==file_hash(OUT/'protocol.json')
    assert protocol['preparation_sha256']==file_hash(OUT/'preparation.json')
    for section in ['inputs_sha256','model_sources_sha256','execution_sources_sha256']:
        for name,digest in plan[section].items():assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():assert file_hash(OUT/'model'/name)==digest,name
    assert len(result['rows'])==plan['maximum_diagnostic_integrations']==6
    records,states,files=[],{},{}
    for row,spec in zip(result['rows'],plan['cases'],strict=True):
        folder=OUT/spec['name']
        assert row==json.loads((folder/'result.json').read_text())
        assert row['name']==spec['name'] and row['status']=='passed' and row['baseline_byte_exact']
        assert row['numerical_certificate']['all_checks_passed'] and row['residual_tolerance']==.01
        assert file_hash(folder/'capture.npz')==row['capture_sha256']
        attempt=json.loads((folder/'attempt.json').read_text())
        parent_attempt=json.loads((ROOT/Path(spec['reference_capture']).parent/'attempt.json').read_text())
        assert attempt['params']==parent_attempt['params'] and attempt['spec']==spec
        assert attempt['protocol_sha256']==file_hash(OUT/'protocol.json')
        with np.load(folder/'capture.npz') as z:s=dict(z)
        with np.load(ROOT/spec['reference_capture']) as z:
            for key in z.files:exact(s[key],z[key])
        validate_state(s)
        budget={k:s['budget__'+k] for k in COMPONENTS+['residual']}
        equation_check(budget,s['step_P'].astype(np.float32).astype(float),.01)
        W,Ws,A,inst=[s['rain__'+k] for k in ['W','saturation','dynamics','instability']]
        exact(W,s['step_W'])
        c={k:s['rain__closure_'+k] for k in ['conv','r0','evap','T','fT','cap']}
        constants=row['rainfall_constants'];assert constants['rh_spread']==0
        rh=W/Ws
        gate=np.clip((rh-constants['rh_threshold'])/(1-constants['rh_threshold']),0,2)**1.5
        uncap=c['conv']*np.exp(11.4*(np.minimum(rh,1.5)-c['r0']))*c['fT']
        capped=np.where(c['cap']>0,c['cap']*np.tanh(uncap/np.maximum(c['cap'],1e-9)),uncap)
        loss=np.exp(-c['evap']*np.maximum((20+c['T']/5)*(100-100*np.clip(rh,0,1)),0)/3000)
        # Algebraically separate mm/day rates, independently of the producer
        # helper and production coefficient's rate-per-second accumulation.
        base=A*gate*inst*W/constants['precip_tau_days']*loss
        conv=capped*W/np.maximum(W,.1)*loss
        overflow=np.maximum(W-Ws,0)
        parts=dict(base=base,convective=conv,overflow=overflow)
        for name,value in parts.items():
            np.testing.assert_allclose(value,s['rain__component_'+name],atol=1e-10,rtol=1e-12)
        np.testing.assert_allclose(base+conv+overflow,s['step_P'],atol=1e-10,rtol=1e-12)
        stats=summarize_state(s)
        july_mean=lambda value:float(monthly_amount(value,s['days'])[6]/(365/12))
        records.append(dict(name=spec['name'],region=spec['region'],endpoint=spec['endpoint'],**stats,
            annual_component_mm={k:float(v.mean()*365) for k,v in parts.items()},
            mean_RH=float(rh.mean()),july_RH=july_mean(rh),
            mean_effective_r0=float(c['r0'].mean()),july_effective_r0=july_mean(c['r0']),
            mean_dynamics=float(A.mean()),july_dynamics=july_mean(A),
            mean_instability=float(inst.mean()),july_instability=july_mean(inst),
            mean_subcloud_survival=float(loss.mean()),
            convective_above_95_percent_of_cap_sample_fraction=float(((c['cap']>0)&(capped>=.95*c['cap'])).mean()),
            maximum_absolute_reconstruction_mm_day=float(np.abs(base+conv+overflow-s['step_P']).max()),
            july_component_mm_day={k:july_mean(v) for k,v in parts.items()}))
        states[spec['region'],spec['endpoint']]=(s,parts)
        for name in ['attempt.json','result.json','capture.npz']:
            f=folder/name;files[str(f.relative_to(OUT))]=file_hash(f)
    figure(plan,states)
    write_json(OUT/'review.json',dict(status='reviewed_six_exact_actual_rain_closure_captures',
        plan_sha256=file_hash(PLAN),protocol_sha256=file_hash(OUT/'protocol.json'),
        results_sha256=file_hash(OUT/'results.json'),statistics=records,files_sha256=files,
        figure_sha256=file_hash(OUT/'rain_components.png'),extra_integrations=0,
        interpretation='Actual solved-state algebraic rainfall component identities, not independent causal rain reductions or evidence from an intervention. Dynamics/instability/closure thresholds and vapor state interact. No fitting/adoption.',climate_adopted=False,atlas_changed=False))
    print('Reviewed six exact physical replays and independent base/convective/overflow rainfall identities.')


def monthly_amount(values,days):
    n=len(days);out=np.zeros((12,values.shape[1]))
    for month in range(12):
        for k in range(n):
            overlap=max(0.,min((month+1)*365/12,(k+1)*365/n)-max(month*365/12,k*365/n))
            out[month]+=values[k]*overlap
    return out.mean(1)


def figure(plan,states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(15,8))
    for col,(region,title) in enumerate(zip(plan['regions'],['Somalia','Sahara','North India'],strict=True)):
        for row,endpoint in enumerate(['baseline','joint_observed']):
            s,parts=states[region,endpoint];ax=axes[row,col]
            curves=[monthly_amount(parts[k],s['days']) for k in ['base','convective','overflow']]
            ax.stackplot(np.arange(1,13),curves,labels=['Humidity/dynamics base','Exponential convection','Supersaturation'],colors=['#d5a64e','#377d8d','#a5a5a5'])
            ax.plot(np.arange(1,13),s['obs_P'].mean(1),'k--',label='Fixed rain observations')
            ax.set(title=title+' / '+endpoint.replace('_',' '),ylabel='Rain (mm/model month)',xlabel='Model month',xticks=[1,4,7,10,12]);ax.grid(alpha=.15)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Actual rainfall coefficient components: six unchanged endpoint replays')
    fig.text(.5,.035,'Algebraic components evaluated at each actual solved water column, with actual saturation/threshold/cap/subcloud evaporation.\nEvery parent physical/budget array remains byte exact. Component size is not the causal effect of removing that component.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.07,right=.98,top=.89,bottom=.14,hspace=.38,wspace=.32)
    fig.savefig(OUT/'rain_components.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
