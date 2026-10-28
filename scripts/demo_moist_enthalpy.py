"""Same moist pulse with finite water heat capacities and actual rain enthalpy."""
from pathlib import Path
import argparse
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rotclimate.moist_enthalpy import gas_enthalpy,moist_falling_rain
from rotclimate.baroclinic_heating import project_first_mode
from rotclimate.regional_baroclinic import solve_regional_mode
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    previous_path=ROOT/'output/latent_circulation_20261028/verification.json'
    previous=json.loads(previous_path.read_text())
    for n,sha in previous['sources'].items():
        if file_hash(ROOT/n)!=sha:raise ValueError('Changed original comparison source: '+n)
    shared={k:np.asarray(v) for k,v in previous['shared_arrays'].items()}
    t=shared['initial_temperature_k'];mass_layer=shared['layer_mass_kg_m2'];mass=mass_layer.sum(0)
    p=shared['representative_pressure_pa'];ny,nx=mass.shape;dx=previous['configuration']['cell_m']
    j,i=np.mgrid[:ny,:nx];north=2000000.-(j+.5)*dx
    f=2*7.292e-5*np.sin(np.radians(30+np.degrees(north/6371000.)))
    cases={}
    for name,old in previous['cases'].items():
        w=np.asarray(old['arrays']['initial_vapor']);phase=moist_falling_rain(t,w,mass_layer,p)
        heat_equiv=phase.dry_equivalent_heat_j_m2/86400.
        proj=project_first_mode(heat_equiv,mass,[0.,.25,1.],depth_m=15000.,buoyancy_frequency_s=.01,reference_temperature_k=275.)
        mode=solve_regional_mode(proj.forcing_m2_s3,dx,f,column_mass=mass,wave_speed_ms=proj.wave_speed_ms,
            momentum_drag_s=1/(5*86400.),thermal_drag_s=1/(20*86400.))
        before=gas_enthalpy(t,w,mass_layer);after=gas_enthalpy(phase.temperature_k,phase.vapor_kg_m2,mass_layer)
        error=after.sum(0)+phase.ground_rain_enthalpy_j_m2-before.sum(0)
        water_error=w.sum(0)-phase.vapor_kg_m2.sum(0)-phase.ground_rain_kg_m2
        assert np.abs(error).max()<1e-5 and np.abs(water_error).max()<1e-10
        mode_input=proj.physical_modal_energy_factor*mode.certificate['modal_energy_input_m2_s3']
        stats=dict(maximum_column_water_error_kg_m2=float(np.abs(water_error).max()),
            maximum_column_enthalpy_error_j_m2=float(np.abs(error).max()),
            maximum_ground_rain_kg_m2=float(phase.ground_rain_kg_m2.max()),
            previous_maximum_ground_rain_kg_m2=old['independent']['maximum_surface_rain_kg_m2'],
            maximum_absolute_ground_rain_change_kg_m2=float(np.abs(phase.ground_rain_kg_m2-np.asarray(old['arrays']['ground_rain'])).max()),
            maximum_rain_enthalpy_export_w_m2=float(np.abs(phase.ground_rain_enthalpy_j_m2).max()/86400.),
            maximum_absolute_dry_equivalent_sum_w_m2=float(np.abs(heat_equiv.sum(0)).max()),
            maximum_gas_enthalpy_change_w_m2=float(np.abs(after.sum(0)-before.sum(0)).max()/86400.),
            continuous_mode_input_m2_s3=mode_input,
            previous_continuous_mode_input_m2_s3=old['independent']['continuous_first_mode_input_m2_s3'])
        cases[name]=dict(certificate=phase.certificate,projection_certificate=proj.certificate,mode_certificate=mode.certificate,
            statistics=stats,arrays=dict(temperature_k=phase.temperature_k.tolist(),vapor_kg_m2=phase.vapor_kg_m2.tolist(),
            initial_vapor_kg_m2=w.tolist(),ground_rain_kg_m2=phase.ground_rain_kg_m2.tolist(),
            rain_enthalpy_j_m2=phase.ground_rain_enthalpy_j_m2.tolist(),gas_enthalpy_change_j_m2=(after-before).tolist(),
            dry_equivalent_heat_w_m2=heat_equiv.tolist(),condensation_kg_m2=phase.condensation_kg_m2.tolist(),
            rain_evaporation_kg_m2=phase.rain_evaporation_kg_m2.tolist(),projected_forcing=proj.forcing_m2_s3.tolist(),
            geopotential=mode.geopotential.tolist(),u_east=mode.u_east.tolist(),v_south=mode.v_south.tolist(),
            divergence_per_s=mode.divergence_per_s.tolist()))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained')
    limits=[max(c['statistics']['maximum_ground_rain_kg_m2'] for c in cases.values()),
            max(c['statistics']['maximum_rain_enthalpy_export_w_m2'] for c in cases.values()),
            max(c['statistics']['maximum_absolute_dry_equivalent_sum_w_m2'] for c in cases.values())]
    for row,(name,case) in enumerate(cases.items()):
        a=case['arrays'];label='Dry lower air' if row==0 else 'Humid lower air'
        values=[np.asarray(a['ground_rain_kg_m2']),np.asarray(a['rain_enthalpy_j_m2'])/86400.,np.asarray(a['dry_equivalent_heat_w_m2']).sum(0)]
        titles=['Ground rain','Actual rain sensible-energy export','Dry-equivalent temperature forcing sum']
        units=['kg/m² over pulse','W/m² over one-day interval','W/m² equivalent; NOT net moist heat']
        for col,(value,title,unit) in enumerate(zip(values,titles,units)):
            ax=axes[row,col];limit=max(limits[col],1e-20)
            image=ax.imshow(value,origin='upper',extent=[-2400,2400,-2000,2000],cmap='YlGnBu' if col==0 else 'RdBu_r',
                            vmin=0 if col==0 else -limit,vmax=limit)
            ax.set(title=label+'\n'+title,xlabel='Eastward distance km',ylabel='Northward distance km')
            fig.colorbar(image,ax=ax,shrink=.8,label=unit)
    fig.suptitle('Water heat capacities and precipitation enthalpy\nInitial gas enthalpy = final gas enthalpy + exported rain energy; fixed pulse, not an Earth forecast',fontsize=15)
    picture=out/'moist_enthalpy_budget.png';fig.savefig(picture,dpi=150);plt.close(fig)
    sources=['rotclimate/moist_enthalpy.py','tests/test_moist_enthalpy.py','scripts/demo_moist_enthalpy.py','reports/MOIST_ENTHALPY_20261028.md']
    write_json(out/'verification.json',dict(status='passed_isolated_moist_enthalpy_comparison',
        actual_earth_integrations=0,isolated_linear_responses=2,manufactured_only=True,coupled_climate_connected=False,
        physics_or_atlas_adoption=False,previous_receipt_sha256=file_hash(previous_path),
        sources={n:file_hash(ROOT/n) for n in sources},image_sha256=file_hash(picture),cases=cases,
        shared_arrays=previous['shared_arrays'],configuration=previous['configuration'],
        new_tests_passed=10,limitations='Liquid-only fixed-pressure boxes, no ice/convection/precipitation gravitational energy/prognostic moist transport/radiation. Dry-equivalent forcing is actual Tdot, not thermodynamic net heating.'))
    print({name:c['statistics'] for name,c in cases.items()})


if __name__=='__main__':main()
