"""Export the Earth-corrected hierarchy comparison with explicit legends."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from PIL import Image
    from local_benchmark_protocol import file_hash
    data=ROOT/'atlases/earth_fit/data'
    manifest=json.loads((data/'administrative_hierarchy.json').read_text());packet=manifest['packets']['corrected']
    views={v['value']:v for v in packet['layers'][0]['variants']['options']}
    fig,axes=plt.subplots(2,2,figsize=(14,8),facecolor='#f8faf9')
    keys=['local_marked','chain_marked','chain_proposed','proposed_gain']
    titles=['Provincial reply · marked interchanges','Imperial reply via province · marked interchanges',
        'Imperial reply via province · proposed transport','Worst imperial reply · days saved by proposed transport']
    for ax,key,title in zip(axes.ravel(),keys,titles):
        view=views[key];path=data/view['file']
        if file_hash(path)!=packet['image_sha256'][view['file']]:raise ValueError('Hierarchy map changed')
        ax.imshow(Image.open(path));ax.axis('off');ax.set_title(title,loc='left',fontsize=11,pad=8)
        ax.legend(handles=[Patch(facecolor=v['color'],label=v['label']) for v in view['items'][:6]],
            loc='upper center',bbox_to_anchor=(.5,-.005),ncol=3,fontsize=8,frameon=False,columnspacing=1)
    fig.suptitle('Communication through the recorded provincial hierarchy',x=.04,ha='left',fontsize=18,y=.985)
    fig.text(.04,.935,'Earth-corrected climate · coloured dots: recorded seats · outer rings: provincial capitals · connectors are schematic, not routes',fontsize=10)
    fig.subplots_adjust(left=.035,right=.985,bottom=.19,top=.88,hspace=.33,wspace=.04)
    medians=[s['median_worst_reply_days'] for s in packet['summaries']]
    fig.text(.04,.025,f'Median worst-season imperial reply among 69 noncapital seats: {medians[0]:.1f} days marked → {medians[1]:.1f} days proposed.\n'
        'Travel-only snapshots hold seasonal conditions fixed throughout the reply. No courier relays, processing delays, provisioning or control inferred.\n'
        '70 of 72 seats located; Kudā and the disputed Thalamâtâs/Pitané seat remain unresolved. Provincial self-links are zero, not hinterland coverage.',fontsize=9)
    output=ROOT/'output/administrative_hierarchy_20261104/communication_comparison.png'
    fig.savefig(output,dpi=160,facecolor=fig.get_facecolor());plt.close(fig);print(output)


if __name__=='__main__':main()
