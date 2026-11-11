"""Show the conditional role contrast and all declared coordinate scenarios."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    result=json.loads((ROOT/'output/settlement_role_contrast_20261111/results.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(12,5),facecolor='#f5f5ee')
    predictors=['uniform','environment','history_L450_intensity']
    labels=['Uniform baseline','Existing suitability score','History-weighted intensity']
    for ax in axes:
        ax.set_facecolor('#f5f5ee');ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
    for y,p in enumerate(predictors):
        global_=result['results'][0]['predictors'][p]['AUC'];local=result['spatial_blocks']['equal_block_mean_AUC'][p]
        axes[0].plot([global_,local],[y,y],color='#999999',lw=1)
        axes[0].scatter(global_,y+.04,color='#ac7027',marker='^',s=65,label='All represented cell/class units' if y==0 else None)
        axes[0].scatter(local,y-.04,color='#227c70',s=65,label='Equal 50 km blocks, both classes' if y==0 else None)
    axes[0].set_yticks(range(3),labels);axes[0].invert_yaxis();axes[0].set_xlim(.48,.64)
    axes[0].axvline(.5,color='#777777',ls='--');axes[0].set_xlabel('Conditional ranking AUC');axes[0].legend(fontsize=8,loc='upper right')
    axes[0].set_title('Central coordinate interpretation',fontsize=12)
    for key,color,label in [('environment','#ac7027','Existing suitability'),('history_L450_intensity','#227c70','History-weighted intensity')]:
        axes[1].plot(range(9),[r['predictors'][key]['AUC'] for r in result['results']],'-o',color=color,label=label)
    axes[1].axhline(.5,color='#777777',ls='--');axes[1].set_ylim(.49,.565)
    axes[1].set_xticks(range(9),['0','E−2','E+2','N−2','N+2','E−5','E+5','N−5','N+5'],rotation=40)
    axes[1].set_xlabel('Declared British-grid offsets (km)');axes[1].set_ylabel('Conditional ranking AUC');axes[1].legend(fontsize=8)
    axes[1].set_title('All coordinate scenarios retained',fontsize=12)
    fig.suptitle('Recorded settlement contexts: weak separation',x=.035,ha='left',fontsize=18,fontweight='bold')
    fig.text(.035,.88,'Nucleated versus farm/villa evidence · selected excavated archive · mixed cells retained · no parameter fitting',fontsize=10)
    fig.text(.035,.035,'AUC 0.5 means no ranking discrimination, not 50% of settlements correct. Block diagnostics are not held-out validation.\nThese whole-record contexts do not establish AD200 roles, population, political control or climate accuracy.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.21,right=.98,top=.78,bottom=.25,wspace=.35)
    out=ROOT/'reports/figures/settlement_role_contrast_20261111.png';fig.savefig(out,dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
    print(out)


if __name__=='__main__':main()
