"""Read-only audit of painted tiers, current ramps and mapped rivers.

Produces a baseline illustration and constraint counts, not a new terrain
realization or a hydrologically validated DEM. Never changes model inputs.
"""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from scipy import ndimage as ndi
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,LightSource
from matplotlib.patches import Patch
from local_benchmark_protocol import file_hash,write_json
from rotclimate.config import SOURCE
from rotclimate.geography import source_layers,elevation_fullres,MI_KM,TIER_COLORS,TIER_NAMES


def main():
    out=ROOT/'output/terrain_constraints_20261026';out.mkdir(exist_ok=True)
    atlas_summary=ROOT/'atlases/earth_fit/summary.json'
    params_path=ROOT/json.loads(atlas_summary.read_text())['params']
    p=json.loads(params_path.read_text());tops=np.array([0.,*p['tier_tops']])
    layers=source_layers();tier=layers['tier'];land=layers['land'];river=layers['rivers']
    h=elevation_fullres(tuple(p['tier_tops']))
    labels,n=ndi.label(river,structure=np.ones((3,3)))
    sizes=ndi.sum(river,labels,np.arange(1,n+1))
    near_water=ndi.binary_dilation(~land,iterations=2)
    contact=np.unique(labels[river&near_water]);contact=contact[contact>0]
    low,high=tops[np.maximum(tier.astype(int)-1,0)],tops[tier]
    outside=land&((h<low-.5)|(h>high+.5))
    pixel_km=p['map_width_mi']*MI_KM/tier.shape[1]
    cmap=ListedColormap(np.vstack([np.array([216,231,237]),TIER_COLORS])/255)
    fig,axes=plt.subplots(2,1,figsize=(13,12),constrained_layout=True)
    extent=(0,tier.shape[1]*pixel_km,tier.shape[0]*pixel_km,0)
    axes[0].imshow(tier,cmap=cmap,vmin=-.5,vmax=4.5,extent=extent,interpolation='nearest')
    shaded=LightSource(azdeg=315,altdeg=45).shade(h,cmap=plt.get_cmap('terrain'),vert_exag=4,
        dx=pixel_km*1000,dy=pixel_km*1000,blend_mode='soft')
    shaded[~land,:3]=[216/255,231/255,237/255]
    axes[1].imshow(shaded,extent=extent,interpolation='nearest')
    overlay=np.zeros(tier.shape+(4,));overlay[river]=[.04,.3,.53,.95]
    for ax in axes:
        ax.imshow(overlay,extent=extent,interpolation='nearest')
        ax.set(xlabel='Map x (km)',ylabel='Map y (km, downward)')
    axes[0].set_title('Source height bands and mapped rivers')
    axes[1].set_title('Current model terrain: distance ramps plus smoothing · hillshade exaggerated4×')
    handles=[Patch(facecolor=TIER_COLORS[i]/255,label=f'{TIER_NAMES[i].title()}: {tops[i]:g}–{tops[i+1]:g} m') for i in range(4)]
    fig.legend(handles=handles,loc='outside lower center',ncol=4,frameon=False)
    fig.suptitle('Terrain constraints already available · no new heights generated',fontsize=17)
    image=out/'baseline_terrain_and_rivers.png';fig.savefig(image,dpi=130);plt.close(fig)
    sources=[atlas_summary,params_path,SOURCE/'elevation.png',SOURCE/'rivers.png',ROOT/'rotclimate/geography.py',Path(__file__)]
    report=dict(scope='Read-only source/current-ramp audit; no generated or adopted terrain and no climate solves',
        shape=list(tier.shape),pixel_km=pixel_km,tier_tops_m=p['tier_tops'],land_pixels=int(land.sum()),
        river_pixels=int(river.sum()),river_land_pixels=int((river&land).sum()),components_8=n,
        components_at_least20px=int((sizes>=20).sum()),components_within2px_of_water=len(contact),
        river_pixels_by_tier={str(i):int((river&(tier==i)).sum()) for i in range(1,5)},
        current_ramp_outside_own_tier_by_over_half_metre_pixels=int(outside.sum()),
        current_ramp_outside_tier_land_fraction=float(outside.sum()/land.sum()),
        flow_direction_inferred=False,river_tier_conflict_feasibility_tested=False,
        limitations='Raster components can include separate rivers or broken strokes; near-water contact does not establish outlet direction. Existing smoothing is not a hard tier-bound constraint. Hillshade is exaggerated for legibility.',
        sources_sha256={str(f.relative_to(ROOT)):file_hash(f) for f in sources},image_sha256=file_hash(image))
    write_json(out/'audit.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['sources_sha256','limitations']},indent=2))


if __name__=='__main__':main()
