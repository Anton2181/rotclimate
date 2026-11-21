"""T8: what the fitted occupation field implies on the fantasy map (raw climate): A x base-weighted mean exp(-D/800 km) from the lore cores."""
import json,sys,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from harvest.export import climate_arrays, derive
from harvest.models import core_term, lore_cores
r=json.load(open(str(Path(__file__).resolve().parents[1])+'/calibration/occupation_field_20261121/results.json'))
units=r['units']
y=np.array([np.log(u['people']/u['base']) for u in units]); D=np.array([u['D'] for u in units])
w=np.array([0.5/sum(1 for v in units if v['pool']==u['pool']) for u in units])
a800=float(np.sum(w*(y+D/0.8))/w.sum())   # slope fixed at 1/800 km
print('A (L=800)', np.exp(a800))
atlas=Path(__file__).resolve().parents[1]/'atlases/earth_fit';data=atlas/'data';meta=json.loads((data/'atlas.json').read_text())
arrays=climate_arrays(data,meta)
fields,geo,names,_=derive(meta,arrays,365.0)
land=np.isfinite(fields['settlement_base'])
shape=land.shape;cell_km=meta['width']*meta['mi_per_px']*1.609344/shape[1]
t=core_term(land,np.asarray(arrays['biome']),np.asarray(arrays['elev'],float),cell_km,lore_cores(meta['width'],meta['height'],shape))
wt=geo['land_fraction'].astype(float); b=np.nan_to_num(fields['settlement_base'])
mt=float(np.sum(b*t*wt)/np.sum(b*wt))
print('raw: base-weighted mean core term', mt, 'central fraction', np.exp(a800)*mt)
json.dump(dict(A=float(np.exp(a800)),mean_term_raw=mt),open(str(Path(__file__).resolve().parents[1])+'/calibration/occupation_field_20261121/fantasy_level.json','w'))
