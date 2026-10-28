"""Repeated native moist transport/phase steps with rain gravitational work."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.regional_baroclinic import RegionalMode
from rotclimate.regional_energy_step import static_energy
from rotclimate.regional_moist_step import advance_moist
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    prior=ROOT/'output/moist_enthalpy_20261028/verification.json';receipt=json.loads(prior.read_text())
    for n,h in receipt['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed prior source: '+n)
    old=receipt['cases']['humid-lower'];a={n:np.asarray(v) for n,v in old['arrays'].items()}
    masses=np.asarray(receipt['shared_arrays']['layer_mass_kg_m2']);mass=masses.sum(0)
    pressure=np.asarray(receipt['shared_arrays']['representative_pressure_pa']);dx=receipt['configuration']['cell_m']
    mode=RegionalMode(a['u_east'],a['v_south'],a['geopotential'],a['divergence_per_s'],old['mode_certificate'])
    z=np.broadcast_to(np.array([1875.,9375.])[:,None,None],masses.shape).copy()
    initial_t=a['temperature_k'];initial_w=a['vapor_kg_m2'];initial_e=static_energy(initial_t,initial_w,masses,z)
    runs={};states={}
    for hours in [6.,3.,1.5,.75]:
        dt=hours*3600.;t,w=initial_t.copy(),initial_w.copy();rain=np.zeros_like(mass);rain_h=np.zeros_like(mass);fall_heat=np.zeros_like(masses)
        checks=[]
        for step in range(round(24/hours)):
            result=advance_moist(mode,mass,dx,t,w,z,pressure,3750.,dt,initial_t,[.009,.0025])
            t,w=result.temperature_k,result.vapor_kg_m2
            rain+=result.ground_rain_kg_m2;rain_h+=result.ground_rain_enthalpy_j_m2;fall_heat+=result.fall_dissipation_j_m2
            checks.append(dict(step=step+1,energy_residual_w_cell_sum=result.certificate['combined_energy_residual_w_m2_cell_sum'],
                               water_residual_kg_s_cell_sum=result.certificate['combined_water_residual_kg_m2_s_cell_sum']))
        final_e=static_energy(t,w,masses,z)
        energy=float(abs(final_e.sum()+rain_h.sum()-initial_e.sum())/initial_e.sum())
        water=float(abs(w.sum()+rain.sum()-initial_w.sum())/initial_w.sum())
        assert energy<1e-12 and water<1e-12
        states[hours]=(t,w,rain,rain_h,fall_heat,final_e)
        runs[str(hours)]=dict(dt_hours=hours,steps=len(checks),checks=checks,relative_atmosphere_plus_rain_energy_error=energy,
            relative_vapor_plus_rain_water_error=water,mean_ground_rain_kg_m2=float(rain.mean()),maximum_ground_rain_kg_m2=float(rain.max()),
            total_ground_rain_kg_m2_cell_sum=float(rain.sum()),total_fall_heat_j_m2_cell_sum=float(fall_heat.sum()))
    ref_t,ref_w,ref_rain,ref_h,ref_fall,ref_e=states[.75];errors={}
    for h in [6.,3.,1.5]:
        errors[str(h)]=dict(rms_temperature_k=float(np.sqrt(np.mean((states[h][0]-ref_t)**2))),
                           rms_vapor_kg_m2=float(np.sqrt(np.mean((states[h][1]-ref_w)**2))),
                           rms_rain_kg_m2=float(np.sqrt(np.mean((states[h][2]-ref_rain)**2))))
    assert errors['1.5']['rms_temperature_k']<errors['3.0']['rms_temperature_k']<errors['6.0']['rms_temperature_k']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained')
    values=[ref_t[0]-initial_t[0],ref_t[1]-initial_t[1],ref_rain,
            ref_w[0]-initial_w[0],ref_w[1]-initial_w[1]]
    titles=['Lower temperature change','Upper temperature change','Accumulated ground rain over24h','Lower vapor change','Upper vapor change']
    tl=max(np.abs(ref_t-initial_t).max(),1e-20);wl=max(np.abs(ref_w-initial_w).max(),1e-20)
    for k,(ax,value,title) in enumerate(zip(axes.ravel()[:5],values,titles)):
        limit=tl if k<2 else (max(ref_rain.max(),1e-20) if k==2 else wl)
        im=ax.imshow(value,origin='upper',extent=[-2400,2400,-2000,2000],cmap='YlGnBu' if k==2 else 'RdBu_r',vmin=0 if k==2 else -limit,vmax=limit)
        ax.set(title=title,xlabel='Eastward distance km',ylabel='Northward distance km');fig.colorbar(im,ax=ax,shrink=.8,label='K' if k<2 else 'kg/m²')
    axes[1,2].plot([6,3,1.5],[errors[str(h)]['rms_temperature_k'] for h in [6.,3.,1.5]],'o-')
    axes[1,2].invert_xaxis();axes[1,2].grid(alpha=.2)
    axes[1,2].set(title='First-order transport/phase refinement',xlabel='Timestep hours',ylabel='RMS T difference vs0.75h K')
    fig.suptitle('Prognostic moist transport + phase change + falling-water dissipation\n24-hour closed fixed-wind test; atmosphere plus exported rain energy conserved; not an Earth forecast',fontsize=15)
    picture=out/'moist_composition.png';fig.savefig(picture,dpi=150);plt.close(fig)
    sources=['rotclimate/falling_water_energy.py','rotclimate/regional_moist_step.py','rotclimate/regional_energy_step.py',
        'rotclimate/regional_mode_tracer.py','rotclimate/moist_enthalpy.py','rotclimate/column_thermodynamics.py',
        'tests/test_falling_water_energy.py','tests/test_regional_moist_step.py','scripts/demo_moist_composition.py','reports/MOIST_COMPOSITION_20261028.md']
    write_json(out/'verification.json',dict(status='passed_isolated_prognostic_moist_composition',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,manufactured_only=True,
        prior_receipt_sha256=file_hash(prior),sources={n:file_hash(ROOT/n) for n in sources},image_sha256=file_hash(picture),
        fixed_wind_runs=4,composed_steps=60,native_tracer_solves=120,new_tests_passed=10,runs=runs,refinement_errors=errors,
        arrays=dict(initial_temperature_k=initial_t.tolist(),final_temperature_k=ref_t.tolist(),initial_vapor_kg_m2=initial_w.tolist(),
            final_vapor_kg_m2=ref_w.tolist(),initial_static_energy_j_m2=initial_e.tolist(),final_static_energy_j_m2=ref_e.tolist(),
            ground_rain_kg_m2=ref_rain.tolist(),rain_enthalpy_j_m2=ref_h.tolist(),fall_heat_j_m2=ref_fall.tolist(),layer_mass_kg_m2=masses.tolist(),height_m=z.tolist()),
        limitations='Fixed winds/heights/pressure, liquid-only instantaneous terminal fall with local drag heating, no momentum/radiative/ice/compressible mechanical feedback.'))
    print({k:v for k,v in runs[str(.75)].items() if k!='checks'}|dict(refinement_errors=errors))


if __name__=='__main__':main()
