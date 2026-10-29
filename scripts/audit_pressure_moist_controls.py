"""Stable and dry controls for the conditionally unstable repeated moist run."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.pressure_moist import PressureMoistModel,enthalpy_phase
from rotclimate.phase_adjustment import saturation_vapor_mass
from local_benchmark_protocol import file_hash,write_json


def run(out):
    original=json.loads((out/'verification.json').read_text())
    for n,h in original['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Conditional run source changed: '+n)
    if file_hash(out/'fields.npz')!=original['raw_fields_sha256']:raise ValueError('Conditional raw fields changed')
    with np.load(out/'fields.npz') as record:conditional={k:record[k] for k in record.files}
    nz,ny,nx=original['configuration']['levels'],*original['configuration']['shape'];edges=conditional['pressure_edges'];duration=21600.
    coriolis=2*7.2921159e-5*np.sin(np.deg2rad(30));drag=1/(5*86400.)
    model=PressureMoistModel(edges,(ny,nx),100000.,coriolis,momentum_drag_s=drag)
    p=model.column.centers_pa;y,x=np.mgrid[:ny,:nx]
    rh=.88+.23*np.exp(-((x-(nx-1)/2)/2.5)**2-((y-(ny-1)/2)/2)**2)
    t=np.broadcast_to((300*(p/p[0])**.08)[:,None,None],model.mass.shape).copy()
    w=saturation_vapor_mass(t,model.mass,model.pressure)*rh[None]
    arrays=dict(initial_temperature=t,initial_vapor=w);runs={}
    for dt in [600.,300.,150.,75.]:
        state=model.initial_state(t,w);rain=np.zeros((ny,nx));rain_h=np.zeros((ny,nx));history=[]
        for step in range(int(duration/dt)):
            state=model.advance(state,dt);rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2
            history.append(dict(time_s=(step+1)*dt,mean_rain_mm=float(rain.mean()),mean_step_rain_mm=float(state.ground_rain_kg_m2.mean()),
                **{k:v for k,v in state.certificate.items() if not k.startswith('transport_')}))
        key=str(int(dt))
        for field,value in dict(temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,
            rain=rain,rain_enthalpy=rain_h).items():arrays[key+'_'+field]=value
        runs[key]=dict(dt_s=dt,steps=len(history),history=history,last_step_certificate=state.certificate)
    for key in ['600','300','150']:
        runs[key]['difference_vs_75s']={field:float(np.sqrt(np.mean((arrays[key+'_'+field]-arrays['75_'+field])**2)))
            for field in ['temperature','vapor','rain','u','v']}
    tc,wc,rc,hc=enthalpy_phase(t,w,model.mass,model.pressure)
    arrays.update(column_control_temperature=tc,column_control_vapor=wc,column_control_rain=rc,column_control_rain_enthalpy=hc)
    dry=PressureMoistModel(edges,(ny,nx),100000.,coriolis,momentum_drag_s=drag,phase_enabled=False)
    dry_initial=conditional['control_temperature'];state=dry.initial_state(dry_initial);history=[];dt=150.
    for step in range(int(duration/dt)):
        state=dry.advance(state,dt);history.append(dict(time_s=(step+1)*dt,**{k:v for k,v in state.certificate.items() if not k.startswith('transport_')}))
    for field,value in dict(initial_temperature=dry_initial,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south).items():arrays['dry_'+field]=value
    dry_control=dict(dt_s=dt,steps=len(history),history=history,peak_level_velocity_ms=float(max(abs(state.u_east).max(),abs(state.v_south).max())))
    stable_peak=float(max(abs(arrays['75_u']).max(),abs(arrays['75_v']).max()))
    conditional_peak=float(max(abs(conditional['75_u']).max(),abs(conditional['75_v']).max()))
    fig,axes=plt.subplots(2,2,figsize=(12,8));extent=[0,nx*100,ny*100,0]
    for ax,field,title in [(axes[0,0],arrays['75_rain'],'Saturated-stable column: coupled rain after 6 h'),
        (axes[0,1],conditional['75_rain'],'Conditional-instability stress case: rain after 6 h')]:
        im=ax.imshow(field,extent=extent,cmap='YlGnBu',vmin=0,vmax=max(float(field.max()),1e-10))
        fig.colorbar(im,ax=ax,shrink=.8,label='mm (separate color scales)');ax.set_title(title);ax.set_xlabel('East (km)');ax.set_ylabel('South (km)')
    ax=axes[1,0];mass=float(model.column.cell_mass_kg_m2.sum())
    for history,color,label in [(runs['75']['history'],'#387966','Stable moist'),(original['runs']['75']['history'],'#b85938','Conditionally unstable moist'),(dry_control['history'],'#5d739d','Dry, phase-adjusted initial T')]:
        ax.semilogy([h['time_s']/3600 for h in history],[np.sqrt(2*h['kinetic_energy_j_m2']/mass) for h in history],label=label,color=color)
    ax.set_xlabel('Elapsed h');ax.set_ylabel('Mass-weighted velocity norm (m/s)');ax.set_title('Dry/stable controls distinguish latent feedback');ax.legend(fontsize=8);ax.grid(alpha=.2)
    ax=axes[1,1]
    for history,mean,color,label in [(runs['75']['history'],float(rc.mean()),'#387966','stable'),(original['runs']['75']['history'],float(conditional['control_rain'].mean()),'#b85938','conditional')]:
        ax.plot([h['time_s']/3600 for h in history],[h['mean_rain_mm'] for h in history],label=label+' coupled',color=color)
        ax.axhline(mean,color=color,ls=':',label=label+' isolated phase')
    ax.set_xlabel('Elapsed h');ax.set_ylabel('Mean cumulative rain (mm)');ax.set_title('Phase and transport update at every timestep');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Repeated moist feedback: working coupling and a convection warning',fontsize=14)
    fig.text(.5,.012,'10 pressure cells • initially motionless moist cases • closed walls • dry/dilute approximation • no convection closure or Earth adoption',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'pressure_moist_controls.png',dpi=155);plt.close(fig)
    np.savez_compressed(out/'controls_fields.npz',**arrays)
    receipt=dict(status='stable_and_dry_controls_complete',actual_earth_integrations=0,interactive_moist_feedback=True,physics_or_atlas_adoption=False,
        stable_temperature_pressure_exponent=.08,conditional_temperature_pressure_exponent=.18,
        stable_environmental_lapse_k_km=.08*9.80665/287.05*1000,conditional_environmental_lapse_k_km=.18*9.80665/287.05*1000,
        stable_peak_level_velocity_ms=stable_peak,conditional_peak_level_velocity_ms=conditional_peak,
        stable_mean_rain_mm=float(arrays['75_rain'].mean()),conditional_mean_rain_mm=float(conditional['75_rain'].mean()),
        runs=runs,dry_control=dry_control,image_sha256=file_hash(out/'pressure_moist_controls.png'),
        raw_fields_sha256=file_hash(out/'controls_fields.npz'),original_receipt_sha256=file_hash(out/'verification.json'),
        original_fields_sha256=file_hash(out/'fields.npz'),control_script_sha256=file_hash(Path(__file__)),
        scope='Stable/dry mechanism controls; conditionally unstable moist response retained. Conservation and time convergence do not establish realistic convection or justify Earth adoption.')
    write_json(out/'controls_verification.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['runs','dry_control']},indent=2));print('dry peak',dry_control['peak_level_velocity_ms'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);run(ap.parse_args().out.resolve())
