"""Illustrate directed hinterlands and trade with known-answer examples."""
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from polity.directed_trade import inbound_catchments, gravity_routes
from polity.trade import catchments, flows


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    net=SimpleNamespace(base=csr_matrix(([1.,10.,9.,2.],([0,1,2,1],[1,0,1,2])),shape=(3,3)),n_cells=3,n=3)
    old, _=catchments(net,[0,2],[10.,100.,20.])
    new, _=inbound_catchments(net,[0,2],[10.,100.,20.])
    fig,axes=plt.subplots(2,2,figsize=(13,8),gridspec_kw={'height_ratios':[1,1.1]})
    colors=['#3278b4','#c85f36']
    for ax,mass,owner,title in [(axes[0,0],old,0,'Historical catchment: town → village cost'),
                              (axes[0,1],new,1,'Inbound catchment: village → town cost')]:
        ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');ax.set_title(title,fontsize=12)
        for x,label,c in [(.12,'Town A\n10 people',colors[0]),(.5,'Village\n100 people',colors[owner]),(.88,'Town B\n20 people',colors[1])]:
            ax.add_patch(FancyBboxPatch((x-.09,.35),.18,.3,boxstyle='round,pad=.01',facecolor=c,alpha=.18,edgecolor=c,lw=2))
            ax.text(x,.5,label,ha='center',va='center',fontsize=11)
        for x1,x2,label in [(.23,.39,'A → village: 1\nvillage → A: 10'),(.61,.77,'village → B: 2\nB → village: 9')]:
            ax.annotate('',xy=(x2,.74),xytext=(x1,.74),arrowprops=dict(arrowstyle='<->',color='#555'))
            ax.text((x1+x2)/2,.92,label,ha='center',va='center',fontsize=9)
        ax.text(.5,.12,f'People assigned to A: {mass[0]:.0f} · B: {mass[1]:.0f}',ha='center',fontsize=11)
    ax=axes[1,0]
    x=np.arange(2);w=.32
    ax.bar(x-w/2,old,w,label='Historical',color='#a8b2bb');ax.bar(x+w/2,new,w,label='Inbound',color=colors)
    ax.set(xticks=x,xticklabels=['Town A','Town B'],ylabel='Catchment people',title='Population is conserved; the receiving town changes')
    ax.legend(frameon=False)
    net=SimpleNamespace(base=csr_matrix(([1.,10.],([0,1],[1,0])),shape=(2,2)),n_cells=2,n=2)
    totals=[flows([net],[0,1],[10.,20.],scale=100.)[2].sum(),
            flows([net],[1,0],[20.,10.],scale=100.)[2].sum()]
    a,b,v=gravity_routes([net],[0,1],[10.,20.],scale=100.)
    ax=axes[1,1]
    ax.barh([2,1],totals,color='#a8b2bb')
    ax.barh(0,v[(a==0)&(b==1)].sum(),color=colors[0],label='A → B')
    ax.barh(0,v[(a==1)&(b==0)].sum(),left=v[(a==0)&(b==1)].sum(),color=colors[1],label='B → A')
    ax.set(yticks=[2,1,0],yticklabels=['Historical: A listed first','Historical: B listed first','Directed: either order'],
           xlabel='Relative gravity weights (not tonnes)',title='Town record order must not choose the shipping direction')
    ax.legend(frameon=False,loc='lower right')
    fig.suptitle('Why river and sailing direction matter for the economic model',fontsize=16)
    fig.text(.5,.015,'Manufactured examples with declared costs, not Earth validation or a new population estimate.\n'
             'Directed gravity counts both ordered shipments; historical totals count one arbitrarily selected direction.',
             ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,.94])
    out=ROOT/'output/directed_trade_20261025/direction_contracts.png';out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(out,dpi=145);plt.close(fig);print(out)


if __name__=='__main__':main()
