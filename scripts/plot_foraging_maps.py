"""Render a fixed comparison of the four separate foraging scenario modes."""
from pathlib import Path
import argparse
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from foraging.export import MODES as DEFINITIONS, PALETTES
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
from matplotlib.cm import ScalarMappable
from PIL import Image
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from foraging.export import PALETTES
MODES=[('forage_density','Foraging density'),('forage_effort','Foraging effort'),
       ('forage_shortfall','Intake shortfall'),('forage_carnivory','Meat-energy share')]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plot(atlas_root,out):
    names=['free_fit','earth_fit','whittaker_fit'];labels=['Free fit','Earth fit','Whittaker fit']
    fig,axes=plt.subplots(3,4,figsize=(19,9.2));sources={};summaries={}
    for i,(name,label) in enumerate(zip(names,labels)):
        data=atlas_root/name/'data';metadata=json.loads((data/'foraging.json').read_text())
        summaries[name]=metadata['summary']
        for j,(key,title) in enumerate(MODES):
            file=data/(key+'.webp');sources[str(file)]=sha(file)
            axes[i,j].imshow(Image.open(file));axes[i,j].set(xticks=[],yticks=[])
            for spine in axes[i,j].spines.values():spine.set_visible(False)
            if i==0:axes[i,j].set_title(title,fontsize=13)
            if j==0:
                text=(f'{label}\n{metadata["summary"]["total_scenario_people"]/1e6:.2f} M scenario people\n'
                      f'{100*metadata["summary"]["converged_land_share"]:.1f}% annual-state convergence')
                axes[i,j].text(-.035,.5,text,transform=axes[i,j].transAxes,ha='right',va='center',fontsize=10)
    fig.suptitle('Adapted FORGE wild-food scenarios · up to 300 years, final 50-year means',fontsize=17)
    fig.subplots_adjust(left=.135,right=.99,bottom=.20,top=.89,hspace=.12,wspace=.04)
    colorbars=[('density_people_km2',LogNorm(.001,10.),[.001,.01,.1,1,10],'people/km²'),
        ('foraging_hours_day',Normalize(0,8),[0,2,4,6,8],'hours/person/day'),
        ('scarcity_days_year',Normalize(0,365),[0,90,180,270,365],'days/year, including reserve drawdown'),
        ('meat_fraction',Normalize(0,1),[0,.25,.5,.75,1],'fraction of consumed food energy')]
    for j,(key,norm,ticks,unit) in enumerate(colorbars):
        box=axes[2,j].get_position();cax=fig.add_axes([box.x0,.145,box.width,.012])
        cmap=LinearSegmentedColormap.from_list(key,PALETTES[key])
        bar=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=cax,orientation='horizontal',ticks=ticks)
        bar.ax.tick_params(labelsize=8);bar.set_label(unit,fontsize=8)
        if key=='density_people_km2':bar.ax.set_xticklabels(['0.001','0.01','0.1','1','10'])
    fig.text(.55,.018,'Same climate packets; separate area-averaged 116 × 250 analysis. Miami NPP, grass allocation, prey supply and plant turnover are explicit proxies.\n'
        'These are finite-horizon foraging scenarios, not agricultural population totals, validated carrying capacities or a ranking of development.\n'
        'Shortfall counts intake below expenditure, including ordinary reserve drawdown; multiyear population cycles may remain unconverged.',ha='center',fontsize=9)
    out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(out,dpi=145);plt.close(fig)
    result=dict(status='passed',figure_sha256=sha(out),sources_sha256=sources,
                script_sha256=sha(Path(__file__)),summaries=summaries)
    out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='passed',figure=str(out),sha256=result['figure_sha256']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atlases',type=Path,default=ROOT/'atlases')
    parser.add_argument('--out',type=Path,default=ROOT/'output/foraging_20261027/foraging_comparison.png')
    args=parser.parse_args();plot(args.atlases,args.out)
