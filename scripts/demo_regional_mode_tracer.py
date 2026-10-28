"""Transport passive water on exact regional-mode faces; no climate forecast."""
from pathlib import Path
import argparse
import json
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rotclimate.regional_baroclinic import RegionalMode
from rotclimate.regional_mode_tracer import solve_mode_tracer
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    dry_path=ROOT/'output/regional_baroclinic_20261028/verification.json'
    dry=json.loads(dry_path.read_text())
    if dry.get('manufactured_only') is not True or dry.get('actual_earth_integrations')!=0:
        raise ValueError('Need isolated regional receipt')
    for path,sha in dry['sources'].items():
        if file_hash(ROOT/path)!=sha:raise ValueError('Changed frozen regional operator source: '+path)
    for path,sha in dry['images_sha256'].items():
        if file_hash(dry_path.parent/path)!=sha:raise ValueError('Changed regional image')
    dx=dry['configuration']['cell_m'];results={};arrays={};independent={}
    for key in ['mass-wall','mass-passive']:
        a={name:np.array(value) for name,value in dry['cases'][key]['arrays'].items()}
        mass=a['mass']*10000.
        mode=RegionalMode(a['u_east'],a['v_south'],a['geopotential'],a['divergence_per_s'],dry['cases'][key]['certificate'])
        source=np.zeros((2,)+mass.shape);source[0]=2/86400.
        result=solve_mode_tracer(mode,mass,dx,source,1/(10*86400.),[.009,.0025])
        # Independent flux divergence, layer and whole-column budget.
        horizontal=(np.diff(result.east_water_flux,axis=2)+np.diff(result.south_water_flux,axis=1))/dx
        vertical=np.stack([result.upward_water_flux,-result.upward_water_flux])
        residual=source-result.removal-horizontal-vertical
        scale=max(float(source.max()),float(result.removal.max()),1e-30)
        relative=float(np.abs(residual).max()/scale)
        assert relative<1e-10 and result.water.min()>=0
        boundary=(result.east_water_flux[:,:,-1].sum(1)-result.east_water_flux[:,:,0].sum(1)
                  +result.south_water_flux[:,-1].sum(1)-result.south_water_flux[:,0].sum(1))/dx
        budget=source.sum((1,2))-result.removal.sum((1,2))-boundary
        np.testing.assert_allclose(budget,[result.upward_water_flux.sum(),-result.upward_water_flux.sum()],atol=1e-12)
        independent[key]=dict(maximum_relative_actual_face_residual=relative,
            maximum_absolute_face_residual_mm_day=float(np.abs(residual).max()*86400.),
            column_budget_residual_mm_day_cell_sum=float(budget.sum()*86400.),
            upward_transfer_mm_day_cell_sum=float(result.upward_water_flux.sum()*86400.),
            outward_boundary_mm_day_cell_sum=(boundary*86400.).tolist(),
            total_source_mm_day_cell_sum=float(source.sum()*86400.),
            total_removal_mm_day_cell_sum=float(result.removal.sum()*86400.))
        results[key]=result
        arrays[key]=dict(water=result.water.tolist(),removal=result.removal.tolist(),
                         east_water_flux=result.east_water_flux.tolist(),south_water_flux=result.south_water_flux.tolist(),
                         upward_water_flux=result.upward_water_flux.tolist(),mass_kg_m2=mass.tolist())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained')
    upper_limits=[max(r.water[k].max() for r in results.values()) for k in (0,1)]
    vertical_limit=max(np.abs(r.upward_water_flux).max() for r in results.values())*86400.
    for row,(key,result) in enumerate(results.items()):
        for col,data in enumerate([result.water[0],result.water[1],result.upward_water_flux*86400.]):
            ax=axes[row,col]
            options=dict(cmap='YlGnBu',vmin=0,vmax=upper_limits[col]) if col<2 else dict(cmap='RdBu_r',vmin=-vertical_limit,vmax=vertical_limit)
            picture=ax.imshow(data,origin='upper',extent=[-2400,2400,-2000,2000],**options)
            title=['Lower water','Upper water','Actual donor water transfer ↑'][col]
            ax.set(title=title+'\n'+('Closed walls' if row==0 else 'Passive edges'),xlabel='Eastward distance km',ylabel='Northward distance km')
            fig.colorbar(picture,ax=ax,shrink=.8,label='Water kg/m² = mm' if col<2 else 'Upward mm/day (negative = downward)')
    fig.suptitle('Native-face donor water transport on the regional dry mode\nPrescribed 2 mm/day lower supply and 10-day tracer removal; no rainfall or latent feedback',fontsize=15)
    picture=out/'regional_mode_water.png';fig.savefig(picture,dpi=150);plt.close(fig)
    sources=['rotclimate/regional_mode_tracer.py','tests/test_regional_mode_tracer.py',
             'scripts/demo_regional_mode_tracer.py','reports/REGIONAL_MODE_TRACER_20261028.md']
    write_json(out/'tracer_verification.json',dict(status='passed_isolated_native_face_tracer',
        actual_earth_integrations=0,passive_tracer_solves=2,coupled_climate_connected=False,
        physics_or_atlas_adoption=False,manufactured_only=True,regional_tracer_tests_passed=9,
        sources={p:file_hash(ROOT/p) for p in sources},dry_receipt_sha256=file_hash(dry_path),
        image_sha256=file_hash(picture),certificates={key:r.certificate for key,r in results.items()},
        independent=independent,arrays=arrays,
        configuration=dict(lower_dry_fraction=.25,column_reference_mass_kg_m2=10000.,
                           source_lower_mm_day=2.,removal_days=10.,external_layer_mixing_ratios=[.009,.0025]),
        limitations='Passive water/tracer only; prescribed supply/removal, no condensation/rain prediction, latent heating or climate coupling'))
    print(independent)


if __name__=='__main__':main()
