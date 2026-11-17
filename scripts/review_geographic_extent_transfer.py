"""Independent buffered-region fitting checks, diagnostic, and final seal."""
import argparse
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.distance import cdist

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from geographic_extent_transfer import OUT, PLAN, NAMES, GRAIN, ROMAN, WINDOW, guard, fit
from cereal_activity_packet import read, write, sha
from review_conditional_grain_extent import scalar_fit, close


def review(out):
    assert not (out/'review.json').exists();guard();r=read(out/'results.json')
    assert r['status']=='conditional_extent_contiguous_geographical_transfer'
    for n,h in r['sources_sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in r['files_sha256'].items():assert sha(out/n)==h,n
    with np.load(out/'design.npz') as z:a=dict(z)
    with np.load(out/'ensembles.npz') as z:e=dict(z)
    with np.load(ROMAN/'design.npz') as z:d=dict(z)
    with np.load(WINDOW) as z:w=dict(z)
    with np.load(GRAIN/'features.npz') as z:f=dict(z)
    np.testing.assert_array_equal(a['lnH'],f['x__H_reference'])
    flat=w['real'][f['row_centre']];rr,cc=np.unravel_index(flat,w['land'].shape)
    lat=w['lat'][rr,cc];lon=w['lon'][rr,cc]
    g=np.select([(lat<38)&(lon<17),(lat<38)&(lon>=17),(lat>=38)&(lon<17)], [0,1,2], default=3)
    np.testing.assert_array_equal(g,a['group']);np.testing.assert_array_equal(np.column_stack([rr,cc]),a['centre_rc'])
    np.testing.assert_array_equal(a['centre_lat'],lat);np.testing.assert_array_equal(a['centre_lon'],lon)
    for centre in np.unique(flat):assert len(set(g[flat==centre]))==1
    distance=cdist(np.column_stack([rr,cc]),np.column_stack([rr,cc]))*float(w['cell_km'])
    masks_checked=0;minimum=[]
    for outer in range(4):
        te=g==outer;tr=(g!=outer)&np.all(distance[:,te]>120,axis=1)
        for label,v in [('train',tr),('test',te)]:np.testing.assert_array_equal(a[f'{label}_{outer}'],v);masks_checked+=1
        minimum.append(float(distance[tr][:,te].min()))
        for held in range(4):
            if held==outer:continue
            ti=tr&(g==held);ii=tr&(g!=held)&np.all(distance[:,ti]>120,axis=1)
            for label,v in [('train',ii),('test',ti)]:np.testing.assert_array_equal(a[f'inner_{label}_{outer}_{held}'],v);masks_checked+=1
            assert ii.sum()>=10 and ti.any() and distance[ii][:,ti].min()>120
    y=np.log(d['area']);n=len(y)
    for model in ['M0','H_reference']:
        x=None if model=='M0' else a['lnH'];X=np.ones((n,1)) if x is None else np.column_stack([np.ones(n),x])
        mean=np.zeros(n)
        for outer in range(4):
            tr=a[f'train_{outer}'];te=a[f'test_{outer}'];b=scalar_fit(x,y,tr)
            receipt=next(v for v in r['fits'] if v['model']==model and v['outer']==outer)
            close(b,receipt['coefficients']);residual=[]
            for held in range(4):
                if held==outer:continue
                ii=a[f'inner_train_{outer}_{held}'];ti=a[f'inner_test_{outer}_{held}'];beta=scalar_fit(x,y,ii)
                ri=y[ti]-X[ti]@beta;residual.extend(ri)
                rec=next(v for v in receipt['inner'] if v['heldout']==held)
                close(beta,rec['coefficients']);close(ri@ri,rec['squared_error'])
            sigma=np.sqrt(np.mean(np.square(residual)));close(sigma,receipt['sigma'])
            yp=y.copy();yp[te]+=1000;bb,ss,_=fit(X,yp,a,outer);close(bb,b);close(ss,sigma)
            mean[te]=X[te]@b
            for j,seed in enumerate(e['seeds']):
                normal=np.clip(np.random.default_rng(int(seed)).standard_normal(n),-2.5,2.5)
                area=np.clip(np.exp(X@b+sigma*normal),*r['bounds_ha']);close(area[te],e[model][j,te])
        close(mean,e['mean__'+model])
    cohorts={'all664':np.ones(n,bool),'AD200_compatible':d['year200'],
             'AD200_strict':d['year200']&d['strict'],'AD200_known_end':d['year200']&d['end_known']}
    checked=0
    for model in ['M0','H_reference']:
        z=np.log(e[model]);err=np.median(z,axis=0)-y;direct=np.empty(n)
        for start in range(0,n,8):
            part=z[:,start:start+8];direct[start:start+8]=np.abs(part-y[start:start+8]).mean(0)-.5*np.abs(part[:,None,:]-part[None,:,:]).mean((0,1))
        for name in ['scores.csv','groups.csv']:
            for row in csv.DictReader((out/name).open()):
                if row['model']!=model:continue
                mask=cohorts[row['cohort']].copy()
                if name=='groups.csv':mask &= g==NAMES.index(row['group'])
                assert mask.sum()==int(row['n'])
                if not mask.any():assert row['log_area_crps']=='';continue
                expected=[direct[mask].mean(),np.abs(err[mask]).mean(),np.sqrt(np.square(err[mask]).mean()),
                          err[mask].mean(),e[model][:,mask].sum(1).mean()/d['area'][mask].sum()]
                for key,v in zip(['log_area_crps','median_log_area_mae','median_log_area_rmse','median_log_bias','mean_generated_total_area_ratio'],expected):
                    close(v,float(row[key]));checked+=1
    # Figures use only reviewed geometry and CSV quantities.
    groups=list(csv.DictReader((out/'groups.csv').open()))
    fig,axes=plt.subplots(1,2,figsize=(15,6.3));ax=axes[0]
    ax.contourf(w['lon'],w['lat'],w['land'].astype(int),levels=[.5,1.5],colors=['#eeeee9'])
    colors=['#ab7655','#b3a24e','#3f7a91','#78729b']
    for group in range(4):
        use=g==group;ax.scatter(lon[use],lat[use],s=12,c=colors[group],label=f'{NAMES[group]}: {use.sum()} source rows')
    ax.axvline(17,color='#666666',linewidth=.7);ax.axhline(38,color='#666666',linewidth=.7)
    ax.set(xlim=(-17,51),ylim=(23,56),xlabel='Centre longitude (°E)',ylabel='Centre latitude (°N)',title='Fixed contiguous quadrants; shared centres stay together')
    ax.legend(fontsize=8,loc='upper right');ax.grid(alpha=.12)
    ax=axes[1]
    for j,(cohort,label,color) in enumerate([('AD200_compatible','All compatible records','#3f7a91'),('AD200_strict','Inhabited-area subset','#ab7655')]):
        gains=[]
        for name in NAMES:
            values=[next(float(v['log_area_crps']) for v in groups if v['cohort']==cohort and v['group']==name and v['model']==m) for m in ['M0','H_reference']]
            gains.append(100*(1-values[1]/values[0]))
        xx=np.arange(4)+(j-.5)*.32;ax.bar(xx,gains,width=.3,color=color,label=label)
        for x,value in zip(xx,gains):ax.text(x,value+(.35 if value>=0 else -.6),f'{value:+.1f}%',ha='center',va='bottom' if value>=0 else 'top',fontsize=9)
    ax.axhline(0,color='#555555',linewidth=.8);ax.set(xticks=np.arange(4),xticklabels=NAMES,
        ylabel='CRPS improvement of population feature vs intercept (%)',title='Modest gain overall; northeast strict subset loses',ylim=(-15.5,9))
    ax.legend(fontsize=9,loc='lower left');ax.grid(axis='y',alpha=.15)
    fig.suptitle('Buffered regional transfer of the existing population feature',fontsize=16)
    fig.text(.5,.035,'Training centres must be >120 km from test centres in the projected grid; 60-km hinterland disks do not overlap across train/test.\n'
             'All locations supplied; exposed and phase-undated extents. This is a development diagnostic, not independent demographic validation.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.055,right=.985,bottom=.19,top=.86,wspace=.24)
    fig.savefig(out/'geographic_transfer.png',dpi=160);plt.close(fig)
    write(out/'review.json',dict(status='passed_independent_buffered_geographical_transfer',
        results_sha256=sha(out/'results.json'),reviewer_sha256=sha(Path(__file__)),
        source_reviewer_sha256=sha(ROOT/'scripts/review_conditional_grain_extent.py'),
        masks_independently_checked=masks_checked,scalar_outer_fits=8,heldout_outcome_perturbations=8,
        direct_pair_CRPS_models=2,score_cells_checked=checked,
        minimum_outer_train_test_projected_km=min(minimum),shared_centres_grouped=True,
        figure_sha256=sha(out/'geographic_transfer.png'),historical_capacity_calibrated=False,adopt=False))
    print(f'Independent geometry/8 fits/perturbations/{checked} score cells pass; rendered diagnostic.')


def seal(out):
    assert not (out/'qualification.json').exists();guard();r=read(out/'results.json');q=read(out/'review.json')
    assert q['results_sha256']==sha(out/'results.json') and q['reviewer_sha256']==sha(Path(__file__))
    assert q['source_reviewer_sha256']==sha(ROOT/'scripts/review_conditional_grain_extent.py')
    assert q['figure_sha256']==sha(out/'geographic_transfer.png')
    for n,h in r['sources_sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in r['files_sha256'].items():assert sha(out/n)==h,n
    for n in [*r['files_sha256'],'results.json']:assert (out/n).read_bytes()==(out/'fresh'/n).read_bytes(),n
    files=[*r['files_sha256'],'results.json','review.json','geographic_transfer.png']
    paths=[Path(__file__),ROOT/'scripts/review_conditional_grain_extent.py',ROOT/'reports/GEOGRAPHIC_EXTENT_TRANSFER_20261117.md']
    write(out/'qualification.json',dict(status='passed_buffered_region_development_transfer_not_atlas_validation',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={n:sha(out/n) for n in files},independent_mask_checks=32,independent_outer_fits=8,
        independently_checked_score_cells=q['score_cells_checked'],fresh_exports_byte_exact=6,
        figure_visually_inspected=True,historical_capacity_calibrated=False,dated_extents_qualified=False,
        atlas_adoption=False,new_blind_validation=False,adopt=False))
    print('Sealed geographical transfer diagnostic; six fresh exports byte-identical; atlas unchanged.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--seal',action='store_true')
    args=p.parse_args();(seal if args.seal else review)(args.out)
