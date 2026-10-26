"""Publish the separate momentum-balance campaign and constrained-hull diagnosis."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/momentum_balance_20261026'
    hull_dir=ROOT/'output/momentum_hull_20261026'
    review=json.loads((out/'review.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text())
    hull=json.loads((hull_dir/'review.json').read_text())
    hull_protocol=json.loads((hull_dir/'protocol.json').read_text())
    if (not review['complete'] or review['eligible_for_earth_adoption'] or review['finalists']
            or not hull['complete'] or hull['strict']['feasible'] or hull['proposal'] is not None
            or hull['model_integrations']!=0):
        raise ValueError('Unexpected campaign or surrogate state')
    for sources in [protocol['sources'],hull_protocol['evidence_sha256']]:
        for name,expected in sources.items():
            if file_hash(ROOT/name)!=expected:
                raise ValueError('Changed scientific inputs or evidence: '+name)
    folders={'reference':out/'reference',**{name:out/'development'/name for name in protocol['plan']['candidates']}}
    summaries={}
    for name,folder in folders.items():
        summary=json.loads((folder/'summary.json').read_text())
        if not summary['complete'] or len(summary['regions'])!=31:
            raise ValueError('Incomplete 31-region case')
        for region,row in summary['regions'].items():
            if row['status']!='passed' or not row['numerics']['all_checks_passed']:
                raise ValueError('Unverified climate integration')
            if file_hash(folder/'cells'/f'{region}.npz')!=row['cells_sha256']:
                raise ValueError('Changed sampled climate')
        summaries[name]=summary
    response=hull['responses']
    labels=['r39','Drag ×1.25','Drag ×1.5','Nominal drags','Land only','Ocean only','Pressure ×1.1','Pressure ×1.2']
    if len(labels)!=len(hull['point_names']):
        raise ValueError('Unexpected surrogate response points')
    fig,axes=plt.subplots(1,2,figsize=(12.8,5.4),constrained_layout=True)
    x=100*(1-np.array(response['north_india']))
    y=100*(np.array(response['pacific_nw'])-1)
    color=100*(np.array(response['overall'])-1)
    ax=axes[0]
    ax.fill_between([5,15],-.25,2,facecolor='#e6f1e9',alpha=.7)
    ax.axvline(5,color='#59665f',ls='--',lw=1)
    ax.axhline(2,color='#59665f',ls='--',lw=1)
    im=ax.scatter(x,y,c=color,cmap='viridis_r',s=65,vmin=-.55,vmax=0,edgecolors='#333333',linewidths=.5)
    offsets=[(5,8),(-64,-13),(5,-12),(5,-12),(5,-12),(5,8),(5,7),(5,7)]
    for i,label in enumerate(labels):
        ax.annotate(label,(x[i],y[i]),xytext=offsets[i],textcoords='offset points',fontsize=8)
    ax.set(xlabel='North India rainfall-loss improvement (%)',ylabel='Pacific NW combined-error increase (%)',
           title='Two regional protections already conflict',xlim=(-9,15),ylim=(-.25,6.2))
    ax.text(5.3,.4,'Meets these two criteria only',fontsize=8,color='#356347')
    ax.grid(alpha=.12)
    fig.colorbar(im,ax=ax,shrink=.75,label='31-region combined error change (%)')
    ax=axes[1]
    names=['reference',*protocol['plan']['candidates']]
    colors=['#285c80','#4d9b91','#ce8848','#9c4665','#7968a9']
    pretty=['r39','Land drag only','Ocean drag only','Nominal drag + pressure ×1.1','Nominal drag + pressure ×1.2']
    for name,c,label in zip(names,colors,pretty):
        with np.load(folders[name]/'cells/north_india.npz') as z:
            ax.plot(z['Ps'].mean(1),color=c,lw=1.8,label=label)
            observed=z['Po'].mean(1)
    ax.plot(observed,color='#20272d',lw=2.5,label='Observed')
    ax.set(title='The monsoon deficit remains in all four trials',ylabel='Rain (mm / equal model month)',
           xticks=np.arange(12),xticklabels=list('JFMAMJJASOND'))
    ax.legend(frameon=False,fontsize=8)
    ax.grid(axis='y',alpha=.15)
    fig.suptitle('Momentum balance: regional tradeoffs survive a coupled retest',fontsize=16)
    fig.supxlabel('Left: eight actual development responses, not simulated convex mixtures. Shaded area addresses only two criteria; all other gates still apply.\n'
                  'Four new candidates / 155 verified runs. Full constrained response hull is infeasible: no proposal, no extra integration, no adoption.',fontsize=9)
    data=ROOT/'atlases/climate_accuracy/data'
    image=data/'momentum_balance.png'
    fig.savefig(image,dpi=150)
    plt.close(fig)
    summary=dict(complete=True,decision='Retain r39',verified_integrations=155,
        exact_regional_error_controls=31,development=review['development'],
        north_india_annual_rain_mm={name:s['regions']['north_india']['rain']['sim_mean_annual_mm'] for name,s in summaries.items()},
        hull=hull,scope=protocol['plan']['fixed'],
        provenance=dict(review_sha256=file_hash(out/'review.json'),protocol_sha256=file_hash(out/'protocol.json'),
                        plotter_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image)))
    write_json(data/'momentum_balance.json',summary)
    page=ROOT/'atlases/climate_accuracy/index.html'
    content=page.read_text()
    start,end='<!--momentum-balance-start-->','<!--momentum-balance-end-->'
    section='''<!--momentum-balance-start--><section aria-labelledby="balance-h"><h2 id="balance-h">Land, ocean and pressure balance</h2>
<p>The next fixed experiment separated land and ocean drag, then tested nominal drags with 10% and 20% stronger thermal-pressure amplitudes. All 155 integrations passed numerical checks, with 31 fresh reference error/geography controls. No planetary property changed.</p>
<p>The 10% pressure candidate improved average rainfall loss by <strong>1.64%</strong> and passed the old group gate, but failed the declared Japan, Mexico and Pacific NW protections. Land-only, ocean-only and 20% pressure candidates failed their complete criteria too. No candidate reached the ocean-finalist, fine-grid or established-six stage.</p>
<figure><a href="data/momentum_balance.png"><img src="data/momentum_balance.png" width="1920" height="810" loading="lazy" alt="Momentum tradeoff plot and Indian seasonal rainfall: no tested candidate meets all regional protections"></a><figcaption>The eight plotted points are actual paired development results. No convex combination of their error responses satisfies all the declared constraints, even in a diagnostic that omits the overall-improvement threshold. This surrogate result is limited to this sampled neighborhood; it is not proof that realistic physical improvements are impossible.</figcaption></figure>
<p>A constrained proposal tool therefore generated <strong>no new candidate and no extra climate run</strong>. It rejects infeasible combinations rather than allowing a larger average gain to pay for protected regional failures. Adopted Earth physics remains r39; all three atlas climates and population fields are unchanged.</p>
<p><a href="data/momentum_balance.json" download>Download momentum-balance and feasibility measurements</a> · <a href="../../reports/MOMENTUM_BALANCE_20261026.md">Experiment and proposal method</a></p></section><!--momentum-balance-end-->'''
    if start in content:
        before,rest=content.split(start,1)
        _,after=rest.split(end,1)
        content=before+section+after
    else:
        content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_rejected_diagnostic',
        image_sha256=file_hash(image),metadata_sha256=file_hash(data/'momentum_balance.json'),
        page_sha256=file_hash(page),physics_or_atlas_climate_adoption=False))


if __name__=='__main__':main()
