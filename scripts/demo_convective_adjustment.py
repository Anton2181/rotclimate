"""Predeclared instantaneous/one-hour/three-hour conservative closure tests."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.pressure_moist import PressureMoistModel
from rotclimate.convective_adjustment import advance_with_convection
from rotclimate.parcel_stability import diagnose_parcel
from local_benchmark_protocol import file_hash,write_json


def run(out):
    out.mkdir(parents=True,exist_ok=True);parent=ROOT/'output/pressure_moist_20261029'
    original=json.loads((parent/'verification.json').read_text());control=json.loads((parent/'controls_verification.json').read_text())
    for n,h in original['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed coupled baseline source')
    with np.load(parent/'fields.npz') as r:a={k:r[k] for k in r.files}
    with np.load(parent/'controls_fields.npz') as r:b={k:r[k] for k in r.files}
    edges=a['pressure_edges'];mass=a['cell_mass'];shape=mass.shape[1:];p=np.sqrt(edges[:-1]*edges[1:])
    make=lambda:PressureMoistModel(edges,shape,100000.,2*7.2921159e-5*np.sin(np.deg2rad(30)),momentum_drag_s=1/(5*86400.))
    model=make();duration=21600.;arrays=dict(pressure_edges=edges,cell_mass=mass,initial_temperature=a['initial_temperature'],initial_vapor=a['initial_vapor']);cases={}
    for name,tau in [('instant',0.),('one_hour',3600.),('three_hour',10800.)]:
        runs={}
        for dt in [300.,150.,75.]:
            state=model.initial_state(a['initial_temperature'],a['initial_vapor']);rain=np.zeros(shape);rain_h=np.zeros(shape);history=[]
            for step in range(int(duration/dt)):
                state=advance_with_convection(model,state,dt,relaxation_s=tau);rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2
                c=state.certificate;adjust=c['convective_adjustment'];dynamic=c['dynamics_before_adjustment']
                history.append(dict(time_s=(step+1)*dt,mean_rain_mm=float(rain.mean()),
                    gas_enthalpy_plus_kinetic_energy_j_m2=c['gas_enthalpy_plus_kinetic_energy_j_m2'],kinetic_energy_j_m2=c['kinetic_energy_j_m2'],
                    energy_error_j_m2=c['actual_combined_energy_rain_source_residual_j_m2'],water_error_kg_m2=c['actual_combined_water_rain_source_residual_kg_m2'],
                    target_converged=adjust['converged'],adjusted_pairs=adjust['adjusted_pairs'],target_sweeps=adjust['sweeps'],
                    actual_remaining_active_interfaces=c['actual_remaining_active_interfaces'],adjusted_fraction=c['adjusted_fraction'],
                    pressure_compression_error_w_m2=dynamic['actual_pressure_compression_cancellation_error_w_m2']))
            diag=diagnose_parcel(p,state.temperature_k,state.vapor_kg_m2/mass,max_log_pressure_step=.005);key=str(int(dt));prefix=name+'_'+key+'_'
            for field,value in dict(temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,rain=rain,rain_enthalpy=rain_h,
                positive_parcel_energy=diag.positive_buoyancy_energy_j_kg,negative_parcel_energy=diag.negative_buoyancy_energy_j_kg).items():arrays[prefix+field]=value
            runs[key]=dict(dt_s=dt,steps=len(history),history=history,last_certificate=state.certificate,
                mean_positive_parcel_energy_j_kg=float(diag.positive_buoyancy_energy_j_kg.mean()),mean_rain_mm=float(rain.mean()),
                peak_level_velocity_ms=float(max(abs(state.u_east).max(),abs(state.v_south).max())))
            print(name,key,'peak',runs[key]['peak_level_velocity_ms'],'positive',runs[key]['mean_positive_parcel_energy_j_kg'],'rain',rain.mean(),flush=True)
        for key in ['300','150']:
            runs[key]['difference_vs_75s']={field:float(np.sqrt(np.mean((arrays[name+'_'+key+'_'+field]-arrays[name+'_75_'+field])**2))) for field in ['temperature','vapor','u','v','rain']}
        cases[name]=dict(relaxation_s=tau,runs=runs)
    state=model.initial_state(b['initial_temperature'],b['initial_vapor']);stable_rain=np.zeros(shape);stable_h=np.zeros(shape);stable_pairs=0
    for _ in range(144):
        state=advance_with_convection(model,state,150.);stable_rain+=state.ground_rain_kg_m2;stable_h+=state.ground_rain_enthalpy_j_m2;stable_pairs+=state.certificate['convective_adjustment']['adjusted_pairs']
    for field,value in dict(initial_temperature=b['initial_temperature'],initial_vapor=b['initial_vapor'],temperature=state.temperature_k,vapor=state.vapor_kg_m2,
        u=state.u_east,v=state.v_south,rain=stable_rain,rain_enthalpy=stable_h).items():arrays['stable_'+field]=value
    stable=dict(steps=144,dt_s=150.,adjusted_pairs=stable_pairs,maximum_temperature_difference_vs_no_adjustment_k=float(np.max(abs(state.temperature_k-b['150_temperature']))),
        maximum_velocity_difference_vs_no_adjustment_ms=float(max(abs(state.u_east-b['150_u']).max(),abs(state.v_south-b['150_v']).max())))
    baseline={}
    for key in ['300','150','75']:
        d=diagnose_parcel(p,a[key+'_temperature'],a[key+'_vapor']/mass,max_log_pressure_step=.005)
        baseline[key]=dict(mean_positive_parcel_energy_j_kg=float(d.positive_buoyancy_energy_j_kg.mean()),mean_rain_mm=float(a[key+'_rain'].mean()),
            peak_level_velocity_ms=float(max(abs(a[key+'_u']).max(),abs(a[key+'_v']).max())))
    fig,axes=plt.subplots(2,2,figsize=(12,8));steps=[300,150,75];colors={'instant':'#387966','one_hour':'#4478a8','three_hour':'#a67a43'}
    for name,case in cases.items():
        axes[0,0].plot(steps,[case['runs'][str(k)]['mean_positive_parcel_energy_j_kg'] for k in steps],'-o',label=name.replace('_',' '),color=colors[name])
        axes[0,1].plot(steps,[case['runs'][str(k)]['peak_level_velocity_ms'] for k in steps],'-o',label=name.replace('_',' '),color=colors[name])
        history=case['runs']['75']['history'];axes[1,0].plot([h['time_s']/3600 for h in history],[h['mean_rain_mm'] for h in history],label=name.replace('_',' '),color=colors[name])
    for ax,key,label in [(axes[0,0],'mean_positive_parcel_energy_j_kg','Positive partial-column parcel energy (J/kg)'),(axes[0,1],'peak_level_velocity_ms','Peak level velocity (m/s)')]:
        ax.plot(steps,[baseline[str(k)][key] for k in steps],'k--o',label='No adjustment');ax.set_xlabel('Timestep (s)');ax.set_xticks(steps);ax.set_ylabel(label);ax.legend(fontsize=8);ax.grid(alpha=.2)
    axes[0,0].set_title('Convection target and actual remaining parcel energy');axes[0,1].set_title('Closure sensitivity is retained, not fitted away')
    h=original['runs']['75']['history'];axes[1,0].plot([v['time_s']/3600 for v in h],[v['mean_rain_mm'] for v in h],'k--',label='No adjustment')
    axes[1,0].set_xlabel('Elapsed h');axes[1,0].set_ylabel('Mean cumulative rain (mm)');axes[1,0].legend(fontsize=8);axes[1,0].grid(alpha=.2);axes[1,0].set_title('Repeated conditional-moist stress case')
    field=arrays['one_hour_75_rain']-a['75_rain'];lim=max(float(abs(field).max()),1e-10)
    im=axes[1,1].imshow(field,extent=[0,1000,800,0],cmap='RdBu_r',vmin=-lim,vmax=lim);fig.colorbar(im,ax=axes[1,1],label='Rain difference (mm)',shrink=.8)
    axes[1,1].set_xlabel('East (km)');axes[1,1].set_ylabel('South (km)');axes[1,1].set_title('One-hour closure minus unadjusted rain at 6 h')
    fig.suptitle('Conservative convective adjustment: closure and timestep sensitivity',fontsize=14)
    fig.text(.5,.012,'Instant / 1 h / 3 h declared in advance • actual water and enthalpy/rain budgets • no entrainment or convective momentum • no Earth adoption',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'convective_adjustment.png',dpi=155);plt.close(fig)
    np.savez_compressed(out/'fields.npz',**arrays)
    files=['rotclimate/convective_adjustment.py','rotclimate/pressure_moist.py','rotclimate/pressure_coordinate.py','rotclimate/parcel_stability.py',
        'rotclimate/multilevel_transport.py','rotclimate/falling_water_energy.py','rotclimate/moist_enthalpy.py','rotclimate/column_thermodynamics.py',
        'rotclimate/phase_adjustment.py','scripts/demo_convective_adjustment.py','output/pressure_moist_20261029/verification.json',
        'output/pressure_moist_20261029/fields.npz','output/pressure_moist_20261029/controls_verification.json','output/pressure_moist_20261029/controls_fields.npz']
    r=dict(status='experimental_conservative_convective_adjustment',actual_earth_integrations=0,physics_or_atlas_adoption=False,
        configuration=dict(duration_s=duration,relaxation_times_s=[0,3600,10800],timesteps_s=steps,neutral_tolerance_k=.01,max_sweeps=64,
            trigger='Dry instability, or near-saturated lower cell with a warmer saturated parcel above; no wind cap',
            target='Adjacent dry/neutral saturated parcel lapse, common vapor ratio and exact pair gas enthalpy; actual rain enthalpy',
            relaxation='Convex gas enthalpy/water and exported-rain budgets, then explicit phase of the homogenized mixture; first-order operator split'),
        cases=cases,baseline=baseline,stable_control=stable,raw_fields_sha256=file_hash(out/'fields.npz'),image_sha256=file_hash(out/'convective_adjustment.png'),
        sources={n:file_hash(ROOT/n) for n in files},scope='Manufactured reduced pressure-coordinate closure sensitivity, not calibration. Instantaneous neutral target need not remove all parcel energy; finite relaxation may retain active layers. No entrainment, convective momentum/TKE, ice, terrain, radiation, nonlinear momentum or Earth validation.')
    write_json(out/'verification.json',r);print('stable',stable,flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);run(ap.parse_args().out.resolve())
