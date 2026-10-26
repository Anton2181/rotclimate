"""Publish the completed full-development surface-momentum experiment."""
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
    out=ROOT/'output/surface_momentum_20261026'
    review=json.loads((out/'review.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text())
    if not review['complete'] or review['eligible_for_earth_adoption'] or review['finalists']:
        raise ValueError('Need the completed rejected development campaign')
    for name,expected in protocol['sources'].items():
        if file_hash(ROOT/name)!=expected:
            raise ValueError('Experiment source changed: '+name)
    folders={'reference':out/'reference',**{name:out/'development'/name for name in protocol['plan']['candidates']}}
    summaries={}
    for name,folder in folders.items():
        s=json.loads((folder/'summary.json').read_text())
        if not s['complete'] or len(s['regions'])!=31:
            raise ValueError('Incomplete full-development run')
        for region,row in s['regions'].items():
            if (row['status']!='passed' or not row['numerics']['all_checks_passed']
                    or file_hash(folder/'cells'/f'{region}.npz')!=row['cells_sha256']):
                raise ValueError('Changed or unverified region')
        summaries[name]=s
    names=list(protocol['plan']['candidates'])
    colors=['#4d9b91','#ce8848','#9c4665']
    labels=['Both drags ×1.25','Both drags ×1.5','Nominal land/ocean drag']
    fig,axes=plt.subplots(1,2,figsize=(12.5,4.9),constrained_layout=True)
    ax=axes[0]
    protected=protocol['protected_regions']
    short=['North India','Iran plateau','Iberia','Japan','Mexico','East Australia','Pacific NW']
    x=np.arange(7)
    for i,(name,color,label) in enumerate(zip(names,colors,labels)):
        b,c=summaries['reference']['regions'],summaries[name]['regions']
        changes=[100*(.5*(c[r]['rain']['loss']/b[r]['rain']['loss']+
                          c[r]['temperature']['monthly_mae_C']/b[r]['temperature']['monthly_mae_C'])-1) for r in protected]
        ax.barh(x+(i-1)*.22,changes,height=.2,color=color,label=label)
    ax.axvline(0,color='#444444',lw=.7)
    ax.axvline(2,color='#777777',lw=1,ls='--',label='Other protected regions: +2% ceiling')
    ax.set(yticks=x,yticklabels=short,xlabel='Combined local error change from r39 (%)',
           title='Regional improvements and regressions')
    ax.invert_yaxis()
    ax.legend(frameon=False,fontsize=8)
    ax=axes[1]
    for name,color,label in zip(['reference',*names],['#285c80',*colors],['r39',*labels]):
        with np.load(folders[name]/'cells/north_india.npz') as z:
            simulated=z['Ps'].mean(1)
            observed=z['Po'].mean(1)
        ax.plot(simulated,lw=1.8,color=color,label=label)
    ax.plot(observed,lw=2.5,color='#20272d',label='Observed')
    ax.set(title='North India improves, but the missing monsoon remains',ylabel='Rain (mm / equal model month)',
           xticks=np.arange(12),xticklabels=list('JFMAMJJASOND'))
    ax.legend(frameon=False,fontsize=8)
    ax.grid(axis='y',alpha=.15)
    fig.suptitle('Surface momentum: modest rainfall gains, no adoption',fontsize=16)
    fig.supxlabel('124 verified integrations; 31 fresh r39 controls reproduce archived regional errors/geography. Nominal drag passes the old full-development gate,\n'
                  'but fails the declared Mexico/Pacific NW protections. No finer-grid, ocean-finalist or established-six runs; planet/geography unchanged.',fontsize=9)
    data=ROOT/'atlases/climate_accuracy/data'
    image=data/'surface_momentum.png'
    fig.savefig(image,dpi=150)
    plt.close(fig)
    write_json(data/'surface_momentum.json',dict(complete=True,decision='Rejected; retain r39',
        verified_integrations=124,exact_regional_error_controls=31,development=review['development'],
        north_india_annual_rain_mm={name:s['regions']['north_india']['rain']['sim_mean_annual_mm'] for name,s in summaries.items()},
        scope=protocol['plan']['fixed'],provenance=dict(review_sha256=file_hash(out/'review.json'),
            protocol_sha256=file_hash(out/'protocol.json'),plotter_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image))))
    page=ROOT/'atlases/climate_accuracy/index.html'
    content=page.read_text()
    start,end='<!--surface-momentum-start-->','<!--surface-momentum-end-->'
    section='''<!--surface-momentum-start--><section aria-labelledby="momentum-h"><h2 id="momentum-h">Surface momentum: a gain that did not qualify</h2>
<p>Three fixed land/ocean drag settings were tested against all 31 development regions, keeping the planet and other physics fixed. All 124 integrations passed their numerical checks; the fresh r39 reference reproduced the archived regional errors and geography.</p>
<p>The nominal drag values reduced mean rainfall loss by <strong>1.54%</strong> and raised North India's annual rain from <strong>256 to 285 mm</strong>. Temperature MAE rose from 1.793 to 1.802°C. Every protected group improved on the existing combined metric, and the nominal candidate passed that development gate.</p>
<p><strong>It still failed this experiment's declared regional protections.</strong> Mexico and the Pacific Northwest had combined error increases above 2%. The candidate was rejected, and no ocean-finalist, fine-grid or established-region stage was run. The other two candidates failed their development or extra regional criteria too.</p>
<figure><a href="data/surface_momentum.png"><img src="data/surface_momentum.png" width="1875" height="735" loading="lazy" alt="Surface-drag experiment showing regional tradeoffs and a modest Indian rainfall increase that remains far below observations"></a><figcaption>A physically plausible parameter change can improve average rainfall and still be unsuitable for adoption. These are reused development regions; the result does not establish measured fantasy-world accuracy.</figcaption></figure>
<p><a href="data/surface_momentum.json" download>Download surface-momentum measurements</a> · <a href="../../reports/SURFACE_MOMENTUM_20261026.md">Experiment record</a></p></section><!--surface-momentum-end-->'''
    if start in content:
        before,rest=content.split(start,1)
        _,after=rest.split(end,1)
        content=before+section+after
    else:
        content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_rejected_diagnostic',
        image_sha256=file_hash(image),metadata_sha256=file_hash(data/'surface_momentum.json'),
        page_sha256=file_hash(page),physics_or_atlas_climate_adoption=False))


if __name__=='__main__':main()
