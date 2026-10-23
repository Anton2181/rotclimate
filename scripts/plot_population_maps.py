"""Render the six default population maps with their shared data scales."""
import argparse
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,LogNorm,Normalize
from matplotlib.cm import ScalarMappable
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from population.export import DEFINITIONS,COLORS

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlas',type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    data=a.atlas/'data';m=json.loads((data/'population.json').read_text())
    fig,axes=plt.subplots(2,3,figsize=(18,8.5))
    for ax,(key,label,unit,lo,hi,log,palette) in zip(axes.flat,DEFINITIONS):
        ax.imshow(Image.open(data/('pop_'+key+'.webp')));ax.set_axis_off();ax.set_title(label,loc='left',fontsize=13)
        norm=LogNorm(lo,hi) if log else Normalize(lo,hi)
        bar=fig.colorbar(ScalarMappable(norm=norm,cmap=LinearSegmentedColormap.from_list(key,COLORS[palette])),ax=ax,
                         orientation='horizontal',fraction=.045,pad=.04)
        bar.set_label(unit,fontsize=9);bar.ax.tick_params(labelsize=8)
    fig.suptitle(f'Population lab · {a.atlas.name.replace("_"," ").title()} · {m["default_population"]/1e6:.3f} M supplied people',fontsize=18,y=.97)
    fig.text(.5,.038,'Scenario allocation within local support · Default attraction: water, terrain and walking access to named markets\nGrey walking cells have no overland market. No roads, ships, imports or reconstructed census are assumed.',ha='center',fontsize=11)
    fig.subplots_adjust(left=.025,right=.98,top=.87,bottom=.15,wspace=.12,hspace=.42)
    a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=150,facecolor='white');plt.close(fig)
