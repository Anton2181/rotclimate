"""Compare the same c.200 AD settlement scenarios across the three climate fits."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,LogNorm,Normalize
from PIL import Image
from harvest.export import RAMPS


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlases',nargs='+',type=Path)
    ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    fig,axes=plt.subplots(len(a.atlases),2,figsize=(15,3.9*len(a.atlases)),squeeze=False)
    for row,root in enumerate(a.atlases):
        data=root/'data';m=json.loads((data/'harvest.json').read_text());s=m['summary']
        label={'free_fit':'Free fit','earth_fit':'Earth fit','whittaker_fit':'Whittaker fit'}.get(root.name,root.name)
        pop=s['population']['endemic']
        for col,file in enumerate(['land_density_central_endemic.webp','land_livability_endemic.webp']):
            axes[row,col].imshow(Image.open(data/file));axes[row,col].set_axis_off()
        axes[row,0].set_title(f'{label} · {pop["central"]/1e6:.1f} M people in central scenario\nFrontier–core scenarios: {pop["frontier"]/1e6:.1f}–{pop["core"]/1e6:.1f} M',fontsize=11,loc='left')
        axes[row,1].set_title(f'{label} · environmental settlement potential\nMixed food ceiling: {s["food_capacity"]/1e6:.1f} M people',fontsize=11,loc='left')
    fig.subplots_adjust(left=.025,right=.975,top=.91,bottom=.13,hspace=.3,wspace=.04)
    for x,palette,norm,label in [(.1,'people',LogNorm(.1,300),'Central scenario · people / km²'),(.58,'green',Normalize(0,100),'Settlement potential · 0–100')]:
        cax=fig.add_axes([x,.085,.32,.012]);bar=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=LinearSegmentedColormap.from_list(palette,RAMPS[palette])),cax=cax,orientation='horizontal')
        bar.set_label(label,fontsize=10);bar.ax.tick_params(labelsize=9)
    fig.suptitle('Land and people with low-input technology around 200 AD',fontsize=17,y=.98)
    fig.text(.5,.025,'Environmental malaria potential included. Population ranges are occupation scenarios, not confidence intervals.\nFood, clearing, water access and disease assumptions are documented in each atlas; these are not reconstructed censuses.',ha='center',fontsize=10)
    a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=160,facecolor='white');plt.close(fig)


if __name__=='__main__':main()
