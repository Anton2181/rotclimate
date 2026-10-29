"""Repeated pressure/enthalpy/vapor/phase coupling, not a prescribed pulse."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.pressure_moist import PressureMoistModel,enthalpy_phase,gas_energy
from rotclimate.phase_adjustment import saturation_vapor_mass
from local_benchmark_protocol import file_hash,write_json


def run(out):
    out.mkdir(parents=True,exist_ok=True);nz,ny,nx=10,8,10;edges=np.geomspace(101325.,38000.,nz+1)
    model=PressureMoistModel(edges,(ny,nx),100000.,2*7.2921159e-5*np.sin(np.deg2rad(30)),momentum_drag_s=1/(5*86400.))
    p=model.column.centers_pa;t=np.broadcast_to((300*(p/p[0])**.18)[:,None,None],model.mass.shape).copy()
    y,x=np.mgrid[:ny,:nx];rh=.88+.23*np.exp(-((x-(nx-1)/2)/2.5)**2-((y-(ny-1)/2)/2)**2)
    w=saturation_vapor_mass(t,model.mass,model.pressure)*rh[None]
    arrays=dict(pressure_edges=edges,cell_mass=model.mass,initial_temperature=t,initial_vapor=w)
    runs={};duration=21600.;last=None
    for dt in [600.,300.,150.,75.]:
        state=model.initial_state(t,w);rain=np.zeros((ny,nx));rain_h=np.zeros((ny,nx));history=[]
        for step in range(int(duration/dt)):
            state=model.advance(state,dt);rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2
            history.append(dict(time_s=(step+1)*dt,mean_rain_mm=float(rain.mean()),mean_step_rain_mm=float(state.ground_rain_kg_m2.mean()),
                **{k:v for k,v in state.certificate.items() if not k.startswith('transport_')}))
        key=str(int(dt))
        for name,value in dict(temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,
            rain=rain,rain_enthalpy=rain_h,final_step_rain=state.ground_rain_kg_m2).items():arrays[key+'_'+name]=value
        runs[key]=dict(dt_s=dt,steps=len(history),history=history,last_step_certificate=state.certificate)
        last=state
    for key in ['600','300','150']:
        runs[key]['difference_vs_75s']={field:float(np.sqrt(np.mean((arrays[key+'_'+field]-arrays['75_'+field])**2)))
            for field in ['temperature','vapor','rain','u','v']}
    # Independent local phase-only columns: no transport or circulation.
    tc,wc,rc,hc=enthalpy_phase(t,w,model.mass,model.pressure)
    arrays.update(control_temperature=tc,control_vapor=wc,control_rain=rc,control_rain_enthalpy=hc)
    fig,axes=plt.subplots(2,2,figsize=(12,8));extent=[0,nx*100,ny*100,0]
    for ax,field,title in [(axes[0,0],arrays['75_rain'],'Repeated coupled rain after 6 h (mm)'),
        (axes[0,1],arrays['75_rain']-rc,'Coupled rain minus isolated-column phase (mm)')]:
        lim=max(float(abs(field).max()),1e-10)
        if ax is axes[0,0]:im=ax.imshow(field,extent=extent,cmap='YlGnBu',vmin=0,vmax=lim)
        else:im=ax.imshow(field,extent=extent,cmap='RdBu_r',vmin=-lim,vmax=lim)
        fig.colorbar(im,ax=ax,shrink=.8);ax.set_title(title);ax.set_xlabel('East (km)');ax.set_ylabel('South (km)')
    k=2;u=.5*(last.u_east[k,:,:-1]+last.u_east[k,:,1:]);v=.5*(last.v_south[k,:-1]+last.v_south[k,1:])
    ax=axes[1,0];field=last.temperature_k[k]-t[k];lim=max(float(abs(field).max()),1e-10)
    im=ax.imshow(field,extent=extent,cmap='RdBu_r',vmin=-lim,vmax=lim);fig.colorbar(im,ax=ax,shrink=.8,label='K')
    arrows=ax.quiver((np.arange(nx)+.5)[::2]*100,(np.arange(ny)+.5)[::2]*100,u[::2,::2],-v[::2,::2],scale=8)
    ax.quiverkey(arrows,.08,.92,.5,'0.5 m/s',labelpos='E',coordinates='axes');ax.set_title(f'Actual temperature and winds at {p[k]/100:.0f} hPa');ax.set_xlabel('East (km)');ax.set_ylabel('South (km)')
    ax=axes[1,1]
    for key,color in [('600','#a66b41'),('300','#5d739d'),('150','#48826a'),('75','#234f68')]:
        history=runs[key]['history'];ax.plot([h['time_s']/3600 for h in history],[h['mean_rain_mm'] for h in history],label=f'{int(key)} s',color=color)
    ax.axhline(float(rc.mean()),color='k',ls=':',label='Isolated-column phase');ax.set_xlabel('Elapsed h');ax.set_ylabel('Mean cumulative rain (mm)');ax.set_title('Moist state and circulation evolve at every step');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Repeated moist feedback in a reduced pressure-coordinate model',fontsize=14)
    fig.text(.5,.012,'10 pressure cells • initially motionless • closed walls • dry/dilute pressure and enthalpy approximation • no Earth forcing or adoption',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'pressure_moist.png',dpi=155);plt.close(fig)
    np.savez_compressed(out/'fields.npz',**arrays)
    files=['rotclimate/pressure_coordinate.py','rotclimate/pressure_moist.py','rotclimate/multilevel_transport.py',
        'rotclimate/falling_water_energy.py','rotclimate/moist_enthalpy.py','rotclimate/phase_adjustment.py','rotclimate/column_thermodynamics.py','scripts/demo_pressure_moist.py']
    receipt=dict(status='isolated_repeated_pressure_moist_feedback',actual_earth_integrations=0,interactive_moist_feedback=True,
        physics_or_atlas_adoption=False,configuration=dict(levels=nz,shape=[ny,nx],cell_m=100000.,duration_s=duration,
            timesteps_s=[600,300,150,75],momentum_drag_s=1/(5*86400.),closed_lids=True,closed_horizontal_walls=True,
            moisture_volume_and_loading=False,water_potential_and_fall_work=False,nonlinear_momentum_advection=False),
        runs=runs,raw_fields_sha256=file_hash(out/'fields.npz'),image_sha256=file_hash(out/'pressure_moist.png'),
        sources={n:file_hash(ROOT/n) for n in files},scope='Manufactured repeated pressure-coordinate gas-enthalpy/vapor/phase/momentum feedback with compression once, drag heating and actual ground-rain enthalpy. Zero depth-mean flow; no water loading/volume/potential, ice, predicted radiation, terrain, compressible density or Earth adoption.')
    write_json(out/'verification.json',receipt)
    print(json.dumps(dict(time_refinement={k:v.get('difference_vs_75s') for k,v in runs.items()},finest_last=runs['75']['history'][-1],
        mean_rain_mm=float(arrays['75_rain'].mean()),control_mean_rain_mm=float(rc.mean()),peak_u_ms=float(abs(last.u_east).max()),peak_v_ms=float(abs(last.v_south).max())),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);run(ap.parse_args().out.resolve())
