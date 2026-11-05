"""Standalone causal comparison: listed field work → grain → available reach."""
from pathlib import Path
import gzip
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    origin=ROOT/'output/settlement_labour_20261105';folder=origin/'earth_fit_corrected';r=json.loads((folder/'review.json').read_text());m=json.loads(gzip.decompress((folder/'settled_reach.json.gz').read_bytes()))
    raw=gzip.decompress((folder/'settled_reach.bin.gz').read_bytes());shape=r['shape'];size=int(np.prod(shape));lookup=np.frombuffer(raw,'<u4',count=size);masks=np.frombuffer(raw,'<u2',offset=r['offsets']['masks']).reshape(r['masks_shape']);k=next(i for i,c in enumerate(m['cases']) if c['id']=='work300_30');pop=np.array([i.bit_count() for i in range(4096)],np.uint8)
    base=np.bitwise_or.reduce(masks[1],axis=0);after=np.bitwise_or.reduce(masks[k],axis=0);lost=pop[base&~after];loss=np.full(size,np.nan);loss[lookup>0]=lost
    with np.load(folder/'field_support.npz') as f:
        retained=np.full(size,np.nan);retained[f['cell_index']]=f['work300_30_retained']*100
    fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained');fig.patch.set_facecolor('#f1f3ef')
    image=axs[0,0].imshow(retained.reshape(shape),vmin=0,vmax=100,cmap='YlGn');axs[0,0].set_title('Earth corrected · cereal production retained (%)');fig.colorbar(image,ax=axs[0,0],shrink=.6);axs[0,0].axis('off')
    image=axs[0,1].imshow(loss.reshape(shape),vmin=0,vmax=12,cmap='YlOrRd');axs[0,1].set_title('Earth corrected · access bins lost versus food-only');fig.colorbar(image,ax=axs[0,1],shrink=.6);axs[0,1].axis('off')
    names=[];sources=[];civ=[];coverage=[]
    for packet in ['free_fit_raw','earth_fit_raw','earth_fit_corrected','whittaker_fit_raw']:
        model=json.loads(gzip.decompress((origin/packet/'settled_reach.json.gz').read_bytes()));s={c['id']:c for c in model['summaries']};a=s['joint365'];b=s['work300_30'];names.append(packet.replace('_',' '));sources.append(a['active_sources']-b['active_sources']);civ.append((a['civilian_people']-b['civilian_people'])/a['civilian_people']*100);coverage.append(a['area_weighted_access_bins']-b['area_weighted_access_bins'])
    bars=axs[1,0].bar(names,sources,color='#42786a');axs[1,0].bar_label(bars,padding=3);axs[1,0].set(ylabel='Unavailable institutional source candidates',title='Shared food budget removes marginal institutional cohorts');axs[1,0].tick_params(axis='x',rotation=15,labelsize=8)
    bars=axs[1,1].bar(names,coverage,color='#a76b52');axs[1,1].bar_label(bars,fmt='%.2f',padding=3);axs[1,1].set(ylabel='Area-weighted access bins lost',title='Resulting reach changes; transport stays fixed');axs[1,1].tick_params(axis='x',rotation=15,labelsize=8)
    for ax in axs[1]:ax.margins(y=.2);ax.grid(axis='y',alpha=.15)
    fig.suptitle('300 listed field hours per reference worker/year · 30-day reaping scenario',fontsize=15)
    fig.supxlabel('Workforce anchored to the earlier fixed rural cereal-food claim, not census residents. Rural meals do not shrink with production.\nPartial field tasks only: other food, household/draft labour, water volumes and rights remain unresolved. No validated sovereignty or famine forecast.',fontsize=10)
    fig.savefig(origin/'fieldwork_settlement_reach.png',dpi=130);plt.close(fig)


if __name__=='__main__':main()
