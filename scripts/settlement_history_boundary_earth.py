"""Declared boundary extension using the unchanged adaptive producer/scorer."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_intensity_earth as experiment
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/settlement_history_boundary_20261111/plan.json'
OUT=ROOT/'output/settlement_history_boundary_20261111'
PRIOR=ROOT/'output/settlement_intensity_20261110'


def main():
    old=json.loads((PRIOR/'results.json').read_text())
    for path,digest in old['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen adaptive source: '+path)
    if sha(PRIOR/'positions.npz')!=old['positions_sha256']:raise ValueError('Changed prior positions')
    experiment.PLAN=PLAN
    experiment.run(OUT)
    result=json.loads((OUT/'results.json').read_text())
    previous={(r['pool'],r['variant'],r['seed']):r for r in old['rows']}
    controls=0
    with np.load(PRIOR/'positions.npz') as before,np.load(OUT/'positions.npz') as after:
        for row in result['rows']:
            if row['scale_km']!=450:continue
            key=(row['pool'],row['variant'],row['seed'])
            if row!=previous[key]:raise ValueError('450km control metrics changed')
            name='__'.join(map(str,key))
            if not np.array_equal(before[name],after[name]):raise ValueError('450km control sites changed')
            controls+=1
    if controls!=20:raise ValueError('Incomplete overlap controls')
    combined={r['variant']:r for r in old['ranking']+result['references']+result['ranking']}
    available=[r for r in combined.values() if r['feasible']]
    ordered=sorted(available,key=lambda r:(-r['Q'],r['variant']))
    def vector(row):return np.array([row['mean']['unique_F1'],row['mean']['M1'],-row['mean']['M3']])
    frontier=[r['variant'] for r in ordered if not any(np.all(vector(o)>=vector(r)) and np.any(vector(o)>vector(r)) for o in ordered)]
    sensitivity={}
    for weight in [.4,.6,.8]:
        lead=max(available,key=lambda r:experiment.quality(r['mean'],weight))
        sensitivity[str(weight)]=dict(variant=lead['variant'],Q=experiment.quality(lead['mean'],weight))
    result.update(driver_sha256=sha(Path(__file__)),prior_adaptive_results_sha256=sha(PRIOR/'results.json'),
        prior_adaptive_positions_sha256=sha(PRIOR/'positions.npz'),overlap_controls_exact=controls,
        combined_ranking=ordered,combined_pareto_frontier=frontier,combined_weight_sensitivity=sensitivity,
        prior_adaptive_lead=old['development_lead'],combined_development_lead=ordered[0]['variant'],
        Q_gain_over_prior_adaptive=ordered[0]['Q']-old['ranking'][0]['Q'])
    write(OUT/'results.json',result)
    print('Combined lead',ordered[0]['variant'],'Q',ordered[0]['Q'],'gain',result['Q_gain_over_prior_adaptive'],flush=True)


if __name__=='__main__':main()
