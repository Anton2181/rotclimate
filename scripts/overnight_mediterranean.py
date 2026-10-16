"""User-run bounded overnight parameter sweep, validation and atlas update.

Default is a read-only plan. --run enables the long batch. An eight-hour soft
budget stops new work before the atlas reserve; in-flight solves finish. Each
case resumes independently. Numerical failures are saved and excluded, never
assigned a valid score. Atlas replacement happens only after staged validation.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[variable] = '1'
os.environ.setdefault('MPLBACKEND', 'Agg')
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate.config import Params, SOURCE
from scripts.check_mediterranean_spinup import changes, monthly_changes
from scripts.mediterranean_pilot import matching_params
from scripts.tune_mediterranean import checked_summary, guard_failures, GUARDS, load_cached
from scripts.validate_mediterranean import finalists, model_code_id

# Bounded climate-physics sweep. Geometry, spin, terrain and surrounding-land
# fractions stay fixed so improvements must survive the same procedural worlds.
SPACE = {
    'eddy_rate': (.75, 1.25), 'eddy_seasonality': (.45, .85),
    'storm_width': (4.8, 7.2), 'storm_track': (5.8, 8.),
    'storm_reach': (2., 5.5), 'storm_asym': (.1, .5),
    'hadley_edge': (22.5, 26.5), 'hadley_shift': (1.5, 5.5),
    'itcz_mean': (7.5, 10.), 'itcz_shift': (8., 14.),
    'westerly_speed': (2., 3.2), 'trade_speed': (3.1, 5.3),
    'monsoon_strength': (2.8, 4.6), 'monsoon_scale_km': (250., 400.),
    'cross_isobar_deg': (25., 45.), 'land_recycling': (.2, .5),
    'evap_tau_days': (1., 2.), 'precip_tau_days': (3.8, 7.),
    'rh_threshold': (.2, .36), 'orographic': (3.3, 5.8),
    'instability': (.3, 1.2), 'wet_cooling': (.35, .75),
    'sst_offset': (-2., -.8), 'land_offset': (1., 2.),
}
TRAIN = (1, 302, 301)
FRESH = (401, 402)


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def log(out, message):
    line = time.strftime('%H:%M:%S') + ' ' + message
    print(line, flush=True)
    with (out / 'run.log').open('a') as stream:
        stream.write(line + '\n')


def source_id():
    h = hashlib.sha256(model_code_id().encode())
    paths = [Path(__file__), ROOT/'scripts/diagnose_numerics.py',
             ROOT/'scripts/check_mediterranean_spinup.py', ROOT/'scripts/tune_mediterranean.py',
             ROOT/'scripts/diagnose_moisture.py', ROOT/'scripts/mediterranean_pilot.py']
    paths += [ROOT/'rotclimate'/f'{name}.py' for name in
              ('atlas','render','hydrology','analogs','diurnal','calendar','__main__','diagnostics')]
    paths += sorted(SOURCE.glob('*.png')) + sorted(SOURCE.glob('*.webp'))
    paths += sorted((ROOT/'data').glob('*.csv'))
    for path in paths:
        h.update(str(path.relative_to(ROOT)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def sweep(base, seed=20261014):
    trials = {}
    for key, bounds in SPACE.items():
        for suffix, value in zip(('low', 'high'), bounds):
            trials[f'{key}_{suffix}'] = base.replace(**{key:value})
    # Sixteen joint Latin-hypercube probes give each dimension one sample per
    # equal interval. They expose interactions without calling this exhaustive.
    rng = np.random.default_rng(seed)
    samples = np.column_stack([(rng.permutation(16) + rng.random(16))/16 for _ in SPACE])
    for i, sample in enumerate(samples):
        trials[f'joint_{i+1:02d}'] = base.replace(**{key:float(lo + x*(hi-lo))
            for (key,(lo,hi)),x in zip(SPACE.items(),sample)})
    return trials


def job(name, p, spinup, out, code, full=False, transport=False):
    settings = dict(params=asdict(p), spinup=spinup, full=full, transport=transport, source_id=code)
    signature = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    return dict(name=name, out=str(out), input_id=signature, **settings)


def cost(j):
    p = j['params']
    return (p['steps_per_year'] + j['spinup']) / 33 * (8/p['downsample'])**2


def cached(j):
    folder = Path(j['out']) / 'cases'
    path = folder / (j['name'] + '.json')
    if not path.exists():
        # Identical bounded settings (including the incumbent's SST lower
        # bound) are one simulation even if they have different trial names.
        for other in sorted(folder.glob('*.json')):
            if other.stem.endswith('_diagnostic'):
                continue
            saved = json.loads(other.read_text())
            if saved.get('input_id') == j['input_id']:
                path = other
                break
        else:
            return None
    d = json.loads(path.read_text())
    if d.get('input_id') != j['input_id']:
        return None
    if d['status'] == 'failed':
        return {**d, 'name':j['name']}
    required = ['fields'] + (['result'] if j['full'] else []) + (['transport'] if j['transport'] else [])
    if not all(Path(d[k]).exists() for k in required):
        return None
    with np.load(d['fields'], allow_pickle=False) as f:
        if not matching_params(json.loads(str(f['params_json'])), Params(**j['params'])):
            return None
    return {**d, 'name':j['name']}


def worker(j):
    out, p = Path(j['out']), Params(**j['params'])
    folder = out/'cases'
    folder.mkdir(exist_ok=True)
    stem = folder/j['name']
    paths = {key:str(stem.with_name(stem.name+'_'+key+'.npz')) for key in ('fields','result','transport')}
    started = time.monotonic()
    try:
        if source_id() != j['source_id']:
            raise RuntimeError('Source or map inputs changed during the batch; refusing mixed results.')
        from scripts.diagnose_numerics import diagnose
        def progress(done,total):
            if done == 1 or done % 10 == 0 or done == total:
                log(out, f"{j['name']}: {done}/{total} steps; {(time.monotonic()-started)/60:.1f} min")
        d = diagnose(p, snapshot=paths['fields'], spinup=j['spinup'], progress=progress,
                     result_snapshot=paths['result'] if j['full'] else None,
                     transport_snapshot=paths['transport'] if j['transport'] else None)
        row = checked_summary(d)
        if source_id() != j['source_id']:
            raise RuntimeError('Source changed while solving; result excluded.')
        atomic_json(stem.with_name(stem.name+'_diagnostic.json'), d)
        answer = dict(status='ok', name=j['name'], input_id=j['input_id'], row=row,
                      seconds=time.monotonic()-started, **paths)
    except Exception as error:
        answer = dict(status='failed', name=j['name'], input_id=j['input_id'], error=str(error),
                      details=getattr(error,'details',None), traceback=traceback.format_exc(),
                      seconds=time.monotonic()-started)
    atomic_json(stem.with_suffix('.json'), answer)
    return answer


def run_jobs(jobs, workers, deadline, out, record, rate=900.):
    """Keep a small spawned pool fed, but reserve time before starting work."""
    answers, todo = {}, []
    for j in jobs:
        d = cached(j)
        if d is None:
            todo.append(j)
        else:
            answers[j['name']] = d
            record(d)
    rates = []
    pending = {}
    pool_broken = False
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) as pool:
        while todo or pending:
            while todo and len(pending) < workers and not pool_broken:
                estimate = max(rate, float(np.median(rates))) if rates else rate
                if time.monotonic() + estimate*cost(todo[0]) > deadline:
                    break
                j = todo.pop(0)
                try:
                    pending[pool.submit(worker,j)] = j
                except Exception as error:
                    d = dict(name=j['name'],status='failed',input_id=j['input_id'],error=f'Worker pool unavailable: {error}')
                    atomic_json(out/'cases'/(j['name']+'.json'),d)
                    answers[j['name']]=d
                    record(d)
                    pool_broken=True
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                j = pending.pop(future)
                try:
                    d = future.result()
                except Exception as error:
                    d = dict(name=j['name'], status='failed', error=f'Worker exited: {error}', input_id=j['input_id'])
                    atomic_json(out/'cases'/(j['name']+'.json'), d)
                answers[j['name']] = d
                if d['status'] == 'ok':
                    rates.append(d['seconds']/cost(j))
                    r = d['row']
                    log(out, f"Finished {j['name']}: overall {r['accuracy']:.1%}, Med dry "
                        f"{r['mediterranean']['dry_share']:.1%}, cold-dry {r['zone_recall']['cold_dry']:.1%}")
                else:
                    log(out, f"Excluded {j['name']}: {d['error']}")
                record(d)
    for j in todo:
        d = dict(name=j['name'], status='deferred_budget', input_id=j['input_id'])
        answers[j['name']] = d
        record(d)
    return answers


def passed(d):
    return d is not None and d['status'] == 'ok'


def rank(rows):
    return (max(r['mediterranean']['dry_share'] for r in rows),
            -sum(r['accuracy'] for r in rows)/len(rows))


def qualifies(candidate, baseline, seeds):
    return (all(passed(candidate.get(s)) and passed(baseline.get(s)) for s in seeds)
            and all(not guard_failures(candidate[s]['row'],baseline[s]['row']) for s in seeds))


def stability(a,b):
    if not passed(a) or not passed(b):
        return dict(passed=False, reason='Missing converged warm-up pair')
    with np.load(a['fields']) as before, np.load(b['fields']) as after:
        report = changes(before,after)
    with np.load(a['transport']) as before, np.load(b['transport']) as after:
        monthly = monthly_changes(before,after,365)
    # Explicit development tolerances, not a universal accuracy theorem.
    regions = [report['painted'],*report['zones'].values()]
    monthly_regions = [monthly['painted'],*monthly['zones'].values()]
    ok = all(r['fields'][k]['absolute_change']['p95'] <= .1
             for r in regions for k in ('MAT','Tcold','Thot'))
    ok &= all(r['fields'][k]['absolute_change']['p95'] <= 5.
              for r in regions for k in ('MAP','Pwin','Psum'))
    ok &= all(r['temperature_c']['absolute_p95'] <= .1 and
              r['precipitation_mm_month']['absolute_p95'] <= 1. for r in monthly_regions)
    return dict(passed=bool(ok), index_changes=report, monthly_changes=monthly,
                limits=dict(p95_temperature_c=.1,p95_annual_seasonal_rain_mm=5.,p95_monthly_rain_mm=1.),
                note='One development-world warm-up check; not grid or unseen-world validation.')


def verify_atlas(folder,p):
    from PIL import Image
    meta = json.loads((folder/'atlas.json').read_text())
    from rotclimate.__main__ import numerical_settings
    if meta['numerics'] != numerical_settings(p):
        raise ValueError('Atlas numerical metadata differs from the selected simulation')
    size = (folder/'atlas.bin').stat().st_size
    for spec in meta['arrays'].values():
        end = spec['offset'] + int(np.prod(spec['shape']))*np.dtype(spec['dtype']).itemsize
        if spec['offset'] < 0 or end > size:
            raise ValueError('Atlas binary arrays are incomplete')
    for name in ('koppen.webp','zones.webp','agreement.webp','precip.webp','t_annual.webp',
                 't_cold.webp','t_hot.webp','labels.png','year_temperature.gif','year_precipitation.gif'):
        with Image.open(folder/name) as img:
            img.verify()


def publish_folder(staged,current,backup):
    """Swap only complete data; roll back if the second rename fails."""
    if backup.exists():
        raise FileExistsError('Refusing to overwrite the previous atlas backup')
    current.rename(backup)
    try:
        staged.rename(current)
    except BaseException:
        backup.rename(current)
        raise


def export_atlas(spec_path):
    spec = json.loads(spec_path.read_text())
    out = Path(spec['out'])
    if source_id() != spec['source_id']:
        raise RuntimeError('Source changed before export; refusing to publish')
    p = Params(**spec['params'])
    from rotclimate.model import Result
    from rotclimate.geography import build_grid
    from rotclimate.score import evaluate
    from rotclimate import atlas,render as R
    with np.load(spec['result'],allow_pickle=False) as saved:
        if not matching_params(json.loads(str(saved['params_json'])),p):
            raise ValueError('Saved simulation does not match selected atlas parameters')
        arrays = {k:saved[k].copy() for k in ('days','T','Tsl','P','W','u','v','snow','E')}
    r = Result(params=p,grid=build_grid(p),**arrays)
    if not np.isfinite(r.T).all() or not np.isfinite(r.P).all():
        raise ValueError('Nonfinite saved simulation; atlas unchanged')
    stage = out/'atlas_next'
    stage.mkdir(exist_ok=True)
    # Preserve historical experiment illustrations while regenerating every
    # current-climate layer, climograph, animation and packed climate array.
    shutil.copytree(ROOT/'atlas/data',stage,dirs_exist_ok=True)
    fr,ev = R.FullRes(r),evaluate(r)
    original = atlas.build_hires_layers
    atlas.build_hires_layers = lambda result,scale=3,outdir=stage:original(result,scale=spec['layer_scale'],outdir=outdir)
    atlas.build(r,fr,ev,outdir=stage)
    R.season_gif(fr,stage/'year_temperature.gif','T')
    R.season_gif(fr,stage/'year_precipitation.gif','P')
    from rotclimate.__main__ import CLIMOGRAPH_CITIES
    R.climographs(fr,CLIMOGRAPH_CITIES,stage/'climographs.png')
    R.comparison_map(fr,R.fullres_memberships(fr),stage/'comparison.png')
    R.context_map(r,stage/'world_context.png')
    atomic_json(stage/'overnight_run.json',spec)
    verify_atlas(stage,p)
    backup = out/('atlas_previous_'+time.strftime('%Y%m%d_%H%M%S'))
    publish_folder(stage,ROOT/'atlas/data',backup)
    p.to_json(out/'selected_params.json')
    atomic_json(out/'atlas_publication.json',dict(status='published',backup=str(backup),
                selected=spec['selected'],params=asdict(p),layer_scale=spec['layer_scale']))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--hours',type=float,default=8.)
    ap.add_argument('--workers',type=int,default=3)
    ap.add_argument('--out',type=Path,default=ROOT/'output/overnight_mediterranean')
    ap.add_argument('--export-spec',type=Path,help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.export_spec:
        export_atlas(a.export_spec)
        return
    if not np.isfinite(a.hours) or a.hours < 4 or not 1 <= a.workers <= 4:
        ap.error('Use at least four hours and 1–4 workers')
    base = Params.from_json(ROOT/'calibration/round20_retrograde_local_shortlist.json')
    anchor = finalists()['strong_seasonal'].replace(beyond_seed=1)
    for p in (base,anchor):
        if p.downsample != 8 or p.steps_per_year != 25 or not all((p.t_require_convergence,
                p.moisture_require_convergence,p.solver_require_convergence)):
            ap.error('This batch requires the strict 8/25 starting profiles.')
    if any(v!=asdict(anchor)[key] for key,v in asdict(base).items() if key not in SPACE):
        ap.error('Starting profiles differ outside the declared physics controls.')
    trials = sweep(base)
    print(f'64 planned trials across 24 climate controls: 48 coordinate bounds + 16 joint probes.\n'
          f'{a.workers} workers, {a.hours:g}-hour soft budget; final hour reserved for atlas export.\n'
          'Two-year warm-up for all qualifying/validation/render runs. Search screen uses the old\n'
          '8-step warm-up only as a proposal stage, never as promotion evidence.\n'
          'Top two proposals checked on worlds 1/302/301; one chosen fit validated on 401/402.\n'
          'Paired finer-grid checks if time permits. Strict solves and per-world dry-zone limits.\n'
          'Save every case; exclude failures; reuse matching results; stage and back up the atlas.\n'
          'Budget may leave trials deferred; in-flight cases/export can finish after the time limit.',flush=True)
    if not a.run:
        print('Plan only. Add --run to execute.')
        return
    out = a.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    (out/'cases').mkdir(exist_ok=True)
    code = source_id()
    manifest = dict(source_id=code,search_bounds=SPACE,search_seed=20261014,
                    base=asdict(base),anchor=asdict(anchor),training=list(TRAIN),validation=list(FRESH),guards=GUARDS)
    prior = out/'experiment.json'
    if prior.exists() and json.loads(prior.read_text()) != json.loads(json.dumps(manifest)):
        ap.error('Experiment inputs changed; use a new --out to preserve the previous run.')
    atomic_json(prior,manifest)
    started = time.monotonic()
    deadline = started+a.hours*3600
    atlas_start = deadline-3600
    state = dict(stage='warmup',runs={},atlas=dict(status='pending'),planned_trials=len(trials))
    def save():
        atomic_json(out/'summary.json',state)
        rows = [f'# Overnight Mediterranean batch',f"Stage: {state['stage']}",
                f"Atlas: {state['atlas']['status']}",
                f"Completed: {sum(d['status']=='ok' for d in state['runs'].values())}; "
                f"failed: {sum(d['status']=='failed' for d in state['runs'].values())}; "
                f"deferred: {sum(d['status'].startswith('deferred') for d in state['runs'].values())}."]
        if 'selected' in state:
            rows += [f"Selected: {state['selected']}.",
                     'This is bounded development/validation evidence, not a statistical final verdict.']
            table = ['| World | Anchor Med dry | Selected Med dry | Selected cold-dry | Selected hot-dry | Overall |',
                     '|---|---:|---:|---:|---:|---:|']
            for groups,seeds in ((state.get('training',{}),TRAIN),(state.get('fresh_results',{}),FRESH)):
                for seed in seeds:
                    b=groups.get('anchor',{}).get(seed)
                    c=groups.get(state['selected'],{}).get(seed)
                    if passed(b) and passed(c):
                        br,cr=b['row'],c['row']
                        table += [f"| {seed} | {br['mediterranean']['dry_share']:.2%} | "
                                 f"{cr['mediterranean']['dry_share']:.2%} | {cr['zone_recall']['cold_dry']:.2%} | "
                                 f"{cr['zone_recall']['hot_dry']:.2%} | {cr['accuracy']:.2%} |"]
            rows += ['\n'.join(table)]
            if 'atlas_simulation' in state:
                r=state['atlas_simulation']
                rows += [f"Atlas simulation: overall {r['accuracy']:.2%}, Mediterranean dry "
                         f"{r['mediterranean']['dry_share']:.2%}; grid setting "
                         f"{state['selected_params']['downsample']}, 25 steps/year, two warm-up years."]
            changes={k:v for k,v in state['selected_params'].items() if k in SPACE and v!=getattr(base,k)}
            rows += ['Changed climate controls relative to the starting shortlist: '+json.dumps(changes)+'.']
            if 'med_goal_met' in state:
                rows += ['Mediterranean dry area <=5% on every completed required check: '+
                         ('met.' if state['med_goal_met'] else 'not established.')]
        (out/'summary.md').write_text('\n\n'.join(rows)+'\n')
    def record(d):
        state['runs'][d['name']]=d
        save()
    def make(name,p,spin=50,full=False,transport=False):
        return job(name,p,spin,out,code,full,transport)
    def execute(jobs,cutoff,workers=a.workers):
        return run_jobs(jobs,workers,cutoff,out,record)
    # Reuse the two exact old short-warm-up anchors as provisional screen
    # evidence; long-warm-up qualifying results are always separate jobs.
    for name,p,old in (('anchor',anchor,'anchor'),('incumbent',base,'slightly_narrower')):
        j=make('screen_'+name,p,8)
        old_path=ROOT/'output/mediterranean_tuning'/f'{old}_seed1.json'
        old_fields=old_path.with_name(old_path.stem+'_fields.npz')
        old_detail=load_cached(old_path,old_fields,p,model_code_id())
        if cached(j) is None and old_detail is not None and len(old_detail['temperature_convergence']['converged'])-25==8:
            answer=dict(status='ok',name=j['name'],input_id=j['input_id'],row=checked_summary(old_detail),
                        fields=str(old_fields),seconds=old_detail['seconds'],origin=str(old_path))
            atomic_json(out/'cases'/(j['name']+'.json'),answer)
    warm = execute([make(f'{n}_warm{y}',p,25*y,full=y==2,transport=True)
                    for n,p in (('anchor',anchor),('incumbent',base)) for y in (1,2)],atlas_start)
    state['warmup'] = {n:stability(warm.get(n+'_warm1'),warm.get(n+'_warm2')) for n in ('anchor','incumbent')}
    save()
    state['stage']='sweep'
    screen = execute([make('screen_anchor',anchor,8),make('screen_incumbent',base,8)] +
                     [make('screen_'+n,p,8) for n,p in trials.items()], started+a.hours*3600*.55)
    proposals = {'incumbent':base,**trials}
    screened = [n for n in proposals if passed(screen.get('screen_'+n)) and
                passed(screen.get('screen_anchor')) and not guard_failures(
                    screen['screen_'+n]['row'],screen['screen_anchor']['row'])]
    screened.sort(key=lambda n:rank([screen['screen_'+n]['row']]))
    shortlist = screened[:2]
    state['screen_shortlist']=shortlist
    state['stage']='training_checks'
    groups = {'anchor':anchor,**{n:proposals[n] for n in shortlist}}
    # Warm-up captures are exact matching full simulations; reuse them directly.
    training = {'anchor':{1:warm.get('anchor_warm2')}}
    for n in shortlist:
        training[n] = {1:warm.get('incumbent_warm2')} if n=='incumbent' else {}
    jobs = [make(f'train_{n}_s{s}',p.replace(beyond_seed=s),full=s==1,transport=s==1)
            for n,p in groups.items() for s in TRAIN if s not in training.get(n,{})]
    checked = execute(jobs,started+a.hours*3600*.76)
    for n in groups:
        training.setdefault(n,{})
        for s in TRAIN:
            if s not in training[n]: training[n][s]=checked.get(f'train_{n}_s{s}')
    acceptable = [n for n in shortlist if qualifies(training[n],training['anchor'],TRAIN)]
    acceptable.sort(key=lambda n:rank([training[n][s]['row'] for s in TRAIN]))
    selected = next((n for n in acceptable if rank([training[n][s]['row'] for s in TRAIN]) <
                     rank([training['anchor'][s]['row'] for s in TRAIN])), 'anchor')
    state['training_qualified']=acceptable
    state['training']=training
    state['stage']='validation'
    if selected not in ('anchor','incumbent'):
        extra = execute([make('selected_warm1',groups[selected],25,transport=True)],atlas_start)
        state['selected_warmup']=stability(extra.get('selected_warm1'),training[selected].get(1))
    else:
        state['selected_warmup']=state['warmup'][selected]
    if not state['selected_warmup']['passed']:
        selected='anchor'
    validation = execute([make(f'fresh_{n}_s{s}',groups[n].replace(beyond_seed=s))
        for s in FRESH for n in dict.fromkeys(('anchor',selected))],atlas_start)
    fresh = {n:{s:validation.get(f'fresh_{n}_s{s}') for s in FRESH}
             for n in dict.fromkeys(('anchor',selected))}
    state['fresh_checks_complete']=all(passed(d) for g in fresh.values() for d in g.values())
    state['fresh_results']=fresh
    if selected!='anchor' and not qualifies(fresh[selected],fresh['anchor'],FRESH):
        selected='anchor'
    state['selected']=selected
    state['selected_params']=asdict(groups[selected])
    state['stage']='resolution'
    chosen = training[selected].get(1)
    # A coarse atlas is preferable to falsely declaring a lone fine run verified.
    fine_jobs = [make('fine_'+n,groups[n].replace(downsample=4),full=True)
                 for n in dict.fromkeys(('anchor',selected))]
    if time.monotonic()+max(cost(j) for j in fine_jobs)*900 <= atlas_start:
        fine = execute(fine_jobs,atlas_start,workers=min(2,a.workers))
        fa,fc = fine.get('fine_anchor'),fine.get('fine_'+selected)
        if passed(fa) and passed(fc) and not guard_failures(fc['row'],fa['row']):
            drift = guard_failures(fc['row'],chosen['row']) if passed(chosen) else ['Missing coarse check']
            if not drift:
                chosen=fc
                state['selected_params']=asdict(groups[selected].replace(downsample=4))
        state['fine_checked']=dict(anchor=passed(fa),selected=passed(fc),used=chosen is fc)
    else:
        state['fine_checked']=dict(status='deferred_budget')
    state['stage']='atlas'
    if passed(chosen): state['atlas_simulation']=chosen['row']
    required=[training[selected].get(s) for s in TRAIN]+[fresh.get(selected,{}).get(s) for s in FRESH]+[chosen]
    state['med_goal_met']=all(passed(d) and d['row']['mediterranean']['dry_share']<=.05 for d in required)
    save()
    # Publishing requires a settled anchor or candidate and a converged captured
    # run. A numerical failure never becomes an atlas just because time is up.
    settled = state['warmup']['anchor']['passed'] if selected=='anchor' else state['selected_warmup']['passed']
    if not passed(chosen) or not settled:
        state['atlas']=dict(status='blocked_checks',reason='No settled, converged captured simulation; existing atlas retained.')
    else:
        spec = dict(out=str(out),selected=selected,params=state['selected_params'],result=chosen['result'],
                    source_id=code,layer_scale=3,warmup_steps=50,
                    fresh_checks_complete=state['fresh_checks_complete'],fine_checks=state['fine_checked'])
        atomic_json(out/'export_spec.json',spec)
        for scale in (3,1):
            spec['layer_scale']=scale
            atomic_json(out/'export_spec.json',spec)
            log(out,f'Building atlas at image scale {scale}; previous data remain live until verification.')
            with (out/'atlas_export.log').open('a') as stream:
                done = subprocess.run([sys.executable,str(Path(__file__).resolve()),'--export-spec',str(out/'export_spec.json')],
                                      cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            if done.returncode==0:
                state['atlas']=json.loads((out/'atlas_publication.json').read_text())
                break
        else:
            state['atlas']=dict(status='export_failed',reason='See atlas_export.log; previous atlas retained.')
    state['stage']='complete'
    state['elapsed_hours']=(time.monotonic()-started)/3600
    save()
    log(out,f"Batch complete; atlas {state['atlas']['status']}. Read {out/'summary.md'}")


if __name__=='__main__':
    main()
