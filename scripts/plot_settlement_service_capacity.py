"""Map a fixed, local-only workload diagnostic at unchanged atlas sites."""
import gzip
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write


def main():
    out=ROOT/'output/settlement_service_capacity_20261111';fields=dict(np.load(out/'fields.npz'))
    fig,axes=plt.subplots(1,2,figsize=(15,6.2),facecolor='#f5f5ee');sources={}
    for ax,climate in zip(axes,['raw','corrected']):
        folder=ROOT/'atlases/earth_fit/data'/('corrected' if climate=='corrected' else '')
        path=folder/'settled_reach.json.gz';model=json.loads(gzip.decompress(path.read_bytes()));h,w=model['shape']
        binary=folder/'settled_reach.bin.gz'
        with gzip.open(binary,'rb') as stream:lookup=np.frombuffer(stream.read(h*w*4),dtype='<u4').reshape(h,w)
        land=lookup>0;nodes=fields[climate+'__nodes'];rr,cc=np.divmod(nodes,w)
        if not np.all(land.ravel()[nodes]):raise ValueError('Model nodes disagree with stored atlas land lookup')
        prefix=climate+'__joint365';people=fields[prefix+'__people'];good=people>0
        served=fields[prefix+'__committed50__served'].sum(axis=0)
        ratio=np.divide(served,2*people,out=np.zeros_like(people),where=good)
        ax.imshow(land,cmap=ListedColormap(['#dce8ee','#e3e2d8']),interpolation='nearest',vmin=0,vmax=1)
        ax.contour(land.astype(float),levels=[.5],colors='#435653',linewidths=.45)
        ax.scatter(cc[~good],rr[~good],s=8,color='#93968e',marker='x',linewidths=.5)
        points=ax.scatter(cc[good],rr[good],c=ratio[good],cmap='viridis',vmin=0,vmax=1,s=14,edgecolors='#243833',linewidths=.15)
        ax.set_title(('Raw' if climate=='raw' else 'Corrected')+' climate food ledger · same sites',fontsize=12)
        ax.set(xlim=(0,w-1),ylim=(h-1,0),xlabel='Atlas grid column',ylabel='Atlas grid row')
        sources[str(binary.relative_to(ROOT))]=sha(binary);sources[str(path.relative_to(ROOT))]=sha(path)
    bar=fig.colorbar(points,ax=axes,location='bottom',shrink=.52,pad=.16,aspect=45);bar.set_label('Modelled requests fulfilled / requested · illustrative local work only',fontsize=10)
    fig.suptitle('Food-supported staff put a finite limit on services',x=.04,ha='left',fontsize=18,fontweight='bold')
    fig.text(.04,.89,'Fixed year-store case: 600 annual hours per supported staff member, 50% reserved for other duties. Original sites and residents unchanged.',fontsize=10)
    fig.text(.04,.035,'Each resident requests two neutral services/year, costing 1 and 2 hours. Identity provider choice: no travel catchments or rerouting.\nDots: same marked/proposed model sites with residents; grey crosses: zero resident demand, not perfect service. Grid orientation follows the atlas.\nStress scenarios, not observed ancient productivity, welfare or political control. Staffing affiliation and food assumptions remain those of the legacy scenario.',fontsize=9,color='#555555')
    # Position maps explicitly so the shared colour scale and notes do not overlap.
    for ax,rect in zip(axes,[[.045,.35,.44,.44],[.535,.35,.44,.44]]):ax.set_position(rect)
    bar.ax.set_position([.265,.23,.47,.025])
    path=ROOT/'reports/figures/settlement_service_capacity_20261111.png';fig.savefig(path,dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
    write(out/'figure_provenance.json',dict(figure_sha256=sha(path),source_models_and_land_lookup=sources,
        fixed_case='joint365',fixed_committed_fraction=.5,local_identity_choice_only=True,producer_sha256=sha(Path(__file__))))
    print(path)


if __name__=='__main__':main()
