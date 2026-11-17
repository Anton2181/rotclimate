"""Draw the checked known-site comparison and fixed-scenario diagnostic."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from conditional_grain_extent import OUT, ROMAN, WINDOW
from cereal_activity_packet import read, write, sha


def main():
    assert not (OUT/'presentation.json').exists(), 'Keep completed presentation'
    r=read(OUT/'results.json');q=read(OUT/'review.json')
    assert q['results_sha256']==sha(OUT/'results.json')
    assert q['reviewer_sha256']==sha(ROOT/'scripts/review_conditional_grain_extent.py')
    with np.load(ROMAN/'design.npz') as z:d=dict(z)
    with np.load(OUT/'ensembles.npz') as z:e=dict(z)
    with np.load(OUT/'features.npz') as z:f=dict(z)
    with np.load(WINDOW) as z:w=dict(z)
    use=d['year200'];arrays={'source':d['area'],**{k:np.exp(np.median(np.log(e[k]),axis=0)) for k in ['M0','H_reference','G_h600']}}
    fig,axes=plt.subplots(2,2,figsize=(15,11),sharex=True,sharey=True)
    titles=['Recorded extent · phase undated','Intercept-only baseline',
            'Reference population feature','Gross grain feature · fixed 600-hour scenario']
    for ax,(key,area),title in zip(axes.flat,arrays.items(),titles):
        ax.contourf(w['lon'],w['lat'],w['land'].astype(int),levels=[.5,1.5],colors=['#eeeee9'])
        ax.contour(w['lon'],w['lat'],w['land'].astype(int),levels=[.5],colors=['#a1aaa5'],linewidths=.35)
        for strict in [False,True]:
            m=use&(d['strict']==strict)
            ax.scatter(d['lon'][m],d['lat'][m],s=4+.14*area[m],
                facecolors='#34677d' if strict else '#fafaf8',edgecolors='#34677d',linewidths=.6,alpha=.8)
        ax.set(xlim=(-17,51),ylim=(23,56),title=title);ax.grid(alpha=.12)
        ax.set_aspect(1/np.cos(np.deg2rad(38)));ax.tick_params(labelsize=9)
    for ax in axes[1]:ax.set_xlabel('Longitude (°E)')
    for ax in axes[:,0]:ax.set_ylabel('Latitude (°N)')
    fig.suptitle('Roman city extents: grain features do not improve this comparison',fontsize=17)
    handles=[Line2D([],[],marker='o',linestyle='',markerfacecolor='#34677d',markeredgecolor='#34677d',label='Inhabited-area basis'),
             Line2D([],[],marker='o',linestyle='',markerfacecolor='#fafaf8',markeredgecolor='#34677d',label='Other extent basis')]
    handles += [Line2D([],[],marker='o',linestyle='',markersize=np.sqrt(4+.14*s),color='#6a7776',markerfacecolor='none',label=f'{s} ha') for s in [10,100,1000]]
    fig.legend(handles=handles,ncol=5,loc='lower center',bbox_to_anchor=(.5,.085),frameon=False,fontsize=9)
    fig.text(.5,.028,'663 supplied sites compatible with occupation in AD200; recorded extents lack dated phases. Same hectare bubble scale.\n'
             'Predictions are out-of-fold medians of 256 draws. Conditional development experiment; no location/population forecast or atlas adoption.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.06,right=.99,top=.92,bottom=.17,hspace=.14,wspace=.12)
    fig.savefig(OUT/'roman_extent_comparison.png',dpi=160);plt.close(fig)
    labels=['M0','H_reference','G_potential','G_h600','G_h300','hierarchy_reference']
    short=['Intercept','Population','Potential\ngrain','Grain\n600h','Grain\n300h','Existing\nhierarchy']
    colors=['#9daba8','#3b7084','#d3a675','#b56c43','#d48d5c','#365762']
    fig,axes=plt.subplots(1,3,figsize=(17,5.8))
    for ax,cohort,title in zip(axes[:2],['AD200_compatible','AD200_strict'],['All 663 compatible records','152 inhabited-area records']):
        values=[next(s for s in r['scores'] if s['model']==k and s['cohort']==cohort)['log_area_crps'] for k in labels]
        ax.bar(np.arange(6),values,color=colors,width=.7)
        ax.set(xticks=np.arange(6),xticklabels=short,ylabel='Log-area CRPS · lower is better',ylim=(0,.68),title=title)
        ax.tick_params(axis='x',labelsize=8.5);ax.grid(axis='y',alpha=.15)
        for j,value in enumerate(values):ax.text(j,value+.009,f'{value:.3f}',ha='center',fontsize=9)
    a,b=f['x__G_h600'],f['x__G_h300'];ax=axes[2]
    ax.scatter(a,b,s=8,alpha=.45,color='#b56c43')
    line=np.array([a.min(),a.max()]);ident=r['identifiability']
    ax.plot(line,ident['affine_intercept']+ident['affine_h300_on_h600_slope']*line,color='#365762',linewidth=1)
    ax.set(xlabel='log(1 + grain ration-years), 600h',ylabel='log(1 + grain ration-years), 300h',title='Fixed hours mostly rescale the feature')
    ax.text(.04,.96,f"Correlation {ident['log_feature_correlation']:.4f}\nHeld-out mean-log prediction difference RMS {ident['out_of_fold_mean_log_prediction_difference_rms']:.3f}",transform=ax.transAxes,va='top',fontsize=9)
    ax.grid(alpha=.15)
    fig.suptitle('A conditional size fit does not identify historical work allowances',fontsize=16)
    fig.text(.5,.035,'Same training folds and draws; hierarchy is a frozen reference with additional structure. Gross grain is before food claims and transport.\n'
             'Fixed 300/600-hour scenarios are not observed work budgets; exposed city-area records do not establish actual household hours.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.055,right=.985,bottom=.23,top=.84,wspace=.29)
    fig.savefig(OUT/'grain_extent_diagnostic.png',dpi=160);plt.close(fig)
    np.savez_compressed(OUT/'plot_values.npz',**arrays,lat=d['lat'],lon=d['lon'],mask=use,strict=d['strict'],
                        x_h600=a,x_h300=b)
    files=['roman_extent_comparison.png','grain_extent_diagnostic.png','plot_values.npz']
    write(OUT/'presentation.json',dict(status='rendered_checked_conditional_extent_comparison',
        results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),
        renderer_sha256=sha(Path(__file__)),files_sha256={n:sha(OUT/n) for n in files},
        map_panels=4,same_ha_bubble_scale=True,all_map_sites_in_frame=bool(np.all((d['lon'][use]>=-17)&(d['lon'][use]<=51)&(d['lat'][use]>=23)&(d['lat'][use]<=56))),
        atlas_adopted=False))
    print('Rendered four-panel Roman extent comparison and fixed-grain diagnostic.')


if __name__=='__main__':main()
