"""Bounded continuation of the October campaign; no hidden calibration loops.

Run one branch with --branch free or earth. Logs, status and result caches
survive interruption; completed calibration checkpoints are reused.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from rotclimate.config import Params
from combine_world_physics import WORLD_KEYS
OUT=ROOT/'output/autonomous_20261021'
CAL=ROOT/'calibration/autonomous_20261021'
PY=ROOT/'.venv/bin/python'

def wait_for(test, description, timeout=3600):
    start=time.monotonic()
    print('Waiting for '+description,flush=True)
    while not test():
        if time.monotonic()-start > timeout: raise TimeoutError(description)
        time.sleep(5)

def count(path):
    if not path.exists():return 0
    with path.open('rb') as f:return pickle.load(f)[2]

def run(args, log):
    print('Running '+ ' '.join(map(str,args)),flush=True)
    with (OUT/log).open('a') as f:
        subprocess.run([str(PY),'-u','-I',*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
                       check=True,env={**os.environ,'OMP_NUM_THREADS':'1'})

def calibrate(start,folder,physics,evals,seeds,sigma):
    destination=CAL/folder
    state=destination/'state.pkl'
    if count(state)<evals:
        args=['scripts/calibrate_cli.py','--start',start,'--physics',physics,'--objective','zonefit',
              '--downsample','32','--saved-numerics','--evals',str(evals),'--popsize','8',
              '--sigma',str(sigma),'--seed','2210','--workers','2','--out',destination,
              '--fix','{"retrograde":0.75}','--race','0']
        if seeds:args+=['--seeds',seeds]
        if state.exists():args+=['--resume']
        run(args,folder+'.log')
    return destination/'best_params.json'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--branch',choices=['free','earth'],required=True)
    a=ap.parse_args();OUT.mkdir(exist_ok=True);CAL.mkdir(exist_ok=True)
    status=OUT/(a.branch+'_pipeline_status.json')
    if status.exists() and json.loads(status.read_text()).get('stage') == 'promoted':
        print('Campaign branch is already promoted; see '+str(status), flush=True)
        return
    def save(**fields):status.write_text(json.dumps(dict(branch=a.branch,**fields),indent=2))
    try:
        if a.branch=='free':
            save(stage='waiting_for_broad_refinement')
            wait_for(lambda:count(CAL/'free_fit/state.pkl')>=97,'free fit generation checkpoint 97')
            save(stage='fine_refinement')
            best=calibrate(CAL/'free_fit/best_params.json','free_polish','e3b5',25,'',.003)
            title='Rotclimate Free-Fit Atlas';name='free_fit_next';seeds=''
            note='World and physics fitted to the painted zones, refining the existing reversed-spin basin. Whittaker maps show potential biomes from annual temperature and precipitation.'
        else:
            save(stage='waiting_for_earth_screen')
            wait_for(lambda:(OUT/'screen2/summary.json').exists(),'second complete Earth screen')
            candidates=[]
            for phase in ['screen1','screen2']:
                results=json.loads((OUT/phase/'summary.json').read_text());base=results['base']
                settings=json.loads((OUT/phase/'manifest.json').read_text())['settings']
                for name,row in results.items():
                    if name!='base' and row['status']=='complete' and all(row[k]<base[k] for k in ['training','previous_holdout','midlatitude']):
                        candidates.append((row['all'],phase,name,settings[name]))
            p=Params.from_json(ROOT/'calibration/earth/earth_bg_r29.json')
            chosen=min(candidates) if candidates else None
            if chosen:p=p.replace(**chosen[3])
            reference=CAL/'earth_reference.json';p.to_json(reference)
            selection=dict(reference='r29',accepted=chosen,criterion='strict improvement in every regional group',
                           reused_regions_are_development_evidence=True)
            (OUT/'earth_selection.json').write_text(json.dumps(selection,indent=2))
            world=Params.from_json(ROOT/'calibration/earth/earthfit_world_r16.json')
            fields=asdict(p)
            for k,v in asdict(world).items():
                if k in WORLD_KEYS or k.startswith('beyond_'):fields[k]=v
            start=CAL/'earth_start.json';Params(**fields).to_json(start)
            save(stage='world_calibration',selection=selection)
            best=calibrate(start,'earth_fit','world',49,'1,2,3',.045)
            title='Rotclimate Earth-Fit Atlas';name='earth_fit_next';seeds='1,2,3'
            note='World fitted with the current Earth reference physics held fixed; climate averaged over three layouts of the unknown surroundings. Includes seasonal mountain-temperature corrections and Whittaker potential biomes.'
        save(stage='atlas_build',params=str(best))
        args=['scripts/build_atlas_variant.py','--params',best,'--name',name,'--title',title,
              '--eyebrow','Simulated climate · 25 seasonal steps · Whittaker potential biomes',
              '--note',note,'--downsample','8','--image-scale','2','--workers','2',
              '--checkpoint',OUT/(a.branch+'_atlas_result.pkl')]
        if seeds:args+=['--seeds',seeds]
        run(args,a.branch+'_atlas.log')
        save(stage='built_pending_review',params=str(best),atlas=name)
    except Exception as exc:
        save(stage='failed',error=repr(exc));raise
if __name__=='__main__':main()
