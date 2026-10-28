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
    declaration_metadata_issues=[]
    evaluator=evaluate
    progress=json.loads((out/'progress.json').read_text());review=json.loads((out/'review.json').read_text())
    if (progress.get('complete') is not True or review.get('complete') is not True
            or progress['identity']!=run_id or review['identity']!=run_id
            or review['physics_or_atlas_adoption'] is not False):raise ValueError('Need completed unchanged research comparison')
    for n,sha in protocol['sources'].items():
        if file_hash(ROOT/n)!=sha:raise ValueError('Changed scientific source: '+n)
    if p['design']['sampler']=='scrambled Sobol':
        if 'joint_global_parent' in p:
            parent_info=p['joint_global_parent'];parent=ROOT/parent_info['parent']
            for filename,key in [('review.json','parent_review_sha256'),('progress.json','parent_progress_sha256'),('scientific_verification.json','parent_verification_sha256')]:
                if file_hash(parent/filename)!=parent_info[key]:raise ValueError('Changed joint-search parent archive')
            parent_review=json.loads((parent/'review.json').read_text())
            parent_plan=json.loads((parent/'protocol.json').read_text())['plan']
            if parent_review['validation_shortlist'] or any(p[k]!=parent_plan[k] for k in ['objective','validation_shortlist','fixed_model']):raise ValueError('Changed conditional joint-search policy')
        expected_points=qmc.Sobol(len(p['design']['bounds']),scramble=True,seed=p['design']['seed']).random_base2(p['design']['base2_exponent'])
        actual_points=np.stack([coordinates(p['profiles'][n],p['design']) for n in p['global_names']])
        np.testing.assert_allclose(actual_points,expected_points,rtol=0,atol=1e-14)
    elif p['design']['sampler']=='paired wind bracket':
        interaction=p['wind_interaction'];parent=ROOT/interaction['parent']
        for filename,key in [('review.json','parent_review_sha256'),('progress.json','parent_progress_sha256'),('scientific_verification.json','parent_verification_sha256')]:
            if file_hash(parent/filename)!=interaction[key]:raise ValueError('Changed wind-anchor source archive')
        parent_review=json.loads((parent/'review.json').read_text());parent_progress=json.loads((parent/'progress.json').read_text())
        old_updates={r['name']:r['updates'] for r in parent_progress['records']}
        if parent_review['validation_shortlist'] or diverse_starts(parent_review['scores'],old_updates,interaction['anchor_selection'])!=interaction['anchors']:raise ValueError('Changed conditional anchor selection')
        expected=[]
        for basin,anchor in enumerate(interaction['anchors']):
            for wind in interaction['winds_ms']:
                name=f'global{len(expected)+1:02}';expected.append(dict(name=name,basin=basin+1,parent_profile=anchor,westerly_speed=wind))
                if p['profiles'][name]!={**old_updates[anchor],'westerly_speed':wind}:raise ValueError('Changed paired wind/rain coefficients')
        if expected!=interaction['grid'] or [x['name'] for x in expected]!=p['global_names']:raise ValueError('Changed paired wind grid')
    elif p['design']['sampler']=='paired drying ablation':
        ablation=p['drying_ablation'];parent=ROOT/ablation['parent']
        for filename,key in [('review.json','parent_review_sha256'),('progress.json','parent_progress_sha256'),('scientific_verification.json','parent_verification_sha256')]:
            if file_hash(parent/filename)!=ablation[key]:raise ValueError('Changed drying-anchor source archive')
        parent_review=json.loads((parent/'review.json').read_text());parent_progress=json.loads((parent/'progress.json').read_text())
        old_updates={r['name']:r['updates'] for r in parent_progress['records']}
        selection=json.loads(json.dumps(ablation['anchor_selection']))
        parent_design=json.loads((parent/'protocol.json').read_text())['plan']['design']
        if selection['bounds']!=parent_design['bounds']:
            # Original generator selected before mutating a shallow-copied nested
            # bounds dict. The literal pre-run grid/anchors remain frozen. Only
            # reconstruct that already executed parent-space selection here.
            expected_bounds={**parent_design['bounds'],**{k:dict(range=[0.,v],scale='linear') for k,v in ablation['retained'].items()}}
            if selection['bounds']!=expected_bounds:raise ValueError('Unrecognized anchor-selection metadata discrepancy')
            declaration_metadata_issues.append(dict(field='drying_ablation.anchor_selection.bounds',
                issue='Generator shallow-copy alias appended the two new axes after parent-space anchor selection',
                resolution='Verify the literal pre-run candidate grid and reconstruct selection in the committed parent parameter space; original plan retained',
                saved_bounds=selection['bounds'],actual_selection_bounds=parent_design['bounds'],
                scientific_runs_or_scores_changed=False))
            selection['bounds']=parent_design['bounds']
        if parent_review['validation_shortlist'] or diverse_starts(parent_review['scores'],old_updates,selection)!=ablation['anchors']:raise ValueError('Changed conditional drying anchors')
        variants={'subsidence_off':{'subsidence_drying':0.},'monsoon_off':{'monsoon_descent':0.},'both_off':{'subsidence_drying':0.,'monsoon_descent':0.}}
        if ablation['variants']!=variants or p['design']['local_poll_order']:raise ValueError('Changed fixed drying ablation')
        for row in parent_progress['records']:
            if row['name'] in ablation['anchors'] and any(row['params'][k]!=v for k,v in ablation['retained'].items()):raise ValueError('Incorrect retained drying coefficients')
        expected=[]
        for basin,anchor in enumerate(ablation['anchors']):
            for variant,changes in variants.items():
                name=f'global{len(expected)+1:02}';expected.append(dict(name=name,basin=basin+1,parent_profile=anchor,variant=variant,changes=changes))
                if p['profiles'][name]!={**old_updates[anchor],**ablation['retained'],**changes}:raise ValueError('Changed paired drying coefficients')
        if expected!=ablation['grid'] or [x['name'] for x in expected]!=p['global_names']:raise ValueError('Changed ablation grid')
    elif p['design']['sampler']=='paired hydrostatic ocean pilot':
        from ocean_source_epoch import validate_epoch,current_sources,reference_sources
        from ocean_profile_pilot import evaluate_ocean
        evaluator=evaluate_ocean;validate_epoch(p['source_epoch'])
        old_protocol=json.loads((ROOT/p['parent_protocol']).read_text())
        upgraded=current_sources(old_protocol['sources'],p['source_epoch'])
        references,refresh=reference_sources(p)
        if protocol.get('source_transition')!=p['source_epoch'] or protocol.get('reference_refresh')!=refresh:raise ValueError('Changed ocean source/reference transition')
        if any(protocol['sources'].get(k)!=v for k,v in {**upgraded,**references}.items()):raise ValueError('Missing ocean epoch source binding')
        experiment=p['ocean_profile_pilot'];parent=ROOT/experiment['parent']
        for filename,key in [('review.json','parent_review_sha256'),('progress.json','parent_progress_sha256'),('scientific_verification.json','parent_verification_sha256')]:
            if file_hash(parent/filename)!=experiment[key]:raise ValueError('Changed ocean pilot parent archive')
        parent_plan=old_protocol['plan'];parent_review=json.loads((parent/'review.json').read_text())
        if parent_review['validation_shortlist'] or any(p[k]!=parent_plan[k] for k in ['objective','validation_shortlist','fixed_model']):raise ValueError('Changed ocean pilot tradeoff policy')
        anchor_review=json.loads((ROOT/experiment['anchor_review']).read_text())
        if file_hash(ROOT/experiment['anchor_review'])!=experiment['anchor_review_sha256']:raise ValueError('Changed retained wind anchor review')
        anchor=min((n for n,s in anchor_review['scores'].items() if s.get('physical_admissible')),key=lambda n:(anchor_review['scores'][n]['objective'],n))
        if anchor!=experiment['anchor_profile']:raise ValueError('Changed retained best wind anchor')
        source=json.loads((ROOT/experiment['anchor_archive']/(p['regions'][0]+'.json')).read_text())
        expected=[]
        for wind in [4.5,3.5]:
            for mode,enabled,taper in [('legacy',False,0.),('hydrostatic_uniform',True,0.),('hydrostatic_half',True,.5)]:
                name=f'global{len(expected)+1:02}';expected.append(dict(name=name,westerly_speed=wind,mode=mode,hydrostatic=enabled,rh_taper=taper))
                coefficients={**source['updates'],**{k:source['params'][k] for k in ['subsidence_drying','monsoon_descent']},
                    'westerly_speed':wind,'moisture_ocean_hydrostatic':enabled,'moisture_ocean_rh_taper':taper}
                if p['profiles'][name]!=coefficients or p['profile_numerics'][name]!=source['numerical_updates']:raise ValueError('Changed paired ocean coefficients or numerical rules')
        if expected!=experiment['grid'] or p['global_names']!=[g['name'] for g in expected] or p['design']['local_poll_order']:raise ValueError('Changed fixed ocean pilot grid')
        if p['profile_control_archives'].get('global01')!=experiment['anchor_archive']:raise ValueError('Missing matched legacy epoch control')
    else:raise ValueError('Unknown frozen sampling design')
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()));cases={r:earth.region_case(r,p['cell_km']) for r in p['regions']}
    derived={r:case_hash(c,observed_sea=True) for r,c in cases.items()}
    records=progress['records'];keys=set();controls=[];extra_controls=[];row_hashes={};passed=0
    matched_ocean_controls=[];matched_ocean_native_controls=[]
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
            if {k:v for k,v in row['updates'].items() if k not in p['design']['bounds']}!={k:v for k,v in p['base_candidate'].items() if k not in p['design']['bounds']}:raise ValueError('Undeclared physical coefficient')
        row_hashes[n+'/'+r]=file_hash(path)
        if row['status']=='passed':
            passed+=1;raw=path.with_suffix('.npz')
            if row['numerics']['all_checks_passed'] is not True or file_hash(raw)!=row['arrays_sha256']:raise ValueError('Invalid climate NPZ/numerics')
            if n not in p['control_names']:
                steps=row['numerics']['moisture_reservoirs']['steps']
                for step in steps:
                    if ('ocean_profile_pilot' in p and actual['moisture_ocean_hydrostatic']
                            and step.get('ocean_target_cells')!=int((~cases[r].grid.land).sum())):raise ValueError('Actual ocean target grid footprint differs')
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
            matched_ocean=('ocean_profile_pilot' in p and n=='global01')
            if n in p['control_names'] or matched_ocean:
                archived=ROOT/p['profile_control_archives'][n]/raw.name
                prior=json.loads(archived.with_suffix('.json').read_text())
                if file_hash(archived)!=prior['arrays_sha256']:raise ValueError('Changed archived climate')
                if matched_ocean and {k:v for k,v in row['params'].items() if k not in ['moisture_ocean_hydrostatic','moisture_ocean_rh_taper']}!=prior['params']:raise ValueError('Matched legacy ocean parameters differ from old source epoch')
                with np.load(raw) as a,np.load(archived) as b:
                    if set(a.files)!=set(b.files) or any(a[k].dtype!=b[k].dtype or not np.array_equal(a[k],b[k],equal_nan=True) for k in a.files):raise ValueError('Control fieldset/array not exact')
                (matched_ocean_controls if matched_ocean else controls).append(n+'/'+r)
                if r in p['extra_circulation_regions']:
                    oldextra=archived.with_name(r+'_extra.npz')
                    if file_hash(oldextra)!=prior['extra_circulation_arrays_sha256']:raise ValueError('Changed archived native companion')
                    with np.load(extra) as a,np.load(oldextra) as b:
                        if set(a.files)!=set(b.files) or any(not np.array_equal(a[k],b[k],equal_nan=True) for k in a.files):raise ValueError('Native control not exact')
                    (matched_ocean_native_controls if matched_ocean else extra_controls).append(n+'/'+r)
        elif n in p['control_names']:raise ValueError('Failed historical control')
    names={r['name'] for r in records}
    if any({(n,r) for r in p['regions']}-keys for n in names):raise ValueError('Incomplete profile')
    scores={n:evaluator(n,records,p) for n in names if n not in p['control_names']}
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
    basin_diagnostics=[]
    for basin,start in enumerate(starts):
        current=start;accepted=[]
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
            if trial in scores and scores[trial].get('physical_admissible') and scores[trial]['objective']<scores[current]['objective']:
                current=trial;accepted.append(trial)
        final_point=coordinates(updates[current],p['design'])
        edges={key:('lower' if x<=.03 else 'upper') for key,x in zip(p['design']['bounds'],final_point) if x<=.03 or x>=.97}
        basin_diagnostics.append(dict(start=start,end=current,start_objective=scores[start]['objective'],end_objective=scores[current]['objective'],
            accepted_improvements=accepted,start_parameters={k:updates[start][k] for k in p['design']['bounds']},
            end_parameters={k:updates[current][k] for k in p['design']['bounds']},near_boundaries=edges,
            scope=('One frozen coordinate-poll cycle; no numerical optimizer convergence claim' if p['design']['local_poll_order'] else
                   'No local proposals; common-runner best-point bookkeeping only')))
    if index!=len(history) or len(records)!=len(names)*len(p['regions']) or len(controls)!=28:raise ValueError('Undeclared trial/count')
    if 'ocean_profile_pilot' in p and (len(matched_ocean_controls)!=7 or len(matched_ocean_native_controls)!=1):raise ValueError('Missing exact matched legacy ocean epoch control')
    if pareto_names(scores)!=review['pareto_front']:raise ValueError('Changed Pareto frontier')
    shortlist=sorted((n for n,v in scores.items() if v.get('validation_ready')),key=lambda n:(scores[n]['objective'],n))[:2]
    if shortlist!=review['validation_shortlist']:raise ValueError('Changed prospective shortlist')
    actual_updates={r['name']:r['updates'] for r in records if r['name'] in scores}
    near_duplicates=[];actual_names=list(actual_updates)
    for i,n in enumerate(actual_names):
        x=coordinates(actual_updates[n],p['design'])
        for m in actual_names[:i]:
            distance=float(np.linalg.norm(x-coordinates(actual_updates[m],p['design'])))
            if distance<1e-10:near_duplicates.append(dict(profiles=[m,n],normalized_parameter_distance=distance,
                scope='Separate actual runs count as attempts, but are not materially distinct parameter-space samples'))
    if (review['actual_integrations']!=len(records) or review['strictly_passed']!=passed
            or review['failed_integrations']!=len(records)-passed):raise ValueError('Changed actual integration count')
    # Compare all normal climate/foraging assets with the last published state.
    normal=['atlases/free_fit','atlases/earth_fit','atlases/whittaker_fit']
    if subprocess.check_output(['git','diff','--name-only','d3c7c0d','--',*normal],cwd=ROOT).strip():raise ValueError('Normal atlas files changed')
    plan_paths=[n for n in protocol['sources'] if n.endswith('/plan.json') and json.loads((ROOT/n).read_text())==p]
    if len(plan_paths)!=1:raise ValueError('Need unique committed declaration')
    declaration_commit=subprocess.check_output(['git','log','-1','--format=%H','--',plan_paths[0]],cwd=ROOT,text=True).strip()
    if not declaration_commit:raise ValueError('Declaration was not committed')
    parent_receipt=ROOT/Path(p['parent_protocol']).parent/'scientific_verification.json'
    previous=json.loads(parent_receipt.read_text())
    if previous.get('status')!='passed' or previous.get('identity')!=identity(json.loads((ROOT/p['parent_protocol']).read_text())):
        raise ValueError('Invalid parent scientific counter/identity chain')
    previous_attempts=previous.get('cumulative_attempts',previous.get('attempted_integrations'))
    previous_passes=previous.get('cumulative_passes',previous.get('passed'))
    previous_failures=previous.get('cumulative_preserved_failures',previous.get('preserved_failures'))
    result=dict(status='passed',scientific_source_epoch=declaration_commit[:7],declaration_commit=declaration_commit,identity=run_id,
        actual_integrations=len(records),strictly_passed=passed,failed_this_round=len(records)-passed,
        cumulative_attempts=previous_attempts+len(records),cumulative_passes=previous_passes+passed,cumulative_preserved_failures=previous_failures+len(records)-passed,
        parent_scientific_verification_sha256=file_hash(parent_receipt),
        frozen_sources_verified=len(protocol['sources']),actual_case_identities=derived,archived_controls_exact=controls,
        local_basin_diagnostics=basin_diagnostics,
        declaration_metadata_issues=declaration_metadata_issues,
        near_duplicate_parameter_pairs=near_duplicates,
        native_controls_exact=extra_controls,all_actual_parameters_and_row_hashes_verified=True,
        matched_ocean_epoch_controls_exact=matched_ocean_controls,matched_ocean_native_controls_exact=matched_ocean_native_controls,
        all_scores_physical_checks_and_adaptive_decisions_recomputed=True,row_hashes=row_hashes,
        protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),normal_atlas_comparison_commit='d3c7c0d',
        physics_or_atlas_adoption=False)
    write_json(out/'scientific_verification.json',result);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    r=verify(ap.parse_args().out.resolve());print(json.dumps({k:v for k,v in r.items() if k not in ['row_hashes','actual_case_identities']},indent=2))
