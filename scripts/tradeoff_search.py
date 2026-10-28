"""Bounded global rainfall exploration with explicit physical and skill objectives.

Prior acceptance rules remain archived. This new predeclared research policy
ranks physically admissible tradeoffs; it never publishes an adopted climate.
"""
from pathlib import Path
from multiprocessing import Pool
from dataclasses import asdict
import argparse,json,math,sys,time,importlib.metadata
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from local_benchmark_protocol import file_hash,freeze,identity,write_json
from paired_physics_pilot import run_one
from check_surface_momentum import branch_failures
from check_vapor_flux import environmental_reference
from rotclimate.config import Params


def coordinates(updates,design):
    values=[]
    for key,spec in design['bounds'].items():
        lo,hi=spec['range'];v=updates[key]
        if not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Parameter outside frozen bounds: '+key)
        values.append(math.log(v/lo)/math.log(hi/lo) if spec['scale']=='log' else (v-lo)/(hi-lo))
    return np.array(values)


def parameters(point,design):
    point=np.asarray(point,float)
    if point.shape!=(len(design['bounds']),) or not np.isfinite(point).all() or ((point<0)|(point>1)).any():
        raise ValueError('Need a finite bounded unit point')
    out={}
    for x,(key,spec) in zip(point,design['bounds'].items()):
        lo,hi=spec['range'];out[key]=float(lo*(hi/lo)**x if spec['scale']=='log' else lo+x*(hi-lo))
    return out


def positive_ratio(a,b,floor=1e-12):
    if not all(math.isfinite(v) and v>=0 for v in [a,b]) or b<=0:
        raise ValueError('Missing/nonfinite/zero-baseline error metric')
    return a/max(b,floor)


def skill_objective(temperature,rain,native_regressions,sst_regressions,policy):
    """Equal-region normalized errors and explicit nonnegative regret penalties."""
    t,r=np.asarray(temperature,float),np.asarray(rain,float)
    n,o=np.asarray(native_regressions,float),np.asarray(sst_regressions,float)
    if (t.ndim!=1 or t.size==0 or r.shape!=t.shape or any(not np.isfinite(a).all() for a in [t,r,n,o])
            or (t<0).any() or (r<0).any()):raise ValueError('Invalid skill metrics')
    s=.5*(t+r);regret=np.maximum(s-policy['regional_free_ratio'],0.)
    regional=float(np.mean(regret**2));native=float(np.mean(np.maximum(n,0.)**2)) if n.size else 0.
    ocean=float(np.mean(np.maximum(o,0.)**2)) if o.size else 0.
    mean=float(s.mean());value=mean+policy['regional_weight']*regional+policy['native_weight']*native+policy['ocean_weight']*ocean
    return dict(objective=value,mean_combined_ratio=mean,mean_temperature_ratio=float(t.mean()),
        mean_rain_ratio=float(r.mean()),worst_regional_combined_ratio=float(s.max()),
        regional_squared_regret=regional,native_squared_regret=native,ocean_squared_regret=ocean,
        regional_ratios=s.tolist(),native_normalized_regressions=n.tolist(),ocean_normalized_regressions=o.tolist())


def paired_native(candidate,control,group):
    if candidate.get('case_identity')!=control.get('case_identity'):raise ValueError('Unpaired native case')
    a,b=candidate['report'],control['report'];values=[]
    for kind,keys,floors in [('scores',['vector_rmse_ms'],[.5]),
                            ('humidity',['partial_water_mae_mm','partial_q_ratio_mae'],[1.,.02])]:
        x=a['scores']['q925_300'][group] if kind=='scores' else a['humidity']['scores'][group]
        y=b['scores']['q925_300'][group] if kind=='scores' else b['humidity']['scores'][group]
        if any(x.get(k)!=y.get(k) for k in ['native_cells','area_km2']):raise ValueError('Unpaired native footprint')
        if not math.isfinite(x['area_km2']) or x['area_km2']<=0 or x['native_cells']<=0:raise ValueError('Empty native footprint')
        for key,floor in zip(keys,floors):
            u,v=x[key],y[key]
            if not all(math.isfinite(z) and z>=0 for z in [u,v]):raise ValueError('Invalid native prediction error')
            values.append((u-v)/max(v,floor))
    return values


