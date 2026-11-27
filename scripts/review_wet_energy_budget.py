"""Independently review raw arrays, actual cooling identities and policy-v6 dev97."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT)]
from local_benchmark_protocol import file_hash, write_json
from review_current_climate_reference import score_bounds
from gate_v3 import score
from score_ci import ci
OUT = ROOT/'output/wet_energy_budget_20261127'
PLAN = ROOT/'calibration/wet_energy_budget_20261127/plan.json'


def main():
    assert not (OUT/'review.json').exists()
    plan = json.loads(PLAN.read_text())
    protocol = json.loads((OUT/'protocol.json').read_text())
    results = json.loads((OUT/'results.json').read_text())
    assert file_hash(PLAN) == protocol['plan_sha256']
    assert file_hash(OUT/'protocol.json') == results['protocol_sha256']
    assert len(results['rows']) == plan['maximum_integrations'] == 99
    assert file_hash(OUT/'preparation.json') == protocol['preparation_sha256']
    for section in ['model_sources_sha256','execution_sources_sha256','inputs_sha256']:
        for name,digest in plan[section].items():
            assert file_hash(ROOT/name) == digest, name
    for name,digest in plan['private_files_sha256'].items():
        assert file_hash(OUT/'model'/name) == digest, name
    qualified = json.loads((ROOT/plan['control_qualification']).read_text())
    assert qualified['reference_regions'] == 97
    assert qualified['model_sources_sha256'] == plan['model_sources_sha256']
    specmap = {s['region']:s for s in plan['cases']}
    R, C, stats, files, repeats = {}, {}, [], {}, []
    for row in results['rows']:
        arm, name, part = row['arm'], row['region'], row['part']
        spec = specmap[name]
        folder = OUT/(arm+'_'+part)
        assert row['status'] == 'passed' and row['numerics']['all_checks_passed']
        original = json.loads((ROOT/spec['control_record']).read_text())
        assert row['case_identity'] == original['case_identity'] == spec['case_identity']
        local = {k:v for k,v in row.items() if k not in ['arm','part']}
        assert local == json.loads((folder/'cases'/(name+'.json')).read_text())
        p = json.loads((folder/'protocol.json').read_text())
        assert p['params'] == json.loads((ROOT/plan['parts_by_name'][part]['control_protocol']).read_text())['params']
        assert p['sources'] == plan['benchmark_protocol_sources_sha256']
        assert p['physical_operator_override']['WET_ENERGY_BUDGET'] == (arm == 'candidate')
        attempt = json.loads((folder/'attempts'/(name+'.json')).read_text())
        assert attempt['spec'] == spec and attempt['arm'] == arm
        assert attempt['protocol_sha256'] == file_hash(folder/'protocol.json')
        assert file_hash(folder/'cells'/(name+'.npz')) == row['cells_sha256']
        with np.load(folder/'cells'/(name+'.npz')) as z:
            new = dict(z)
        with np.load(ROOT/spec['control_cells']) as z:
            old = dict(z)
        assert set(new) == set(old)
        for key in new:
            assert new[key].shape == old[key].shape and np.isfinite(new[key]).all()
            if arm == 'default_off' or key not in ['Ts','Ps']:
                assert new[key].dtype == old[key].dtype and new[key].tobytes() == old[key].tobytes(), (name,key)
        assert (new['Ps'] >= 0).all()
        tb,pb = score_bounds(new)
        assert tb[0]-1e-12 <= row['temperature']['monthly_mae_C'] <= tb[1]+1e-12
        assert pb[0]-1e-12 <= row['rain']['loss'] <= pb[1]+1e-12
        for rel in ['cases/'+name+'.json','cells/'+name+'.npz','attempts/'+name+'.json']:
            f = folder/rel
            files[str(f.relative_to(OUT))] = file_hash(f)
        if arm == 'default_off':
            repeats.append(name)
            continue
        capture = folder/'cells'/(name+'_energy.npz')
        assert file_hash(capture) == row['energy_capture_sha256']
        files[str(capture.relative_to(OUT))] = file_hash(capture)
        with np.load(capture) as e:
            assert all(np.isfinite(e[k]).all() for k in e.files)
            for key in ['i','j','lat','lon']:
                np.testing.assert_array_equal(e[key], new[key])
            assert e['full_grid_bound_excess_max_W_m2'] <= 1e-10
            assert (e['scale'] >= 0).all() and (e['scale'] <= 1).all()
            assert (e['applied'] <= e['bound'] + 1e-10).all()
            positive = np.maximum(e['delta_wet'],0)+np.maximum(e['delta_sun'],0)
            np.testing.assert_allclose(e['legacy'], e['conductance']*positive, rtol=2e-15, atol=1e-12)
            np.testing.assert_allclose(e['applied'], e['legacy']*e['scale'], rtol=0., atol=0.)
            np.testing.assert_allclose(e['before']-e['after_wet'], e['delta_wet']*e['scale'], rtol=0., atol=1e-12)
            ds = e['delta_sun']
            np.testing.assert_allclose(e['after_wet']-e['after_sun'], np.where(ds>0,ds*e['scale'],ds), rtol=0., atol=1e-12)
            nt = int(e['scored_steps'])
            np.testing.assert_array_equal(e['day'][-nt:], e['scored_days'])
            scale = e['scale'][-nt:]
            removed = (e['legacy'][-nt:]-e['applied'][-nt:])/e['conductance'][-nt:]
            mechanism = dict(scored_cell_step_cap_binding_fraction=float((scale<1).mean()),
                mean_reduced_positive_cooling_K=float(removed.mean()),
                max_reduced_positive_cooling_K=float(removed.max()),
                implied_legacy_cooling_W_m2=float(e['legacy'][-nt:].mean()),
                implied_bounded_cooling_W_m2=float(e['applied'][-nt:].mean()))
        R[name], C[name] = original, row
        t,p0 = original['temperature']['monthly_mae_C'], original['rain']['loss']
        stats.append(dict(region=name, part=part, T_before=t, T_after=row['temperature']['monthly_mae_C'],
            T_ratio=row['temperature']['monthly_mae_C']/t, rain_loss_before=p0, rain_loss_after=row['rain']['loss'],
            rain_loss_ratio=row['rain']['loss']/p0, annual_rain_before_mm=original['rain']['sim_mean_annual_mm'],
            annual_rain_after_mm=row['rain']['sim_mean_annual_mm'], observed_annual_rain_mm=row['rain']['obs_mean_annual_mm'],
            annual_T_bias_before_C=original['temperature']['annual_bias_C'], annual_T_bias_after_C=row['temperature']['annual_bias_C'],
            **mechanism))
    assert repeats == plan['default_off_controls'] and set(C) == set(specmap) and len(C) == 97
    for arm in ['candidate','default_off']:
        for part in plan['parts']:
            names = [n for n in part['regions'] if arm == 'candidate' or n in repeats]
            if not names:
                continue
            folder = OUT/(arm+'_'+part['name'])
            summary = json.loads((folder/'summary.json').read_text())
            assert summary['complete'] and set(summary['regions']) == set(names)
            for name,row in summary['regions'].items():
                assert row == json.loads((folder/'cases'/(name+'.json')).read_text())
            for rel in ['protocol.json','summary.json']:
                files[str((folder/rel).relative_to(OUT))] = file_hash(folder/rel)
    names = sorted(R)
    a = np.array([[C[n]['temperature']['monthly_mae_C'],R[n]['temperature']['monthly_mae_C'],
                   C[n]['rain']['loss'],R[n]['rain']['loss']] for n in names])
    bootstrap, point = ci(a), score(R,C,names)
    tags = json.loads((ROOT/'calibration/regimes_20261124/regimes_v2.json').read_text())['regimes']
    regimes = {g:score(R,C,[n for n in names if tags[n]==g]) for g in sorted({tags[n] for n in names})}
    passes = bootstrap['q95'] < 1. and point['T'] <= .01 and point['P'] <= .01 and max(v['S'] for v in regimes.values()) <= 1.02
    gate = dict(stage='dev6', policy='policy_v6', n=97, S=point, bootstrap=bootstrap,
                regimes=regimes, passes=bool(passes), reference='qualified current-source97', no_adoption=True)
    write_json(OUT/'development_gate.json', gate)
    figure(plan,stats)
    write_json(OUT/'review.json', dict(status='independently_reviewed_fixed_solar_bound_dev97',
        statistics=stats, files_sha256=files, development_gate=gate, default_off_controls_byte_exact=repeats,
        original_numerical_certificates=99, actual_case_identities_exact=True, development_regions=97,
        plan_sha256=file_hash(PLAN), results_sha256=file_hash(OUT/'results.json'),
        figure_sha256=file_hash(OUT/'thermal_response.png'), candidate_integrations=97,
        AA_opened=False, W18c_reopened=False, climate_adopted=False, atlas_changed=False))
    print('Full97 solar-bound policy-v6 development gate:', bool(passes), point, bootstrap, flush=True)


def figure(plan,stats):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    chosen = ['middle_volga','canadian_prairies','british_isles','north_india','u2_59n_76w','u2_56n_135e']
    specs = {s['region']:s for s in plan['cases']}
    fig,axes = plt.subplots(2,6,figsize=(20,7))
    for col,name in enumerate(chosen):
        s = specs[name]
        with np.load(ROOT/s['control_cells']) as z:
            old = dict(z)
        with np.load(OUT/('candidate_'+s['part'])/'cells'/(name+'.npz')) as z:
            new = dict(z)
        for row,(field,obs,unit) in enumerate([('Ts','To','Temperature C'),('Ps','Po','Rain mm/month')]):
            ax = axes[row,col]
            for values,label,color in [(old[field],'Current control','#377d8d'),(new[field],'Solar bound','#b47552')]:
                ax.plot(np.arange(1,13),values.mean(1),label=label,color=color)
            ax.plot(np.arange(1,13),old[obs].mean(1),'k--',label='Fixed observations')
            ax.set(ylabel=unit,xlabel='Model month',xticks=[1,4,7,10,12])
            ax.grid(alpha=.15)
        axes[0,col].set_title(name,fontsize=9)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('One fixed shared solar limit on wet-soil cooling: exposed97-region experiment')
    fig.text(.5,.03,'Heat capacity assumes existing EBM atmosphere+soil column. Absorbed TOA sunlight is an upper bound, not a closed surface energy or latent-heat budget.\nSame r58 params, inputs and strict solvers. Two default-off repeats byte exact. No fitting, fine28, AA, adoption or atlas rebuild.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.04,right=.99,top=.89,bottom=.14,hspace=.35,wspace=.4)
    fig.savefig(OUT/'thermal_response.png',dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
