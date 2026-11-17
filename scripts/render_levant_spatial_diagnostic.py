"""Plot the native-resolution limits and conditional spatial scores."""
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
from pyproj import CRS,Transformer

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from qualify_roman_regional_sources import sha,read,write
OUT=ROOT/'output/levant_spatial_diagnostic_20261117'


def main():
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert review['status']=='passed_independent_projection_support_counts_probabilities_and_conditional_scores'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_levant_spatial_diagnostic.py')
    with np.load(OUT/'model_support.npz') as z:d=dict(z)
    np.testing.assert_array_equal(d['legacy_weight'],d['refreshed_weight'])
    with (OUT/'scores.csv').open() as f:scores=list(csv.DictReader(f))
    names=r['source_names'];gain=np.array([float(next(s for s in scores if s['reference']==name and s['model']=='refreshed')['mean_log_gain']) for name in names])
    auc=np.array([float(next(s for s in scores if s['reference']==name and s['model']=='refreshed')['presence_background_auc']) for name in names])
    # These are observation totals by model cell, not allocated populations.
    cells={}
    for rr,cc,count in zip(d['row'],d['column'],d['count']):cells[int(rr),int(cc)]=cells.get((int(rr),int(cc)),0)+int(count)
    projection=CRS.from_proj4('+proj=aeqd +lat_0=40 +lon_0=17 +R=6371000 +units=m +no_defs')
    transform=Transformer.from_crs(projection,4326,always_xy=True)
    fig,(ax,bars,ranking)=plt.subplots(1,3,figsize=(19,7),gridspec_kw={'width_ratios':[1.,1.15,.8]})
    mx=[];my=[]
    for (rr,cc),count in cells.items():
        left=(cc-300)*9000;top=(200-rr)*9000
        xy=np.array([transform.transform(x,y) for x,y in [(left,top),(left+9000,top),(left+9000,top-9000),(left,top-9000)]])
        ax.add_patch(Polygon(xy,facecolor='#e6ecea',edgecolor='#8c9e9b',lw=.6))
        lon,lat=transform.transform(left+4500,top-4500);mx.append(lon);my.append(lat)
        if count>0:ax.scatter([lon],[lat],s=8+4*count,c='#244e61',alpha=.7,linewidths=.5,edgecolors='white')
    ax.set(xlim=(min(mx)-.1,max(mx)+.1),ylim=(min(my)-.09,max(my)+.09),xlabel='Longitude (°E)',ylabel='Latitude (°N)',title='565 records occupy a coarse 9 km grid\n55 distinct support cells')
    ax.set_aspect(1/np.cos(np.deg2rad(32)));ax.grid(alpha=.12)
    pos=np.arange(8);colors=np.where(gain<0,'#ad614d','#3d7c96')
    bars.barh(pos,gain,color=colors);bars.axvline(0,color='#555',lw=1)
    bars.set(yticks=pos,yticklabels=names,xlabel='Mean conditional log-likelihood gain (nats / site)',title='Fixed population-pattern fields vs uniform\nLegacy and refreshed fields coincide here');bars.invert_yaxis();bars.grid(axis='x',alpha=.15)
    ranking.barh(pos,auc,color='#668b98');ranking.axvline(.5,color='#555',lw=1,ls='--')
    ranking.set(yticks=pos,yticklabels=['']*8,xlim=(0,1),xlabel='Area-weighted presence/background AUC',title='Conditional ranking\nUniform baseline = 0.5');ranking.invert_yaxis();ranking.grid(axis='x',alpha=.15)
    fig.subplots_adjust(left=.045,right=.985,top=.78,bottom=.22,wspace=.65)
    fig.suptitle('Roman-period spatial diagnostic · AD70–324 habitation proxy around AD200',fontsize=17,y=.97)
    fig.text(.5,.90,'Equal-source mean log gain −0.0395; mean AUC 0.477. Both fixed fields perform slightly worse than uniform under this observation model.',ha='center',fontsize=11)
    fig.text(.5,.09,'Within-source uniform observation opportunity and a population-to-site-intensity link are assumptions. Survey envelopes are not certified walked land.\n'
             'Bubbles count recorded site IDs assigned to model cells. No census population, town counts, independent validation or calibrated confidence.',ha='center',fontsize=10)
    fig.text(.5,.025,'Observations: Titolo & Palmisano2025, doi10.5334/joad.158, CC-BY4.0; pinned source a3537c67. No refit or atlas change.',ha='center',fontsize=9)
    fig.savefig(OUT/'spatial_comparison.png',dpi=170);plt.close(fig)
    write(OUT/'presentation.json',dict(status='rendered_reviewed_conditional_spatial_diagnostic',renderer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),figure_sha256=sha(OUT/'spatial_comparison.png'),
        source_names=names,plotted_refreshed_mean_log_gain=gain.tolist(),plotted_refreshed_auc=auc.tolist(),
        native_cell_observation_counts=[dict(row=rr,column=cc,site_count=n) for (rr,cc),n in sorted(cells.items())],
        legacy_refreshed_weights_identical=True,atlas_changed=False))
    print('Rendered native-grid limitations and all-eight-source score comparison',flush=True)


if __name__=='__main__':main()
