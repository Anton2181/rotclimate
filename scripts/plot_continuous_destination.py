"""Paired old/new resident allocations and all provider changes."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha
OUT=ROOT/'output/settlement_continuous_destination_20261112'


def plot():
    r=json.loads((OUT/'comparison.json').read_text());review=json.loads((OUT/'comparison_review.json').read_text())
    assert review['status']=='passed' and review['comparison_sha256']==sha(OUT/'comparison.json')
    keys=list(dict.fromkeys(v['key'] for v in r['rows']));y=np.arange(4);labels=[key.split('_load')[0].replace('_h',' · ').title()+'h' for key in keys];paths=[]
    matched={k:{v['accounting']:v for v in r['rows'] if v['key']==k} for k in keys}
    fig,axes=plt.subplots(1,2,figsize=(12.5,5.3))
    for offset,account,color,label in [(-.16,'parent','#9a9b8f','Original monthly meals'),(.16,'continuous','#417d97','Continuous destination bins')]:
        axes[0].barh(y+offset,[matched[k][account]['town_people']/1000 for k in keys],height=.3,color=color,label=label)
        axes[1].barh(y+offset,[matched[k][account]['active_sources'] for k in keys],height=.3,color=color)
    for ax in axes:ax.set_yticks(y,labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_xlabel('Proposed town residents · thousands');axes[1].set_xlabel('Active institutional source scenarios')
    axes[0].set_title('Source food,field work and dispatch recomputed',fontsize=11);axes[1].set_title('One source fewer in each 300h case',fontsize=11)
    for i,key in enumerate(keys):
        old,new=matched[key]['parent'],matched[key]['continuous']
        axes[0].text(new['town_people']/1000+3,i,f'Δ{(new["town_people"]-old["town_people"])/1000:+.3f}',va='center',fontsize=9)
    axes[0].set_xlim(0,430)
    handles,names=axes[0].get_legend_handles_labels();fig.legend(handles,names,ncol=2,loc='lower center',bbox_to_anchor=(.5,.10),frameon=False)
    fig.suptitle('Continuous destination meals inside the SAME finite source/work resident feedback',fontsize=12)
    fig.text(.5,.025,'All four old and four new cases retained;no resident tuning,extra grain,free staff or altered geographic inputs.\nBin-start food passes do not qualify new collector-return timing;maps and defaults remain unchanged.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.12,right=.99,top=.86,bottom=.27,wspace=.4)
    path=ROOT/'reports/figures/settlement_continuous_destination_summary_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);paths.append(path)
    fig,axes=plt.subplots(2,2,figsize=(11.5,8),layout='constrained')
    for ax,key in zip(axes.flat,keys):
        f=dict(np.load(OUT/key/'fields.npz'));old=f['seeded_parent_total'];new=f['total'];delta=new-old;active=(old>0)|(new>0);lost=f['seeded_parent_active'] & ~f['active']
        ax.scatter(old[active],delta[active],s=8,color='#417d97',alpha=.6)
        if lost.any():ax.scatter(old[lost],delta[lost],s=55,color='#ba654c',marker='x',label='Old active source not retained');ax.legend(fontsize=8,frameon=False)
        ax.axhline(0,color='#8e918c',lw=.7);ax.set_title(key.split('_load')[0].replace('_',' '),fontsize=10)
        ax.set_xlabel('Original proposed residents at provider');ax.set_ylabel('New minus original residents');ax.grid(alpha=.15)
        ax.text(.03,.07,f'{len(new)} providers retained;{int((~active).sum())} at zero in both',transform=ax.transAxes,fontsize=8)
    fig.suptitle('Every provider retained;individual changes and threshold losses remain visible',fontsize=12)
    fig.supxlabel('Same 64-point resident scan,known staff threshold and bracket refinements. Zero sources are counted explicitly.\nA failed searched branch is not proof of absent communities or physical impossibility;these are conditional scenarios.',fontsize=9)
    path=ROOT/'reports/figures/settlement_continuous_destination_providers_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);paths.append(path)
    return paths


if __name__=='__main__':
    for path in plot():print(path)
