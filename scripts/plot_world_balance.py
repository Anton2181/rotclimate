"""Show the actual native tree/Mediterranean tradeoff and the selected prediction."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


def main():
    out=ROOT/'output/r39_world_balance'
    paths=[ROOT/'output/r39_world_transfer/review.json',out/'review.json',
           out/'selection.json',ROOT/'output/atlas_r38/earth_publication.json']
    parent,review,selection,publication=[json.loads(p.read_text()) for p in paths]
    if not review['complete'] or not review['native']:raise ValueError('Actual native result is required')
    reference=publication['published']
    maximum=100*(reference['mediterranean']['dry_share']+.005)
    minimum=100*(reference['recall']['tree']-.02)
    native=review['native'][0]
    if 'metrics' not in native:raise ValueError('No completed native climate')
    chosen=next(r for r in review['screen'] if r['name']==selection['selected'])
    xy=lambda m:(100*m['mediterranean']['dry_share'],100*m['recall']['tree'])
    prediction=xy(chosen['prediction']);actual=xy(native['metrics'])
    points=[xy(r['metrics']) for r in parent['native']]+[prediction,actual]
    xmin=min(x for x,y in points)-.65;xmax=max(x for x,y in points)+.85
    ymin=min(y for x,y in points)-.6;ymax=max(y for x,y in points)+.65
    fig,ax=plt.subplots(figsize=(9,6),constrained_layout=True)
    ax.add_patch(Rectangle((xmin,minimum),maximum-xmin,ymax-minimum,facecolor='#e8f3e9',zorder=0))
    ax.axvline(maximum,color='#668866',ls='--',lw=1)
    ax.axhline(minimum,color='#668866',ls='--',lw=1)
    ax.text(xmin+.08,ymax-.12,'Within these two protections',va='top',fontsize=10,color='#315f36')
    for r,offset in zip(parent['native'],[(-8,-35),(9,8)]):
        x,y=xy(r['metrics']);ax.scatter(x,y,c='#b44c46',s=90,zorder=3)
        label=r['name'].replace('native_','Candidate ')+f'\nZone fit {r["metrics"]["zonefit"]:.4f}'
        ax.annotate(label,(x,y),xytext=offset,textcoords='offset points',
                    ha='right' if offset[0]<0 else 'left',fontsize=10)
    ax.scatter(*prediction,facecolor='white',edgecolor='#777777',marker='D',s=90,zorder=3)
    color='#277349' if not native['failures'] else '#b44c46'
    ax.scatter(*actual,c=color,marker='*',s=240,zorder=4)
    ax.annotate('',xy=actual,xytext=prediction,arrowprops=dict(arrowstyle='->',color='#777777',lw=1))
    ax.annotate('Balanced geography'+f'\nZone fit {native["metrics"]["zonefit"]:.4f}',actual,
                xytext=(10,12),textcoords='offset points',fontsize=11,color=color)
    ax.set(xlim=(xmin,xmax),ylim=(ymin,ymax),
        xlabel='Mediterranean target classified dry (%) — lower is better\nOnly these two regional protections are plotted; all other publication checks also apply.',
        ylabel='Tree-zone recall (%) — higher is better')
    status=('Passed native and additional-layout checks' if review['eligible_for_publication'] else
            'Not eligible for publication')
    ax.set_title('Fixed planet, fixed r39 physics: balancing the world geography\n'+status,pad=14)
    ax.grid(alpha=.15)
    handles=[Line2D([],[],marker='o',color='none',markerfacecolor='#b44c46',markersize=8,label='Rejected native endpoints'),
        Line2D([],[],marker='D',color='none',markeredgecolor='#777777',markerfacecolor='white',markersize=7,label='Selected case: predicted native metrics'),
        Line2D([],[],marker='*',color='none',markerfacecolor=color,markersize=13,label='Selected case: actual native metrics')]
    fig.legend(handles=handles,loc='outside lower center',ncol=1,fontsize=9,frameon=False)
    picture=out/'native_balance.png';fig.savefig(picture,dpi=155);plt.close(fig)
    (out/'native_balance.json').write_text(json.dumps(dict(diagnostic_only=True,
        inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        picture_sha256=hashlib.sha256(picture.read_bytes()).hexdigest()),indent=2)+'\n')


if __name__=='__main__':main()
