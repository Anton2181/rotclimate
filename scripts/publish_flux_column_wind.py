"""Publish the complete numerical replay and conservative-column-wind follow-up."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/flux_column_wind_20261026'
    review=json.loads((out/'review.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text())
    plan=protocol['plan']
    if not review['complete'] or not review['all_per_step_checks_passed'] or review['development_finalists']:
        raise ValueError('Expected the completed numerically verified, rejected follow-up')
    for name,expected in protocol['sources'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Source epoch changed: '+name)
    records={}
    for name in plan['profiles']:
        records[name]={}
        for region in plan['regions']:
            path=out/name/f'{region}.json';row=json.loads(path.read_text())
            if (row['identity']!=review['identity'] or row['status']!='passed' or not row['numerics']['all_checks_passed']
                    or file_hash(path.with_suffix('.npz'))!=row['arrays_sha256']):
                raise ValueError('Unverified follow-up record')
            records[name][region]=row
    drift={}
    for region in plan['regions']:
        with np.load(out/'reference'/f'{region}.npz') as a,np.load(out/'reference_damped'/f'{region}.npz') as b:
            if not np.array_equal(a['valid'],b['valid']):raise ValueError('Numerical-reference masks differ')
            delta=(b['simulated']-a['simulated'])[:,a['valid']]
            drift[region]=dict(maximum_absolute_rain_mm_month=float(np.abs(delta).max()),
                mean_absolute_rain_mm_month=float(np.abs(delta).mean()),
                temperature_mae_change_C=records['reference_damped'][region]['temperature']['monthly_mae_C']-
                                         records['reference'][region]['temperature']['monthly_mae_C'])
    names=list(plan['profiles'])
    labels=['r39','r39 damped','Flux, damped','Flux + shear .75','Flux + shear .5','Flux + shear .25']
    colors=['#285c80','#777777','#298b82','#ce8848','#9c4665','#7968a9']
    fig,axes=plt.subplots(1,2,figsize=(13,5.3),constrained_layout=True)
    ax=axes[0]
    for name,label,color in zip(names,labels,colors):
        ax.plot(records[name]['north_india']['monthly_rain']['simulated'],color=color,lw=1.8,
                ls='--' if name=='reference_damped' else '-',label=label)
    ax.plot(records['reference']['north_india']['monthly_rain']['observed'],color='#20272d',lw=2.5,label='Observed')
    ax.set(title='Numerical replay succeeds; shear weakens the monsoon',ylabel='Rain (mm / equal model month)',
           xticks=np.arange(12),xticklabels=list('JFMAMJJASOND'))
    ax.legend(frameon=False,fontsize=8);ax.grid(axis='y',alpha=.15)
    regions=plan['regions']
    amounts=np.array([[records[name][region]['rain']['sim_mean_annual_mm']/records[name][region]['rain']['obs_mean_annual_mm']
                       for name in names] for region in regions])
    ax=axes[1]
    im=ax.imshow(np.log10(amounts),norm=TwoSlopeNorm(vmin=-1,vcenter=0,vmax=1),cmap='BrBG',aspect='auto')
    for i,j in np.ndindex(amounts.shape):
        ax.text(j,i,f'{amounts[i,j]:.2f}',ha='center',va='center',fontsize=9,
                bbox=dict(facecolor='white',alpha=.7,edgecolor='none',pad=1))
    ax.set(xticks=np.arange(6),xticklabels=['r39','Damped','Flux','+.75','+.5','+.25'],
           yticks=np.arange(7),yticklabels=['North India','Iran plateau','Iberia','Japan','Mexico','East Australia','Pacific NW'],
           title='Annual simulated / observed rain · 1 is unbiased')
    fig.colorbar(im,ax=ax,shrink=.75,ticks=[-1,0,1],extend='min',label='Log ratio: −1 = 0.1×, 0 = 1×, +1 = 10×')
    fig.suptitle('Conservative flux and column wind: stable numerics, unresolved coastal rainfall',fontsize=15)
    fig.supxlabel('All 42 runs pass, including the previously failing pure-flux regions. Residual tolerance stays 1%; damping .05, at most 1,024 iterations.\n'
                  'The damped r39 control changes rain by at most0.0091 mm/month on mapped cells. No physical candidate qualifies; atlas climates unchanged.',fontsize=9)
    data=ROOT/'atlases/climate_accuracy/data';image=data/'flux_column_wind.png'
    fig.savefig(image,dpi=150);plt.close(fig)
    summary=dict(complete=True,decision='Rejected; retain r39',verified_runs=42,exact_legacy_controls=7,
        screen=review['screen'],numerical_reference_drift=drift,
        annual_rain_ratio=amounts.tolist(),profiles=names,regions=regions,
        numerical_settings=plan['profile_numerics'],scope=plan['numerical_interpretation'],
        provenance=dict(protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
                        plotter_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image)))
    write_json(data/'flux_column_wind.json',summary)
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text()
    start,end='<!--flux-column-wind-start-->','<!--flux-column-wind-end-->'
    section='''<!--flux-column-wind-start--><section aria-labelledby="flux-wind-h"><h2 id="flux-wind-h">Stable conservative replay and column winds</h2>
<p>The next fixed experiment separates numerical stability from physical accuracy. A lower-damping replay uses up to 1,024 moisture iterations at the <strong>same 1% residual tolerance</strong>. It converges in every region, including Japan and Mexico, whose original failures remain preserved. All 42 runs pass, and seven original controls reproduce exactly.</p>
<p>A damped r39 control changes mapped-cell monthly rainfall by at most <strong>0.0091 mm</strong>, so the large conservative-transport changes are not explained by this numerical drift. Three physically distinct trials then reduce and turn the column-pressure wind while keeping conservative mean and storm transport.</p>
<p><strong>No physical trial qualifies.</strong> Lower column drag reduces Indian rain again while leaving severe coastal wet biases. The pure conservative replay still gives 482 mm/year in North India, 1,057 in Iberia, and 3,966 in Pacific NW. All residual, budget, regional and ocean protections remain in force; no full31 or finer stage runs.</p>
<figure><a href="data/flux_column_wind.png"><img src="data/flux_column_wind.png" width="1950" height="795" loading="lazy" alt="Stable replay and column-wind trials: small numerical drift, persistent coastal wet biases, and weaker Indian rainfall with lower drag"></a><figcaption>Ratios compare annual regional means and do not measure local spatial accuracy. The full selection uses monthly cell errors and regional protections. Stable numerics and conservative accounting are separate from accurate circulation and rainfall.</figcaption></figure>
<p>The surface-derived winds remain a likely structural limitation for a full-column flux equation: turning their pressure component alone is insufficient. This experiment does not establish the correct vertical wind or mass-return circulation. Qualified Earth physics stays r39; the published Earth atlas retains r38.</p>
<p><a href="data/flux_column_wind.json" download>Download numerical drift and column-wind measurements</a> · <a href="../../reports/FLUX_COLUMN_WIND_20261026.md">Complete follow-up record</a></p></section><!--flux-column-wind-end-->'''
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_rejected_diagnostic',page_sha256=file_hash(page),
        image_sha256=file_hash(image),metadata_sha256=file_hash(data/'flux_column_wind.json'),physics_or_atlas_climate_adoption=False))


if __name__=='__main__':main()
