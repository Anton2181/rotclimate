"""Plots of the declared diagnostic and isolated physics-probe results."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PROBE=ROOT/'output/descent_continuity_20261102'
names=['tripolitania','north_india','manchuria','pacific_nw']
fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
for ax,name in zip(axes.flat,names):
 d=json.loads((HERE/f'{name}.json').read_text());p=json.loads((PROBE/f'{name}.json').read_text())
 obs=np.array(d['monthly_mm_day']['observed_rain'])*365/12
 raw=p['modes']['reference']['monthly_rain_mm'];alt=p['modes']['continuity']['monthly_rain_mm']
 ax.plot(range(1,13),obs,'o-',color='#222222',label='Observed (WorldClim)',ms=3)
 ax.plot(range(1,13),raw,color='#1c7c8a',label='r42')
 ax.plot(range(1,13),alt,'--',color='#bb6136',label='Continuity prototype')
 ax.set(title=name.replace('_',' ').title(),ylabel='Rain (mm / equal calendar month)',xticks=[1,3,5,7,9,11],xticklabels=['Jan','Mar','May','Jul','Sep','Nov'],ylim=(0,None))
 ax.grid(alpha=.15)
axes[0,0].legend(fontsize=9)
fig.suptitle('One physical hypothesis, tested on unchanged development footprints',fontsize=15)
fig.savefig(PROBE/'monthly_rain_comparison.png',dpi=150)
labels={'evaporation':'Evaporation','advection':'Advective tendency','diffusion':'Diffusion','storm_exchange':'Storm exchange','column_drying':'Column drying','convergence_import':'Convergence source'}
colors=['#4d9766','#3c80b0','#96b8d4','#9670a4','#a46e4d','#df9b33']
fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
seasons=[[11,0,1],[2,3,4],[5,6,7],[8,9,10]]
for ax,name in zip(axes,['tripolitania','north_india']):
 d=json.loads((HERE/f'{name}.json').read_text())['monthly_mm_day'];positive=np.zeros(4);negative=np.zeros(4)
 for (key,label),color in zip(labels.items(),colors):
  values=np.array([np.mean([d[key][i] for i in s]) for s in seasons]);bottom=np.where(values>=0,positive,negative)
  ax.bar(range(4),values,bottom=bottom,color=color,label=label,width=.65)
  positive+=np.maximum(values,0);negative+=np.minimum(values,0)
 for key,label,color,marker in [('rain','r42 rain','#222222','o'),('observed_rain','Observed rain','#c02d2d','x')]:
  ax.plot(range(4),[np.mean([d[key][i] for i in s]) for s in seasons],marker=marker,color=color,label=label,ms=6)
 ax.axhline(0,color='#555',lw=.6);ax.set(title=name.replace('_',' ').title(),xticks=range(4),xticklabels=['DJF','MAM','JJA','SON'],ylabel='Mean signed term (mm/day)')
handles,legend=axes[0].get_legend_handles_labels();fig.legend(handles,legend,loc='outside lower center',ncol=4,fontsize=9)
fig.suptitle('r42 steady column equation: contrasting desert and monsoon errors',fontsize=15)
fig.savefig(HERE/'seasonal_moisture_budget.png',dpi=150)
