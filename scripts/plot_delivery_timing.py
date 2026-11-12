"""Show every matched destination timing outcome and deterministic stock examples."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.event_food_stocks import _flow
from harvest.food_stocks import food_year
from settlement_locations_earth import sha

OUT=ROOT/'output/network_visit_delivery_timing_20261112'
COLORS=dict(A='#8b8c83',B='#bc7450',C='#417d97')


def trace(times,cargo,initial,rate,capacity):
    h=-np.log(.95)/365;stock=initial;previous=0.;xx=[0.];yy=[stock]
    for time,q in list(zip(times,cargo))+[(365.,0.)]:
        for instant in np.linspace(previous,time,16)[1:]:
            value=_flow(stock,instant-previous,rate,h)[0];xx.append(instant);yy.append(value)
        stock=_flow(stock,time-previous,rate,h)[0];stock=min(capacity,stock+q)
        xx.append(time);yy.append(stock);previous=time
    return np.array(xx),np.array(yy)/rate


def plot():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    a=dict(np.load(OUT/'fields.npz'));keys=list(dict.fromkeys(v['key'] for v in r['rows']));figures=[]
    matched={key:{v['accounting']:v for v in r['rows'] if v['key']==key} for key in keys}
    labels=[key.replace('_h',' · ').replace('_crew','h · crew ').title() for key in keys];y=np.arange(8)
    fig,axes=plt.subplots(1,2,figsize=(13,5.7))
    for j,account in enumerate('ABC'):
        gap=[100*matched[k][account]['unmet']/matched[k][account]['needed'] for k in keys]
        axes[0].barh(y+(j-1)*.23,gap,height=.22,color=COLORS[account],label=dict(A='A: original bins',B='B: continuous, bin starts',C='C: continuous, job returns')[account])
    changes=[]
    for key in keys:
        b,c=matched[key]['B'],matched[key]['C'];changes.append(100*(c['unmet']-b['unmet'])/b['needed'])
    axes[1].barh(y,changes,color=COLORS['C'])
    for i,value in enumerate(changes):axes[1].text(value-.0004,i,f'{value:+.4f}',ha='right',va='center',fontsize=8)
    axes[1].set_xlim(min(changes)*1.5,.001)
    for ax in axes:ax.set_yticks(y,labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_xlabel('Unmet cereal energy / annual meals · percent');axes[0].set_title('A → B changes inventory convention',fontsize=11)
    axes[1].set_xlabel('C minus B · percentage points of annual meals');axes[1].set_title('B → C isolates the declared arrival phase',fontsize=11)
    handles,names=axes[0].get_legend_handles_labels();fig.legend(handles,names,loc='lower center',bbox_to_anchor=(.5,.09),ncol=3,frameon=False,fontsize=9)
    fig.suptitle('Identical people and shipments; timing exposes gaps hidden by immediate monthly meals',fontsize=12)
    fig.text(.5,.02,'All eight fixed scenarios; all previously calendar-qualified providers scored. Original one-bin lag and 0.95 retention retained.\nDestination cereal inventory only; no observed hunger, source timing, crew ration/location or complete-diet claim.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.19,right=.99,top=.88,bottom=.25,wspace=.65)
    path=ROOT/'reports/figures/network_visit_delivery_timing_accountings_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);figures.append(path)
    fig,axes=plt.subplots(2,4,figsize=(14,6.5),layout='constrained')
    for ax,key in zip(axes.flat,keys):
        scored=a[key+'__scored'];need=a[key+'__C__needed'][scored]
        for account in 'BC':
            values=np.sort(100*a[f'{key}__{account}__unmet'][scored]/need)
            ax.plot(np.linspace(0,100,len(values)),values,color=COLORS[account],label=account,lw=1.3)
        ax.set_title(key.replace('_',' '),fontsize=10);ax.set_ylim(bottom=0);ax.grid(alpha=.15)
        ax.set_xlabel('Provider percentile');ax.set_ylabel('Unmet / meals · %')
        ax.text(.03,.08,f'{scored.sum()} scored; zero B/C pass',transform=ax.transAxes,fontsize=8)
    axes[0,0].legend(title='Inventory',frameon=False,fontsize=8)
    fig.suptitle('Every scored provider is retained, including all continuous-inventory shortfalls',fontsize=12)
    fig.supxlabel('Percentile ordering is separate for B and C; no providers are dropped or used to select a calendar.\nNumerical no-shortage diagnostic is the existing parent tolerance; it is not a historical famine threshold.',fontsize=9)
    path=ROOT/'reports/figures/network_visit_delivery_timing_providers_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);figures.append(path)
    fig,axes=plt.subplots(2,2,figsize=(13,7),layout='constrained')
    for i,mode in enumerate(('raw','corrected')):
        key=f'{mode}_h600_crew1';site=int(np.flatnonzero(a[key+'__scored'])[0]);rate=a[key+'__residents'][site]*2500;cap=a[key+'__capacity'][site]
        events=dict(np.load(OUT/f'{key}_events.npz'));mask=events['site']==site
        for account,times,cargo in [('B',np.arange(12)*365/12,a[key+'__arrivals'][:,site]),('C',events['time'][mask],events['cargo'][mask])]:
            xx,yy=trace(times,cargo,a[f'{key}__{account}__initial_stock'][site],rate,cap)
            axes[i,0].plot(xx,yy,color=COLORS[account],label=account,lw=1.)
        old=food_year(a[key+'__arrivals'][:,site],np.full(12,rate*365/12),cap,initial_stock=a[key+'__A__initial_stock'][site],loss_fraction_year=.05,step_days=365/12,record=True)
        axes[i,0].scatter(np.arange(13)*365/12,old.stock_path/rate,color=COLORS['A'],s=10,label='A bin-end stocks',zorder=3)
        axes[i,0].set_title(f'{mode.title()} · 600h · crew 1 · first qualified provider ID {site}',fontsize=10)
        axes[i,0].set_xlabel('Day in repeated year');axes[i,0].set_ylabel('Stored cereal / daily meals · days');axes[i,0].legend(fontsize=8,frameon=False,ncol=3)
        phase=np.mod(events['time'],365/12)
        axes[i,1].hist(phase,bins=np.linspace(0,365/12,31),weights=events['cargo']/events['cargo'].sum()*100,color=COLORS['C'])
        axes[i,1].set_title(f'{mode.title()} · all qualified providers in the same case',fontsize=10)
        axes[i,1].set_xlabel('Return phase inside the lagged arrival bin · days');axes[i,1].set_ylabel('Retained annual cargo · percent')
        for ax in axes[i]:ax.grid(alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('Continuous stock paths and recorded delivery phases; examples chosen by provider ID',fontsize=12)
    fig.supxlabel('A consumes the entire bin meal before capacity and decay; its end-stock markers are not a daily provisioning trajectory.\nB and C integrate the same continuous meals/decay; only delivery phase changes. Imposed one-bin transport lag stays fixed.',fontsize=9)
    path=ROOT/'reports/figures/network_visit_delivery_timing_stocks_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);figures.append(path)
    return figures


if __name__=='__main__':
    for path in plot():print(path)