def evaluate(name,records,plan):
    own={r['region']:r for r in records if r['name']==name};ref={r['region']:r for r in records if r['name']=='reference'}
    failures=[];t=[];rain=[];native=[];ocean=[]
    if set(own)!=set(plan['regions']):return dict(physical_admissible=False,failures=['Incomplete comparison'])
    for region in plan['regions']:
        c,b=own[region],ref[region]
        if c.get('status')!='passed':failures.append(region+': numerical failure');continue
        p=c['params'];n=c['numerics']
        if c['case_identity']!=b['case_identity']:raise ValueError('Changed candidate geography')
        if n.get('all_checks_passed') is not True:failures.append(region+': numerical certificate missing')
        if name not in plan['control_names']:
            base=next(r for r in records if r['name']=='environment_control' and r['region']==region)['params']
            free=set(plan['design']['bounds'])
            if {k:v for k,v in p.items() if k not in free}!={k:v for k,v in base.items() if k not in free}:
                failures.append(region+': undeclared actual parameter change')
            failures.extend(branch_failures({region:c},Params(**p)))
            for key,value in plan['fixed_model'].items():
                if p.get(key)!=value:failures.append(region+': fixed physics changed: '+key)
            ledger=n.get('vapor_flux_budget',{})
            if (ledger.get('horizontal_transport_conservative') is not True
                    or ledger.get('max_relative_transport_cancellation',float('inf'))>1e-10):
                failures.append(region+': water transport conservation failed')
        if c['column_speed']['maximum_ms']>60 or c['column_speed']['p95_ms']>25:failures.append(region+': wind bound failed')
        t.append(positive_ratio(c['temperature']['monthly_mae_C'],b['temperature']['monthly_mae_C']))
        rain.append(positive_ratio(c['rain']['loss'],b['rain']['loss']))
        if (c['sst'] is None)!=(b['sst'] is None):raise ValueError('Ocean mask changed')
        if c['sst']:
            if c['sst']['cells']!=b['sst']['cells']:raise ValueError('Ocean footprint changed')
            ocean.append((c['sst']['monthly_mae_C']-b['sst']['monthly_mae_C'])/max(.1,b['sst']['monthly_mae_C']))
        if region in plan['circulation_regions']:
            baseline=next(r for r in records if r['name']=='transport_control' and r['region']==region)
            native.extend(paired_native(dict(c,report=c['circulation']),dict(baseline,report=baseline['circulation']),plan['circulation_groups'][region]))
        if region in plan['extra_circulation_regions']:
            baseline=next(r for r in records if r['name']=='column_control' and r['region']==region)
            native.extend(paired_native(dict(c,report=c['extra_circulation']),dict(baseline,report=baseline['extra_circulation']),plan['extra_circulation_groups'][region]))
    if failures:return dict(physical_admissible=False,failures=failures)
    score=skill_objective(t,rain,native,ocean,plan['objective'])
    # Research validation shortlist, never an adoption authorization.
    q=plan['validation_shortlist']
    ready=(score['mean_combined_ratio']<=q['mean_combined_max'] and score['mean_rain_ratio']<=q['mean_rain_max']
           and score['mean_temperature_ratio']<=q['mean_temperature_max'] and score['worst_regional_combined_ratio']<=q['worst_region_max'])
    return dict(physical_admissible=True,failures=[],validation_ready=ready,**score)


def diverse_starts(scores,updates,design):
    order=sorted((n for n,v in scores.items() if v.get('physical_admissible')),key=lambda n:(scores[n]['objective'],n))
    selected=[]
    for name in order:
        x=coordinates(updates[name],design)
        if all(float(np.linalg.norm(x-coordinates(updates[m],design)))>=design['start_minimum_distance'] for m in selected):
            selected.append(name)
        if len(selected)==design['local_starts']:break
    return selected


