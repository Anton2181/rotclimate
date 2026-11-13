"""Separate collection omissions,return phases and complete mandatory work."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha
OUT=ROOT/'output/continuous_collection_calendar_20261112';COLORS=dict(A='#9a9b8f',B='#bc7450',C='#417d97')


def plot():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    keys=[case['key'] for case in r['cases']];matched={k:{v['accounting']:v for v in r['rows'] if v['key']==k} for k in keys};labels=[k.split('_load')[0].replace('_h',' · ').title()+'h' for k in keys];y=np.arange(4);figures=[]
    fig,axes=plt.subplots(1,2,figsize=(13,5.7))
    for j,account in enumerate('ABC'):
        for ax,field in zip(axes,['food_no_shortage','mandatory_and_food']):
            values=[matched[k][account][field] for k in keys];ax.barh(y+(j-1)*.24,values,height=.23,color=COLORS[account],label=account)
            for i,value in enumerate(values):ax.text(value+4,i+(j-1)*.24,str(value),va='center',fontsize=8)
    for ax in axes:ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlim(0,1000);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.set_xlabel('Providers · every active source retained')
    axes[0].set_title('Destination food diagnostic alone',fontsize=11);axes[1].set_title('ALL twelve mandatory bins AND food',fontsize=11)
    handles,names=axes[0].get_legend_handles_labels();fig.legend(handles,['A: all planned, bin starts','B: packed only, bin starts','C: packed only, job returns'],loc='lower center',bbox_to_anchor=(.5,.10),ncol=3,frameon=False,fontsize=9)
    fig.suptitle('NEW collection calendars: missing loads and return phases are separate tests',fontsize=12)
    fig.text(.5,.025,'Same new resident plans, staff, stores, funded home services, cargo and original one-bin lag. No visit jobs in these calendars.\nSix C entries pass food but fail mandatory work; food alone cannot repair a missing commitment.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.14,right=.99,top=.87,bottom=.26,wspace=.35)
    path=ROOT/'reports/figures/continuous_collection_calendar_counts_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);figures.append(path)
    fig,axes=plt.subplots(1,2,figsize=(13,5.8))
    for offset,account in [(-.16,'B'),(.16,'C')]:
        axes[0].barh(y+offset,[100*matched[k][account]['unmet']/matched[k][account]['needed'] for k in keys],height=.3,color=COLORS[account],label=account)
    lost=[];recovered=[]
    for key in keys:
        a=dict(np.load(OUT/key/'fields.npz'));active=a['active'];b=a['B__no_shortage'];c=a['C__no_shortage'];lost.append(int((active&b&~c).sum()));recovered.append(int((active&~b&c).sum()))
    axes[1].barh(y-.16,lost,height=.3,color='#bc7450',label='B pass → C fail');axes[1].barh(y+.16,recovered,height=.3,color='#417d97',label='B fail → C pass')
    for i,(loss,recovery) in enumerate(zip(lost,recovered)):
        axes[1].text(loss+.6,i-.16,str(loss),va='center',fontsize=9);axes[1].text(recovery+.6,i+.16,str(recovery),va='center',fontsize=9)
    for ax in axes:ax.set_yticks(y,labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_title('Aggregate energy gaps get smaller in C',fontsize=11);axes[0].set_xlabel('Unmet cereal energy / annual meals · percent');axes[0].legend(title='Same packed cargo',frameon=False,fontsize=9)
    axes[1].set_title('More individual providers nevertheless fail',fontsize=11);axes[1].set_xlabel('Provider food-status transitions · B to C');axes[1].set_xlim(0,max(lost)*1.2);axes[1].legend(frameon=False,fontsize=8,loc='lower right')
    fig.suptitle('An improved aggregate does not establish food sufficiency at every provider',fontsize=12)
    fig.text(.5,.025,'B → C changes only phase for the same packed shipments. A → B separately removes unpacked cargo.\nAll active providers are scored, including partial delivery. Numeric food gaps are scenarios, not observed hunger or authority.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.14,right=.99,top=.87,bottom=.19,wspace=.4)
    path=ROOT/'reports/figures/continuous_collection_calendar_phase_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);figures.append(path)
    return figures


if __name__=='__main__':
    for path in plot():print(path)
