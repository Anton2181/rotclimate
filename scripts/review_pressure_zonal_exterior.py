"""Review six pressure-boundary candidates against the qualified full reference."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from local_benchmark_protocol import file_hash,write_json
from review_current_climate_reference import score_bounds
from circulation_reference import projection_jacobian,geographic_wind
OUT=ROOT/'output/pressure_zonal_exterior_20261127'
PLAN=ROOT/'calibration/pressure_zonal_exterior_20261127/plan.json'


def main():
    assert not (OUT/'review.json').exists()
    plan=json.loads(PLAN.read_text());protocol=json.loads((OUT/'protocol.json').read_text())
    results=json.loads((OUT/'results.json').read_text())
    assert file_hash(PLAN)==protocol['plan_sha256']
    assert file_hash(OUT/'protocol.json')==results['protocol_sha256']
    assert len(results['rows'])==plan['maximum_integrations']==6
    for section in ['inputs_sha256','model_sources_sha256','execution_sources_sha256']:
        for name,digest in plan[section].items():assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():assert file_hash(OUT/'model'/name)==digest,name
    qualification=json.loads((ROOT/plan['control_qualification']).read_text())
    assert qualification['model_sources_sha256']==plan['model_sources_sha256'] and qualification['reference_regions']==97
    stats,states,files=[],{},{}
    for row,spec in zip(results['rows'],plan['cases'],strict=True):
        name=spec['region'];folder=OUT/'candidate'/('r58_'+spec['part'])
        original=json.loads((ROOT/spec['control_record']).read_text())
        assert row['region']==name and row['status']=='passed' and row['numerics']['all_checks_passed']
        assert row['case_identity']==original['case_identity']==spec['case_identity']
        assert {k:v for k,v in row.items() if k!='part'}==json.loads((folder/'cases'/(name+'.json')).read_text())
        p=json.loads((folder/'protocol.json').read_text())
        assert p['physical_operator_override']==plan['physical_operator_override']
        assert p['params']==json.loads((ROOT/plan['parts_by_name'][spec['part']]['control_protocol']).read_text())['params']
        assert p['sources']==plan['benchmark_protocol_sources_sha256']
        assert file_hash(folder/'cells'/(name+'.npz'))==row['cells_sha256']
        assert file_hash(folder/'cells'/(name+'_wind.npz'))==row['wind_capture_sha256']
        with np.load(folder/'cells'/(name+'.npz')) as z:new=dict(z)
        with np.load(ROOT/spec['control_cells']) as z:old=dict(z)
        assert set(new)==set(old)
        for key in new:
            assert new[key].shape==old[key].shape and np.isfinite(new[key]).all()
            if key not in ['Ts','Ps']:assert new[key].dtype==old[key].dtype and new[key].tobytes()==old[key].tobytes(),(name,key)
        assert (new['Ps']>=0).all()
        tb,pb=score_bounds(new)
        assert tb[0]-1e-12<=row['temperature']['monthly_mae_C']<=tb[1]+1e-12
        assert pb[0]-1e-12<=row['rain']['loss']<=pb[1]+1e-12
        with np.load(folder/'cells'/(name+'_wind.npz')) as z:
            assert all(np.isfinite(z[k]).all() for k in z.files)
            for k in ['lat','lon']:np.testing.assert_array_equal(z[k],new[k])
            center=plan['region_definitions'][name]
            assert center['lat0']>0
            geom=projection_jacobian(z['lat'],z['lon'],center['lat0'],center['lon0'])
            east,north=geographic_wind(z['u'],z['v'],geom)
            wind=dict(july_geographic_east_m_s=float(east[6].mean()),july_geographic_north_m_s=float(north[6].mean()))
        t,p0=original['temperature']['monthly_mae_C'],original['rain']['loss']
        stats.append(dict(region=name,T_before=t,T_after=row['temperature']['monthly_mae_C'],
            rain_loss_before=p0,rain_loss_after=row['rain']['loss'],T_ratio=row['temperature']['monthly_mae_C']/t,
            rain_loss_ratio=row['rain']['loss']/p0,
            annual_rain_before_mm=original['rain']['sim_mean_annual_mm'],annual_rain_after_mm=row['rain']['sim_mean_annual_mm'],
            observed_annual_rain_mm=row['rain']['obs_mean_annual_mm'],**wind))
        states[name]=(old,new)
        for rel in ['cases/'+name+'.json','cells/'+name+'.npz','cells/'+name+'_wind.npz','attempts/'+name+'.json']:
            f=folder/rel;files[str(f.relative_to(OUT))]=file_hash(f)
    target=next(r for r in stats if r['region']=='u_21n_21e')
    eligible=all(r['T_ratio']<=1.01 and r['rain_loss_ratio']<=1.01 for r in stats) and target['rain_loss_ratio']<=.90
    figure(plan,states)
    write_json(OUT/'review.json',dict(status='reviewed_six_fixed_zonal_pressure_exterior_candidates',
        statistics=stats,files_sha256=files,prospective_screen=plan['screen'],eligible_for_further_exposed_evaluation=bool(eligible),
        protocol_sha256=file_hash(OUT/'protocol.json'),results_sha256=file_hash(OUT/'results.json'),
        figure_sha256=file_hash(OUT/'pressure_response.png'),new_candidate_integrations=6,reused_current_source_controls=6,
        physical_operator_override=plan['physical_operator_override'],climate_adopted=False,atlas_changed=False))
    print('Pressure-boundary candidate screen:',bool(eligible))


def figure(plan,states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,6,figsize=(20,7))
    for col,spec in enumerate(plan['cases']):
        old,new=states[spec['region']]
        for row,(field,obs,unit) in enumerate([('Ps','Po','Rain mm/month'),('Ts','To','Temperature C')]):
            ax=axes[row,col];ax.plot(np.arange(1,13),old[field].mean(1),label='Qualified control',color='#377d8d')
            ax.plot(np.arange(1,13),new[field].mean(1),label='Zonal anomaly exterior',color='#b47552')
            ax.plot(np.arange(1,13),old[obs].mean(1),'k--',label='Fixed observations')
            ax.set(ylabel=unit,xlabel='Model month',xticks=[1,4,7,10,12]);ax.grid(alpha=.15)
        axes[0,col].set_title(spec['region'],fontsize=9)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Thermal-pressure boundary hypothesis: zero exterior anomaly versus nearest continuation')
    fig.text(.5,.035,'Only the two pressure-anomaly filters change exterior assumption. Same params, grids, inputs and original numerics; no observed forcing.\nOff-domain thermal anomalies are not known; this is a coupled hypothesis, not an assumed correct global pressure reconstruction.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.04,right=.99,top=.89,bottom=.14,hspace=.35,wspace=.4)
    fig.savefig(OUT/'pressure_response.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
