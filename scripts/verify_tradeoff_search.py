"""Independently verify a completed global/local search without integrating climate."""
from pathlib import Path
import math
from dataclasses import asdict
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from scipy.stats import qmc
from rotclimate import earth,joint
from benchmark_local import DEV12_SPECS
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash,file_hash,identity,write_json
from tradeoff_search import coordinates,parameters,diverse_starts,evaluate,pareto_names


def independent_objective(name,records,p):
    """Reconstruct the scalar independently with Python summation of raw errors."""
    rows={(r['name'],r['region']):r for r in records};combined=[];native=[];ocean=[]
    for region in p['regions']:
        a,b=rows[name,region],rows['reference',region]
        combined.append(.5*(a['temperature']['monthly_mae_C']/b['temperature']['monthly_mae_C']+a['rain']['loss']/b['rain']['loss']))
        if a['sst'] is not None:ocean.append((a['sst']['monthly_mae_C']-b['sst']['monthly_mae_C'])/max(.1,b['sst']['monthly_mae_C']))
        routes=[]
        if region in p['circulation_regions']:routes.append(('circulation','transport_control',p['circulation_groups'][region]))
        if region in p['extra_circulation_regions']:routes.append(('extra_circulation','column_control',p['extra_circulation_groups'][region]))
        for key,baseline,group in routes:
            x,y=a[key],rows[baseline,region][key]
            windx,windy=x['scores']['q925_300'][group],y['scores']['q925_300'][group]
            qx,qy=x['humidity']['scores'][group],y['humidity']['scores'][group]
            for u,v,floor in [(windx['vector_rmse_ms'],windy['vector_rmse_ms'],.5),(qx['partial_water_mae_mm'],qy['partial_water_mae_mm'],1.),(qx['partial_q_ratio_mae'],qy['partial_q_ratio_mae'],.02)]:native.append((u-v)/max(v,floor))
    mean=lambda values:math.fsum(values)/len(values) if values else 0.
    policy=p['objective']
    return mean(combined)+policy['regional_weight']*mean([max(v-policy['regional_free_ratio'],0.)**2 for v in combined])+policy['native_weight']*mean([max(v,0.)**2 for v in native])+policy['ocean_weight']*mean([max(v,0.)**2 for v in ocean])


