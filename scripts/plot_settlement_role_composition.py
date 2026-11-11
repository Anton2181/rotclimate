"""Display fixed predictors across all support-qualified source subgroups."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    result=json.loads((ROOT/'output/settlement_role_composition_20261111/results.json').read_text())
    predictors=[('environment','Existing suitability','#555555','o'),('history_L450_intensity','Existing history intensity','#526f9a','s'),
        ('history_L450__inverse_mass','Inverse historical opportunities','#8c638c','^'),
        ('history_L450__recorded_roads_B1__per_centre','Historical opportunities: one-day service','#227c70','D')]
    groups=['village_only','vicus_only','roadside_only'];fig,axes=plt.subplots(2,2,figsize=(12,8.5),facecolor='#f5f5ee')
    for row,cohort in enumerate(['full','strict_nonroadside']):
        for col in [0,1]:
            ax=axes[row,col];ax.set_facecolor('#f5f5ee')
            for offset,(key,label,color,marker) in zip(np.linspace(-.15,.15,4),predictors):
                for i,group in enumerate(groups):
                    case=result['cases'][cohort+'__'+group]
                    if not case['results']:continue
                    value=case['results'][0]['predictors'][key]['AUC'] if col==0 else case['spatial_blocks']['equal_block_mean_AUC'][key]
                    ax.scatter(i+offset,value,color=color,marker=marker,s=38,label=label if i==0 else None)
            ax.axhline(.5,lw=.8,color='#aaaaaa');ax.set(xticks=[0,1,2],xticklabels=['Village labels','Vicus labels','Roadside-only labels'],ylim=(.1,.95),xlim=(-.4,2.4))
            if row==1:ax.text(2,.2,'Excluded by\nstrict definition',ha='center',fontsize=9,color='#777777')
            ax.set_title(('Full contexts' if row==0 else 'Every roadside tag excluded')+' · '+('global' if col==0 else '50 km block means'),fontsize=11)
            ax.set_ylabel('Conditional ranking AUC' if col==0 else 'Equal-block mean AUC');ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.065),ncol=2,fontsize=9)
    fig.suptitle('Villages and vici do not share one ecological ranking',x=.055,ha='left',fontsize=17,fontweight='bold')
    fig.text(.055,.91,'Central coordinates; one-day recorded-road service shown as a fixed illustration. All 66 predictors and nine coordinate cases exported.',fontsize=9)
    fig.text(.055,.02,'Full positive cell/class units: village 47, vicus 47, roadside-only 154; strict: 46, 44, 0. Small-town and mixed-label groups fail the fixed gate.\nWhole-record selected-archive contexts, not dated AD200 roles. No fitting, predictor selection, garrison or control assignment.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.075,right=.97,top=.855,bottom=.22,hspace=.34,wspace=.22)
    path=ROOT/'reports/figures/settlement_role_composition_20261111.png';fig.savefig(path,dpi=150,facecolor=fig.get_facecolor());plt.close(fig);print(path)


if __name__=='__main__':main()
