"""Show observed and paired saved rainfall, including improvements and losses."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reference',required=True,type=Path);ap.add_argument('--candidate',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);ap.add_argument('--regions',nargs='+',default=['iran_plateau','north_india'])
    a=ap.parse_args();folders=[a.reference,a.candidate]
    summaries=[json.loads((p/'summary.json').read_text()) for p in folders]
    if any(not s.get('complete') for s in summaries):raise ValueError('Complete benchmarks required')
    protocols=[json.loads((p/'protocol.json').read_text()) for p in folders]
    if protocols[0]['sources']!=protocols[1]['sources']:raise ValueError('Unpaired scientific sources')
    hashes={};fig,axes=plt.subplots(len(a.regions),4,figsize=(14,3.4*len(a.regions)+.5),squeeze=False,constrained_layout=True)
    for row,name in enumerate(a.regions):
        fields=[]
        for folder,summary in zip(folders,summaries):
            path=folder/'cells'/f'{name}.npz';checksum=hashlib.sha256(path.read_bytes()).hexdigest()
            if checksum!=summary['regions'][name]['cells_sha256']:raise ValueError('Changed saved cells')
            hashes[str(path)]=checksum
            with np.load(path) as z:fields.append({k:z[k] for k in ['Ps','Po','i','j']})
        x,y=fields
        if not all(np.array_equal(x[k],y[k]) for k in ['i','j','Po']):raise ValueError('Unpaired observations/cells')
        yy=x['i']-x['i'].min();xx=x['j']-x['j'].min();shape=(yy.max()+1,xx.max()+1)
        obs=x['Po'].sum(0);ref=x['Ps'].sum(0);cand=y['Ps'].sum(0)
        delta=np.abs(cand-obs)-np.abs(ref-obs)
        vmax=max(100,float(np.percentile(np.r_[obs,ref,cand],98)))
        for col,(values,title) in enumerate([(obs,'Observed'),(ref,'r38'),(cand,'r39'),(delta,'Absolute-error change')]):
            pixels=np.full(shape,np.nan);pixels[yy,xx]=values;ax=axes[row,col]
            ax.set_xticks([]);ax.set_yticks([]);ax.set_facecolor('#dce7f0')
            im=ax.imshow(pixels,cmap='RdBu_r' if col==3 else 'YlGnBu',vmin=-300 if col==3 else 0,vmax=300 if col==3 else vmax)
            fig.colorbar(im,ax=ax,shrink=.65,label='mm/year',extend='both' if col==3 else 'max')
            ax.set_title(title,fontsize=10)
        axes[row,0].set_ylabel(name.replace('_',' ').title(),fontsize=12)
        before=summaries[0]['regions'][name]['rain']['loss'];after=summaries[1]['regions'][name]['rain']['loss']
        axes[row,3].set_xlabel(f'Rain loss {before:.3f} → {after:.3f}',fontsize=9)
    fig.suptitle('Measured r39 gains and remaining rainfall failures',fontsize=16)
    fig.supxlabel('Same 56 km Earth cells. Blue error change improves; red worsens. Reused development regions; no rain fields edited.',fontsize=9)
    a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=145);plt.close(fig)
    a.out.with_suffix('.json').write_text(json.dumps(dict(reference=str(a.reference),candidate=str(a.candidate),cells_sha256=hashes),indent=2)+'\n')


if __name__=='__main__':main()
