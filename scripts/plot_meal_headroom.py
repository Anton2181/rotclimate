"""All fixed-staff civilian meal bounds; no inferred population map."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha

OUT=ROOT/'output/network_visit_meal_headroom_20261112';COLORS=dict(B='#bc7450',C='#417d97')


def plot():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    a=dict(np.load(OUT/'fields.npz'));keys=list(dict.fromkeys(v['key'] for v in r['rows']));labels=[k.replace('_h',' · ').replace('_crew','h · crew ').title() for k in keys];y=np.arange(8);paths=[]
    fig,axes=plt.subplots(1,2,figsize=(13,5.8))
    for offset,account in [(-.16,'B'),(.16,'C')]:
        rows=[next(v for v in r['rows'] if v['key']==key and v['accounting']==account) for key in keys]
        axes[0].barh(y+offset,[v['civilian_meal_equivalent_reduction'] for v in rows],height=.3,color=COLORS[account],label=account)
        axes[1].barh(y+offset,[100*v['civilian_meal_equivalent_reduction']/v['parent_civilian'] for v in rows],height=.3,color=COLORS[account])
    for ax in axes:ax.set_yticks(y,labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_xlabel('Daily civilian meal equivalents · 2,500 kcal each');axes[0].set_title('Conditional bound under fixed shipments',fontsize=11)
    axes[1].set_xlabel('Civilian meal-equivalent reduction / original civilians · %');axes[1].set_title('Staff meals and original physical stores stay fixed',fontsize=11)
    handles,names=axes[0].get_legend_handles_labels();fig.legend(handles,names,title='B: bin starts · C: job returns',loc='lower center',bbox_to_anchor=(.5,.09),ncol=2,frameon=False,fontsize=9)
    fig.suptitle('Fixed-staff meal demand can be bounded; this does not replan residents or production',fontsize=12)
    fig.text(.5,.025,'All eight original scenarios, both delivery calendars, every qualified provider. Staff-only failures remain explicit.\nSource production, field work, exports and collector/visit jobs are frozen; these are not revised population estimates.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.19,right=.99,top=.88,bottom=.26,wspace=.65)
    path=ROOT/'reports/figures/network_visit_meal_headroom_summary_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);paths.append(path)
    fig,axes=plt.subplots(2,4,figsize=(14,6.6),layout='constrained')
    for ax,key in zip(axes.flat,keys):
        scored=a[key+'__scored'];counts=[]
        for account in 'BC':
            feasible=scored & a[f'{key}__{account}__staff_feasible'];values=np.sort(100*(1-a[f'{key}__{account}__passing_alpha'][feasible]));counts.append(int((scored & ~feasible).sum()))
            ax.plot(np.linspace(0,100,len(values)),values,color=COLORS[account],label=account,lw=1.3)
        ax.set_title(key.replace('_',' '),fontsize=10);ax.set_xlabel('Provider percentile');ax.set_ylabel('Civilian meal reduction · %');ax.set_ylim(bottom=0);ax.grid(alpha=.15)
        ax.text(.03,.05,f'Staff infeasible B/C: {counts[0]}/{counts[1]}',transform=ax.transAxes,fontsize=8)
    axes[0,0].legend(frameon=False,fontsize=8)
    fig.suptitle('Every provider is retained; conditional meal multipliers are bounded separately for B and C',fontsize=12)
    fig.supxlabel('Each curve orders its own providers. B/C are matched pulse calendars, not a policy selection.\nThe 48-step brackets are numerical bounds, not historical precision or population confidence intervals.',fontsize=9)
    path=ROOT/'reports/figures/network_visit_meal_headroom_providers_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);paths.append(path)
    return paths


if __name__=='__main__':
    for path in plot():print(path)
