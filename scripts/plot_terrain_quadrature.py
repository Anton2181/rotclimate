"""Plot the verified paired terrain-closure results; never run the model."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    out=ROOT/'output/terrain_quadrature_20261025';review=json.loads((out/'review.json').read_text())
    fig,axes=plt.subplots(2,4,figsize=(14,6),constrained_layout=True)
    for i,km in enumerate([56,28]):
        folder=out/'cases'/f'north_india_{km}km'
        with np.load(folder/'reference.npz') as z:a={k:z[k] for k in z.files}
        with np.load(folder/'terrain_quadrature.npz') as z:b={k:z[k] for k in z.files}
        assert np.array_equal(a['i'],b['i']) and np.array_equal(a['j'],b['j'])
        yy=a['i']-a['i'].min();xx=a['j']-a['j'].min();shape=(yy.max()+1,xx.max()+1)
        observed=a['Po'].sum(0);reference=a['Ps'].sum(0);trial=b['Ps'].sum(0)
        change=np.abs(trial-observed)-np.abs(reference-observed)
        for j,(values,title) in enumerate([(observed,'Observed'),(reference,'r38 control'),(trial,'Terrain replacement'),(change,'Change in absolute error')]):
            grid=np.full(shape,np.nan);grid[yy,xx]=values;ax=axes[i,j]
            ax.set_facecolor('#d6e3f0');ax.set_xticks([]);ax.set_yticks([])
            if j==3:im=ax.imshow(grid,cmap='RdBu_r',vmin=-400,vmax=400)
            else:rain=ax.imshow(grid,cmap='YlGnBu',vmin=0,vmax=2000)
            ax.set_title(f'{km} km · {title}',fontsize=10)
    fig.colorbar(rain,ax=list(axes[:,:3].flat),shrink=.6,label='Annual rain (mm; clipped at 2,000)',location='bottom')
    fig.colorbar(im,ax=list(axes[:,3]),shrink=.6,label='mm/year: blue improves; red worsens',location='bottom')
    fig.suptitle('North India: a consistent terrain closure alone does not repair the rainfall pattern',fontsize=14)
    fig.supxlabel('Same r38 parameters and common 14 km DEM; replaced relief proxy disabled. All controls reproduce and all solves converge. Not adopted.',fontsize=9)
    fig.savefig(out/'north_india_rainfall.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,key,label in zip(axes,['regions','P_ratio'],['Combined temperature/rain score by region','Mean rainfall-loss ratio']):
        for i,km in enumerate([56,28]):
            r=review['scores'][str(km)]
            if key=='regions':
                names=['north_india','japan','pacific_nw','iberia'];values=[r[key][n] for n in names]
                ax.bar(np.arange(4)+(i-.5)*.35,values,.35,label=f'{km} km')
                ax.set_xticks(range(4),['North India','Japan','Pacific NW','Iberia'],rotation=20)
            else:ax.bar(i,r[key],.5);ax.set_xticks([0,1],['56 km','28 km'])
        ax.axhline(1,color='#333333',ls='--',lw=1);ax.set_ylim(.95,1.055);ax.set_title(label,fontsize=11)
    axes[0].legend(frameon=False);fig.supxlabel('Below 1 improves. Development pilot only; original r38 physics remains adopted.',fontsize=9)
    fig.savefig(out/'regional_scores.png',dpi=140);plt.close(fig)
    print('Saved terrain-pilot rainfall and regional-score figures.')


if __name__=='__main__':main()
