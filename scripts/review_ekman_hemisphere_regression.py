"""Review changed-source matched regional arrays, with zero integrations."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json
from padding_budget_capture import exact, equation_check, COMPONENTS
from review_padding_sensitivity import validate_state, summarize_state
from surface_wind_forcing import at_day
OUT = ROOT / 'output/ekman_hemisphere_fix_20261127'
PLAN = ROOT / 'calibration/ekman_hemisphere_fix_20261127/plan.json'


def main():
    assert not (OUT / 'review.json').exists()
    plan = json.loads(PLAN.read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    prep = json.loads((OUT / 'preparation.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    assert file_hash(PLAN) == protocol['plan_sha256'] == prep['plan_sha256']
    assert file_hash(OUT / 'protocol.json') == result['protocol_sha256']
    assert file_hash(OUT / 'preparation.json') == protocol['preparation_sha256']
    for section in ['inputs_sha256','model_sources_sha256','execution_sources_sha256']:
        for name,digest in plan[section].items(): assert file_hash(ROOT/name) == digest,name
    for name,digest in plan['private_files_sha256'].items(): assert file_hash(OUT/'model'/name) == digest,name
    assert len(result['rows']) == plan['maximum_diagnostic_integrations'] == 6
    statistics,states,files = [],{},{}
    for row,spec in zip(result['rows'],plan['cases'],strict=True):
        folder = OUT/spec['name']
        assert row == json.loads((folder/'result.json').read_text())
        assert row['status'] == 'passed' and row['numerical_certificate']['all_checks_passed']
        assert row['name'] == spec['name'] and row['residual_tolerance'] == .01
        assert file_hash(folder/'capture.npz') == row['capture_sha256']
        attempt = json.loads((folder/'attempt.json').read_text())
        assert attempt['spec'] == spec and attempt['protocol_sha256'] == file_hash(OUT/'protocol.json')
        old_attempt = json.loads((ROOT/Path(spec['reference_capture']).parent/'attempt.json').read_text())
        assert attempt['params'] == old_attempt['params'], 'Only source, not coefficients, changes'
        with np.load(folder/'capture.npz') as z: state=dict(z)
        with np.load(ROOT/spec['reference_capture']) as z: old=dict(z)
        validate_state(state)
        for name in ['rows','cols','lat','lon','obs_T','obs_P','days']: exact(state[name],old[name])
        if spec['require_byte_exact']:
            assert row['baseline_byte_exact'] and row['model_latitude_min'] > 0
            for key in state: exact(state[key],old[key])
        else:
            assert row['model_latitude_min'] < 0 and row['southern_upwelling_source_cells'] > 0
        if spec['arm'] == 'observed':
            assert row['actual_observed_wind_verified']
            f=OUT/('forcing_'+spec['region']+'.npz')
            assert file_hash(f) == prep['forcing_sha256'][f.name]
            with np.load(f) as z:
                expected=np.stack([at_day(z['wind'],day)[:,state['rows'],state['cols']] for day in state['days']])
            for axis,name in enumerate(['u','v']):
                exact(state['step_'+name],expected[:,axis])
                exact(state['step_moisture_'+name],expected[:,axis])
                exact(state['step_'+name],old['step_'+name])
        budget={k:state['budget__'+k] for k in COMPONENTS+['residual']}
        scaled=equation_check(budget,state['step_P'].astype(np.float32).astype(float),.01)
        before,after=summarize_state(old),summarize_state(state)
        statistics.append(dict(name=spec['name'],region=spec['region'],arm=spec['arm'],
            before=before,after=after,physical_and_budget_byte_exact=spec['require_byte_exact'],
            temperature_mae_change_C=after['temperature_mae_C']-before['temperature_mae_C'],
            annual_rain_change_mm=after['annual_rain_mm']-before['annual_rain_mm'],
            rain_loss_relative_change=after['rain_loss']/before['rain_loss']-1,
            monthly_T_max_absolute_change_C=float(np.abs(state['T']-old['T']).max()),
            annual_sources_change_mm={k:float((state['budget__'+k].astype(float)-old['budget__'+k]).mean()*365) for k in COMPONENTS},
            max_scaled_exported_residual=scaled,source_geometry={k:row[k] for k in ['model_latitude_min','model_latitude_max','southern_upwelling_source_cells']}))
        states[spec['region'],spec['arm']]=(old,state)
        for name in ['attempt.json','result.json','capture.npz']:
            f=folder/name;files[str(f.relative_to(OUT))]=file_hash(f)
    figure(plan,states)
    write_json(OUT/'review.json',dict(status='reviewed_generic_ekman_hemisphere_correction_not_accuracy_qualification',
        protocol_sha256=file_hash(OUT/'protocol.json'),results_sha256=file_hash(OUT/'results.json'),
        statistics=statistics,files_sha256=files,figure_sha256=file_hash(OUT/'source_changes.png'),
        interpretation=plan['interpretation'],climate_adopted=False,atlas_changed=False))
    print('Reviewed six changed-source regressions; four unaffected-domain arrays byte exact.')


def figure(plan,states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(15,7))
    for col,(region,title) in enumerate(zip(plan['regions'],['Somalia','Sahara','North India'],strict=True)):
        for arm,color in [('model','#377d8d'),('observed','#b47552')]:
            old,new=states[region,arm]
            for row,field,unit in [(0,'P','Rain change (mm/model month)'),(1,'T','T change (C)')]:
                axes[row,col].plot(np.arange(1,13),(new[field]-old[field]).mean(1),label=arm+' wind',color=color)
                axes[row,col].set(xticks=[1,4,7,10,12],xlabel='Model month',ylabel=unit)
                axes[row,col].grid(alpha=.15)
        axes[0,col].set_title(title)
    axes[0,0].legend()
    fig.suptitle('Signed-hemisphere Ekman correction: changed source minus matched old source')
    fig.text(.5,.035,'Same parameters, observations, grid and original solver criteria. Northern-only domains must remain byte exact.\nGeneric directional correction, not global accuracy validation or an adopted new climate profile.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.07,right=.98,top=.89,bottom=.14,hspace=.35,wspace=.32)
    fig.savefig(OUT/'source_changes.png',dpi=160)
    plt.close(fig)


if __name__=='__main__': main()