def pareto_names(scores):
    valid={n:v for n,v in scores.items() if v.get('physical_admissible')}
    keys=['mean_combined_ratio','worst_regional_combined_ratio','native_squared_regret']
    return sorted(n for n,a in valid.items() if not any(all(b[k]<=a[k] for k in keys) and any(b[k]<a[k] for k in keys) for m,b in valid.items() if m!=n))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();path=args.plan.resolve();plan=json.loads(path.read_text());out=args.out.resolve()
    if out.exists() and any(out.iterdir()):raise SystemExit('Preserve existing campaign; choose a fresh output')
    out.mkdir(parents=True,exist_ok=True);start=time.monotonic();phase='freeze';records=[];scores={};history=[];updates=dict(plan['profiles'])
    try:
        thermal=environmental_reference(plan)
        if thermal['reviews']['environmental_6']['qualifies'] is not True:raise ValueError('Independent temperature/capacity reference failed')
        parent=ROOT/plan['parent_protocol'];previous=json.loads(parent.read_text());sources=dict(previous['sources'])
        for name,sha in sources.items():
            if file_hash(ROOT/name)!=sha:raise ValueError('Changed parent scientific source: '+name)
        for p in [path,Path(__file__),parent,ROOT/'scripts/paired_physics_pilot.py',ROOT/'scripts/check_vapor_flux.py',ROOT/'scripts/check_surface_momentum.py']:
            sources[str(p.relative_to(ROOT))]=file_hash(p)
        for archive in plan['profile_control_archives'].values():
            for region in plan['regions']:
                for suffix in ['.json','.npz']:
                    p=ROOT/archive/(region+suffix);sources[str(p.relative_to(ROOT))]=file_hash(p)
        run_id=freeze(out/'protocol.json',dict(plan=plan,sources=sources,packages={n:importlib.metadata.version(n) for n in ['numpy','scipy','numba']}))
        def check_sources():
            if time.monotonic()-start>plan['maximum_seconds']:raise TimeoutError('Frozen campaign deadline exceeded')
            for name,sha in sources.items():
                if file_hash(ROOT/name)!=sha:raise ValueError('Frozen source changed: '+name)
        def save(complete=False):
            write_json(out/'progress.json',dict(complete=complete,identity=run_id,records=records,scores=scores,history=history,
                seconds=time.monotonic()-start,actual_integrations=len(records),physics_or_atlas_adoption=False))
        with Pool(2) as pool:
            def run_profile(name,coeff,stage):
                nonlocal phase
                phase=stage;check_sources()
                numerical=plan.get('profile_numerics',{}).get(name,plan['candidate_numerics'])
                runtime=dict(plan,profile_numerics={**plan['profile_numerics'],name:numerical})
                rows=pool.map(run_one,[(name,r,coeff,runtime,run_id,str(out)) for r in plan['regions']])
                records.extend(rows);updates[name]=coeff
                if name in plan['control_names']:
                    if any(r['status']!='passed' for r in rows):raise ValueError('Exact historical control failed')
                else:scores[name]=evaluate(name,records,plan)
                history.append(dict(name=name,stage=stage,updates=coeff,score=scores.get(name)))
                check_sources();save();print('PROFILE '+name+' '+json.dumps(scores.get(name,{'control':'exact'})),flush=True)
            for name in plan['control_names']:run_profile(name,updates[name],'controls')
            for name in plan['global_names']:run_profile(name,updates[name],'global')
            starts=diverse_starts({n:scores[n] for n in plan['global_names']},updates,plan['design'])
            write_json(out/'local_starts.json',dict(identity=run_id,starts=starts,selection_rule=plan['design']))
            for index,name in enumerate(starts):
                current=name
                for step,(axis,sign) in enumerate(plan['design']['local_poll_order']):
                    point=coordinates(updates[current],plan['design']);point[axis]=np.clip(point[axis]+sign*plan['design']['local_step'],0,1)
                    coeff={**plan['base_candidate'],**parameters(point,plan['design'])}
                    same=next((n for n,v in updates.items() if v==coeff),None)
                    trial=f'local{index+1}_{step+1:02}'
                    if same is not None:
                        history.append(dict(name=trial,stage='cached_local_proposal',reused=same,updates=coeff));save();trial=same
                    else:run_profile(trial,coeff,'local')
                    if trial in scores and scores[trial].get('physical_admissible') and scores[trial]['objective']<scores[current]['objective']:current=trial
        check_sources();save(True)
        shortlist=sorted((n for n,v in scores.items() if v.get('validation_ready')),key=lambda n:(scores[n]['objective'],n))[:2]
        write_json(out/'review.json',dict(complete=True,identity=run_id,physical_admissible=sum(v.get('physical_admissible',False) for v in scores.values()),
            scores=scores,pareto_front=pareto_names(scores),validation_shortlist=shortlist,local_starts=starts,
            actual_integrations=len(records),strictly_passed=sum(r['status']=='passed' for r in records),
            failed_integrations=sum(r['status']!='passed' for r in records),seconds=time.monotonic()-start,
            physics_or_atlas_adoption=False,scope='New predeclared research tradeoff policy; no automatic adoption or validation-set reuse'))
    except BaseException as e:
        write_json(out/'failure.json',dict(phase=phase,error=repr(e),actual_integrations=len(records),seconds=time.monotonic()-start,physics_or_atlas_adoption=False));raise


if __name__=='__main__':main()
