"""Show observed, simulated and local annual rainfall errors from saved cells."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--benchmark', type=Path, required=True)
    ap.add_argument('--regions', nargs='+', default=['california','east_china','east_australia','japan'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--title',default='Earth climate: where rainfall is right and wrong')
    a = ap.parse_args()
    summary = json.loads((a.benchmark/'summary.json').read_text())
    if not summary.get('complete'): raise ValueError('A complete verified benchmark is required')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(a.regions),3,figsize=(13,4.0*len(a.regions)+1.3),squeeze=False)
    hashes = {}
    for row, name in enumerate(a.regions):
        record = summary['regions'][name]
        path = a.benchmark/'cells'/f'{name}.npz'
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        if checksum != record['cells_sha256']: raise ValueError('Saved cells changed: '+name)
        hashes[str(path)] = checksum
        with np.load(path) as z:
            i, j = z['i']-z['i'].min(), z['j']-z['j'].min()
            observed, simulated = z['Po'].sum(0), z['Ps'].sum(0)
        shape = (int(i.max())+1,int(j.max())+1)
        arrays = []
        for values in [observed,simulated,np.log((simulated+50)/(observed+50))]:
            image = np.full(shape,np.nan);image[i,j]=values;arrays.append(image)
        vmax = max(100,np.percentile(np.r_[observed,simulated],98))
        for column, data in enumerate(arrays):
            ax = axes[row,column];ax.set_facecolor('#e5edf2')
            if column < 2:
                im = ax.imshow(data,cmap='YlGnBu',vmin=0,vmax=vmax,interpolation='nearest')
                fig.colorbar(im,ax=ax,shrink=.65,label='mm/year',extend='max')
            else:
                im = ax.imshow(data,cmap='BrBG',vmin=-np.log(3),vmax=np.log(3),interpolation='nearest')
                cb = fig.colorbar(im,ax=ax,shrink=.65,extend='both',ticks=np.log([1/3,.5,1,2,3]))
                cb.ax.set_yticklabels(['⅓×','½×','1×','2×','3×']);cb.set_label('Simulated / observed (+50 mm)')
            ax.set_xticks([]);ax.set_yticks([])
            ax.set_title(['Observed annual rainfall','Simulated annual rainfall','Local rainfall amount error'][column],fontsize=10)
        axes[row,0].set_ylabel(name.replace('_',' ').title(),fontsize=12)
        rain = record['rain']
        axes[row,2].set_xlabel(f'Monthly cell MAE {rain["monthly_mae_mm"]:.1f} mm · annual rank {rain["annual_spearman"]:.2f}',fontsize=9)
    fig.suptitle(a.title,fontsize=17,y=.985)
    fig.text(.5,.94,f'WorldClim 2.1 monthly normals (1970–2000) · {summary["cell_km"]:g} km model cells · reused development regions',ha='center',fontsize=10)
    fig.text(.03,.016,'Blue-green error areas are too wet; brown areas too dry. A +50 mm offset stabilizes ratios in deserts.\n'
             'Southern regions appear in the model’s mirrored northern frame. Grey areas are unscored; these are gridded climate comparisons, not station validation.',fontsize=9)
    fig.tight_layout(rect=[0,.09,1,.90],h_pad=3.5,w_pad=2.0)
    a.out.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.out,dpi=145);plt.close(fig)
    a.out.with_suffix('.json').write_text(json.dumps(dict(benchmark=str(a.benchmark),regions=a.regions,
        cells_sha256=hashes,image_sha256=hashlib.sha256(a.out.read_bytes()).hexdigest()),indent=2)+'\n')
    print(a.out)


if __name__ == '__main__': main()
