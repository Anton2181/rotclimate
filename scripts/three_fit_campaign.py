"""Resume one of three bounded fit/atlas branches, using verified numerics.

Run --branch free, earth and whittaker concurrently. Each search has one
worker; image exports serialize through the atlas builder's shared lock.
Publication uses the same three-layout mean and numerical profile throughout.
"""
from dataclasses import asdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from rotclimate.config import Params
from combine_world_physics import WORLD_KEYS

OUT=ROOT/'output/three_fit_20261022'
CAL=ROOT/'calibration/three_fit_20261022'
SPECS={
    'free':dict(start='calibration/autonomous_20261021/free_polish/best_params.json',
                physics='e3b5',objective='zonefit',evals=17,sigma=.005,title='Rotclimate Free-Fit Atlas'),
    'earth':dict(start='calibration/autonomous_20261021/earth_fit/best_params.json',
                 physics='world',objective='zonefit',evals=17,sigma=.012,title='Rotclimate Earth-Fit Atlas'),
    'whittaker':dict(start='calibration/whittaker_20261022/free/best_params.json',
                     physics='e3b5',objective='whittaker',evals=25,sigma=.012,title='Rotclimate Whittaker-Fit Atlas')}


def count(path):
    if not path.exists():return 0
    with path.open('rb') as f:return pickle.load(f)[2]


def run(args, log):
    print('Running '+' '.join(map(str,args)),flush=True)
    with (OUT/log).open('a') as f:
        subprocess.run([str(ROOT/'.venv/bin/python'),'-u','-I',*map(str,args)],cwd=ROOT,
                       stdout=f,stderr=subprocess.STDOUT,check=True,
                       env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--branch',choices=list(SPECS),required=True)
    a=ap.parse_args();spec=SPECS[a.branch]
    OUT.mkdir(exist_ok=True);CAL.mkdir(exist_ok=True)
    status=OUT/(a.branch+'_status.json')
    if status.exists() and json.loads(status.read_text()).get('stage') in ['ready_for_review','promoted']:
        print('Branch already built; see '+str(status));return
    def save(stage,**fields):status.write_text(json.dumps(dict(branch=a.branch,stage=stage,**fields),indent=2)+'\n')
    base=Params.from_json(ROOT/spec['start']).replace(solver_recover=True,solver_require_convergence=True,
              solver_rtol=1e-6,t_anderson=True,t_require_convergence=True,moisture_require_convergence=True)
    start=CAL/(a.branch+'_start.json')
    current=dict(spec=spec,params=json.loads(json.dumps(asdict(base))),seeds=[1,2,3],
                 calibration_downsample=32,publication_downsample=8,image_scale=2,
                 sources={f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                          for f in (ROOT/'rotclimate').glob('*.py')
                          if f.name not in ['atlas.py','render.py']},
                 crosswalk=json.loads((ROOT/'data/biome_target_crosswalk.json').read_text()))
    manifest=OUT/(a.branch+'_manifest.json')
    if manifest.exists() and json.loads(manifest.read_text())!=current:
        raise ValueError('Resume inputs changed; preserve this campaign and use a new output directory')
    manifest.write_text(json.dumps(current,indent=2)+'\n');base.to_json(start)
    destination=CAL/a.branch
    try:
        save('calibration')
        if count(destination/'state.pkl')<spec['evals']:
            args=['scripts/calibrate_cli.py','--start',start,'--physics',spec['physics'],
                  '--objective',spec['objective'],'--downsample','32','--saved-numerics',
                  '--evals',str(spec['evals']),'--popsize','8','--sigma',str(spec['sigma']),
                  '--seed','231022','--workers','1','--fix','{"retrograde":0.75}',
                  '--seeds','1,2,3','--race','0','--out',destination]
            if (destination/'state.pkl').exists():args+=['--resume']
            run(args,a.branch+'_calibration.log')
        best=destination/'best_params.json'
        if a.branch=='earth':
            fitted=asdict(Params.from_json(best));reference=asdict(base)
            changes={k for k in reference if fitted[k]!=reference[k]}
            assert all(k in WORLD_KEYS or k.startswith('beyond_') for k in changes),changes
        note=('World and physics fitted to the painted seasonal zones.' if a.branch=='free' else
              'Only world parameters fitted; Earth r29 physics held fixed.' if a.branch=='earth' else
              'Fitted to the proposed strict target-to-Whittaker crosswalk. Annual biomes do not guarantee Mediterranean summer drought or swamp hydrology; seasonal scores are shown separately.')
        note+=' Climate averages surroundings layouts 1–3. All exported model fields must pass recorded linear, temperature and moisture checks.'
        save('atlas_build',params=str(best))
        name=a.branch+'_fit_next'
        run(['scripts/build_atlas_variant.py','--params',best,'--name',name,'--title',spec['title'],
             '--eyebrow','Simulated climate · three surroundings layouts · Whittaker potential biomes',
             '--note',note,'--downsample','8','--image-scale','2','--seeds','1,2,3','--workers','1',
             '--fit-objective',spec['objective'],'--require-verified',
             '--checkpoint',OUT/(a.branch+'_publication.pkl')],a.branch+'_atlas.log')
        save('ready_for_review',params=str(best),atlas=name)
    except Exception as exc:
        save('failed',error=repr(exc));raise


if __name__=='__main__':main()
