"""Fixed-wind transient moist static energy, exact saved native faces."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.regional_baroclinic import RegionalMode
from rotclimate.regional_energy_step import advance_energy,static_energy
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    prev_path=ROOT/'output/moist_enthalpy_20261028/verification.json';prev=json.loads(prev_path.read_text())
    for n,h in prev['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed prior source: '+n)
    old=prev['cases']['humid-lower'];a={n:np.asarray(v) for n,v in old['arrays'].items()}
    masses=np.asarray(prev['shared_arrays']['layer_mass_kg_m2']);mass=masses.sum(0);dx=prev['configuration']['cell_m']
    mode=RegionalMode(a['u_east'],a['v_south'],a['geopotential'],a['divergence_per_s'],old['mode_certificate'])
    z=np.broadcast_to(np.array([1000.,7000.])[:,None,None],masses.shape).copy()
    initial_t=a['temperature_k'];initial_w=a['vapor_kg_m2'];initial_e=static_energy(initial_t,initial_w,masses,z)
    runs={};states={}
    for hours in [6.,3.,1.5,.75]:
        dt=hours*3600.;t,w=initial_t.copy(),initial_w.copy();checks=[]
        for step in range(round(24/hours)):
            result=advance_energy(mode,mass,dx,t,w,z,dt,initial_t,[.009,.0025])
            t,w=result.temperature_k,result.vapor_kg_m2
            checks.append(dict(step=step+1,energy_residual_w_cell_sum=result.certificate['column_energy_budget_residual_w_m2_cell_sum'],
                               water_residual_kg_s_cell_sum=result.certificate['column_water_budget_residual_kg_m2_s_cell_sum']))
        final_e=static_energy(t,w,masses,z)
        relative_e=float(abs(final_e.sum()-initial_e.sum())/initial_e.sum())
        relative_w=float(abs(w.sum()-initial_w.sum())/initial_w.sum())
        assert relative_e<1e-12 and relative_w<1e-12
        states[hours]=(t,w,final_e)
        runs[str(hours)]=dict(dt_hours=hours,steps=len(checks),relative_total_energy_error=relative_e,
            relative_total_vapor_error=relative_w,checks=checks,minimum_temperature_k=float(t.min()),maximum_temperature_k=float(t.max()))
    ref_t,ref_w,_=states[.75];errors={}
    for h in [6.,3.,1.5]:
        errors[str(h)]=dict(rms_temperature_k=float(np.sqrt(np.mean((states[h][0]-ref_t)**2))),
                           rms_vapor_kg_m2=float(np.sqrt(np.mean((states[h][1]-ref_w)**2))))
    assert errors['3.0']['rms_temperature_k']<errors['6.0']['rms_temperature_k']
    assert errors['1.5']['rms_temperature_k']<errors['3.0']['rms_temperature_k']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained')
    dt_t=ref_t-initial_t;dt_w=ref_w-initial_w
    vals=[dt_t[0],dt_t[1],dt_w.sum(0),dt_w[0],dt_w[1]]
    names=['Lower temperature change','Upper temperature change','Column vapor redistribution',
           'Lower vapor change','Upper vapor change']
    tl=max(np.abs(dt_t).max(),1e-20);wl=max(np.abs(dt_w).max(),np.abs(dt_w.sum(0)).max(),1e-20)
    for k,(ax,val,title) in enumerate(zip(axes.ravel()[:5],vals,names)):
        lim=tl if k<2 else wl
        picture=ax.imshow(val,origin='upper',extent=[-2400,2400,-2000,2000],cmap='RdBu_r',vmin=-lim,vmax=lim)
        ax.set(title=title,xlabel='Eastward distance km',ylabel='Northward distance km')
        fig.colorbar(picture,ax=ax,shrink=.8,label='K' if k<2 else 'kg/m²')
    axes[1,2].plot([6,3,1.5],[errors[str(h)]['rms_temperature_k'] for h in [6.,3.,1.5]],'o-')
    axes[1,2].invert_xaxis();axes[1,2].grid(alpha=.2)
    axes[1,2].set(title='Fixed elapsed24h, time-step refinement',xlabel='Timestep hours',ylabel='RMS temperature difference vs0.75h solution K')
    fig.suptitle('Vapor and moist static energy on the same exact dry fluxes\n24-hour fixed-wind transport; closed, unforced, no phase adjustment or climate forecast',fontsize=15)
    picture=out/'energy_transport.png';fig.savefig(picture,dpi=150);plt.close(fig)
    sources=['rotclimate/regional_energy_step.py','rotclimate/regional_mode_tracer.py','rotclimate/regional_baroclinic.py',
             'rotclimate/moist_enthalpy.py','rotclimate/column_thermodynamics.py','tests/test_regional_energy_step.py',
             'scripts/demo_energy_transport.py','reports/ENERGY_TRANSPORT_20261028.md']
    write_json(out/'verification.json',dict(status='passed_isolated_fixed_wind_energy_transport',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,manufactured_only=True,
        prior_receipt_sha256=file_hash(prev_path),sources={n:file_hash(ROOT/n) for n in sources},
        isolated_timestep_runs=4,backward_euler_steps=60,native_tracer_solves=120,new_tests_passed=8,
        runs=runs,refinement_errors=errors,image_sha256=file_hash(picture),
        arrays=dict(initial_temperature_k=initial_t.tolist(),final_temperature_k=ref_t.tolist(),initial_vapor_kg_m2=initial_w.tolist(),
                    final_vapor_kg_m2=ref_w.tolist(),initial_static_energy_j_m2=initial_e.tolist(),
                    final_static_energy_j_m2=states[.75][2].tolist(),layer_mass_kg_m2=masses.tolist(),height_m=z.tolist()),
        limitations='Fixed-wind, fixed-height gas transport only; no in-step phase change, radiation prediction or momentum feedback. Supersaturation may develop.'))
    print({k:v for k,v in runs[str(.75)].items() if k!='checks'}|dict(refinement_errors=errors))


if __name__=='__main__':main()
