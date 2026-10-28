"""Frozen eighteen-run stable thermal-separation test; no fitting or adoption."""
from pathlib import Path
from multiprocessing import Pool
import argparse
import hashlib
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,identity,freeze,write_json
from transport_diagnostic_recorder import run_one

CORE={'rotclimate/config.py','rotclimate/model.py','rotclimate/joint.py'}


def sources_for(plan,path):
    old=json.loads((ROOT/plan['parent_protocol']).read_text());epoch=plan['source_epoch']
    if set(epoch['files'])!=CORE:raise ValueError('Unexpected thermal-wind core transition')
    for name,hashes in epoch['files'].items():
        for side in ('before','after'):
            data=subprocess.check_output(['git','show',epoch[side+'_commit']+':'+name],cwd=ROOT)
            if hashlib.sha256(data).hexdigest()!=hashes[side+'_sha256']:raise ValueError('Changed declared Git bytes: '+name)
        if hashes['before_sha256']==hashes['after_sha256']:raise ValueError('Empty source transition')
        if name not in old['sources'] or old['sources'][name]!=hashes['before_sha256']:raise ValueError('Unexpected parent core')
    sources={name:epoch['files'].get(name,{}).get('after_sha256',sha) for name,sha in old['sources'].items()}
    sources.update({name:hashes['after_sha256'] for name,hashes in epoch['files'].items()})
    for name in [str(path.relative_to(ROOT)),plan['parent_protocol'],*plan['new_sources']]:sources[name]=file_hash(ROOT/name)
    for region in plan['regions']:
        for archive in plan['base_archives'].values():
            for suffix in ('.json','.npz')+ (('_extra.npz',) if region in plan['extra_circulation_regions'] else ()):
                name=archive+'/'+region+suffix;sources[name]=file_hash(ROOT/name)
    for name,sha in sources.items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Undeclared changed source/input: '+name)
    return sources


def check_row(row,plan,out):
    import numpy as np
    if row['status']!='passed':return dict(physical_pass=False,failures=[row['error']])
    name,region=row['name'],row['region'];flags=plan['mode_flags'][name]
    old_path=ROOT/plan['comparison_archives'][name]/(region+'.json')
    old=json.loads(old_path.read_text());expected=dict(old['params'],**flags)
    if json.loads(json.dumps(row['params']))!=expected or row['case_identity']!=old['case_identity']:
        raise ValueError('Actual fixed parameters/case changed')
    fields=out/name/(region+'.npz');sidecar=out/name/(region+'_transport.npz')
    if file_hash(fields)!=row['arrays_sha256'] or file_hash(sidecar)!=row['transport_arrays_sha256']:raise ValueError('Changed saved arrays')
    failures=[];cert=row['numerics'].get('thermal_layer_winds');is_new=flags['moisture_thermal_anomaly_decay']
    if flags['moisture_thermal_layer_winds']:
        if cert is None or len(cert['steps'])!=row['params']['steps_per_year']+8:raise ValueError('Missing actual wind certificates')
        for step in cert['steps']:
            if (step['thermal_lapse_k_km']!=6. or step['reference_smoothing_km']!=500.
                    or step['reference_pressure_pa']!=101325. or step['thermal_floor_k']!=200.
                    or step['lower_dry_mass_fraction']!=.25 or abs(step['pressure_centroid_ratio']-7/3)>1e-14):
                raise ValueError('Actual wind mechanism differs from declaration')
            if is_new:
                if step.get('thermal_profile')!='stable-separated' or step['quadrature_nodes']!=16:
                    raise ValueError('Missing actual separated thermal profile')
                if abs(step['nominal_anomaly_decay_exponent']-1/(-np.log(.75)))>1e-14:
                    raise ValueError('Changed geometry-based decay law')
                if step['maximum_possible_lapse_k_km']>9.80665/1004*1000+1e-9:
                    failures.append('Dry stability bound failed')
        if cert['maximum_branch_speed_ms']>plan['physical_limits']['maximum_branch_speed_ms']:
            failures.append('Branch speed exceeds declared Earth-like guard')
    elif cert is not None:raise ValueError('Unexpected thermal flag/certificate')
    if not is_new:
        if row.get('physical_control_exact') is not True:raise ValueError('Historical exact control changed')
        with np.load(fields) as new,np.load(old_path.with_suffix('.npz')) as before:
            if set(new.files)!=set(before.files):raise ValueError('Historical field set changed')
            for key in before.files:np.testing.assert_array_equal(new[key],before[key])
        if region in plan['extra_circulation_regions']:
            with np.load(fields.with_name(region+'_extra.npz')) as new,np.load(old_path.with_name(region+'_extra.npz')) as before:
                if set(new.files)!=set(before.files):raise ValueError('Extra native field set changed')
                for key in before.files:np.testing.assert_array_equal(new[key],before[key])
    return dict(physical_pass=not failures,failures=sorted(set(failures)),exact_control=not is_new)


