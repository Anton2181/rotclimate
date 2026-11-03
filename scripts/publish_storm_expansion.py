"""Publish the complete broad storm comparison, never a partial-profile mean."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from validate_r42_multistart import paired_score
from organize_climate_accuracy import organize


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source=ROOT/'output/storm_expansion_20261103b';plan=json.loads((source/'plan.json').read_text())
    result=json.loads((source/'result.json').read_text())
    if result['adoption']:raise ValueError('This experiment does not adopt physics')
    baseline=json.loads((source/'reference61/summary.json').read_text())
    if not baseline.get('complete'):raise ValueError('Incomplete reference')
    curves={};scores={};raw={};files={}
    for name in ['reference',*plan['candidates']]:
        folder=source/('reference61' if name=='reference' else name+'_dev61')
        summary=json.loads((folder/'summary.json').read_text());raw[name]=summary
        if set(summary['regions'])!=set(plan['regions']):raise ValueError('Missing declared cases')
        scores[name]=(paired_score(baseline['regions'],summary['regions'],plan['regions'])
                      if summary.get('complete') else None)
        if name!='reference' and scores[name]!=result['dev61'][name]:raise ValueError('Final score changed')
        curves[name]={}
        for region,row in summary['regions'].items():
            if row['status']!='passed':continue
            path=folder/'cells'/(region+'.npz')
            if file_hash(path)!=row['cells_sha256']:raise ValueError('Raw packet changed')
            files[str(path.relative_to(ROOT))]=row['cells_sha256']
            with np.load(path) as z,np.load(source/'reference61/cells'/(region+'.npz')) as ref:
                for key in ['i','j','To','Po','lat','lon','elev','elev_max','coast_km']:
                    if not np.array_equal(z[key],ref[key]):raise ValueError('Unpaired input footprint')
                curves[name][region]=dict(sim=z['Ps'].mean(1),obs=z['Po'].mean(1))
    # Display examples include both familiar seasonal failures and broader
    # geographical failures. They never determine the full61 score or selection.
    examples=['california','japan','north_india','pacific_nw',
              'tripolitania','algeria_sahara','kenya_highlands','northeast_brazil']
    fig,axes=plt.subplots(2,4,figsize=(16,7.5),layout='constrained')
    for ax,region in zip(axes.flat,examples):
        ax.plot(range(1,13),curves['reference'][region]['obs'],'--',color='#222',lw=2,label='Observed')
        for name,label,color in [('reference','Adopted r43 control','#2868a2'),
            ('storm_r42','Conservative storms, r42 strengths','#d97726'),
            ('storm_r43','Conservative storms, r43 strengths','#36916d')]:
            if scores[name] is None:continue
            ax.plot(range(1,13),curves[name][region]['sim'],color=color,lw=1.7,label=label)
        ax.set_title(region.replace('_',' ').title(),loc='left',fontsize=11)
        ax.set_xticks([1,4,7,10],['Jan','Apr','Jul','Oct']);ax.set_ylim(bottom=0);ax.set_ylabel('mm/month')
        ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Both complete conservative-storm families on 61 development regions\nSelected seasonal examples shown; all regions retained in the aggregate and downloadable evidence',fontsize=14)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=2,frameon=False)
    out=ROOT/'output/storm_expansion_review_20261103';out.mkdir(exist_ok=True)
    image=out/'monthly_storm_expansion.png';fig.savefig(image,dpi=135);plt.close(fig)
    overview=dict(result=result,scores=scores,baseline=baseline['all'],
        regional_errors={name:{n:dict(status=r['status'],temperature=r.get('temperature'),rain=r.get('rain'),error=r.get('error')) for n,r in summary['regions'].items()}
                         for name,summary in raw.items()},
        packets_sha256=files,result_sha256=file_hash(source/'result.json'),
        figure_sha256=file_hash(image),publisher_sha256=file_hash(Path(__file__)),
        scope='Complete61 development regions. Historical49 separately reported; spent d/e are development, not unseen. Displayed examples do not select or reweight regions. Physics and normal atlas adoption are separate.')
    write_json(out/'review.json',overview)
    destination=ROOT/'atlases/climate_accuracy/data'
    shutil.copyfile(image,destination/'storm_expansion_monthly.png');write_json(destination/'storm_expansion.json',overview)
    rows=[]
    for name in plan['candidates']:
        s=scores[name];old=result['S49_reported'].get(name)
        cells=([f'{s["S"]:.6f}',f'{100*s["T"]:+.2f}%',f'{100*s["P"]:+.2f}%',f'{old["S"]:.6f}']
               if s is not None else ['failed; unscored']*4)
        rows.append('<tr><td>'+name.replace('_',' ')+'</td>'+''.join('<td>'+v+'</td>' for v in cells)+'</tr>')
    commit=subprocess.check_output(['git','log','-1','--format=%H','--',str((source/'result.json').relative_to(ROOT))],cwd=ROOT,text=True).strip()
    if not commit:raise ValueError('Commit the complete result before publishing')
    qualification=('No profile passed the unchanged full-development gate; no finer-grid or reserved-f case ran.'
                   if result['selected'] is None else
                   'One profile was frozen after both full development comparisons; its finer-grid and reserved-f outcomes are retained in the downloadable result. This study does not automatically adopt it.')
    section=f'''<!--storm-expansion-start--><section aria-labelledby="storm-expansion-h">
<h2 id="storm-expansion-h">The broader storm test: the eight-region result does not establish generalization</h2>
<p>Both fixed conservative-storm families have finished their declared 61-region sweeps against the same verified r43 control. Only fully verified profiles receive an aggregate; failed ones remain unscored. The broader pool includes spent d/e; historical S49 remains separate. {qualification}</p>
<div class="table"><table><caption>Equal-region error ratios versus adopted r43; every declared region remains included</caption><thead><tr><th>Fixed profile</th><th>S61</th><th>Temperature</th><th>Rain loss</th><th>Historical S49</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<figure><a href="data/storm_expansion_monthly.png"><img src="data/storm_expansion_monthly.png" width="2160" height="1012" loading="lazy" alt="Monthly observed and all three simulated rainfall curves for eight examples from the complete61-region test"></a><figcaption>These examples expose seasonal errors and regional tradeoffs. They do not replace the full61 score or introduce a region/group veto. All regional errors are retained in the JSON and the immutable raw result archive.</figcaption></figure>
<p>The original eight-region factorial remains a valid result for that reused sample; its gain cannot be advertised as a global improvement. Conservation of storm exchange is a numerical/physical constraint, not proof of realistic humidity supply, circulation or rain closure. No failed physical family replaces the normal atlas.</p>
<p>The prior damped numerical control reproduced all61 actual forcing/observation footprints with max monthly drift0.00356 C and0.04935 mm, within the original limits. Planet/orbit settings and model-generated winds/SST were unchanged. The experiment never fits individual regions or chooses candidates from reserved-f outcomes.</p>
<p><a href="data/storm_expansion.json" download>Complete qualification, baseline, regional errors and packet hashes</a> · <a href="https://github.com/Anton2181/rotclimate/tree/{commit}/output/storm_expansion_20261103b">All raw numerical records and monthly cell packets at the result commit</a></p>
</section><!--storm-expansion-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html'
    text=re.sub(r'<!--storm-expansion-start-->[\s\S]*?<!--storm-expansion-end-->','',page.read_text())
    text=text.replace('</main>',section+'\n</main>');text,studies=organize(text)
    if organize(text)[0]!=text:raise ValueError('Navigation is not idempotent')
    page.write_text(text);write_json(out/'publication.json',dict(status='passed',newest=studies[0],page_sha256=file_hash(page)))
    print('Published complete broad comparison, outcome:',result['outcome'])


if __name__=='__main__':main()
