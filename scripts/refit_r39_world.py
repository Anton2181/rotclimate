"""Fit world geometry while qualified r39 physics and the planet remain fixed."""
from dataclasses import asdict
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json
from rotclimate import calibrate as C


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--resume',action='store_true');a=ap.parse_args()
    folder=ROOT/'calibration/map_world_r39';plan_path=folder/'plan.json';plan=json.loads(plan_path.read_text())
    base=load_params(ROOT/plan['start']).replace(downsample=plan['downsample'])
    old=load_params(ROOT/plan['old_atlas']/'params.json').replace(downsample=plan['downsample'])
    physics=load_params(ROOT/plan['physics'])
    allowed={k for k in C.WORLD_GENES if not k.startswith('tier')}|{'tier_tops','downsample'}
    for key,value in asdict(base).items():
        if key not in allowed and value!=getattr(physics,key):raise ValueError('Shared physics changed: '+key)
    C._set_space(C.SPACE_WORLD);encoded=C.encode(base)
    fixed={name:float(encoded[C.NAMES.index(name)]) for name in ['tilt','retrograde']}
    paths=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),plan_path,folder/'start.json',ROOT/plan['physics'],ROOT/plan['old_atlas']/'params.json']
    freeze(folder/'protocol.json',dict(plan=plan,start=asdict(base),fixed_genes=fixed,
        sources={str(p.relative_to(ROOT)):file_hash(p) for p in paths}))
    control=folder/'coarse_old_control.json'
    if not control.exists():
        print('Evaluating matched old-world coarse control',flush=True)
        result=C.evaluate_params(old,'zonefit',seeds=plan['layouts'],ensemble_objective='climate')
        write_json(control,result);print('Old-world control:',result['score'],flush=True)
    best=C.calibrate(folder/'world',plan['evaluations'],base,sigma0=plan['sigma'],popsize=plan['popsize'],
        workers=plan['workers'],seed=plan['seed'],fixed=fixed,mode='zonefit',seeds=plan['layouts'],
        race=0.,stds=plan['stds'],resume=a.resume,ensemble_objective='climate')
    candidate=load_params(folder/'world/best_params.json')
    for key in ['tilt','retrograde','planet_radius','year_days','eccentricity','perihelion_after_solstice','solar_flux','greenhouse_wm2','map_width_mi','map_height_mi']:
        if not np.isclose(getattr(candidate,key),getattr(base,key),rtol=0,atol=1e-10):raise ValueError('Locked planet changed: '+key)
    for key,value in asdict(candidate).items():
        if key not in allowed and value!=getattr(base,key):raise ValueError('Fitted shared physics: '+key)
    write_json(folder/'best_result.json',best)
    print('World fit complete; native-resolution and layout-transfer checks remain.',flush=True)


if __name__=='__main__':main()