def verify(out):
    protocol=json.loads((out/'protocol.json').read_text());p=protocol['plan'];run_id=identity(protocol)
    progress=json.loads((out/'progress.json').read_text());review=json.loads((out/'review.json').read_text())
    if (progress.get('complete') is not True or review.get('complete') is not True
            or progress['identity']!=run_id or review['identity']!=run_id
            or review['physics_or_atlas_adoption'] is not False):raise ValueError('Need completed unchanged research comparison')
    for n,sha in protocol['sources'].items():
        if file_hash(ROOT/n)!=sha:raise ValueError('Changed scientific source: '+n)
    expected_points=qmc.Sobol(len(p['design']['bounds']),scramble=True,seed=p['design']['seed']).random_base2(p['design']['base2_exponent'])
    actual_points=np.stack([coordinates(p['profiles'][n],p['design']) for n in p['global_names']])
    np.testing.assert_allclose(actual_points,expected_points,rtol=0,atol=1e-14)
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()));cases={r:earth.region_case(r,p['cell_km']) for r in p['regions']}
    derived={r:case_hash(c,observed_sea=True) for r,c in cases.items()}
    records=progress['records'];keys=set();controls=[];extra_controls=[];row_hashes={};passed=0
    for row in records:
        key=(row['name'],row['region'])
        if key in keys:raise ValueError('Repeated regional integration')
        keys.add(key);n,r=key;path=out/n/(r+'.json')
        if (row!=json.loads(path.read_text()) or row['identity']!=run_id or row['case_identity']!=derived[r]):raise ValueError('Changed actual case or row')
        numerical=p['profile_numerics'].get(n,p['candidate_numerics'])
        if row['numerical_updates']!=numerical:raise ValueError('Changed numerical profile')
        theta=joint.update_block(load_params(ROOT/p['physics']),'physics',row['updates'])
        theta=joint.update_block(theta,'numerics',numerical)
        actual=json.loads(json.dumps(asdict(earth.earth_params(joint.earth_profile(theta),cases[r]))))
        if row.get('params')!=actual:raise ValueError('Actual derived parameters differ')
        if n in p['profiles'] and row['updates']!=p['profiles'][n]:raise ValueError('Changed frozen profile coefficients')
        if n not in p['control_names']:
            coordinates(row['updates'],p['design'])
            if {k:v for k,v in row['updates'].items() if k not in p['design']['bounds']}!=p['base_candidate']:raise ValueError('Undeclared physical coefficient')
        row_hashes[n+'/'+r]=file_hash(path)
        if row['status']=='passed':
            passed+=1;raw=path.with_suffix('.npz')
            if row['numerics']['all_checks_passed'] is not True or file_hash(raw)!=row['arrays_sha256']:raise ValueError('Invalid climate NPZ/numerics')
            if n not in p['control_names']:
                steps=row['numerics']['moisture_reservoirs']['steps']
                for step in steps:
                    if (step['all_layer_checks_passed'] is not True
                            or any(not math.isfinite(step[k]) or step[k]<0 or step[k]>actual['moisture_residual_tol'] for k in ['max_scaled_layer_residual','max_scaled_column_residual'])
                            or step['max_scaled_dry_column_residual']>1e-10
                            or step['maximum_internal_precipitation_transfer_residual_mm_day']>1e-10
                            or step['partition_temperature_profile']!='environmental'
                            or step['partition_lapse_k_km']!=6.):raise ValueError('Actual step water/partition certificate failed')
                for step in row['numerics']['two_layer_transport']['steps']:
                    if step['max_scaled_dry_mass_divergence']>1e-10 or step['maximum_branch_speed_ms']>60 or step['p95_branch_speed_ms']>25:raise ValueError('Actual step branch certificate failed')
            if r in p['extra_circulation_regions']:
                extra=path.with_name(r+'_extra.npz')
                if file_hash(extra)!=row['extra_circulation_arrays_sha256']:raise ValueError('Changed native companion')
            if n in p['control_names']:
                archived=ROOT/p['profile_control_archives'][n]/raw.name
                prior=json.loads(archived.with_suffix('.json').read_text())
                if file_hash(archived)!=prior['arrays_sha256']:raise ValueError('Changed archived climate')
                with np.load(raw) as a,np.load(archived) as b:
                    if set(a.files)!=set(b.files) or any(a[k].dtype!=b[k].dtype or not np.array_equal(a[k],b[k],equal_nan=True) for k in a.files):raise ValueError('Control fieldset/array not exact')
                controls.append(n+'/'+r)
                if r in p['extra_circulation_regions']:
                    oldextra=archived.with_name(r+'_extra.npz')
                    if file_hash(oldextra)!=prior['extra_circulation_arrays_sha256']:raise ValueError('Changed archived native companion')
                    with np.load(extra) as a,np.load(oldextra) as b:
                        if set(a.files)!=set(b.files) or any(not np.array_equal(a[k],b[k],equal_nan=True) for k in a.files):raise ValueError('Native control not exact')
                    extra_controls.append(n+'/'+r)
        elif n in p['control_names']:raise ValueError('Failed historical control')
    names={r['name'] for r in records}
    if any({(n,r) for r in p['regions']}-keys for n in names):raise ValueError('Incomplete profile')
    scores={n:evaluate(n,records,p) for n in names if n not in p['control_names']}
    if scores!=review['scores'] or scores!=progress['scores']:raise ValueError('Recomputed objective/certificates differ')
    for n,s in scores.items():
        if s.get('physical_admissible') and not math.isclose(s['objective'],independent_objective(n,records,p),rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Independent raw-error objective differs')
    starts=diverse_starts({n:scores[n] for n in p['global_names']},p['profiles'],p['design'])
    if starts!=review['local_starts']:raise ValueError('Changed separated starting points')
    localfile=json.loads((out/'local_starts.json').read_text())
    if localfile['identity']!=run_id or localfile['starts']!=starts or localfile['selection_rule']!=p['design']:raise ValueError('Changed start-selection archive')
    history=progress['history'];updates=dict(p['profiles']);index=0
    for n in [*p['control_names'],*p['global_names']]:
        h=history[index];index+=1
        if h['name']!=n or h['updates']!=updates[n] or h['stage']!=('controls' if n in p['control_names'] else 'global') or h['score']!=scores.get(n):raise ValueError('Changed declared global order')
    for basin,start in enumerate(starts):
        current=start
        for step,(axis,sign) in enumerate(p['design']['local_poll_order']):
            point=coordinates(updates[current],p['design']);point[axis]=np.clip(point[axis]+sign*p['design']['local_step'],0,1)
            coeff={**p['base_candidate'],**parameters(point,p['design'])}
            same=next((n for n,v in updates.items() if v==coeff),None);trial=f'local{basin+1}_{step+1:02}'
            h=history[index];index+=1
            if h['name']!=trial or h['updates']!=coeff:raise ValueError('Changed adaptive proposal')
            if same:
                if h['stage']!='cached_local_proposal' or h['reused']!=same:raise ValueError('Incorrect cached proposal')
                trial=same
            else:
                if h['stage']!='local' or h['score']!=scores[trial]:raise ValueError('Changed local score')
                own=[r for r in records if r['name']==trial]
                if any(r['updates']!=coeff for r in own) or len(own)!=len(p['regions']):raise ValueError('Changed actual local coefficients')
                updates[trial]=coeff
            if trial in scores and scores[trial].get('physical_admissible') and scores[trial]['objective']<scores[current]['objective']:current=trial
    if index!=len(history) or len(records)!=len(names)*len(p['regions']) or len(controls)!=28:raise ValueError('Undeclared trial/count')
    if pareto_names(scores)!=review['pareto_front']:raise ValueError('Changed Pareto frontier')
    shortlist=sorted((n for n,v in scores.items() if v.get('validation_ready')),key=lambda n:(scores[n]['objective'],n))[:2]
    if shortlist!=review['validation_shortlist']:raise ValueError('Changed prospective shortlist')
    if (review['actual_integrations']!=len(records) or review['strictly_passed']!=passed
            or review['failed_integrations']!=len(records)-passed):raise ValueError('Changed actual integration count')
    # Compare all normal climate/foraging assets with the last published state.
    normal=['atlases/free_fit','atlases/earth_fit','atlases/whittaker_fit']
    if subprocess.check_output(['git','diff','--name-only','d3c7c0d','--',*normal],cwd=ROOT).strip():raise ValueError('Normal atlas files changed')
    result=dict(status='passed',scientific_source_epoch='3ec90ee',identity=run_id,
        actual_integrations=len(records),strictly_passed=passed,failed_this_round=len(records)-passed,
        cumulative_attempts=1025+len(records),cumulative_passes=1021+passed,cumulative_preserved_failures=4+len(records)-passed,
        frozen_sources_verified=len(protocol['sources']),actual_case_identities=derived,archived_controls_exact=controls,
        native_controls_exact=extra_controls,all_actual_parameters_and_row_hashes_verified=True,
        all_scores_physical_checks_and_adaptive_decisions_recomputed=True,row_hashes=row_hashes,
        protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),normal_atlas_comparison_commit='d3c7c0d',
        physics_or_atlas_adoption=False)
    write_json(out/'scientific_verification.json',result);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    r=verify(ap.parse_args().out.resolve());print(json.dumps({k:v for k,v in r.items() if k not in ['row_hashes','actual_case_identities']},indent=2))
