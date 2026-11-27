"""Review two source checks and explicit inactive-branch compatibility proof."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from local_benchmark_protocol import file_hash,write_json
from review_current_climate_reference import score_bounds
from rotclimate.koppen import monthly_stats
PLAN=ROOT/'calibration/southern_zonal_belts_fix_20261127/plan.json'
OUT=ROOT/'output/southern_zonal_belts_fix_20261127'


def main():
    assert not (OUT/'review.json').exists()
    plan=json.loads(PLAN.read_text())
    protocol=json.loads((OUT/'protocol.json').read_text())
    results=json.loads((OUT/'results.json').read_text())
    assert file_hash(PLAN)==protocol['plan_sha256']
    assert file_hash(OUT/'protocol.json')==results['protocol_sha256']
    assert file_hash(OUT/'preparation.json')==protocol['preparation_sha256']
    for section in ['model_sources_sha256','execution_sources_sha256','inputs_sha256']:
        for name,digest in plan[section].items():
            assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():
        assert file_hash(OUT/'model'/name)==digest,name
    scope=json.loads((OUT/'reference_scope.json').read_text())
    assert len(scope['regions'])==97 and scope['new_model_sources_sha256']==plan['model_sources_sha256']
    assert all(s['cells_that_could_enter_new_branch_for_any_season']==0 for s in scope['regions'])
    suites=ET.parse(OUT/'regressions.xml').getroot().iter('testsuite')
    suites=list(suites)
    assert sum(int(s.attrib['tests']) for s in suites)==39
    assert all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
    assert len(results['rows'])==plan['maximum_integrations']==2
    stats,states,files=[],{},{}
    for row,spec in zip(results['rows'],plan['cases'],strict=True):
        folder=OUT/spec['name'];name=spec['region']
        assert row['name']==spec['name'] and row['region']==name
        assert row['status']=='passed' and row['numerics']['all_checks_passed']
        assert row['case_identity']==spec['case_identity']
        assert {k:v for k,v in row.items() if k!='name'}==json.loads((folder/'cases'/(name+'.json')).read_text())
        p=json.loads((folder/'protocol.json').read_text())
        assert p['sources']==plan['benchmark_protocol_sources_sha256']
        assert p['params']==json.loads((ROOT/spec['control_protocol']).read_text())['params']
        attempt=json.loads((folder/'attempts'/(name+'.json')).read_text())
        assert attempt['spec']==spec and attempt['protocol_sha256']==file_hash(folder/'protocol.json')
        assert file_hash(folder/'cells'/(name+'.npz'))==row['cells_sha256']
        assert file_hash(folder/'cells'/(name+'_winds.npz'))==row['wind_capture_sha256']
        with np.load(folder/'cells'/(name+'.npz')) as z:
            new=dict(z)
        with np.load(ROOT/spec['control_cells']) as z:
            old=dict(z)
        assert set(new)==set(old)
        for k in new:
            assert new[k].shape==old[k].shape and np.isfinite(new[k]).all()
            if spec['must_be_exact'] or k not in ['Ts','Ps']:
                assert new[k].dtype==old[k].dtype and new[k].tobytes()==old[k].tobytes(),(spec['name'],k)
        tb,pb=score_bounds(new)
        assert tb[0]-1e-12<=row['temperature']['monthly_mae_C']<=tb[1]+1e-12
        assert pb[0]-1e-12<=row['rain']['loss']<=pb[1]+1e-12
        with np.load(folder/'cells'/(name+'_winds.npz')) as wind,np.load(ROOT/spec['control_winds']) as previous:
            assert all(np.isfinite(wind[k]).all() for k in wind.files)
            np.testing.assert_array_equal(wind['days'],previous['days'])
            for k in ['lat','lon','i','j']:
                np.testing.assert_array_equal(wind[k],new[k])
            for k in ['u','v']:
                actual=monthly_stats(wind['raw_'+k],wind['raw_'+k],wind['days'],365.)['Tm'][:,wind['i'],wind['j']]
                np.testing.assert_array_equal(actual,wind[k])
                if spec['must_be_exact']:
                    assert wind[k].dtype==previous[k].dtype and wind[k].tobytes()==previous[k].tobytes()
            active=wind['active_cells_per_step']
            assert (active>=0).all()
            if spec['must_be_exact']:
                assert not active.any()
            else:
                assert active.any()
            wind_change=max(float(np.abs(wind[k]-previous[k]).max()) for k in ['u','v'])
        original=json.loads((ROOT/spec['control_record']).read_text())
        stats.append(dict(name=spec['name'],pad_km=spec['pad_km'],
            all_saved_arrays_byte_exact_required=spec['must_be_exact'],
            T_before=original['temperature']['monthly_mae_C'],T_after=row['temperature']['monthly_mae_C'],
            rain_loss_before=original['rain']['loss'],rain_loss_after=row['rain']['loss'],
            annual_rain_before_mm=original['rain']['sim_mean_annual_mm'],annual_rain_after_mm=row['rain']['sim_mean_annual_mm'],
            max_scored_monthly_T_change_C=float(np.abs(new['Ts'].astype(float)-old['Ts']).max()),
            max_scored_monthly_P_change_mm=float(np.abs(new['Ps'].astype(float)-old['Ps']).max()),
            max_scored_monthly_wind_component_change_m_s=wind_change,
            new_branch_active_steps=int((active>0).sum()),new_branch_maximum_active_cells=int(active.max())))
        states[spec['name']]=(old,new)
        for rel in ['cases/'+name+'.json','cells/'+name+'.npz','cells/'+name+'_winds.npz','attempts/'+name+'.json','protocol.json','summary.json']:
            files[str((folder/rel).relative_to(OUT))]=file_hash(folder/rel)
    figure(plan,states)
    write_json(OUT/'review.json',dict(status='verified_unfitted_southern_belts_source_fix',
        plan_sha256=file_hash(PLAN),results_sha256=file_hash(OUT/'results.json'),
        statistics=stats,files_sha256=files,original_numerical_certificates=2,
        regression_tests_passed=39,r58_reference_all97_new_branch_inactive=True,
        reference_scope_sha256=file_hash(OUT/'reference_scope.json'),
        figure_sha256=file_hash(OUT/'source_changes.png'),
        source_correctness_fix=True,parameters_refitted=False,climate_accuracy_adoption=False,atlas_changed=False,
        interpretation='Old97 reference has explicit inactive-source-branch compatibility, not97 new integrations. Wide native source regression is not a rescue/rerun of the closed nested candidate.'))


def figure(plan,states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11,7))
    for col,s in enumerate(plan['cases']):
        old,new=states[s['name']]
        for row,(field,obs,unit) in enumerate([('Ts','To','Temperature C'),('Ps','Po','Rain mm/month')]):
            ax=axes[row,col]
            ax.plot(np.arange(1,13),old[field].mean(1),label='Before source correction',color='#377d8d')
            ax.plot(np.arange(1,13),new[field].mean(1),label='Southern belts corrected',color='#b47552')
            ax.plot(np.arange(1,13),new[obs].mean(1),'k--',label='Fixed observations')
            ax.set(ylabel=unit,xlabel='Model month',xticks=[1,4,7,10,12])
            ax.grid(alpha=.15)
        axes[0,col].set_title(s['name'])
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Unfitted source correction: southern extra-tropical wind belts')
    fig.text(.5,.025,'Ordinary Somalia: correction branch inactive, archived arrays exact. Wider Somalia: branch active, original numerical checks unchanged.\nThis is source verification, not improved global skill, a nested-candidate rescue, parameter fitting or a new atlas.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.08,right=.98,top=.88,bottom=.13,hspace=.35,wspace=.28)
    fig.savefig(OUT/'source_changes.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    main()
