import copy, json, sys, numpy as np
from pathlib import Path
sys.path[:0]=['/home/user/rotclimate','/home/user/rotclimate/scripts']
from harvest.export import climate_arrays, surface_months
from rotclimate.geography import target_fullres, source_layers
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
D=Path('atlases/earth_fit/data'); o=json.load(open(D/'atlas.json'))
meta=copy.deepcopy(o)
for k in ('arrays','lapse12','cell_px','harvest'): meta[k]=o['corrected_climate'][k]
a=climate_arrays(D/'corrected',meta); t,p,d,lat=surface_months(meta,a); h,w=t.shape[1:]
tgt=target_fullres(); land=source_layers()['land']
ix=lambda A:A[(np.arange(h)*A.shape[0]//h)][:,(np.arange(w)*A.shape[1]//w)]
zone=ix(tgt); L=ix(land)
T=t.mean(0); P=p.sum(0); warm=np.argsort(-t,0)[:6]; Ps=np.take_along_axis(p,warm,0).sum(0)
add=np.where(Ps>=0.7*P,280.,np.where(Ps<=0.3*P,0.,140.)); r=P/np.maximum(20*T+add,1)
np.savez_compressed(Path(sys.argv[1])/'steppe_fields.npz',T=T,P=P,r=r,zone=zone,land=L,t=t,p=p,lat=lat)
cm=ListedColormap(['#8c510a','#d8b365','#f6e8c3','#c7eae5','#5ab4ac','#01665e'])
R=np.where(L,r,np.nan)
fig,ax=plt.subplots(figsize=(14,7),dpi=110)
ax.imshow(R,cmap=cm,norm=BoundaryNorm([0,0.5,1,1.5,2,3,99],6),interpolation='nearest')
ax.contour((zone==2).astype(float),[0.5],colors='crimson',linewidths=1.2)
ax.contour((zone==7).astype(float),[0.5],colors='darkorange',linewidths=1.0)
ax.set_title('Current climate (corrected): precipitation / Köppen dry threshold. <0.5 desert, 0.5–1 steppe.\nRed outline = painted "cold and dry" zone (target: below 1); orange = painted hot dry')
sm=plt.cm.ScalarMappable(cmap=cm,norm=BoundaryNorm([0,0.5,1,1.5,2,3,4],6)); fig.colorbar(sm,ax=ax,fraction=0.02)
ax.set_xticks([]);ax.set_yticks([]); fig.tight_layout(); fig.savefig(Path(sys.argv[1])/'steppe_aridity_now.png')
m=(zone==2)&L
print('zone monthly T',np.round(np.median(t[:,m],1),1)); print('zone monthly P',np.round(np.median(p[:,m],1)))
print('lat range',lat[m.any(1)].min() if lat.ndim==1 else np.round([lat[m].min(),lat[m].max()],1))
