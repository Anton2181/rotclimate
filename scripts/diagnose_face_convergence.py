"""Observe advection-operator differences on a verified, fixed world state.

No integration, scoring, parameter selection, observations or atlas adoption.
The diagnosed supply difference is not a prediction of changed rainfall.
"""
from pathlib import Path
import json
import pickle
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def operator_difference(water,u,v,dx):
    """Exact flux-minus-point-advection supply and its compression component."""
    import numpy as np
    from rotclimate.transport import moisture_terms,face_divergence
    water,u,v=[np.asarray(a,dtype=float) for a in (water,u,v)]
    old=moisture_terms(water,u,v,dx,0,0,0,0,water)['advection']
    face=moisture_terms(water,u,v,dx,0,0,0,0,water,form='flux')['advection']
    compression=np.full_like(water,np.nan,dtype=float)
    compression[1:-1,1:-1]=-86400*water[1:-1,1:-1]*face_divergence(
        .5*(u[:,1:]+u[:,:-1]),-.5*(v[1:]+v[:-1]),dx)
    return face-old,compression,(face-old)-compression


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    from rotclimate.koppen import monthly_weights
    snapshot=ROOT/'output/atlas_r43/snapshot'
    checkpoint=snapshot/'output/r43_world/candidate_001.pkl'
    with checkpoint.open('rb') as stream:record=pickle.load(stream)
    for name,digest in record['identity']['sources'].items():
        if file_hash(snapshot/'rotclimate'/name)!=digest:raise ValueError('Checkpoint source mismatch')
    r=record['result'];p=r.params;g=r.grid
    if not r.numerics.get('all_checks_passed'):raise ValueError('Unverified world state')
    # Result.u/v are the moisture wind only for these explicit settings.
    expected=dict(moisture_wind_factor=1.,moisture_pressure_drag_ratio=1.,moisture_thermal_height_km=0.,
        moisture_mass_balance=False,water_land_friction=0.,wind_cap=0.,monsoon_heating=0.)
    if any(getattr(p,n)!=value for n,value in expected.items()):raise ValueError('Stored winds are not the vapor winds')
    weights=monthly_weights(r.days,p.year_days).mean(0);sl=g.map_slice();land=g.land[sl]
    fields=np.zeros((3,*land.shape));rain=np.tensordot(weights,r.P,axes=1)[sl]*p.year_days
    for weight,w,u,v in zip(weights,r.W,r.u,r.v):
        components=operator_difference(w,u,v,g.dx_m)
        fields+=weight*np.stack([a[sl] for a in components])*p.year_days
    if not np.isfinite(fields[:,land]).all():raise ValueError('Nonfinite interior diagnostic')
    fig,axes=plt.subplots(2,2,figsize=(14,8),layout='constrained')
    panels=[rain,*fields];titles=['Existing raw annual rainfall',
        'Fixed-state extra supply: flux minus point advection',
        'Compression component: −W div(u)',
        'Remainder from the different discrete stencils']
    for i,(ax,a,title) in enumerate(zip(axes.flat,panels,titles)):
        settings=(dict(vmin=0,vmax=1800) if i==0 else
                  dict(norm=SymLogNorm(linthresh=200,vmin=-50000,vmax=50000)) if i<3 else
                  dict(vmin=-250,vmax=250))
        image=ax.imshow(np.where(land,a,np.nan),cmap='YlGnBu' if i==0 else 'BrBG',
            **settings,interpolation='nearest')
        ax.set_title(title,fontsize=11);ax.set_xticks([]);ax.set_yticks([]);ax.set_facecolor('#d6e4ef')
        ax.spines[['top','right','left','bottom']].set_visible(False)
        fig.colorbar(image,ax=ax,orientation='horizontal',shrink=.9,
            label=('mm/year' if i==0 else 'mm/year equivalent; symmetric log scale, ±50,000' if i<3 else
                   'mm/year equivalent; separate linear scale, ±250'))
    fig.suptitle('Why transport changes can greatly change the water supply\nVerified r43 state held fixed · advection only · not predicted rainfall changes',fontsize=14)
    out=ROOT/'output/face_convergence_20261103';out.mkdir(exist_ok=True)
    image=out/'fixed_state_supply.png';fig.savefig(image,dpi=135);plt.close(fig)
    arrays=out/'fixed_state_supply.npz';np.savez_compressed(arrays,land=land,
        annual_rain_mm=rain,advection_change_mm_year=fields[0],compression_mm_year=fields[1],stencil_remainder_mm_year=fields[2])
    stats={}
    for name,a in zip(['advection_change','compression','stencil_remainder'],fields):
        stats[name]=dict(mean_mm_year=float(a[land].mean()),mean_absolute_mm_year=float(np.abs(a[land]).mean()),
            percentiles_mm_year=dict(zip(['p01','p05','p50','p95','p99'],np.percentile(a[land],[1,5,50,95,99]).tolist())))
    receipt=dict(climate_integrations=0,adoption=False,observations_opened=False,physics_profile='r43',
        checkpoint_sha256=file_hash(checkpoint),checkpoint_identity=record['identity'],
        observer_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image),arrays_sha256=file_hash(arrays),
        region='Mapped model-grid land cells, annual weights from the original calendar',statistics=stats,
        scope='Exact discrete advection difference on identical stored W/u/v. Other sources, evaporation, temperature, rain and storms are held fixed. Switching model transport also removes the existing convergence-import closure and changes the solved state; these maps do not predict that full change. Compression requires compensating dry-air transport or vertical exchange in a stationary physical atmosphere; this diagnostic does not supply it.')
    write_json(out/'receipt.json',receipt);print(json.dumps(stats,indent=2))


if __name__=='__main__':main()
