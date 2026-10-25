"""Bounded geography-only pilot with fixed planet, physics and matched layouts."""
from pathlib import Path
from dataclasses import asdict
import hashlib
import json
import pickle
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json
from rotclimate.model import ClimateModel,ensemble_mean
from rotclimate.score import evaluate,objective
from rotclimate.calibrate import mediterranean_shares


def mapped_identity(grid):
    digest=hashlib.sha256()
    for name in ['inmap','land','elev','elev_max','target','lat']:
        a=getattr(grid,name)
        if name!='inmap':a=a[grid.inmap]
        digest.update(name.encode());digest.update(np.ascontiguousarray(a).tobytes())
    return digest.hexdigest()


def main():
    plan_path=ROOT/'calibration/earthlike_geography_20261025/plan.json'
    plan=json.loads(plan_path.read_text());base=load_params(ROOT/plan['start']).replace(downsample=plan['downsample'])
    out=ROOT/'output/earthlike_geography_20261025';out.mkdir(parents=True,exist_ok=True)
    (out/'checkpoints').mkdir(exist_ok=True)
    allowed={'beyond_north_land','beyond_northeast_land','beyond_southeast_land','beyond_east_land',
             'beyond_continuity_km','beyond_relief_m','far_pole_land'}
    if any(not set(v)<=allowed for v in plan['scenarios'].values()):raise ValueError('Scenario changes non-geographic variables')
    paths=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),plan_path,ROOT/plan['start']]
    paths += [p for p in (ROOT/'data/source').iterdir() if p.is_file()]
    run=freeze(out/'protocol.json',dict(plan=plan,base=json.loads(json.dumps(asdict(base))),
        sources={str(p.relative_to(ROOT)):file_hash(p) for p in paths}))
    records={};mapped=None
    for name,changes in plan['scenarios'].items():
        started=time.monotonic();runs=[]
        print(name+': starting matched-layout geography case',flush=True)
        try:
            for seed in plan['layouts']:
                p=base.replace(**changes,beyond_seed=seed)
                checkpoint=out/'checkpoints'/f'{name}_{seed}.pkl'
                if checkpoint.exists():
                    with checkpoint.open('rb') as stream:saved=pickle.load(stream)
                    if saved['identity']!=run or saved['params']!=asdict(p):raise ValueError('Changed checkpoint inputs')
                    result=saved['result']
                else:
                    result=ClimateModel(p).run()
                    if not result.numerics.get('all_checks_passed'):raise ValueError('Observed numerical checks failed')
                    with checkpoint.with_suffix('.tmp').open('wb') as stream:
                        pickle.dump(dict(identity=run,params=asdict(p),result=result),stream)
                    checkpoint.with_suffix('.tmp').replace(checkpoint)
                actual=mapped_identity(result.grid)
                if mapped is None:mapped=actual
                if actual!=mapped:raise ValueError('Mapped geography changed')
                if not result.numerics.get('all_checks_passed'):raise ValueError('Unverified cached climate')
                runs.append(result);print(f'{name}: layout {seed} verified',flush=True)
            result=ensemble_mean(runs);ev=evaluate(result);g=result.grid;sl=g.map_slice()
            record=dict(status='passed',identity=run,mapped_identity=mapped,zonefit=objective(ev,'zonefit'),
                strict_accuracy=ev['accuracy'],recall=ev['recall'],mediterranean=mediterranean_shares(result,ev),
                numerics=result.numerics,seconds=time.monotonic()-started,changes=changes)
            np.savez_compressed(out/f'{name}.npz',rain=ev['monthly']['Pm'].sum(0)[sl],
                                land=g.land[sl],target=g.target[sl])
        except Exception as error:
            record=dict(status='failed',identity=run,error=repr(error),seconds=time.monotonic()-started,changes=changes)
        records[name]=record;write_json(out/f'{name}.json',record)
        print(name+': '+record['status']+(f', zonefit {record["zonefit"]:.4f}' if record['status']=='passed' else ': '+record['error']),flush=True)
        write_json(out/'progress.json',dict(identity=run,complete=False,scenarios=records))
    control=records['control'];eligible=[]
    if control['status']!='passed':raise RuntimeError('Control failed; no scenario selection')
    for name,r in records.items():
        if name=='control' or r['status']!='passed':continue
        failures=[]
        if r['zonefit']<control['zonefit']+.002:failures.append('Zonefit gain below 0.002')
        if r['strict_accuracy']<control['strict_accuracy']:failures.append('Strict agreement worsened')
        for zone,value in r['recall'].items():
            if value<control['recall'][zone]-.02:failures.append(zone+': recall lost more than 0.02')
        if r['mediterranean']['dry_share']>control['mediterranean']['dry_share']:failures.append('Mediterranean dry share increased')
        if r['mediterranean']['cs_share']<control['mediterranean']['cs_share']-.02:failures.append('Mediterranean Cs share lost more than 0.02')
        r['screen_failures']=failures
        if not failures:eligible.append(name)
    selected=max(eligible,key=lambda n:records[n]['zonefit']) if eligible else None
    write_json(out/'review.json',dict(identity=run,complete=True,scenarios=records,selected_for_native=selected,
        note='Geography pilot only; no planetary/physical parameter or painted target changes. No atlas promotion.'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(14,7),constrained_layout=True)
    for ax,(name,r) in zip(axes.flat,records.items()):
        ax.set_facecolor('#d6e3f0');ax.set_xticks([]);ax.set_yticks([])
        if r['status']=='passed':
            with np.load(out/f'{name}.npz') as z:a=np.where(z['land'],z['rain'],np.nan)
            image=ax.imshow(a,cmap='YlGnBu',vmin=0,vmax=2000,interpolation='nearest')
            ax.set_title(name.replace('_',' ')+f'\nzonefit {r["zonefit"]:.3f} · cold-dry recall {r["recall"]["cold_dry"]:.1%}',fontsize=10)
        else:ax.set_title(name+' failed',fontsize=10)
    fig.colorbar(image,ax=list(axes.flat),shrink=.7,label='Annual rainfall (mm; clipped above 2,000)')
    fig.suptitle('Same planet and r38 physics — alternative off-map geographies',fontsize=14)
    fig.supxlabel('Three fixed surroundings layouts, downsample 16. No radiative, orbital, spin or target changes; coarse pilot, not an adopted atlas.',fontsize=9)
    fig.savefig(out/'geography_rainfall.png',dpi=140);plt.close(fig)
    print('Pilot complete; selected for native check:',selected,flush=True)


if __name__=='__main__':main()
