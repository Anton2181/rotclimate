"""Source/support map for the period-defined residential-presence contract."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pyproj import Transformer
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from qualify_roman_regional_sources import OUT,sha,read,write,load,geometry


def main():
    review=read(OUT/'review.json');result=read(OUT/'results.json')
    assert review['status']=='passed_independent_period_identity_scalar_polygon_and_format_review'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_roman_regional_sources.py')
    _,records,polygons,_=load();cohort=read(OUT/'cohort.json');names=cohort['source_names'];chosen=set(cohort['selected_fids'])
    byfid={r['fid']:r for r in records};transform=Transformer.from_crs(32636,4326,always_xy=True)
    with np.load(OUT/'observations.npz') as z:obs=dict(z)
    fig,(ax,bar)=plt.subplots(1,2,figsize=(14,8),gridspec_kw={'width_ratios':[1.2,1]})
    cmap=plt.get_cmap('tab10');rendered=[]
    for p in polygons:
        g=geometry(p['geom']);xy=np.array([transform.transform(x,y) for x,y in g.exterior.coords]);ref=p['reference']
        if ref:
            color=cmap(names.index(ref));ax.fill(xy[:,0],xy[:,1],color=color,alpha=.12);ax.plot(xy[:,0],xy[:,1],color=color,lw=1.1)
        else:ax.plot(xy[:,0],xy[:,1],color='#b7bcbc',lw=.4,alpha=.7)
        rendered.append(p['fid'])
    context=[r for r in records if r['Period']=='Late Roman' and r['StartDate']==70 and r['EndDate']==324 and r['Type'] in ['Settlement','Fortified Settlement'] and r['fid'] not in chosen]
    xy=np.array([transform.transform(geometry(r['geom']).x,geometry(r['geom']).y) for r in context])
    ax.scatter(xy[:,0],xy[:,1],marker='x',c='#ac775b',s=12,linewidths=.6,alpha=.5)
    ax.scatter(obs['lon'],obs['lat'],c='#152d36',s=8,linewidths=0,alpha=.85)
    ax.set(xlim=(34.4,35.7),ylim=(31,32.7),xlabel='Longitude (°E)',ylabel='Latitude (°N)',title='Published survey envelopes and source-recorded sites')
    ax.set_aspect(1/np.cos(np.deg2rad(32)));ax.grid(alpha=.15)
    counts=[int((obs['source_code']==i).sum()) for i in range(len(names))]
    bar.barh(np.arange(len(names)),counts,color=[cmap(i) for i in range(len(names))],alpha=.8)
    bar.set(yticks=np.arange(len(names)),yticklabels=names,xlabel='Unique retained source site IDs',title='Own-source support after fixed input rules');bar.invert_yaxis();bar.grid(axis='x',alpha=.15)
    for i,n in enumerate(counts):bar.text(n+.5,i,str(n),va='center',fontsize=9)
    fig.suptitle('Roman-period habitation presence · AD70–324 phase, including AD200',fontsize=16,y=.98)
    fig.subplots_adjust(left=.06,right=.97,top=.88,bottom=.24,wspace=.58)
    fig.legend(handles=[Line2D([],[],marker='o',color='#152d36',linestyle='',label='565 retained sites; own named survey support'),
                        Line2D([],[],marker='x',color='#ac775b',linestyle='',label='Other qualifying-type phase rows; excluded/unattributed'),
                        Line2D([],[],color='#b7bcbc',lw=1,label='Unattributed survey polygons; excluded from support')],loc='lower center',bbox_to_anchor=(.5,.13),ncol=1,frameon=False,fontsize=9)
    fig.text(.5,.035,'Survey envelopes are not certified walked land or uniform detection. No population, AD200 census or town-count inference.\n'
             'Source: Titolo & Palmisano2025, doi10.5334/joad.158, CC-BY4.0; pinned repository a3537c67. No model predictions shown.',ha='center',fontsize=9)
    fig.savefig(OUT/'source_support.png',dpi=170);plt.close(fig)
    write(OUT/'presentation.json',dict(status='rendered_input_contract_only_no_predictions',results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),
        renderer_sha256=sha(Path(__file__)),figure_sha256=sha(OUT/'source_support.png'),retained_source_fids=cohort['selected_fids'],polygon_fids=rendered,
        source_count_bars=counts,model_scores_shown=False,atlas_changed=False))
    print('Rendered source/support map:565 retained site IDs, eight named survey strata; no predictions',flush=True)


if __name__=='__main__':main()
