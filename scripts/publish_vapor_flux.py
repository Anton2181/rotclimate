"""Publish the mixed-accuracy conservative-vapor pilot, retaining solver failures."""
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
    out=ROOT/'output/vapor_flux_20261026'
    review=json.loads((out/'review.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text())
    if not review['complete'] or review['development_finalists']:
        raise ValueError('Expected a completed rejected pilot')
    for name,expected in protocol['sources'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Source epoch changed: '+name)
    plan=protocol['plan'];records={};failures=[]
    for name in plan['profiles']:
        records[name]={}
        for region in plan['regions']:
            path=out/name/f'{region}.json';row=json.loads(path.read_text())
            if row['identity']!=review['identity']:raise ValueError('Changed result identity')
            if row['status']=='passed':
                if not row['numerics']['all_checks_passed'] or file_hash(path.with_suffix('.npz'))!=row['arrays_sha256']:
                    raise ValueError('Unverified successful result')
            elif row['status']=='failed':
                failures.append(dict(profile=name,region=region,error=row['error']))
            else:raise ValueError('Unknown run status')
            records[name][region]=row
    fig,axes=plt.subplots(1,2,figsize=(12.8,5.3),constrained_layout=True)
    pretty=['r39','Remove convergence import','Also conserve storms','Flux advection, legacy storms','Flux advection + conservative storms']
    colors=['#285c80','#aaaaaa','#a87c4c','#9971a0','#298b82']
    ax=axes[0]
    for name,label,color in zip(plan['profiles'],pretty,colors):
        row=records[name]['north_india']
        if row['status']!='passed':continue
        ax.plot(row['monthly_rain']['simulated'],label=label,color=color,lw=1.8)
    ax.plot(records['reference']['north_india']['monthly_rain']['observed'],color='#20272d',lw=2.5,label='Observed')
    ax.set(title='North India improves with flux transport',ylabel='Rain (mm / equal model month)',
           xticks=np.arange(12),xticklabels=list('JFMAMJJASOND'))
    ax.legend(frameon=False,fontsize=8)
    ax.grid(axis='y',alpha=.15)
    ax=axes[1];primary='flux_conservative_storm'
    labels=['North India','Iran plateau','Iberia','Japan','Mexico','East Australia','Pacific NW']
    for i,(region,label) in enumerate(zip(plan['regions'],labels)):
        row=records[primary][region];base=records['reference'][region]
        if row['status']=='failed':
            ax.text(0,i,'Solver failed · excluded',va='center',fontsize=9,color='#a23e46')
        else:
            value=100*(row['rain']['loss']/base['rain']['loss']-1)
            ax.barh(i,value,color='#298b82' if value<0 else '#c8874d')
    ax.axvline(0,color='#444444',lw=.7)
    ax.set(yticks=np.arange(7),yticklabels=labels,xlabel='Regional rainfall-loss change (%) · lower is better',
           title='Budgets improve; overall accuracy does not')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.12)
    fig.suptitle('Conservative regional vapor transport: encouraging India, rejected climate',fontsize=15)
    fig.supxlabel('35 attempted integrations: 31 pass, 4 nonlinear-solver failures preserved. All 7 legacy controls reproduce exactly.\n'
                  'No failed run enters a mean. Conservative mean+storm transport has open boundaries and explicit vertical drying; not a closed planet.',fontsize=9)
    data=ROOT/'atlases/climate_accuracy/data';image=data/'vapor_flux.png'
    fig.savefig(image,dpi=150);plt.close(fig)
    summary=dict(complete=True,decision='Rejected; retain r39',attempted_runs=35,passed_runs=31,failures=failures,
        screen=review['screen'],regions={r:dict(reference_rain=records['reference'][r]['rain'],
            candidate_rain=records[primary][r].get('rain'),status=records[primary][r]['status'],
            ledger=records[primary][r].get('numerics',{}).get('vapor_flux_budget')) for r in plan['regions']},
        scope=plan['publication'],provenance=dict(protocol_sha256=file_hash(out/'protocol.json'),
            review_sha256=file_hash(out/'review.json'),plotter_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image)))
    write_json(data/'vapor_flux.json',summary)
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text()
    start,end='<!--vapor-flux-start-->','<!--vapor-flux-end-->'
    section='''<!--vapor-flux-start--><section aria-labelledby="flux-h"><h2 id="flux-h">Conservative vapor transport: a structural test</h2>
<p>An opt-in shared-face flux equation now accounts for both incoming and outgoing vapor. It disables the old separate positive convergence import. Heat keeps its existing solver; moisture has a separate checked solver and a regional ledger that includes boundary reservoirs, evaporation, vertical drying, storms and rain.</p>
<p>Five comparisons isolate import removal, storm conservation and the advection change. Of 35 attempts, <strong>31 pass and four nonlinear solves fail</strong>. All seven unchanged controls reproduce exactly. With conservative mean and storm transport, North India rises from <strong>256 to 482 mm/year</strong>, toward 761 mm observed.</p>
<p><strong>The climate candidate is rejected.</strong> Iberia, eastern Australia and Pacific NW become much too wet; Japan and Mexico fail the solve. No failed run enters an aggregate score or advances to later gates. A closed transport ledger is useful, but it does not establish accurate rainfall or a closed planetary water cycle.</p>
<figure><a href="data/vapor_flux.png"><img src="data/vapor_flux.png" width="1920" height="795" loading="lazy" alt="Conservative vapor pilot: Indian rain improves, several other regions worsen and two candidate regions fail the solver"></a><figcaption>Horizontal flux cancellation is near machine precision in successful conservative runs. This is a steady regional vapor equation with open borders and modeled vertical losses, not a transient atmosphere or a closed planet. Default physics and atlas climate data remain unchanged.</figcaption></figure>
<p><a href="data/vapor_flux.json" download>Download vapor-flux results and failed-solve records</a> · <a href="../../reports/VAPOR_FLUX_20261026.md">Transport method and experiment</a></p></section><!--vapor-flux-end-->'''
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_rejected_diagnostic',page_sha256=file_hash(page),
        image_sha256=file_hash(image),metadata_sha256=file_hash(data/'vapor_flux.json'),physics_or_atlas_climate_adoption=False))


if __name__=='__main__':main()
