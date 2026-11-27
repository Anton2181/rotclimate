"""Independent raw-score, direct-Gaussian and geographic-wind review; no forecast."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.ndimage import gaussian_filter
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from local_benchmark_protocol import file_hash,write_json
from review_current_climate_reference import score_bounds
from circulation_components import bilinear_monthly
from circulation_reference import projection_jacobian,geographic_wind
PLAN=ROOT/'calibration/nested_pressure_context_20261127/plan.json'
OUT=ROOT/'output/nested_pressure_context_20261127'


def direct_pressure(anomaly,p):
    broad=gaussian_filter(anomaly,p['slp_scale_km']/56.,mode='nearest')
    local=gaussian_filter(anomaly,p['slp_local_km']/56.,mode='nearest')-broad
    return -100.*(p['slp_large']*broad+p['slp_local']*local)


def main():
    assert not (OUT/'review.json').exists()
    plan=json.loads(PLAN.read_text())
    protocol=json.loads((OUT/'protocol.json').read_text())
    results=json.loads((OUT/'results.json').read_text())
    assert file_hash(PLAN)==protocol['plan_sha256']
    assert file_hash(OUT/'protocol.json')==results['protocol_sha256']
    assert file_hash(OUT/'preparation.json')==protocol['preparation_sha256']
    assert len(results['rows'])==plan['maximum_integrations']==14
    for section in ['model_sources_sha256','execution_sources_sha256','inputs_sha256']:
        for name,digest in plan[section].items():
            assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():
        assert file_hash(OUT/'model'/name)==digest,name
    qualified=json.loads((ROOT/plan['control_qualification']).read_text())
    assert qualified['reference_regions']==97 and qualified['model_sources_sha256']==plan['model_sources_sha256']
    frozen=json.loads((OUT/'parents_frozen.json').read_text())
    specs={s['region']:s for s in plan['cases']}
    definitions=json.loads((ROOT/plan['region_specs']).read_text())
    with np.load(ROOT/plan['surface_reference']) as z:
        reference=dict(z)
    rows,files,stats,states={}, {}, [], {}
    operator_max=0.
    for row in results['rows']:
        arm,name,part=row['arm'],row['region'],row['part']
        spec=specs[name]
        folder=OUT/(arm+'_'+part)
        p=json.loads((folder/'protocol.json').read_text())
        assert p['params']==json.loads((ROOT/plan['parts_by_name'][part]['control_protocol']).read_text())['params']
        assert p['sources']==plan['benchmark_protocol_sources_sha256']
        assert p['physical_operator_override']['arm']==arm
        if arm=='nested':
            assert p['physical_operator_override']['parent_manifest_sha256']==file_hash(OUT/'parents_frozen.json')
        assert row['status']=='passed' and row['numerics']['all_checks_passed']
        assert {k:v for k,v in row.items() if k not in ['arm','part']}==json.loads((folder/'cases'/(name+'.json')).read_text())
        expected=spec['parent_case_identity'] if arm=='parent' else spec['case_identity']
        assert row['case_identity']==expected
        attempt=json.loads((folder/'attempts'/(name+'.json')).read_text())
        assert attempt['spec']==spec and attempt['arm']==arm and attempt['protocol_sha256']==file_hash(folder/'protocol.json')
        assert attempt['campaign_protocol_sha256']==file_hash(OUT/'protocol.json')
        with np.load(folder/'cells'/(name+'.npz')) as z:
            new=dict(z)
        with np.load(ROOT/spec['control_cells']) as z:
            old=dict(z)
        assert set(new)==set(old)
        assert all(np.isfinite(v).all() for v in new.values()) and (new['Ps']>=0).all()
        for k in new:
            assert new[k].shape==old[k].shape
            if arm=='default_off' or k not in ['Ts','Ps','i','j','coast_km']:
                assert new[k].dtype==old[k].dtype and new[k].tobytes()==old[k].tobytes(),(arm,name,k)
        if arm=='parent':
            for k in ['i','j']:
                np.testing.assert_array_equal(new[k]-52,old[k])
        elif arm=='nested':
            for k in ['i','j','coast_km']:
                np.testing.assert_array_equal(new[k],old[k])
        tb,pb=score_bounds(new)
        assert tb[0]-1e-12<=row['temperature']['monthly_mae_C']<=tb[1]+1e-12
        assert pb[0]-1e-12<=row['rain']['loss']<=pb[1]+1e-12
        cap=folder/'cells'/(name+'_context.npz')
        assert file_hash(folder/'cells'/(name+'.npz'))==row['cells_sha256']
        assert file_hash(cap)==row['context_capture_sha256']
        with np.load(cap) as z:
            captured=dict(z)
        assert all(np.isfinite(v).all() for v in captured.values())
        assert captured['anomaly'].shape==captured['pressure'].shape
        assert captured['anomaly'].shape[0]==len(captured['days'])
        assert captured['pressure_calls']>=len(captured['days'])
        np.testing.assert_array_equal(captured['wind_lat'],new['lat'])
        np.testing.assert_array_equal(captured['wind_lon'],new['lon'])
        for k in ['i','j']:
            np.testing.assert_array_equal(captured['wind_'+k],new[k])
        if arm=='nested':
            parent=frozen['parents'][name]
            assert file_hash(ROOT/parent['capture'])==parent['capture_sha256']
            with np.load(ROOT/parent['capture']) as z:
                parent_field=z['anomaly']
                np.testing.assert_array_equal(z['days'],captured['days'])
                crop=(slice(52,52+captured['anomaly'].shape[1]),slice(52,52+captured['anomaly'].shape[2]))
                np.testing.assert_array_equal(z['full_lat'][crop],captured['full_lat'])
                np.testing.assert_array_equal(z['full_lon'][crop],captured['full_lon'])
        for k,anomaly in enumerate(captured['anomaly']):
            if arm=='nested':
                combined=parent_field[k].copy()
                combined[crop]=anomaly
                reconstructed=direct_pressure(combined,p['params'])[crop]
            else:
                reconstructed=direct_pressure(anomaly,p['params'])
            error=float(np.max(np.abs(reconstructed-captured['pressure'][k])))
            operator_max=max(operator_max,error)
            assert error<=plan['operator_reconstruction_max_Pa'],(arm,name,error)
        center=definitions[name]
        assert center['lat0']>0
        geom=projection_jacobian(new['lat'],new['lon'],center['lat0'],center['lon0'])
        east,north=geographic_wind(captured['u'],captured['v'],geom)
        oe=bilinear_monthly(reference['u'],new['lat'],new['lon'])
        on=bilinear_monthly(reference['v'],new['lat'],new['lon'])
        wind=dict(july_east_m_s=float(east[6].mean()),july_north_m_s=float(north[6].mean()),
            july_observed_east_m_s=float(oe[6].mean()),july_observed_north_m_s=float(on[6].mean()),
            july_vector_rmse_m_s=float(np.sqrt(np.mean((east[6]-oe[6])**2+(north[6]-on[6])**2))))
        rows[arm,name]=dict(record=row,wind=wind)
        states[arm,name]=new
        for rel in ['cases/'+name+'.json','cells/'+name+'.npz','cells/'+name+'_context.npz','attempts/'+name+'.json']:
            f=folder/rel
            files[str(f.relative_to(OUT))]=file_hash(f)
    assert len(rows)==14
    for s in plan['cases']:
        name=s['region']
        base=json.loads((ROOT/s['control_record']).read_text())
        new=rows['nested',name]['record']
        parent=rows['parent',name]['record']
        t,rain=base['temperature']['monthly_mae_C'],base['rain']['loss']
        stats.append(dict(region=name,T_before=t,T_after=new['temperature']['monthly_mae_C'],
            T_ratio=new['temperature']['monthly_mae_C']/t,rain_loss_before=rain,rain_loss_after=new['rain']['loss'],
            rain_loss_ratio=new['rain']['loss']/rain,annual_rain_before_mm=base['rain']['sim_mean_annual_mm'],
            annual_rain_after_mm=new['rain']['sim_mean_annual_mm'],observed_annual_rain_mm=base['rain']['obs_mean_annual_mm'],
            parent_T_mae_C=parent['temperature']['monthly_mae_C'],parent_annual_rain_mm=parent['rain']['sim_mean_annual_mm'],
            parent_rain_loss=parent['rain']['loss'],**rows['nested',name]['wind']))
    soma_before=rows['default_off','s_2n_43e']['wind']['july_vector_rmse_m_s']
    soma_after=rows['nested','s_2n_43e']['wind']['july_vector_rmse_m_s']
    sahara=next(s for s in stats if s['region']=='u_21n_21e')
    eligible=(soma_after/soma_before<=.90 and sahara['rain_loss_ratio']<=.90
        and all(s['T_ratio']<=1.01 and s['rain_loss_ratio']<=1.01 for s in stats))
    figure(plan,states)
    for folder in OUT.glob('*_*'):
        if folder.is_dir() and (folder/'summary.json').exists():
            summary=json.loads((folder/'summary.json').read_text())
            assert summary['complete']
            for name,row in summary['regions'].items():
                assert row==json.loads((folder/'cases'/(name+'.json')).read_text())
            for rel in ['summary.json','protocol.json']:
                files[str((folder/rel).relative_to(OUT))]=file_hash(folder/rel)
    write_json(OUT/'review.json',dict(status='reviewed_fixed14_native_parent_context',
        statistics=stats,files_sha256=files,original_numerical_certificates=14,
        default_off_TP_and_all_saved_cell_arrays_exact=plan['default_off_controls'],
        max_direct_filter_pressure_reconstruction_error_Pa=operator_max,
        somalia_july_vector_rmse_before_m_s=soma_before,somalia_july_vector_rmse_after_m_s=soma_after,
        somalia_july_vector_rmse_ratio=soma_after/soma_before,
        eligible_for_further_exposed_evaluation=bool(eligible),prospective_screen=plan['screen'],
        protocol_sha256=file_hash(OUT/'protocol.json'),results_sha256=file_hash(OUT/'results.json'),
        figure_sha256=file_hash(OUT/'nested_response.png'),climate_adopted=False,atlas_changed=False,
        AA_opened=False,W18c_reopened=False))
    print('Fixed native-parent screen:',bool(eligible),'Somalia July wind ratio',soma_after/soma_before,flush=True)


def figure(plan,states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,6,figsize=(20,7))
    for col,s in enumerate(plan['cases']):
        name=s['region']
        with np.load(ROOT/s['control_cells']) as z:
            old=dict(z)
        for row,(field,obs,unit) in enumerate([('Ps','Po','Rain mm/month'),('Ts','To','Temperature C')]):
            ax=axes[row,col]
            for values,label,color in [(old[field],'Qualified child control','#377d8d'),
                (states['nested',name][field],'Nested pressure context','#b47552'),
                (states['parent',name][field],'Native finite parent','#a6a699')]:
                ax.plot(np.arange(1,13),values.mean(1),label=label,color=color)
            ax.plot(np.arange(1,13),old[obs].mean(1),'k--',label='Fixed observations')
            ax.set(ylabel=unit,xlabel='Model month',xticks=[1,4,7,10,12])
            ax.grid(alpha=.15)
        axes[0,col].set_title(name,fontsize=9)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Native finite-parent thermal context in pressure only: one fixed hypothesis')
    fig.text(.5,.03,'Children retain1100km padding, original moisture boundaries and all r58 parameters. Parents have4012km padding; only their exterior pressure-temperature anomalies enter children.\nFinite parent boundaries, Earth conditioning, planar projection and one-way coupling remain approximations. No global truth, independent validation or adoption claim.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.04,right=.99,top=.89,bottom=.14,hspace=.35,wspace=.4)
    fig.savefig(OUT/'nested_response.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    main()
