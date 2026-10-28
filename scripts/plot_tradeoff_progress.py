"""Plot actual progress and parameter coverage; no model integrations."""
from pathlib import Path
import argparse,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def plot(out,target):
    protocol=json.loads((out/'protocol.json').read_text());p=protocol['plan']
    progress=json.loads((out/'progress.json').read_text());scores=progress['scores']
    updates=dict(p['profiles']);updates.update({x['name']:x['updates'] for x in progress['history'] if 'updates' in x})
    candidates=[x['name'] for x in progress['history'] if x['name'] in scores]
    wide=len(p['design']['bounds'])>3
    fig,axes=plt.subplots(2,3 if wide else 2,figsize=(17.7 if wide else 13,9.3),constrained_layout=True)
    pairs=([('eddy_rate','precip_tau_days'),('convective_rh','westerly_speed'),('subsidence_drying','monsoon_descent'),
            ('eddy_rate','westerly_speed'),('precip_tau_days','convective_rh')] if wide else
           [('eddy_rate','precip_tau_days'),('eddy_rate','convective_rh'),('precip_tau_days','convective_rh')])
    units={'eddy_rate':'Storm exchange rate (day⁻¹)','precip_tau_days':'Dynamic rain timescale (days)',
           'convective_rh':'Convective activation RH','westerly_speed':'Background westerly amplitude (m/s)',
           'subsidence_drying':'Legacy subsidence coefficient','monsoon_descent':'Legacy monsoon-descent coefficient'}
    valid=[n for n in candidates if scores[n].get('physical_admissible')]
    vals=[scores[n]['objective'] for n in valid];low=min(vals) if vals else 0.;high=max(vals) if vals else 1.
    if high-low<.02:
        center=.5*(low+high);low=center-.01;high=center+.01
    cmap=plt.get_cmap('viridis_r');norm=plt.Normalize(low,high)
    for ax,(a,b) in zip(axes.flat,pairs):
        ax.scatter([updates[n][a] for n in p['global_names']],[updates[n][b] for n in p['global_names']],s=42,facecolors='none',edgecolors='#bbb',label='Declared global points')
        for stage,marker in [('global','o'),('local','^')]:
            names=[n for n in valid if n.startswith(stage)]
            if names:ax.scatter([updates[n][a] for n in names],[updates[n][b] for n in names],c=[scores[n]['objective'] for n in names],norm=norm,cmap=cmap,marker=marker,s=70,edgecolors='#222',linewidths=.5,label=stage.title()+' completed')
        failed=[n for n in candidates if not scores[n].get('physical_admissible')]
        if failed:ax.scatter([updates[n][a] for n in failed],[updates[n][b] for n in failed],marker='x',c='#b4373b',s=70,label='Physical/numerical rejection')
        base=next((r['params'] for r in progress['records'] if r['name']=='environment_control'),None)
        if base is not None:ax.scatter([base[a]],[base[b]],marker='D',color='#777',s=65,label='Old environmental control')
        for key,axis in [(a,'x'),(b,'y')]:
            if p['design']['bounds'][key]['scale']=='log':
                getattr(ax,'set_'+axis+'scale')('log')
                getattr(ax,axis+'axis').set_minor_formatter(NullFormatter())
            getattr(ax,'set_'+axis+'lim')(*p['design']['bounds'][key]['range'])
            if key=='eddy_rate':getattr(ax,'set_'+axis+'ticks')([.4,.6,1,1.5,2.5,3.5],labels=['0.4','0.6','1','1.5','2.5','3.5'])
            elif key=='precip_tau_days':getattr(ax,'set_'+axis+'ticks')([3,5,10,20,35],labels=['3','5','10','20','35'])
        ax.set(xlabel=units[a],ylabel=units[b]);ax.grid(alpha=.12)
        if valid:
            best=min(valid,key=lambda n:scores[n]['objective']);ax.annotate(best,(updates[best][a],updates[best][b]),xytext=(6,6),textcoords='offset points',fontsize=8)
    axes.flat[0].legend(frameon=False,fontsize=7)
    if valid:fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=list(axes.flat[:len(pairs)]),shrink=.7,label='Penalized research objective · lower is better')
    ax=axes.flat[-1]
    positions=[candidates.index(n)+1 for n in valid]
    ax.plot(positions,[scores[n]['objective'] for n in valid],'o-',ms=4,label='Objective including regret')
    ax.plot(positions,[scores[n]['mean_combined_ratio'] for n in valid],'s-',ms=3,label='Mean combined climate error / r39')
    if valid:ax.plot(positions,np.minimum.accumulate([scores[n]['objective'] for n in valid]),color='#222',lw=1.6,label='Best objective so far')
    ax.axhline(1,color='#777',ls=':',lw=.8,label='r39 mean climate ratio')
    historical=out/'historical_policy_diagnostic.json'
    if historical.exists():
        old=json.loads(historical.read_text())['scores']
        old_best=min((s['objective'] for n,s in old.items() if n!='environment_control' and s.get('physical_admissible')),default=None)
        if old_best is not None:ax.axhline(old_best,color='#995c35',ls='--',lw=1,label='Best previous factorial · same objective')
    ax.set(xlabel='Completed candidate profiles (seven regions each)',ylabel='Error / research objective',title='No skill veto during exploration');ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=8)
    if len(candidates)<10:ax.set_xticks(range(1,len(candidates)+1))
    count=len(progress['records']);passed=sum(r['status']=='passed' for r in progress['records'])
    title=p.get('publication_title','Global rainfall exploration')
    fig.suptitle(f'{title} · {count} actual integrations, {passed} numerical passes',fontsize=16)
    fig.supxlabel(('Completed bounded search. ' if progress['complete'] else 'Provisional search record. ')+
        'Empty circles are predeclared Sobol points; '+('local triangles follow frozen adaptive rules.\n' if p['design']['local_poll_order'] else 'no local proposals.\n')+
        'Skill tradeoffs remain visible; numerical/physical failures cannot be traded away. No global-optimum or adoption claim.',fontsize=9)
    target.parent.mkdir(parents=True,exist_ok=True);fig.savefig(target,dpi=145);plt.close(fig)
    result=dict(status='rendered',complete=progress['complete'],actual_integrations=count,valid_candidate_profiles=len(valid),
        protocol_sha256=sha(out/'protocol.json'),progress_sha256=sha(out/'progress.json'),script_sha256=sha(Path(__file__)),image_sha256=sha(target))
    if historical.exists():result['historical_diagnostic_sha256']=sha(historical)
    target.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--image',type=Path,required=True)
    a=ap.parse_args();plot(a.out,a.image)
