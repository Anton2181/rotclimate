"""Show where the legacy institutional-staff scenario obtains its providers."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    data=json.loads((ROOT/'output/institution_evidence_20261111/provider_audit.json').read_text())
    names=list(data['atlases']['corrected']['actors']);fig,axes=plt.subplots(1,2,figsize=(13,8),facecolor='#f5f5ee')
    y=np.arange(len(names))
    for ax,climate in zip(axes,['raw','corrected']):
        rows=data['atlases'][climate]['actors'];marked=[];generated=[]
        for name in names:
            row=rows[name];denom=row['legacy_staff']
            marked.append(100*row['staff_at_marked_sites']/denom if denom else 0)
            generated.append(100*row['staff_at_generated_sites']/denom if denom else 0)
        ax.set_facecolor('#f5f5ee');ax.barh(y,marked,color='#227c70',label='At marked sites')
        ax.barh(y,generated,left=marked,color='#c99a58',label='At proposed sites with claim hypotheses')
        ax.set(yticks=y,yticklabels=names,xlim=(0,100),xlabel='Share of legacy institutional cohort (%)')
        ax.invert_yaxis();ax.tick_params(axis='y',labelsize=9);ax.spines[['top','right']].set_visible(False)
        ax.set_title(('Raw' if climate=='raw' else 'Corrected')+f' · {100*data["atlases"][climate]["fraction_of_staff_at_generated_sites"]:.2f}% at proposed sites',fontsize=11)
        ax.text(1,len(names)-1,'No staff in this scenario;\nunresolved is not absence of governance.',fontsize=8,va='center',color='#555555')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.07),ncol=2,fontsize=9)
    fig.suptitle('Most current institutional staff come from proposed-site hypotheses',x=.035,ha='left',fontsize=16,fontweight='bold')
    fig.text(.035,.91,'Fixed year-store case. All 18 actors and unresolved affiliation retained. Marked affiliation is also not a measured staff quantity.',fontsize=10)
    fig.text(.035,.025,'Legacy scenario totals: 98,700 raw / 101,100 corrected. Symbols and painted claims do not establish dated institutions, professional roles or troop strength.\nNo staffing, residents, food or control changed. Non-imperial and tribal actors without marked sources remain unqualified, not ungoverned.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.15,right=.97,top=.85,bottom=.22,wspace=.55)
    path=ROOT/'reports/figures/institution_provider_audit_20261111.png';fig.savefig(path,dpi=150,facecolor=fig.get_facecolor());plt.close(fig);print(path)


if __name__=='__main__':main()
