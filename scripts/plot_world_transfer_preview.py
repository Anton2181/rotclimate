"""Compare saved world climates; no release or new model run."""
from pathlib import Path
import argparse
import hashlib
import json
import pickle
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from rotclimate.model import ensemble_mean
from rotclimate.score import evaluate,objective
from rotclimate import biomes


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native',action='store_true',help='compare the first native finalist with the actual published climate')
    args=ap.parse_args()
    folder=ROOT/'output/r39_world_transfer';selection=json.loads((folder/'native_selection.json').read_text())
    index=selection['selected'][0]
    old_paths=([ROOT/'output/atlas_r38/earth_publication.pkl'] if args.native else
               [ROOT/f'output/earthlike_geography_20261025/checkpoints/control_{s}.pkl' for s in [1,2,3]])
    runs=[]
    for path in old_paths:
        with path.open('rb') as stream:runs.append(pickle.load(stream)['result'])
    old=runs[0] if args.native else ensemble_mean(runs)
    candidate_path=folder/f'{"native" if args.native else "screen"}_{index:03d}.pkl'
    with candidate_path.open('rb') as stream:trial=pickle.load(stream)['result']
    results=[old,trial];evaluations=[evaluate(r) for r in results]
    if not all(r.numerics.get('all_checks_passed') for r in results):raise ValueError('Unverified climate')
    reference=json.loads((ROOT/('atlases/earth_fit/summary.json' if args.native else
                              'output/earthlike_geography_20261025/control.json')).read_text())
    if abs(objective(evaluations[0],'zonefit')-reference['zonefit'])>1e-12:raise ValueError('Archived control does not reproduce')
    progress=json.loads((folder/'progress.json').read_text())
    record=(next(r for r in progress['native'] if r['name']==f'native_{index:03d}') if args.native else
            progress['intermediate'][str(index)])
    if abs(objective(evaluations[1],'zonefit')-record['metrics']['zonefit'])>1e-12:raise ValueError('Screen does not reproduce')
    if abs(evaluations[1]['accuracy']-record['metrics']['accuracy'])>1e-12:raise ValueError('Accuracy does not reproduce')
    fig,axes=plt.subplots(2,2,figsize=(13,7),constrained_layout=True)
    for column,(r,ev,label) in enumerate(zip(results,evaluations,['Published r38 geometry',f'r39 candidate {index}'])):
        g=r.grid;sl=g.map_slice();ix=ev['indices'];land=g.land[sl]
        cls=biomes.classify(ix['MAT'][sl],ix['MAP'][sl],land)
        axes[0,column].imshow(biomes.rgb_image(cls),interpolation='nearest')
        axes[0,column].set_title(label+f' · zonefit {objective(ev,"zonefit"):.4f}',fontsize=11)
        rain=axes[1,column].imshow(np.where(land,ix['MAP'][sl],np.nan),cmap='YlGnBu',vmin=0,vmax=1800,interpolation='nearest')
        axes[1,column].set_facecolor('#d6e3f0');axes[1,column].set_title('Annual rainfall',fontsize=10)
    for ax in axes.flat:ax.set_xticks([]);ax.set_yticks([])
    fig.colorbar(rain,ax=list(axes[1]),location='bottom',shrink=.65,label='mm/year (clipped at 1,800)')
    fig.legend(handles=[Patch(facecolor=c,label=l) for c,l in zip(biomes.COLORS,biomes.LABELS)],
               loc='outside lower center',ncol=4,fontsize=8,frameon=False)
    if args.native:
        status='Rejected: '+', '.join(record['failures']) if record['failures'] else 'Native pass; layout transfer still required'
        heading=f'Native world comparison — {status}\nSame planet · layouts 1–3 · ds8 cells · potential biomes above, rainfall below'
    else:
        heading='Intermediate world comparison — r39 native checks are pending\nSame planet · layouts 1–3 · ds16 cells · potential biomes above, rainfall below'
    fig.suptitle(heading,fontsize=12)
    stem='native_comparison' if args.native else 'world_preview'
    path=folder/(stem+'.png');fig.savefig(path,dpi=145);plt.close(fig)
    (folder/(stem+'.json')).write_text(json.dumps(dict(candidate=index,screen_only=not args.native,
        failures=record.get('failures'),
        inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*old_paths,candidate_path]},
        image_sha256=hashlib.sha256(path.read_bytes()).hexdigest()),indent=2)+'\n')


if __name__=='__main__':main()
