"""Independently verify a completed global/local search without integrating climate."""
from pathlib import Path
from dataclasses import asdict
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from rotclimate import earth,joint
from benchmark_local import DEV12_SPECS
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash,file_hash,identity,write_json
from tradeoff_search import coordinates,parameters,diverse_starts,evaluate,pareto_names


def verify(out):
    protocol=json.loads((out/'protocol.json').read_text());p=protocol['plan'];run_id=identity(protocol)
    progress=json.loads((out/'progress.json').read_text());review=json.loads((out/'review.json').read_text())
    if (progress.get('complete') is not True or review.get('complete') is not True
            or progress['identity']!=run_id or review['identity']!=run_id
            or review['physics_or_atlas_adoption'] is not False):raise ValueError('Need completed unchanged research comparison')
    for n,sha in protocol['sources'].items():
        if file_hash(ROOT/n)!=sha:raise ValueError('Changed scientific source: '+n)
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
        actual=asdict(earth.earth_params(joint.earth_profile(theta),cases[r]))
        if row.get('params')!=actual:raise ValueError('Actual derived parameters differ')
        if n in p['profiles'] and row['updates']!=p['profiles'][n]:raise ValueError('Changed frozen profile coefficients')
        if n not in p['control_names']:
            coordinates(row['updates'],p['design'])
            if {k:v for k,v in row['updates'].items() if k not in p['design']['bounds']}!=p['base_candidate']:raise ValueError('Undeclared physical coefficient')
        row_hashes[n+'/'+r]=file_hash(path)
        if row['status']=='passed':
            passed+=1;raw=path.with_suffix('.npz')
            if row['numerics']['all_checks_passed'] is not True or file_hash(raw)!=row['arrays_sha256']:raise ValueError('Invalid climate NPZ/numerics')
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
