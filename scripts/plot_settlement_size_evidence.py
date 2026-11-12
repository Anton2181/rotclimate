"""Show housing sample exposure and distinct same-place size estimates."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha


def main():
    folder=ROOT/'output/settlement_size_evidence_20261112'
    result=json.loads((folder/'results.json').read_text());review=json.loads((folder/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(folder/'results.json')
    rows=sorted(result['rows'],key=lambda r:r['sample_fraction']);s=result['summary']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,(ax,bx)=plt.subplots(1,2,figsize=(13.5,6),gridspec_kw={'width_ratios':[1.1,1]})
    fig.patch.set_facecolor('#f5f3ed')
    for a in (ax,bx):a.set_facecolor('#f5f3ed')
    for province,color,label in [('Britannia','#ad643b','Britannia (10)'),('Other','#467c88','Other provinces (40)')]:
        keep=np.array([(r['province']=='Britannia')==(province=='Britannia') for r in rows])
        ax.scatter((np.arange(50)+1)[keep],np.array([r['sample_fraction']*100 for r in rows])[keep],
                   c=color,s=38,label=label,zorder=3)
    ax.set_yscale('log');ax.set_ylim(.015,150);ax.set_xlabel('Source records, ordered by investigated fraction')
    ax.set_ylabel('Investigated sample / stated site area (%)')
    ax.set_title('50 property samples; median coverage 1.11%',loc='left',fontsize=12)
    ax.axhline(1,color='#a7a6a0',lw=1,ls='--');ax.axhline(10,color='#a7a6a0',lw=1,ls=':')
    ax.text(2,55,'24 below 1%\n39 below 10%\n2 cover the stated extent',va='top',fontsize=10)
    ax.grid(axis='y',alpha=.15);ax.legend(loc='lower right',frameon=False)
    bx.set_title('Silchester: one place, three evidence paths',loc='left',fontsize=12)
    labels=['Visible properties\nphase composite','Sample extrapolation\nlate first century','Infrastructure regression\nlater Roman period']
    values=[930,3600,5500];colors=['#899087','#ad643b','#467c88']
    bx.barh([2,1,0],values,height=.45,color=colors,alpha=.85)
    bx.errorbar(5500,0,xerr=[[1000],[1400]],fmt='none',color='#253b42',capsize=5,lw=1.5)
    for y,v in zip([2,1,0],values):bx.text(v+130,y+.29,f'{v:,}',va='center',fontsize=11)
    bx.set_yticks([2,1,0],labels);bx.set_xlim(0,7600);bx.set_ylim(-.65,3.1)
    bx.set_xlabel('Conditional / reported residents')
    bx.grid(axis='x',alpha=.15);bx.set_axisbelow(True)
    bx.text(.02,.98,'Housing paths assume 5 people/property.\nWhisker: authors’ reported 95% interval\nfor infrastructure estimate only.',
            transform=bx.transAxes,va='top',fontsize=9,color='#4c5856')
    fig.suptitle('Housing evidence constrains measurement before resident-size fitting',x=.055,ha='left',fontsize=16,y=.98)
    fig.text(.055,.05,'All 50 records retained. No AD150 size labels yet pass phase, extent and representativeness gates.\nSource: Ortman & Hanson (2023), Britannia 54, Tables 1–2 and conclusions · doi:10.1017/S0068113X23000375 · CC BY 4.0',fontsize=9,color='#445451')
    fig.subplots_adjust(left=.07,right=.98,top=.82,bottom=.22,wspace=.65)
    path=ROOT/'reports/figures/settlement_size_evidence_20261112.png';fig.savefig(path,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    print(path)


if __name__=='__main__':main()
