"""Static, reviewed annual grain-support comparison on the fixed town locations."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_candidate_supply_20261116'
BASE=ROOT/'output/urban_hierarchy_candidate_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    presentation=json.loads((BASE/'presentation.json').read_text())
    assert presentation['files_sha256']['terrain.png']==sha(BASE/'terrain.png')
    terrain=np.asarray(Image.open(BASE/'terrain.png').convert('RGB'));h,w=terrain.shape[:2]
    with np.load(OUT/'town_model.npz') as z:a={k:z[k] for k in z.files}
    files=[];plotdata={}
    for mode in ['raw','corrected']:
        sites=json.loads((OUT/f'packets/control/placed_{mode}_sites.json').read_text())['sites']
        xy=np.array([(s['column']+.5,s['row']+.5) for s in sites])
        for scenario in ['central_x34','low_x14']:
            old=a[f'control__{mode}__{scenario}_fed_share'];new=a[f'candidate__{mode}__{scenario}_fed_share']
            plotdata[mode+'__'+scenario]=dict(ids=[s['id'] for s in sites],xy=xy.tolist(),old=old.tolist(),new=new.tolist())
            fig,axes=plt.subplots(1,3,figsize=(18,5.1),facecolor='#f6f7f4',layout='constrained')
            for ax in axes:
                ax.imshow(terrain,extent=(0,w,h,0));ax.set(xlim=(0,w),ylim=(h,0));ax.axis('off')
            for ax,label,values in zip(axes[:2],['control','candidate'],[old,new]):
                dots=ax.scatter(xy[:,0],xy[:,1],s=7,c=values,cmap='RdYlGn',vmin=0,vmax=1,linewidths=.12,edgecolors='#273c38')
                s=result['variants'][label]['climates'][mode]['scenarios'][scenario]
                ax.set_title(f'{"Published" if label=="control" else "Candidate"}: {s["fed_share_of_residents"]:.2%} of town need\n{s["short_towns"]} towns short',fontsize=11)
            delta=new-old
            change=axes[2].scatter(xy[:,0],xy[:,1],s=7,c=delta,cmap='RdBu',vmin=-.25,vmax=.25,linewidths=.12,edgecolors='#273c38')
            axes[2].set_title('Candidate − published support\nblue = improved; red = reduced',fontsize=11)
            fig.colorbar(dots,ax=list(axes[:2]),fraction=.026,pad=.015,label='Annual share of town grain need met')
            fig.colorbar(change,ax=axes[2],fraction=.026,pad=.015,label='Change in share (colours clip at ±0.25)',extend='both')
            reading='size-dependent density, 33.719% extraction' if scenario=='central_x34' else '100 residents/ha, 14.049% extraction'
            fig.suptitle(f'{mode.capitalize()} map · {reading} · 600 field hours/worker/year\nAnnual work-limited grain scenario, seed 1 — development preview; rural deficits remain',fontsize=13)
            fig.supxlabel('Same fixed towns and archived freight network. Painted roads shown. Seasonal continuous food/work feasibility is not established.',fontsize=10)
            name=f'comparison_{mode}_{scenario}.png';fig.savefig(OUT/name,dpi=150);plt.close(fig);files.append(name)
    (OUT/'plot_data.json').write_text(json.dumps(plotdata,separators=(',',':'))+'\n')
    files.append('plot_data.json')
    (OUT/'presentation.json').write_text(json.dumps(dict(renderer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),terrain_sha256=sha(BASE/'terrain.png'),
        files_sha256={n:sha(OUT/n) for n in files},adopt=False),indent=2)+'\n')
    print('Rendered four annual-supply comparison maps')


if __name__=='__main__':main()
