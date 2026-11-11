"""Show the source-data correction and complete benchmark population coverage."""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm,ListedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.population_coverage import population_coverage


def main():
    out=ROOT/'output/earth_population_extension_20261111';figures=ROOT/'reports/figures'
    with np.load(out/'tile.npz') as z:t=dict(z)
    with np.load(ROOT/'output/land_people/earth/earth.npz') as z:g=dict(z)
    rows=np.flatnonzero((t['lat']>=36)&(t['lat']<=44));cols=np.flatnonzero((t['lon']>=122)&(t['lon']<=124))
    rr=np.rint((g['lat'][0]-t['lat'][rows])*12).astype(int);cc=np.rint((t['lon'][cols]-g['lon'][0])*12).astype(int)
    land=t['land'][np.ix_(rows,cols)]&g['land'][np.ix_(rr,cc)]
    mismatch=land&(np.abs(t['arable'][np.ix_(rows,cols)]-g['arable'][np.ix_(rr,cc)])>1e-4)
    assert mismatch.sum()==5
    fig,axes=plt.subplots(1,2,figsize=(12,5.4),layout='constrained');fig.patch.set_facecolor('#f3f4ed')
    x=np.arange(5)
    for ax,key,title in [(axes[0],'relief','A NoData sea value became a false coastal cliff'),(axes[1],'arable','Fallback farmland was reduced by the false relief')]:
        old=g[key][np.ix_(rr,cc)][mismatch];new=t[key][np.ix_(rows,cols)][mismatch]
        ax.bar(x-.18,old,.36,label='Frozen source pipeline',color='#ae7b55');ax.bar(x+.18,new,.36,label='NoData decoded correctly',color='#2d8177')
        ax.set(xticks=x,xticklabels=[f'C{i+1}' for i in x],title=title);ax.grid(axis='y',alpha=.15)
    axes[0].set(yscale='log',ylabel='Apparent elevation range across 3 × 3 cells (m)',ylim=(1,100000))
    axes[1].set(ylabel='Arable land fraction',ylim=(0,1));axes[0].legend(fontsize=8)
    fig.suptitle('Coastal source correction · all five mismatched overlap cells',fontsize=15)
    fig.supxlabel('Original overlap test remains failed. Exact legacy reproduction and the explicitly corrected reference both pass the original thresholds.\nAnnual temperature, rainfall, PET and aridity match exactly across all 1,370 overlap land cells. No physics coefficient was fitted.',fontsize=9)
    fig.savefig(figures/'population_nodata_correction_20261111.png',dpi=150);plt.close(fig)
    with np.load(ROOT/'output/settlement_locations_20261110/han_inputs.npz') as z:old=dict(z)
    with np.load(out/'han_corrected_inputs.npz') as z:new=dict(z)
    covered=population_coverage(old['lat'],old['lon'],g['lat'],g['lon']);land=old['land']&old['allowed']
    h,w=land.shape;cell=float(old['cell_km']);extent=[-w*cell/2,w*cell/2,-h*cell/2,h*cell/2]
    fig,axes=plt.subplots(1,2,figsize=(13,7),layout='constrained');fig.patch.set_facecolor('#f3f4ed')
    for ax,fields,title in [(axes[0],old,'Old benchmark · missing eastern population input'),(axes[1],new,'Complete population input · same occupation scenario')]:
        ax.imshow(np.where(land,1,np.nan),extent=extent,cmap=ListedColormap(['#e6e4d8']),vmin=0,vmax=1,interpolation='nearest')
        density=np.where(land&(fields['density']>0),fields['density'],np.nan)
        image=ax.imshow(density,extent=extent,cmap='YlGnBu',norm=LogNorm(vmin=.1,vmax=300),interpolation='nearest')
        if fields is old:ax.imshow(np.where(land&~covered,1,np.nan),extent=extent,cmap=ListedColormap(['#d89938']),vmin=0,vmax=1,interpolation='nearest')
        ax.set(title=title,xlabel='East / west of window centre (km)',ylabel='North / south of window centre (km)')
    fig.colorbar(image,ax=axes,label='Model density · fixed occupation scenario (people/km²)',shrink=.75)
    fig.suptitle('Earth settlement benchmark: complete required population coverage',fontsize=15)
    fig.supxlabel('Orange denotes missing input in the old benchmark; neutral land has zero model density. No archaeological site points shown.\nAll 1,586 missing required cells are filled; other input arrays stay fixed. This is a benchmark source repair, not a calibrated fantasy-map release.',fontsize=9)
    fig.savefig(figures/'population_extension_han_20261111.png',dpi=150);plt.close(fig)
    print('Wrote coastal NoData proof and complete-input Han population maps.')


if __name__=='__main__':main()
