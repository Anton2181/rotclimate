"""Plot the completed fixed-candidate audit, including its uncertainty failure."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    out=ROOT/'output/r39_world_audit';path=out/'review.json'
    review=json.loads(path.read_text());transfer=review['transfer'];paired=transfer['paired']
    previous_path=ROOT/'output/r39_world_balance/previous_release.json'
    previous=json.loads(previous_path.read_text())['summary'];native=review['native'][0]['metrics']
    interval=transfer['bootstrap'];positive='#277349';negative='#b44c46'
    fig,axes=plt.subplot_mosaic([['paired','paired'],['mean','interval']],figsize=(11,7),constrained_layout=True)
    ax=axes['paired'];values=np.array([r['difference'] for r in paired]);x=np.arange(len(values))
    ax.bar(x,values,color=np.where(values>0,positive,negative));ax.axhline(0,color='#555555',lw=.8)
    ax.set(xticks=x,xticklabels=[str(r['seed']) for r in paired],ylabel='Candidate − r38 zone objective',
           title='Each prospective layout, paired against the same generated seed')
    ax.grid(axis='y',alpha=.15)
    ax=axes['mean']
    for y,a,b in [(1,previous['zonefit'],native['zonefit']),
                  (0,transfer['reference']['zonefit'],transfer['candidate']['zonefit'])]:
        ax.plot([a,b],[y,y],c='#aaaaaa',lw=2)
        ax.scatter(a,y,c='#666666',s=65,label='r38' if y==1 else None)
        ax.scatter(b,y,c=positive,s=65,label='r39 fixed candidate' if y==1 else None)
        ax.annotate(f'{a:.4f}',(a,y),xytext=(0,-18),textcoords='offset points',ha='center',fontsize=9)
        ax.annotate(f'{b:.4f}',(b,y),xytext=(0,10),textcoords='offset points',ha='center',fontsize=9)
    ax.set(yticks=[0,1],yticklabels=['New nine-layout\nmean (ds16)','Native layouts1–3\nmean (ds8)'],
        ylim=(-.55,1.65),xlabel='Zone objective',title='Actual scores of mean climate fields')
    ax.legend(loc='upper left',fontsize=8,frameon=False);ax.grid(axis='x',alpha=.15)
    ax=axes['interval'];mean=interval['mean']
    ax.errorbar(mean,0,xerr=np.array([[mean-interval['lower']],[interval['upper']-mean]]),
                fmt='o',color=negative,capsize=7,lw=2)
    ax.axvline(0,c='#555555',ls='--',lw=1);ax.set_yticks([])
    ax.set(xlabel='Mean individual-layout score gain',title='Paired bootstrap interval crosses zero')
    ax.text(.5,.8,f'Mean {mean:+.4f}\n2.5–97.5% bounds [{interval["lower"]:+.4f}, {interval["upper"]:+.4f}]',
            transform=ax.transAxes,ha='center',fontsize=10)
    ax.text(.5,.15,'Uncertainty gate failed',transform=ax.transAxes,ha='center',color=negative,fontsize=11)
    fig.suptitle('r39 fixed-candidate audit — not eligible for atlas publication',fontsize=15)
    fig.supxlabel('Nine new generated surroundings; no candidate selection or sample extension.\n'
                  'Mean individual score and score of the mean climate are different estimands. This is not real-planet validation.',fontsize=9)
    picture=out/'audit_results.png';fig.savefig(picture,dpi=155);plt.close(fig)
    (out/'audit_results.json').write_text(json.dumps(dict(inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,previous_path]},
        picture_sha256=hashlib.sha256(picture.read_bytes()).hexdigest()),indent=2)+'\n')


if __name__=='__main__':main()
