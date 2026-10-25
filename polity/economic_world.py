"""Prepare the existing trade world without recomputing political reach.

This mirrors the preparation in fields.compute. The comparison runner checks
the resulting geography, population and settlement nodes against the export's
cached arrays before using it; a mismatch is a hard failure.
"""
from pathlib import Path
import json

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from . import fields as F, network as N, control as C


def prepare(atlas):
    from harvest.export import climate_arrays, geometry
    from population.export import decode_harvest
    from rotclimate.geography import target_fullres
    from .transport import ports_of

    data=Path(atlas)/'data';meta=json.loads((data/'atlas.json').read_text())
    arrays=climate_arrays(data,meta)
    elev=np.asarray(arrays['elev'],float);biome=np.asarray(arrays['biome']);shape=elev.shape
    geo,_=geometry(meta,shape);land=geo['land_fraction']>.5
    cell_km=meta['width']/shape[1]*meta['mi_per_px']*1.609344
    swamp=np.asarray(Image.fromarray((target_fullres()==5).astype(np.uint8)*255)
                     .resize((shape[1],shape[0]),Image.BOX))>127
    route=F.block_any(F.rgba('roads.png')[...,3]>0,shape)
    road=route&land;ferry=ndi.binary_closing(route,iterations=2)&~land
    hm,hf=decode_harvest(data)
    density=np.where(land,hf['settlement_base']*hm['occupation']['scenarios']['central'],0.)
    paths=C.path_factor(density);towns=F.settlements(shape)
    _,nearest=ndi.distance_transform_edt(~land,return_indices=True)
    for t in towns:
        t['row'],t['col']=int(nearest[0,t['row'],t['col']]),int(nearest[1,t['row'],t['col']])
    ids,info=F.polity_fills(shape)
    # Town placement historically includes every painted fill. Trade population
    # includes only recognised named claims, exactly as fields.compute does.
    claimed=land&(ids>0)
    eta=C.terrain_coefficient(biome,swamp,None)
    bare=C.travel_graph(elev,land,road,eta,cell_km,paths,ferry)
    marked=[(t['row'],t['col']) for t in towns]
    suggested,_,_=F.place_towns(density,land,geo['water_distance'],road,elev,cell_km,marked,allowed=claimed)
    tracks,routes,_=F.minor_roads(bare,shape,road,suggested,marked)
    towns += [dict(kind='unmarked town',row=int(y),col=int(x)) for y,x in suggested]
    climate=F.map_climate(data,meta,arrays,shape)
    world=dict(elev=elev,land=land,biome=biome,swamp=swamp,density=density,cell_km=cell_km,
               tilt=float(meta['world']['tilt']),river=F.navigable_rivers(shape),road=road,ferry=ferry,
               tracks=tracks,**climate)
    st=N.statics(world);cl=N.climate(world,st)
    places=[(t['row'],t['col']) for t in towns]
    river_near=ndi.binary_dilation(st['basin']>0,iterations=1)
    names=sorted({d['name'].split(' (')[0] for d in info.values() if d['name']})
    claim=np.full(shape,-1,np.int16)
    for k,name in enumerate(names):
        own=[i for i,d in info.items() if d['name'] and d['name'].split(' (')[0]==name]
        claim[np.isin(ids,own)]=k
    return dict(land=land,elev=elev,density=density,cell_km=cell_km,claim=np.where(land,claim,-1),
                towns=towns,world=world,statics=st,climate=cl,ports=ports_of(places,st['water']),
                river_places=[(y,x) for y,x in places if river_near[y,x]],routes=routes)
