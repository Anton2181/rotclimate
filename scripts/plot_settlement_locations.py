"""Plot the fixed protocol's selected development variant, always seed1, not its best draw."""
import json
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_locations_earth import OUT,sha


def main():
    result=json.loads((OUT/'results.json').read_text())
    variant=result['development_lead']
    if variant is None:raise ValueError('No count-feasible development variant')
    if sha(OUT/'positions.npz')!=result['positions_sha256']:
        raise ValueError('Changed archived candidate locations')
    pools=list(result['pools'])
    positions=dict(np.load(OUT/'positions.npz'))
    fig,axes=plt.subplots(len(pools),3,figsize=(14,5.2*len(pools)),squeeze=False,layout='constrained')
    labels={'han':'Han AD2 · county seats','rome':'Rome AD150 · urban sites'}
    for row,pool in enumerate(pools):
        data=dict(np.load(OUT/(pool+'_inputs.npz')))
        if sha(OUT/(pool+'_inputs.npz'))!=result['pools'][pool]['input_sha256']:
            raise ValueError('Changed Earth input')
        h,w=data['land'].shape;cell=float(data['cell_km']);extent=(0,w*cell,h*cell,0)
        real=data['real'];real=real[data['allowed'].ravel()[real]]
        observed=np.column_stack(np.unravel_index(real,(h,w)))
        points=[observed,positions[pool+'__baseline'],positions[pool+'__'+variant+'__1']]
        base=result['baseline'][pool]
        cand=next(r for r in result['rows'] if r['pool']==pool and r['variant']==variant and r['seed']==1)
        titles=[f"{labels[pool]}\n{len(observed):,} observed centres",
            f"Current greedy placement · {len(points[1]):,} centres\nF1 {base['F1']:.3f} · block rank {base['M1']:.3f} · spacing KS {base['M3']:.3f}",
            f"Development candidate · {len(points[2]):,} centres\nF1 {cand['F1']:.3f} · block rank {cand['M1']:.3f} · spacing KS {cand['M3']:.3f}"]
        background=np.empty((h,w,3));background[:]=[.82,.9,.93]
        background[data['land']]=[.9,.9,.87];background[data['allowed']]=[.97,.96,.9]
        shade=np.log1p(np.maximum(data['density'],0))
        for ax,pp,title,color in zip(axes[row],points,titles,['#743d37','#346d98','#277665']):
            ax.imshow(background,extent=extent,origin='upper')
            ax.imshow(np.ma.masked_where(~data['allowed'],shade),extent=extent,origin='upper',cmap='Greens',alpha=.22,vmin=0,vmax=5)
            ax.scatter((pp[:,1]+.5)*cell,(pp[:,0]+.5)*cell,s=3.5,c=color,lw=0)
            ax.set_title(title,fontsize=10);ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Fixed settlement counts · clustered locations tested on exposed Earth data',fontsize=15)
    fig.supxlabel(f'{variant} · seed1 fixed in advance; selection uses five-seed means where stochastic.\n'
        '9-km grid · proximity F1 can match several observed sites to one proposal · no atlas adoption or independent validation.',fontsize=9)
    path=ROOT/'reports/figures/settlement_locations_20261110.png';fig.savefig(path,dpi=135);plt.close(fig)
    print(path)


if __name__=='__main__':main()
