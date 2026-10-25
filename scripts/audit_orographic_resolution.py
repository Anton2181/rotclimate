"""Known-answer geometry audit plus r38 terrain factors; no climate integration."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from experiments.orographic_moments import uplift_moments
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,write_json
from rotclimate import earth
from rotclimate.model import ClimateModel


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=ROOT/'output/orographic_resolution_20261025';out.mkdir(parents=True,exist_ok=True)
    plan=ROOT/'calibration/orographic_resolution_20261025/plan.json'
    blocks=[7,14,28,56];x=(np.arange(336)+.5)*1000.
    h=np.broadcast_to(.01*x,(112,336));plane=[]
    for b in blocks:
        r=uplift_moments(h,1000.,b,u=10.)
        plane.append(dict(cell_km=b,legacy_relief_m=float(r['legacy_relief_m'].mean()),
                          positive_ascent_ms=float(r['positive_ascent_ms'].mean()),
                          unresolved_increment_ms=float(r['unresolved_positive_increment_ms'].mean())))
    earth.REGIONS.update(json.loads((ROOT/'calibration/local_accuracy_20261023/regions_dev12.json').read_text()))
    p=load_params(ROOT/'calibration/local_accuracy_20261023/r38_params.json')
    regions=[]
    for cell in [56.,28.,14.]:
        print('Preparing north India geometry at',cell,'km',flush=True)
        case=earth.region_case('north_india',cell)
        model=ClimateModel(earth.earth_params(p,case),grid=case.grid)
        m=case.grid.land&case.grid.inmap
        wind=10.*model.drag
        resolved=p.orographic*np.clip(wind*model.dhdy/.05,0.,4.)
        extra=p.subgrid_orographic*model.subgrid_relief*np.clip(wind/5.,0.,3.)
        regions.append(dict(cell_km=cell,cells=int(m.sum()),mean_relief_m=float(1000*model.subgrid_relief[m].mean()),
                            resolved_factor=float(resolved[m].mean()),subgrid_factor=float(extra[m].mean()),
                            total_factor=float((resolved+extra)[m].mean())))
    files=[plan,Path(__file__),ROOT/'experiments/orographic_moments.py',ROOT/'rotclimate/model.py',
           ROOT/'calibration/local_accuracy_20261023/r38_params.json']
    result=dict(plane=plane,north_india=regions,no_climate_integration=True,
                note='Geometry only; prescribed wind, not a simulated monsoon. Mean positive ascent is not rainfall.',
                sources_sha256={str(f.relative_to(ROOT)):file_hash(f) for f in files})
    fig,axs=plt.subplots(1,3,figsize=(14,4.8),constrained_layout=True)
    axs[0].plot(blocks,[r['legacy_relief_m'] for r in plane],'o-',color='#c85f36')
    axs[0].set(title='A smooth slope acquires false “hill relief”',xlabel='Analysis cell (km)',ylabel='Max minus mean elevation (m)')
    axs[1].plot(blocks,[1000*r['positive_ascent_ms'] for r in plane],'o-',label='Mean positive fine-terrain ascent')
    axs[1].plot(blocks,[1000*r['unresolved_increment_ms'] for r in plane],'o-',label='Unresolved increment')
    axs[1].set(title='Fine-terrain ascent survives aggregation',xlabel='Analysis cell (km)',ylabel='Vertical speed (mm/s)')
    axs[1].legend(frameon=False,fontsize=8,loc='center right')
    for key,label in [('resolved_factor','Resolved slope'),('subgrid_factor','Existing sub-grid extra'),('total_factor','Sum')]:
        axs[2].plot([r['cell_km'] for r in regions],[r[key] for r in regions],'o-',label=label)
    axs[2].set(title='North India: current r38 geometry factors',xlabel='Analysis cell (km)',ylabel='Dimensionless orographic ascent factor')
    axs[2].legend(frameon=False,fontsize=8)
    for ax in axs:ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Terrain resolution audit — geometry before fitting rainfall',fontsize=14)
    fig.supxlabel('Left: fixed plane and 10 m/s east wind. Right: real terrain, imposed north wind with terrain drag. No rain or annual climate is solved.',fontsize=9)
    fig.savefig(out/'resolution.png',dpi=145);plt.close(fig)
    result['image_sha256']=file_hash(out/'resolution.png');write_json(out/'audit.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
