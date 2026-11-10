"""Maps and location/spacing tradeoffs for the frozen adaptive experiment."""
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_intensity_earth import OUT,ORIGINAL
from settlement_locations_earth import sha


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    if review['source_result_sha256']!=sha(OUT/'results.json') or review['status']!='passed':
        raise ValueError('Missing current proposal review')
    if sha(OUT/'positions.npz')!=r['positions_sha256']:raise ValueError('Changed positions')
    positions=dict(np.load(OUT/'positions.npz'));old=dict(np.load(ORIGINAL/'positions.npz'))
    lead=r['development_lead'];ref='greedy_18km_old_cores_L800'
    reference=next(q for q in r['references'] if q['variant']==ref)
    fig,axes=plt.subplots(2,3,figsize=(14,10.4),layout='constrained')
    for row,(pool,label) in enumerate([('han','Han AD2'),('rome','Rome AD150')]):
        x=dict(np.load(ROOT/r['inputs'][pool]['path']));h,w=x['land'].shape;cell=float(x['cell_km'])
        real=x['real'];real=real[x['allowed'].ravel()[real]]
        actual=np.column_stack(np.unravel_index(real,(h,w)))
        pp=[actual,old[pool+'__'+ref+'__1'],positions[pool+'__'+lead+'__1']]
        cr=next(q for q in r['rows'] if q['pool']==pool and q['variant']==lead and q['seed']==1)
        fr=reference['pools'][pool]
        titles=[f'{label} · observed centres\n{len(actual):,} recorded sites',
            f"Fixed18km history reference · {len(pp[1]):,}\nUnique F1 {fr['unique_F1']:.3f} · spacing KS {fr['M3']:.3f}",
            f"Adaptive spacing · {len(pp[2]):,}\nUnique F1 {cr['unique_F1']:.3f} · spacing KS {cr['M3']:.3f}"]
        base=np.empty((h,w,3));base[:]=[.82,.9,.93];base[x['land']]=[.9,.9,.87];base[x['allowed']]=[.97,.96,.90]
        extent=(0,w*cell,h*cell,0)
        for ax,p,title,color in zip(axes[row],pp,titles,['#743d37','#346d98','#277665']):
            ax.imshow(base,extent=extent,origin='upper')
            ax.scatter((p[:,1]+.5)*cell,(p[:,0]+.5)*cell,s=3.5,c=color,lw=0)
            ax.set_title(title,fontsize=10);ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Centres can be closer where target settlement intensity is higher',fontsize=15)
    fig.supxlabel('Exposed Earth development pools · count and population held fixed · seed1 always shown\n'
        'Adaptive family: prior scale450km, competition coefficient0.35 · not a village, population-growth or control validation.',fontsize=9)
    figures=ROOT/'reports/figures';fig.savefig(figures/'settlement_intensity_maps_20261110.png',dpi=135);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10.5,6),layout='constrained')
    for family,rows,color,marker in [('adaptive',r['ranking'],'#29816a','o'),('fixed',r['references'],'#a57b42','s')]:
        rows=[q for q in rows if q['feasible'] and q['family']==family]
        ax.scatter([q['mean']['M3'] for q in rows],[q['mean']['unique_F1'] for q in rows],
            s=45,marker=marker,c=color,alpha=.6,label=family.capitalize()+' candidates')
    highlighted=[('production_baseline','Production baseline','#333','X'),
                 ('greedy_18km_old_cores_L800','Fixed18km · best fixed under new Q','#346d98','D'),
                 (lead,'Adaptive development lead','#165b48','*')]
    for key,label,color,marker in highlighted:
        q=next(t for t in r['references']+r['ranking'] if t['variant']==key)
        ax.scatter(q['mean']['M3'],q['mean']['unique_F1'],s=150 if marker!='*' else 260,
            marker=marker,c=color,edgecolor='white',linewidth=.7,zorder=5,label=label)
    ax.set(xlabel='Nearest-neighbour spacing KS · lower is better',ylabel='Unique-site F1 within25km · higher is better',
           title='Location versus spacing: both alternatives remain visible')
    ax.grid(alpha=.2);ax.legend(fontsize=9,loc='lower left')
    fig.supxlabel('Equal means over Han/Rome; stochastic variants average five seeds. This is development selection, not transfer evidence.\n'
        'New lead Q0.621 vs best fixed Q0.570 at declared60% location weight; no production adoption.',fontsize=9)
    fig.savefig(figures/'settlement_intensity_tradeoffs_20261110.png',dpi=150);plt.close(fig)
    print('Saved adaptive Earth maps and location/spacing tradeoff plot.')


if __name__=='__main__':main()
