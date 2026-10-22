"""Explain changed outside-diagram land using two trusted local climate checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rotclimate import biomes
from rotclimate.climate_fields import lapse_at_days
from rotclimate.geography import target_fullres,TARGET_CLASSES
from rotclimate.koppen import monthly_weights
from rotclimate.numerics import matrix_product
from rotclimate.render import FullRes


def fields(checkpoint):
    with checkpoint.open('rb') as file:r=pickle.load(file)['result']
    fr=FullRes(r);w=monthly_weights(r.days,r.params.year_days).mean(0)
    mean=lambda a:matrix_product(w[None,:],a.reshape(len(w),-1)).reshape(a.shape[1:])
    t=fr.up(mean(r.Tsl))-float(np.sum(w*lapse_at_days(r.params,r.days)))*fr.elev/1000
    p=np.maximum(fr.up(mean(r.P))*r.params.year_days,0)
    return dict(codes=biomes.classify(t,p,fr.land),temperature=t,precipitation=p,land=fr.land,elevation=fr.elev)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('before',type=Path);ap.add_argument('after',type=Path)
    ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    before=fields(a.before);after=fields(a.after)
    assert np.array_equal(before['land'],after['land'])
    assert np.array_equal(before['elevation'],after['elevation']), 'Terrain differs between the two fits'
    land=before['land'];n=int(land.sum());old=before['codes']==0;new=after['codes']==0
    percentiles=[0,10,50,90,100]
    metrics={}
    target=target_fullres()
    for label,f in [('before',before),('after',after)]:
        outside=land & (f['codes']==0)
        quant=lambda key:np.percentile(f[key][outside],percentiles).tolist() if outside.any() else None
        metrics[label]=dict(outside_share=float(outside.sum()/n),outside_cells=int(outside.sum()),
            outside_temperature_c=quant('temperature'),outside_precipitation_mm=quant('precipitation'),
            outside_elevation_m=quant('elevation'),
            by_target_zone={key:float(outside[land & (target==cid)].mean()) if (land & (target==cid)).any() else None
                for cid,key,*_ in TARGET_CLASSES},
            by_elevation={key:float(outside[mask].mean()) if mask.any() else None for key,mask in [
                ('below_500m',land & (f['elevation']<500)),
                ('500_to_1500m',land & (f['elevation']>=500) & (f['elevation']<1500)),
                ('above_1500m',land & (f['elevation']>=1500))]})
    transitions={biomes.LABELS[i]:int((land & old & (after['codes']==i)).sum()) for i in range(10)}
    assert sum(transitions.values())==metrics['before']['outside_cells']
    report=dict(scope='source_land_pixels',land_cells=n,percentiles=percentiles,**metrics,
        original_outside_destinations=transitions,
        newly_outside_land_share=float((land & ~old & new).sum()/n),
        newly_covered_land_share=float((land & old & ~new).sum()/n),
        checkpoint_sha256={key:hashlib.sha256(p.read_bytes()).hexdigest() for key,p in [('before',a.before),('after',a.after)]},
        interpretation='Area transitions on the same source land, using unchanged published envelopes; not independent validation.')
    a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:metrics[k]['outside_share'] for k in metrics},indent=2))


if __name__=='__main__':main()
