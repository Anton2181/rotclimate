"""Summarize completed three-fit searches, preserving both score definitions."""
import csv
from dataclasses import asdict
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
from rotclimate.config import Params
from combine_world_physics import WORLD_KEYS
from three_fit_campaign import SPECS


def main():
    output = ROOT/'output/three_fit_20261022'
    calibration = ROOT/'calibration/three_fit_20261022'
    review = {}
    evaluations = {}
    table = []
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, (name, spec) in zip(axes, SPECS.items()):
        rows = [json.loads(line) for line in (calibration/name/'evals.jsonl').read_text().splitlines()]
        evaluations[name] = rows
        assert len(rows) == spec['evals'], (name, len(rows), spec['evals'])
        good = [r for r in rows if not r.get('error') and np.isfinite(r['score'])]
        best = max(good, key=lambda r:r['score'])
        base = rows[0]
        selected = asdict(Params.from_json(calibration/name/'best_params.json'))
        assert json.loads(json.dumps(selected)) == best['params'], name
        initial = asdict(Params.from_json(calibration/(name+'_start.json')))
        # Publication resolution differs from the starting saved parameter set.
        changed = {key:dict(before=initial[key],after=selected[key]) for key in initial
                   if initial[key] != selected[key] and key != 'downsample'}
        if name == 'earth':
            assert all(k in WORLD_KEYS or k.startswith('beyond_') for k in changed), changed
        comparison = dict(objective=spec['objective'], evaluations=len(rows),
                          successful=len(good), failures=len(rows)-len(good),
                          baseline_score=base['score'], selected_score=best['score'],
                          improvement=best['score']-base['score'], selected_evaluation=best['eval'],
                          baseline_exact_zone_agreement=base['accuracy'],
                          selected_exact_zone_agreement=best['accuracy'],
                          baseline_mediterranean=base['mediterranean'],
                          selected_mediterranean=best['mediterranean'], changed_parameters=changed)
        if name == 'whittaker':
            comparison['baseline_biomes'] = base['whittaker']
            comparison['selected_biomes'] = best['whittaker']
            comparison['baseline_zonefit'] = base['zonefit_score']
            comparison['selected_zonefit'] = best['zonefit_score']
        review[name] = comparison
        table.append({k:v for k,v in comparison.items() if not isinstance(v,dict)} | dict(branch=name))
        xs = [r['eval'] for r in good]; ys = [r['score'] for r in good]
        ax.scatter(xs,ys,color='#31758c',s=25,label='Candidate')
        ax.plot(xs,np.maximum.accumulate(ys),color='#cf783b',label='Best so far')
        ax.axhline(base['score'],color='#62716c',ls=':',label='Starting fit')
        ax.set(title=name.capitalize()+' fit',xlabel='Candidate evaluation',ylabel=spec['objective']+' objective')
        ax.spines[['top','right']].set_visible(False)
        ax.tick_params(labelsize=9)
    axes[0].legend(fontsize=8)
    fig.suptitle('Bounded local refinements · three surroundings layouts per candidate',fontsize=14)
    fig.text(.5,.012,'Downsample 32 · seed 231022 · different objectives have different scales',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95))
    fig.savefig(output/'search_comparison.png',dpi=160,facecolor='white');plt.close(fig)
    (output/'search_review.json').write_text(json.dumps(review,indent=2)+'\n')
    (output/'search_evaluations.json').write_text(json.dumps(evaluations,indent=1)+'\n')
    keys = list(dict.fromkeys(key for row in table for key in row))
    with (output/'search_review.csv').open('w') as file:
        writer=csv.DictWriter(file,fieldnames=keys,lineterminator='\n');writer.writeheader();writer.writerows(table)
    print(json.dumps({name:{k:v for k,v in item.items() if k in
                           ['baseline_score','selected_score','improvement','failures','selected_evaluation']}
                      for name,item in review.items()},indent=2))


if __name__ == '__main__':
    main()
