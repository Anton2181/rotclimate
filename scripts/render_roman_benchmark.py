"""Scientific regional comparison maps and complete province evidence chart."""
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_roman_benchmark import OUT,BACKGROUND,sha,read,write


def main():
    result=read(OUT/'results.json');review=read(OUT/'review.json');prep=read(OUT/'preparation.json')
    assert review['status']=='passed_independent_baseline_hierarchy_draws_pairwise_scores_and_all_regions'
    assert review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_roman_benchmark.py')
    with np.load(OUT/'design.npz') as z:d=dict(z)
    with np.load(OUT/'ensemble.npz') as z:
        baseline=np.exp(np.median(np.log(z['baseline']),axis=0));hierarchy=np.exp(np.median(np.log(z['hierarchy']),axis=0))
    with np.load(BACKGROUND) as z:land=z['land'];lat=z['lat'];lon=z['grid_lon']
    arrays=dict(source_area=d['area'],baseline_median=baseline,hierarchy_median=hierarchy,lat=d['lat'],lon=d['lon'],AD200=d['year200'],strict=d['strict'],province=d['province'])
    np.savez_compressed(OUT/'plot_values.npz',**arrays)
    files=[];panels=[]
    for region,mask,limits in [('roman',d['year200'],(-17,51,23,56)),('egypt',d['year200']&(d['province']==prep['province_names'].index('Aegyptus')),(24,37,20,34))]:
        fig,axes=plt.subplots(1,3,figsize=(17,6),sharex=True,sharey=True)
        for ax,key,title in zip(axes,['source_area','baseline_median','hierarchy_median'],['Reference extent · inherited adjustments; phase undated','Simple baseline · known locations','Current hierarchy family · known locations']):
            ax.contourf(lon,lat,land.astype(int),levels=[.5,1.5],colors=['#eeeee9'],zorder=0)
            ax.contour(lon,lat,land.astype(int),levels=[.5],colors=['#919996'],linewidths=.35)
            for strict in [False,True]:
                use=mask&(d['strict']==strict)
                ax.scatter(d['lon'][use],d['lat'][use],s=4+.14*arrays[key][use],facecolors='#35677c' if strict else '#fafaf7',edgecolors='#35677c',linewidths=.65,alpha=.8,zorder=3)
            ax.set(xlim=limits[:2],ylim=limits[2:],xlabel='Longitude (°E)');ax.set_aspect(1/np.cos(np.deg2rad(38)))
            ax.set_title(title,fontsize=11);ax.grid(alpha=.15);ax.tick_params(labelsize=8)
            panels.append(dict(region=region,quantity=key,source_rows=np.flatnonzero(mask).tolist(),extent=list(limits),size_intercept=4.,size_per_ha=.14))
        axes[0].set_ylabel('Latitude (°N)')
        fig.suptitle(('Roman region' if region=='roman' else 'Aegyptus focus')+f" · conditional size benchmark, {int(mask.sum())} shared catalogue sites",fontsize=16)
        fig.subplots_adjust(left=.045,right=.99,top=.86,bottom=.24,wspace=.13)
        handles=[Line2D([],[],marker='o',linestyle='',markerfacecolor='#35677c',markeredgecolor='#35677c',label='Exact Inhabited area basis (phase still undated)'),
                 Line2D([],[],marker='o',linestyle='',markerfacecolor='#fafaf7',markeredgecolor='#35677c',label='Other inherited extent basis')]
        for size in [10,100,1000]:handles.append(Line2D([],[],marker='o',linestyle='',markersize=np.sqrt(4+.14*size),color='#707875',markerfacecolor='none',label=str(size)+' ha'))
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.13),ncol=5,frameon=False,fontsize=8.5)
        fig.text(.5,.045,'Same coordinates and bubble scale in every panel. Predictions: medians of 256 frozen-parameter draws, provinces held out in four hash folds.\n'
                 'AD200 occupation compatibility uses open-ended dates; extent phases and survey completeness are unqualified. No population or location forecast.',ha='center',fontsize=9)
        name=region+'_comparison.png';fig.savefig(OUT/name,dpi=180);plt.close(fig);files.append(name)
    with (OUT/'coverage.csv').open() as f:coverage=list(csv.DictReader(f))
    names=[r['province'] for r in coverage];pos=np.arange(len(names))
    catalogue=np.array([int(r['occupation_AD200_compatible']) for r in coverage]);area=np.array([int(r['AD200_positive_area_records']) for r in coverage]);targets=np.array([int(r['AD200_model_targets']) for r in coverage]);strict=np.array([int(r['AD200_strict_targets']) for r in coverage])
    fig,ax=plt.subplots(figsize=(12,14));ax.barh(pos,catalogue,color='#dde2df',label='Catalogue occupation compatible with AD200');ax.barh(pos,area,color='#b8c6c7',label='Positive area record available');ax.barh(pos,targets,color='#7297a6',label='Inherited model target');ax.barh(pos,strict,color='#27576c',label='Exact Inhabited area target (phase undated)')
    ax.set(yticks=pos,yticklabels=names,xlabel='Catalogue records; overlapping nested bars',title='Evidence availability in every catalogue province\nAvailability is not survey completeness or a dated population census')
    ax.invert_yaxis();ax.tick_params(axis='y',labelsize=8);ax.legend(loc='lower right',fontsize=8);ax.grid(axis='x',alpha=.15)
    fig.tight_layout();fig.savefig(OUT/'evidence_coverage.png',dpi=150);plt.close(fig);files.append('evidence_coverage.png')
    write(OUT/'plot_data.json',dict(panels=panels,background_scope='Static land/coordinate context only; no climate, food or population values used.',
                                 same_ha_scale=True,source_areas_phase_undated=True,source_areas_are_inherited_adjusted_extents=True,marker_basis_not_temporal_certification=True))
    files+=['plot_values.npz','plot_data.json']
    write(OUT/'presentation.json',dict(status='rendered_reviewed_conditional_Roman_benchmark',results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),
        renderer_sha256=sha(Path(__file__)),background_sha256=sha(BACKGROUND),files_sha256={name:sha(OUT/name) for name in files},atlas_changed=False))
    print('Rendered Roman/Egypt same-site comparisons and all51-province evidence chart',flush=True)


if __name__=='__main__':main()
