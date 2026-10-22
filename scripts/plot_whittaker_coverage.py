"""Compare original and coverage-constrained Whittaker atlas publications."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('before',type=Path);ap.add_argument('after',type=Path)
    ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    roots=[a.before,a.after];labels=['Original Whittaker fit','Whittaker fit with diagram-coverage guard']
    meta=[json.loads((p/'data/atlas.json').read_text()) for p in roots]
    summaries=[json.loads((p/'summary.json').read_text()) for p in roots]
    outside=[m['biomes'][0]['share']*100 for m in meta]
    fig,axes=plt.subplots(2,2,figsize=(15,8),gridspec_kw={'height_ratios':[2.1,1]})
    for i,(root,label) in enumerate(zip(roots,labels)):
        axes[0,i].imshow(Image.open(root/'data/whittaker.webp'));axes[0,i].set_axis_off()
        axes[0,i].set_title(f'{label}\n{outside[i]:.2f}% of source land outside the unchanged diagram',loc='left',fontsize=12)
    ax=axes[1,0];bars=ax.barh(['Original','Coverage fit'],outside,color=['#a6a8a8','#32786b']);ax.invert_yaxis()
    ax.set(xlabel='Source land outside diagram (%)',xlim=(0,max(outside)*1.17));ax.spines[['top','right']].set_visible(False)
    for bar,value in zip(bars,outside):ax.text(value+.12,bar.get_y()+bar.get_height()/2,f'{value:.2f}%',va='center')
    rows=[['Strict biome objective']+[f'{s["whittaker"]["strict"]["score"]:.4f}' for s in summaries],
          ['Mean exact target-biome match']+[f'{s["whittaker"]["strict"]["macro_hard"]:.1%}' for s in summaries],
          ['Seasonal zone objective']+[f'{s["zonefit"]:.4f}' for s in summaries],
          ['Exact seasonal-zone agreement']+[f'{s["strict_accuracy"]:.1%}' for s in summaries],
          ['Mediterranean Cs share']+[f'{s["mediterranean"]["cs_share"]:.1%}' for s in summaries]]
    axes[1,1].set_axis_off();table=axes[1,1].table(cellText=rows,colLabels=['Same measure','Original','Coverage fit'],loc='center',cellLoc='left',colWidths=[.6,.2,.2]);table.auto_set_font_size(False);table.set_fontsize(10);table.scale(1,1.45)
    fig.suptitle('Reducing unclassified land through the simulated climate',fontsize=18,y=.97)
    fig.text(.5,.025,'Same source terrain, envelopes and classifier · Mean climate over layouts 1–3 · Native downsample 8\nCoverage is a fit preference, not independent physical validation. Grey pixels remain unclassified.',ha='center',fontsize=10)
    fig.subplots_adjust(left=.05,right=.97,top=.9,bottom=.15,hspace=.18,wspace=.16)
    a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=160,facecolor='white');plt.close(fig)


if __name__=='__main__':main()
