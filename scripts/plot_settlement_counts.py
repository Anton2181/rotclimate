"""Show supported-domain fits and missing-input geography without hiding failures."""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.population_coverage import population_coverage


def main():
    out=ROOT/'output/settlement_counts_20261111';r=json.loads((out/'results.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(12,5.7),layout='constrained');fig.patch.set_facecolor('#f3f4ed')
    for pool,label,color in [('han','Han administrative seats','#395e91'),('rome','Roman urban catalogue','#2d8277')]:
        rows=sorted([a for a in r['rows'] if a['pool']==pool and a['domain']=='covered_only' and a['nominal_km']==100 and a['target']=='record_count'
                    and a.get('scale_scope')=='role_specific'],key=lambda a:a['beta'])
        axes[0].plot([a['beta'] for a in rows],[a['total']['deviance_per_source_record'] for a in rows],marker='o',label=label,color=color)
    axes[0].axvline(.7,ls=':',color='#7d6b50',label='Old seat exponent 0.7')
    axes[0].set(xlabel='Population exponent β in count ∝ land area × density^β',ylabel='Held-quadrant Poisson deviance per source record',
        title='Supported domain: modest count-fit improvement',xticks=[0,.5,.7,1,1.5]);axes[0].legend(fontsize=8);axes[0].grid(alpha=.15)
    s=r['source_support']['roman']['AD150'];counts=[s['area_states']['missing_area_record'],s['area_states']['exact20_or30ha_candidate'],s['positive_nondefault_value_candidates']]
    axes[1].barh(['Missing area record','Exact 20 / 30 ha candidate','Other positive numeric area'],counts,color=['#b07b56','#d5aa50','#2d8277'])
    for i,n in enumerate(counts):axes[1].text(n+12,i,str(n),va='center')
    axes[1].set(xlim=(0,max(counts)*1.18),xlabel='Roman catalogue records in operational AD150 cohort',
        title='Urban size evidence needs explicit observation units')
    axes[1].invert_yaxis();axes[1].grid(axis='x',alpha=.15)
    fig.suptitle('Count budgets and resident sizes are separate calibration problems',fontsize=14)
    fig.supxlabel('Four geographic training/held quadrants; exposed development data, not an independent validation. Restricted domain retains 1,267 Han / 1,115 Roman records.\nArea is not residents. Exact 20/30 ha is a conservative value flag; other numeric areas are not automatically certified measured or contemporaneous.',fontsize=9)
    figures=ROOT/'reports/figures';fig.savefig(figures/'settlement_counts_20261111.png',dpi=150);plt.close(fig)
    with np.load(ROOT/'output/settlement_locations_20261110/han_inputs.npz') as z:x=dict(z)
    with np.load(ROOT/'output/land_people/earth/earth.npz') as z:lat,lon=z['lat'],z['lon']
    covered=population_coverage(x['lat'],x['lon'],lat,lon);land=x['allowed']&x['land']
    field=np.where(land,np.where(covered,1,2),np.nan)
    cell=float(x['cell_km']);h,w=land.shape
    fig,ax=plt.subplots(figsize=(9.5,8),layout='constrained');fig.patch.set_facecolor('#f3f4ed')
    ax.imshow(field,extent=[-w*cell/2,w*cell/2,-h*cell/2,h*cell/2],cmap=ListedColormap(['#d2e2cd','#d59c47']),vmin=1,vmax=2,interpolation='nearest')
    with np.load(out/'blocks.npz') as z:
        a={k.removeprefix('full_frozen_han_100km__'):z[k] for k in z.files if k.startswith('full_frozen_han_100km__')}
    zero=(a['population']==0)&(a['record_count']>0)
    ax.scatter(a['centre_x_km'][zero],a['centre_y_km'][zero],s=100,marker='s',facecolors='none',edgecolors='#a22c39',linewidths=1.5)
    for xx,yy,n in zip(a['centre_x_km'][zero],a['centre_y_km'][zero],a['record_count'][zero]):ax.annotate(str(int(n)),(xx,yy),xytext=(-14,4),textcoords='offset points',color='#92192c')
    ax.set(title='Missing population inputs in the frozen Han benchmark',xlabel='East / west of model-window centre (km)',ylabel='North / south of model-window centre (km)')
    ax.legend(handles=[Patch(facecolor='#d2e2cd',label='Allowed land with population input'),Patch(facecolor='#d59c47',label='Missing population input · beyond 125°E'),
        Patch(facecolor='none',edgecolor='#a22c39',label='99 km block: positive source count, zero stored population')],loc='lower right',fontsize=8)
    fig.supxlabel('1,586 allowed land cells / 128,466 km² and 13 source cells lack population input. Six wholly unsupported blocks contain 11 records.\nLabels are aggregated record counts, not site locations. Frozen inputs and all exclusions remain visible; missing coverage is not an ecological zero.',fontsize=9)
    fig.savefig(figures/'settlement_population_coverage_20261111.png',dpi=150);plt.close(fig)
    print('Wrote count/size-support comparison and missing population-coverage map.')


if __name__=='__main__':main()
