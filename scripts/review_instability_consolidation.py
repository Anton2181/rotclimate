"""Review four physical candidates against frozen current-source paired controls."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from local_benchmark_protocol import file_hash,write_json
from padding_budget_capture import exact,equation_check,COMPONENTS
from review_padding_sensitivity import validate_state,summarize_state
from surface_wind_forcing import at_day
OUT=ROOT/'output/instability_consolidation_20261127'
PLAN=ROOT/'calibration/instability_consolidation_20261127/plan.json'


def main():
    assert not (OUT/'review.json').exists()
    plan=json.loads(PLAN.read_text());protocol=json.loads((OUT/'protocol.json').read_text())
    result=json.loads((OUT/'results.json').read_text())
    assert file_hash(PLAN)==protocol['plan_sha256'] and file_hash(OUT/'protocol.json')==result['protocol_sha256']
    assert len(result['rows'])==plan['maximum_diagnostic_integrations']==4
    for section in ['inputs_sha256','model_sources_sha256','execution_sources_sha256']:
        for name,digest in plan[section].items():assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():assert file_hash(OUT/'model'/name)==digest,name
    assert plan['model_sources_sha256']==json.loads((ROOT/plan['exact_control_source_plan']).read_text())['model_sources_sha256']
    statistics,states,files=[],{},{}
    for row,spec in zip(result['rows'],plan['cases'],strict=True):
        folder=OUT/spec['name']
        assert row==json.loads((folder/'result.json').read_text()) and row['name']==spec['name']
        assert row['status']=='passed' and row['numerical_certificate']['all_checks_passed']
        assert row['instability_parameter']==0. and row['residual_tolerance']==.01
        assert file_hash(folder/'capture.npz')==row['capture_sha256']
        attempt=json.loads((folder/'attempt.json').read_text())
        parent_folder=ROOT/Path(spec['reference_capture']).parent
        old_attempt=json.loads((parent_folder/'attempt.json').read_text())
        assert attempt['spec']==spec and attempt['protocol_sha256']==file_hash(OUT/'protocol.json')
        differences={k:[old_attempt['params'][k],attempt['params'][k]] for k in old_attempt['params'] if old_attempt['params'][k]!=attempt['params'][k]}
        assert set(differences)=={'instability'} and differences['instability'][1]==0.
        assert json.loads((parent_folder/'result.json').read_text())['numerical_certificate']['all_checks_passed']
        with np.load(folder/'capture.npz') as z:s=dict(z)
        with np.load(ROOT/spec['reference_capture']) as z:old=dict(z)
        validate_state(s)
        for key in ['rows','cols','lat','lon','obs_T','obs_P','days','sea_rows','sea_cols']:exact(s[key],old[key])
        budget={k:s['budget__'+k] for k in COMPONENTS+['residual']}
        scaled=equation_check(budget,s['step_P'].astype(np.float32).astype(float),.01)
        if spec['arm']=='observed':
            with np.load(OUT/('forcing_'+spec['region']+'.npz')) as z:
                for axis,key in enumerate(['u','v']):
                    expected=np.stack([at_day(z['wind'],d)[axis,s['rows'],s['cols']] for d in s['days']])
                    exact(s['step_'+key],expected);exact(s['step_moisture_'+key],expected)
                sr,sc=s['sea_rows'],s['sea_cols']
                expected=np.stack([at_day(z['sst'],d)[sr,sc] for d in s['days']])
                for key in ['step_sea_SST','step_sea_Teq','step_sea_heat_SST']:exact(s[key],expected)
        before,after=summarize_state(old),summarize_state(s)
        statistics.append(dict(name=spec['name'],region=spec['region'],endpoint=spec['endpoint'],before=before,after=after,
            T_ratio=after['temperature_mae_C']/before['temperature_mae_C'],rain_loss_ratio=after['rain_loss']/before['rain_loss'],
            annual_rain_change_mm=after['annual_rain_mm']-before['annual_rain_mm'],
            annual_source_changes_mm={k:float((s['budget__'+k].astype(float)-old['budget__'+k]).mean()*365) for k in COMPONENTS},max_scaled_residual=scaled))
        states[spec['region'],spec['endpoint']]=(old,s)
        for key in ['attempt.json','result.json','capture.npz']:
            f=folder/key;files[str(f.relative_to(OUT))]=file_hash(f)
    native=[s for s in statistics if s['endpoint']=='native']
    eligible=(all(s['T_ratio']<=1.01 and s['rain_loss_ratio']<=1.01 for s in native)
              and next(s for s in native if s['region']=='s_2n_43e')['rain_loss_ratio']<=.90)
    figure(plan,states)
    write_json(OUT/'review.json',dict(status='reviewed_fixed_instability0_physical_pilot_not_global_qualification',
        protocol_sha256=file_hash(OUT/'protocol.json'),statistics=statistics,files_sha256=files,
        prospective_screen=plan['screen'],eligible_for_further_exposed_evaluation=bool(eligible),
        reused_exact_control_integrations=4,new_candidate_integrations=4,
        figure_sha256=file_hash(OUT/'physical_response.png'),climate_adopted=False,atlas_changed=False))
    print('Four physical candidates reviewed; prospective guard screen:',bool(eligible))


def figure(plan,states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,4,figsize=(17,7))
    labels=['Somalia / native','Sahara / native','North India / native','Somalia / observed wind+SST']
    for col,(spec,label) in enumerate(zip(plan['cases'],labels,strict=True)):
        old,new=states[spec['region'],spec['endpoint']]
        for row,(field,unit) in enumerate([('P','Rain (mm/model month)'),('T','Temperature (C)')]):
            ax=axes[row,col]
            ax.plot(np.arange(1,13),old[field].mean(1),label='Frozen control',color='#377d8d')
            ax.plot(np.arange(1,13),new[field].mean(1),label='Bulk warm boost removed',color='#b47552')
            ax.plot(np.arange(1,13),old['obs_'+field].mean(1),'k--',label='Fixed observations')
            ax.set(ylabel=unit,xlabel='Model month',xticks=[1,4,7,10,12]);ax.grid(alpha=.15)
        axes[0,col].set_title(label,fontsize=10)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Physical candidate: remove inherited bulk instability boost, keep exponential convection')
    fig.text(.5,.035,'Only instability changes to0. All transport, explicit convection, coefficients and original solver criteria retained.\nControls reused from byte-exact current-source replays; four fresh candidates. Regional pilot, not an adopted climate.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.055,right=.99,top=.89,bottom=.14,hspace=.35,wspace=.35)
    fig.savefig(OUT/'physical_response.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
