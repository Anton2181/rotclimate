"""Prepare matching raw/corrected inputs for the isolated imperial-access audit."""
import copy
import json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from . import fields as F,control as C,network as N
from .economic_world import prepare


def audit_world(atlas,mode):
    from harvest.export import climate_arrays,geometry
    from population.export import decode_harvest
    from .transport import ports_of
    atlas=Path(atlas);data=atlas/'data';meta=json.loads((data/'atlas.json').read_text())
    r=prepare(atlas)
    if mode=='raw':return r,meta
    if mode!='corrected' or not meta.get('corrected_climate'):raise ValueError('Unavailable climate mode')
    selected=copy.deepcopy(meta);cc=meta['corrected_climate']
    for key in ['arrays','lapse12','cell_px','harvest']:selected[key]=cc[key]
    arrays=climate_arrays(data/'corrected',selected);geo,_=geometry(selected,r['land'].shape)
    if not np.array_equal(arrays['elev'],r['elev']):raise ValueError('Corrected terrain changed')
    hm,hf=decode_harvest(data/'corrected');land=r['land'];shape=land.shape
    density=np.where(land,hf['settlement_base']*hm['occupation']['scenarios']['central'],0.)
    marked=[dict(t) for t in r['towns'] if 'x_px' in t];positions=[(t['row'],t['col']) for t in marked]
    world=dict(r['world']);world.update(biome=np.asarray(arrays['biome']),density=density)
    eta=C.terrain_coefficient(world['biome'],world['swamp'],None)
    bare=C.travel_graph(r['elev'],land,world['road'],eta,r['cell_km'],C.path_factor(density),world['ferry'])
    ids,_=F.polity_fills(shape)
    suggested,_,_=F.place_towns(density,land,geo['water_distance'],world['road'],r['elev'],r['cell_km'],positions,
        allowed=land&(ids>0),aridity=hf['aridity'],dry_water_km=F.map_dry_water_km())
    tracks,routes,_=F.minor_roads(bare,shape,world['road'],suggested,positions)
    towns=marked+[dict(kind='unmarked town',row=int(y),col=int(x)) for y,x in suggested]
    # Corrections change thermal/rain fields; the published circulation packet
    # remains at the root, matching the corrected export's inherited winds.
    world.update(tracks=tracks,**F.map_climate(data,selected,arrays,shape))
    statics=N.statics(world);climate=N.climate(world,statics);places=[(t['row'],t['col']) for t in towns]
    river_near=ndi.binary_dilation(statics['basin']>0,iterations=1)
    r.update(density=density,towns=towns,world=world,statics=statics,climate=climate,
        ports=ports_of(places,statics['water']),river_places=[(y,x) for y,x in places if river_near[y,x]],routes=routes)
    return r,selected
