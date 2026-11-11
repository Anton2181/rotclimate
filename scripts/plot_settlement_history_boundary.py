"""Show the declared boundary sweep and its location/spacing tradeoffs."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    result=json.loads((ROOT/'output/settlement_history_boundary_20261111/results.json').read_text())
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),facecolor='#f5f5ee')
    for ax in axes:
        ax.set_facecolor('#f5f5ee');ax.grid(alpha=.18)
        ax.spines[['top','right']].set_visible(False)
        ax.set_xlabel('Spatial history scale L (km)')
        ax.axvline(450,color='#777777',ls=':',lw=1)
    colors={.35:'#227c70',.5:'#ac7027'}
    for coef,color in colors.items():
        rows=sorted([r for r in result['ranking'] if r['variant'].startswith(f'draw_c{coef:g}_')],
                    key=lambda r:int(r['variant'].split('_L')[-1]))
        scales=[int(r['variant'].split('_L')[-1]) for r in rows]
        axes[0].plot(scales,[r['Q'] for r in rows],'-o',color=color,label=f'Spacing c={coef:g}')
        for pool,style in [('han','-'),('rome','--')]:
            label=f'{pool.title()}, c={coef:g}'
            axes[1].plot(scales,[r['pools'][pool]['unique_F1'] for r in rows],style+'o',color=color,label=label)
            axes[2].plot(scales,[r['pools'][pool]['M3'] for r in rows],style+'o',color=color,label=label)
    fixed=next(r for r in result['references'] if r['variant']=='greedy_18km_old_cores_L800')
    axes[0].axhline(fixed['Q'],color='#777777',ls='--',lw=1,label='Best fixed-spacing Q')
    for ax,title in zip(axes,['Combined development score Q ↑','Unique-site matching F1 ↑','Spacing discrepancy KS ↓']):
        ax.set_title(title,fontsize=12);ax.legend(fontsize=8,loc='best')
    axes[0].set_ylabel('Equal-pool, five-seed mean');axes[0].set_ylim(.45,.65)
    fig.suptitle('Shorter history scales do not improve the combined fit',x=.045,ha='left',fontsize=17,fontweight='bold')
    fig.text(.045,.89,'100 exposed development evaluations · fixed 1,202 Han / 1,292 Roman centre budgets · 20 overlap controls replay exactly',fontsize=10)
    fig.text(.045,.035,'450 km is now inside the tested range. This is spatial-prior sensitivity, not calibrated occupation age or proof of a global optimum.\nLocation and spacing tradeoffs remain; no production settlement, food or control change.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.065,right=.985,top=.78,bottom=.23,wspace=.26)
    out=ROOT/'reports/figures/settlement_history_boundary_20261111.png'
    fig.savefig(out,dpi=150,facecolor=fig.get_facecolor());plt.close(fig);print(out)


if __name__=='__main__':main()