def score(records,checks,plan):
    import numpy as np
    result={};rows={(r['name'],r['region']):r for r in records}
    for base in plan['base_archives']:
        control=base+'_control';candidate=base+'_thermal'
        if not all((n,r) in rows for n in (control,candidate) for r in plan['regions']):continue
        physical=all(checks.get(n+'/'+r,{}).get('physical_pass',False) for n in (control,candidate) for r in plan['regions'])
        if not physical:
            result[base]=dict(physical_pass=False,process_gain=False);continue
        regional={r:dict(rain_loss_ratio=rows[candidate,r]['rain']['loss']/rows[control,r]['rain']['loss'],
            control_rain_loss=rows[control,r]['rain']['loss'],candidate_rain_loss=rows[candidate,r]['rain']['loss'],
            temperature_mae_change_C=rows[candidate,r]['temperature']['monthly_mae_C']-rows[control,r]['temperature']['monthly_mae_C']) for r in plan['regions']}
        rain=float(np.mean([v['rain_loss_ratio'] for v in regional.values()]));temp=float(np.mean([v['temperature_mae_change_C'] for v in regional.values()]))
        result[base]=dict(physical_pass=True,mean_rain_loss_ratio=rain,mean_temperature_mae_change_C=temp,regional=regional,
            process_gain=rain<=plan['success']['maximum_mean_rain_loss_ratio'] and temp<=plan['success']['maximum_mean_temperature_mae_increase_C'],
            independent_validation=False,adoption=False)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();path=a.plan.resolve();out=a.out.resolve();plan=json.loads(path.read_text())
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve all prior attempts')
    if subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal plan first')
    if len(plan['profiles'])*len(plan['regions'])!=plan['maximum_integrations'] or plan['maximum_integrations']!=18:
        raise ValueError('Expected fixed eighteen-run mechanism test')
    sources=sources_for(plan,path);out.mkdir(parents=True);token=freeze(out/'protocol.json',dict(plan=plan,sources=sources))
    records=[];attempts=[];checks={};started=time.monotonic()
    def check():
        for name,sha in sources.items():
            if file_hash(ROOT/name)!=sha:raise ValueError('Frozen source/input changed: '+name)
    def save(complete=False,error=None):
        passed=sum(r['status']=='passed' for r in records)
        write_json(out/'review.json',dict(complete=complete,identity=token,records=records,attempts=attempts,checks=checks,scores=score(records,checks,plan),
            actual_integrations=len(attempts),strictly_passed=passed,failed_integrations=sum(r['status']!='passed' for r in records),
            pending_integrations=len(attempts)-len(records),cumulative_attempts=plan['counter_before']['attempts']+len(attempts),cumulative_strict_passes=plan['counter_before']['passes']+passed,
            cumulative_failures_or_interruptions=5+sum(r['status']!='passed' for r in records),seconds=time.monotonic()-started,
            error=error,physics_or_atlas_adoption=False))
    try:
        with Pool(2) as pool:
            for name in plan['profiles']:
                check();attempts.extend(dict(profile=name,region=r,state='submitted') for r in plan['regions']);save()
                for row in pool.imap(run_one,[(name,r,plan['profiles'][name],plan,token,str(out)) for r in plan['regions']]):
                    records.append(row)
                    for attempt in attempts:
                        if attempt['profile']==name and attempt['region']==row['region']:attempt['state']=row['status']
                    checks[name+'/'+row['region']]=check_row(row,plan,out);save();check()
                    if name in plan['profile_control_archives'] and row['status']!='passed':raise ValueError('Exact control failed')
        check();save(True)
    except BaseException as error:
        save(False,repr(error));raise


if __name__=='__main__':main()
