"""Plot all-seed transfer comparisons and model-only opportunity geography."""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_vidarbha_transfer import DEFAULT_OUT, METHODS, SEEDS


def main():
    result=json.loads((DEFAULT_OUT/'results.json').read_text());methods=json.loads(METHODS.read_text())
    rows=[r for r in result['grids']['3']['metrics'] if r['cohort']=='EH-S_yes' and r['offset']=='central']
    fig,axes=plt.subplots(1,2,figsize=(13,5.8),layout='constrained');fig.patch.set_facecolor('#f3f4ed')
    colors=['#9b7655','#365f92','#2a8177'];names=['environment','fixed_L800','lead_L450']
    for i,(name,label) in enumerate(zip(names,['Environment only','Fixed L800 opportunity','Lead L450 opportunity'])):
        axes[0].bar(np.arange(3)+(i-1)*.24,[r['opportunity'][name]['mean_percentile'] for r in rows],.24,label=label,color=colors[i])
    axes[0].axhline(.5,color='#555',ls=':',lw=1)
    axes[0].set(xticks=range(3),xticklabels=[r['zone']+'\nn='+str(r['distinct_cells']) for r in rows],ylim=(0,1),
                ylabel='Mean known-site percentile within each nominal survey frame',title='Opportunity scores weakly distinguish known sites')
    axes[0].legend(fontsize=8,loc='upper left')
    radii=[5,10,25]
    for name,label,color in [('production_seed1','Current production','#9b7655'),('fixed_L800_seed1','Fixed-spacing control','#365f92')]:
        axes[1].plot(radii,[np.mean([r['captures'][name][str(d)] for r in rows]) for d in radii],marker='o',label=label,color=color)
    for name,label,color in [('lead_L450','Frozen adaptive lead','#2a8177'),('ablation_nohistory','Adaptive, no history (ablation)','#986d9e')]:
        values=np.array([[np.mean([r['captures'][f'{name}_seed{s}'][str(d)] for r in rows]) for d in radii] for s in SEEDS])
        axes[1].plot(radii,values.mean(0),marker='o',label=label,color=color)
        axes[1].fill_between(radii,values.min(0),values.max(0),color=color,alpha=.12)
    axes[1].set(ylim=(0,1),xticks=radii,xlabel='Distance from a generated centre (km)',ylabel='Known-site capture · equal survey-frame weights',
                title='Frozen lead fails the declared 10 km capture margin')
    axes[1].legend(fontsize=8,loc='upper left')
    for ax in axes:ax.grid(axis='y',alpha=.15)
    fig.suptitle('Primary Vidarbha transfer · 3 km grid · recorded Satavahana phase',fontsize=15)
    fig.supxlabel('53 distinct cell–frame units from 74 included records; 13 of all 134 settlement records lie outside their assigned nominal frame.\nShading is the full range of five fixed seeds, not a confidence interval. Partial targeted coverage: unrecorded land is not absence.',fontsize=9)
    figures=ROOT/'reports/figures';figures.mkdir(exist_ok=True)
    fig.savefig(figures/'settlement_vidarbha_transfer_20261111.png',dpi=150);plt.close(fig)
    with np.load(DEFAULT_OUT/'inputs_3km.npz') as z:x=dict(z)
    with np.load(DEFAULT_OUT/'model_3km.npz') as z:m=dict(z)
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained');fig.patch.set_facecolor('#f3f4ed')
    for ax,name,title in zip(axes,['fixed_L800','lead_L450'],['Fixed-spacing control · L800','Frozen adaptive lead · L450']):
        mass=m[name];p=np.where(x['land']&(mass>0),mass*10000.,np.nan)
        image=ax.pcolormesh(x['lon'],x['lat'],p,cmap='YlGnBu',norm=LogNorm(vmin=.005,vmax=20.),shading='nearest',rasterized=True)
        towns=m['towns_'+('fixed_L800_seed1' if name=='fixed_L800' else 'lead_L450_seed1')]
        ax.scatter(x['lon'][towns[:,0],towns[:,1]],x['lat'][towns[:,0],towns[:,1]],s=2,c='#3c2330',alpha=.65)
        for zone,f in methods['frames'].items():
            ax.scatter(f['longitude'],f['latitude'],s=65,facecolors='none',edgecolors='#b7353b',linewidths=1.5)
            ax.annotate(zone,(f['longitude'],f['latitude']),xytext=(-36,14 if zone=='Mandhal' else -15),textcoords='offset points',fontsize=8,color='#8a1a22')
        ax.set(title=title,xlabel='Longitude',ylabel='Latitude',aspect=1/np.cos(np.radians(20.8)))
    fig.colorbar(image,ax=axes,label='Relative opportunity mass per 10,000 km² · log scale',shrink=.75)
    fig.suptitle('Frozen model comparison in central India · 419 generated centres per model',fontsize=14)
    fig.supxlabel('Dots are generated centres (seed 1); red rings mark published survey-frame centres. No archaeological site coordinates shown.\nOpportunity mass is not an exact inclusion probability, population density, or a fitted count. Core prior shifts mass northwest.',fontsize=9)
    fig.savefig(figures/'settlement_vidarbha_geography_20261111.png',dpi=150);plt.close(fig)
    print('Wrote transfer comparison and model-only regional map.')


if __name__=='__main__':main()
