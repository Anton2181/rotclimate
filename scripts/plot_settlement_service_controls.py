"""Plot a fixed one-day diagnostic, without selecting a winning scenario."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    result=json.loads((ROOT/'output/settlement_service_controls_20261111/results.json').read_text())
    masses=['uniform','environment','history_L450'];x=range(3)
    curves=[('__recorded_roads_B1__per_centre','One-day interaction, recorded roads','#227c70','-o'),
            ('__no_roads_B1__per_centre','One-day interaction, no roads','#526f9a','--o'),
            ('__zero_travel_per_centre','Zero travel: local demand / opportunities','#ac7027',':s'),
            ('__inverse_mass','Inverse opportunities only','#8c638c','-.^')]
    fig,axes=plt.subplots(2,2,figsize=(12,8.5),facecolor='#f5f5ee')
    for row,subset in enumerate(['full','strict_nonroadside']):
        for col in range(2):
            ax=axes[row,col];ax.set_facecolor('#f5f5ee')
            values=(result['subsets'][subset]['results'][0]['predictors'] if col==0 else
                    result['subsets'][subset]['spatial_blocks']['equal_block_mean_AUC'])
            get=lambda key:values[key]['AUC'] if col==0 else values[key]
            for suffix,label,color,style in curves:
                ax.plot(x,[get(m+suffix) for m in masses],style,color=color,label=label)
            ax.axhline(get('environment'),color='#555555',ls=':',label='Existing suitability')
            ax.axhline(.5,color='#bbbbbb',lw=.7)
            ax.set(xticks=list(x),xticklabels=['Uniform','Suitability','History L450'],ylim=(.3,.7))
            ax.margins(x=.13)
            ax.set_title(('Full contexts' if row==0 else 'All roadside tags excluded')+' · '+('global' if col==0 else 'within 50 km blocks'),fontsize=11)
            ax.set_ylabel('Conditional ranking AUC' if col==0 else 'Equal-block mean AUC')
            ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.15)
    fig.suptitle('Opportunity assumptions explain much of the global service gain',x=.055,ha='left',fontsize=16,fontweight='bold')
    fig.text(.055,.91,'Fixed illustration: one-day walking budget, central coordinates. All 66 predictors, nine coordinate cases and source strata exported.',fontsize=9)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.065),ncol=2,fontsize=9)
    fig.text(.055,.02,'Strict global history result: interaction 0.6453, inverse opportunities 0.6462. Local results remain below suitability.\nExposed archive contexts, not dated AD200 roles or independent validation. No predictor selected or adopted.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.075,right=.96,top=.855,bottom=.22,hspace=.34,wspace=.22)
    path=ROOT/'reports/figures/settlement_service_controls_20261111.png'
    fig.savefig(path,dpi=150,facecolor=fig.get_facecolor());plt.close(fig);print(path)


if __name__=='__main__':main()
