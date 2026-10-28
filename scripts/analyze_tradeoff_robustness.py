"""Post-search score sensitivity, never a new selection rule or validation set."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_benchmark_protocol import file_hash,write_json


def analyze(out):
    p=json.loads((out/'protocol.json').read_text())['plan'];review=json.loads((out/'review.json').read_text());progress=json.loads((out/'progress.json').read_text())
    if not review['complete']:raise ValueError('Need completed search')
    valid={n:s for n,s in review['scores'].items() if s.get('physical_admissible')}
    if not valid:raise ValueError('No admissible candidate for sensitivity analysis')
    cases={r['region']:r for r in progress['records'] if r['name']=='reference'}
    native_indices={};ocean_indices={};ni=oi=0
    for region in p['regions']:
        count=3*(int(region in p['circulation_regions'])+int(region in p['extra_circulation_regions']))
        native_indices[region]=list(range(ni,ni+count));ni+=count
        ocean_indices[region]=oi if cases[region]['sst'] is not None else None
        if cases[region]['sst'] is not None:oi+=1
    scenarios={}
    for rw in [0.,.25,.5]:
        for nw in [0.,.05,.1]:
            values={n:s['mean_combined_ratio']+rw*s['regional_squared_regret']+nw*s['native_squared_regret']+.05*s['ocean_squared_regret'] for n,s in valid.items()}
            scenarios[f'regional={rw:g},native={nw:g}']=dict(scope='Alternative objective weights; original choices and results unchanged',values=values)
    for i,region in enumerate(p['regions']):
        values={}
        for n,s in valid.items():
            climate=np.delete(np.asarray(s['regional_ratios']),i)
            native=np.delete(np.asarray(s['native_normalized_regressions']),native_indices[region])
            ocean=np.asarray(s['ocean_normalized_regressions'])
            if ocean_indices[region] is not None:ocean=np.delete(ocean,ocean_indices[region])
            regional=float(np.maximum(climate-p['objective']['regional_free_ratio'],0.)@np.maximum(climate-p['objective']['regional_free_ratio'],0.)/len(climate))
            native_regret=float(np.mean(np.maximum(native,0.)**2)) if native.size else 0.
            ocean_regret=float(np.mean(np.maximum(ocean,0.)**2)) if ocean.size else 0.
            values[n]=float(climate.mean()+p['objective']['regional_weight']*regional+p['objective']['native_weight']*native_regret+p['objective']['ocean_weight']*ocean_regret)
        scenarios['omit '+region]=dict(scope='Remove this reused development region from objective aggregation; not out-of-sample validation',values=values)
    for s in scenarios.values():
        s['ranking']=sorted(s['values'],key=lambda n:(s['values'][n],n));s['winner']=s['ranking'][0]
    top=sorted(valid,key=lambda n:(valid[n]['objective'],n))[:min(12,len(valid))]
    matrix=np.array([[scenarios[k]['ranking'].index(n)+1 for n in top] for k in scenarios])
    fig,ax=plt.subplots(figsize=(12,8),constrained_layout=True)
    image=ax.imshow(matrix,cmap='viridis_r',vmin=1,vmax=max(2,len(valid)),aspect='auto')
    for i,j in np.ndindex(matrix.shape):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=8,color='white' if matrix[i,j]<len(valid)*.45 else 'black')
    ax.set(xticks=range(len(top)),xticklabels=top,yticks=range(len(scenarios)),yticklabels=list(scenarios),title='How stable is the ranking? · original top candidates under alternative aggregation')
    ax.tick_params(axis='x',rotation=45);fig.colorbar(image,ax=ax,label='Rank among all admissible candidates · 1 is best')
    fig.supxlabel('Post-search sensitivity only. No parameter is rerun, no original rule changed, and no omitted region becomes a new validation set.\nWeight sensitivity and geographic sensitivity do not establish a global optimum or observational confidence interval.',fontsize=9)
    image_path=out/'ranking_sensitivity.png';fig.savefig(image_path,dpi=145);plt.close(fig)
    result=dict(status='passed',scope='Post-search sensitivity diagnostics; not prospective validation or a revised selection rule',
        original_best=top[0],scenarios=scenarios,protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        script_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image_path),new_earth_integrations=0,physics_or_atlas_adoption=False)
    write_json(out/'ranking_sensitivity.json',result)
    print(json.dumps(dict(original_best=top[0],different_winners=sorted({v['winner'] for v in scenarios.values()})),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);analyze(ap.parse_args().out.resolve())
