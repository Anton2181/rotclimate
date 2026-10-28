"""All-cell dry dynamics driven by a prescribed, resolved liquid-phase pulse."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.column_thermodynamics import G,EPSILON
from rotclimate.lapse_reference import lapse_reference
from rotclimate.cell_thermal_column import build_cell_thermal_column
from rotclimate.cell_thermal_wave import CellThermalWave
from rotclimate.multilevel_phase import adjust_multilevel_fall
from rotclimate.phase_adjustment import saturation_vapor_mass
from local_benchmark_protocol import file_hash,write_json


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    nz,ny,nx=16,12,16;dx=100000.;edges=np.linspace(0,8000,nz+1);z=.5*(edges[:-1]+edges[1:])
    ref=lapse_reference(z);edge_ref=lapse_reference(edges);m=-np.diff(edge_ref.pressure_pa)/G
    column=build_cell_thermal_column(edges,m/np.diff(edges),ref.stability_s2)
    mass=np.broadcast_to(m[:,None,None],(nz,ny,nx)).copy();t=np.broadcast_to(ref.temperature_k[:,None,None],mass.shape).copy()
    p=np.broadcast_to(ref.pressure_pa[:,None,None],mass.shape).copy()
    y,x=np.mgrid[:ny,:nx];pulse=np.exp(-((x-(nx-1)/2)/3)**2-((y-(ny-1)/2)/2.5)**2)
    vertical=np.exp(-((z-3500)/1800)**2)[:,None,None]
    rh=.8+.28*vertical*pulse
    vapor=saturation_vapor_mass(t,mass,p)*rh
    phase=adjust_multilevel_fall(t,vapor,mass,p,edges)
    r0,r1=vapor/mass,phase.vapor_kg_m2/mass
    virtual=lambda temperature,r:temperature*(1+r/EPSILON)/(1+r)
    db=G*(virtual(phase.temperature_k,r1)-virtual(t,r0))/ref.temperature_k[:,None,None]
    source_duration=3600.;source=db/source_duration
    times=[1200.,600.,300.,150.];runs={};last=None
    for dt in times:
        wave=CellThermalWave(column,(ny,nx),dx,2*7.2921159e-5*np.sin(np.deg2rad(30)))
        state=wave.initial_state(0.);history=[];source_integral=np.zeros_like(source)
        for step in range(round(21600/dt)):
            q=source if step*dt<source_duration else 0.
            previous=state;state=wave.advance(previous,dt,buoyancy_source_s3=q)
            if step*dt<source_duration:source_integral+=.5*dt*(previous.buoyancy_cells+state.buoyancy_cells)
            history.append(dict(time_s=(step+1)*dt,**state.certificate))
        runs[str(int(dt))]=dict(dt_s=dt,steps=len(history),history=history,
            arrays=dict(u_east=state.u_east.tolist(),v_south=state.v_south.tolist(),buoyancy_cells=state.buoyancy_cells.tolist(),
                pressure_cells=wave.pressure_cells(state).tolist(),vertical_velocity=wave.vertical_velocity(state).tolist(),
                source_time_integral_buoyancy=source_integral.tolist()))
        if dt==min(times):last=state
    finest=runs[str(int(min(times)))]['arrays'];refine={}
    for key,run in runs.items():
        if run['dt_s']==min(times):continue
        refine[key]={name:float(np.sqrt(np.mean((np.array(run['arrays'][name])-np.array(finest[name]))**2)))
                     for name in ['buoyancy_cells','u_east','v_south','pressure_cells']}
    k=int(np.argmin(abs(z-3500)));u=.5*(last.u_east[k,:,:-1]+last.u_east[k,:,1:]);v=.5*(last.v_south[k,:-1]+last.v_south[k,1:])
    w=np.array(finest['vertical_velocity']);ymid=ny//2
    fig,axes=plt.subplots(2,2,figsize=(12,8));extent=[0,nx*dx/1e3,ny*dx/1e3,0]
    for ax,field,title,label in [(axes[0,0],phase.temperature_k[k]-t[k],'Resolved phase temperature impulse','K'),
        (axes[0,1],np.array(finest['pressure_cells'])[k],'All-level dry pressure and winds after 6 h','m²/s²')]:
        lim=max(float(np.abs(field).max()),1e-10)
        im=ax.imshow(field,extent=extent,cmap='RdBu_r',vmin=-lim,vmax=lim);fig.colorbar(im,ax=ax,label=label,shrink=.82);ax.set_title(title);ax.set_xlabel('East (km)');ax.set_ylabel('South (km)')
    xx=(np.arange(nx)+.5)*dx/1e3;yy=(np.arange(ny)+.5)*dx/1e3
    arrows=axes[0,1].quiver(xx[::2],yy[::2],u[::2,::2],-v[::2,::2],color='k',scale=4)
    axes[0,1].quiverkey(arrows,.08,.92,.2,'0.2 m/s',labelpos='E',coordinates='axes')
    field=w[:,ymid];lim=max(float(abs(field).max()),1e-10)
    im=axes[1,0].pcolormesh(xx,edges[1:-1]/1000,field,shading='nearest',cmap='RdBu_r',vmin=-lim,vmax=lim)
    fig.colorbar(im,ax=axes[1,0],label='Upward m/s',shrink=.82);axes[1,0].set_title('Continuity-derived vertical velocity at middle row');axes[1,0].set_xlabel('East (km)');axes[1,0].set_ylabel('Height (km)')
    history=runs['150']['history'];hours=np.array([h['time_s']/3600 for h in history]);energy=np.array([h['kinetic_plus_thermal_available_energy_m2_s2'] for h in history])
    invisible=np.array([h['pressure_invisible_available_energy_m2_s2'] for h in history])
    axes[1,1].plot(hours,energy,label='Kinetic + thermal available energy');axes[1,1].plot(hours,invisible,label='Pressure-invisible thermal component',ls='--');axes[1,1].axvspan(0,1,color='#ddd',label='Prescribed phase pulse');axes[1,1].set_xlabel('Elapsed h');axes[1,1].set_ylabel('m²/s²');axes[1,1].set_title('Energy retained after the one-hour source');axes[1,1].legend(fontsize=8);axes[1,1].grid(alpha=.2)
    fig.suptitle('Shared-cell dry circulation driven by a resolved phase pulse',fontsize=14)
    fig.text(.5,.012,'16 levels / shallow 8 km • warm/supercooled liquid-only phase • one prescribed pulse, no interactive moist feedback • closed walls',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'cell_thermal_wave.png',dpi=155);plt.close(fig)
    sources=['rotclimate/cell_thermal_column.py','rotclimate/cell_thermal_wave.py','rotclimate/hydrostatic_wave.py',
        'rotclimate/lapse_reference.py','rotclimate/multilevel_phase.py','rotclimate/falling_water_energy.py',
        'rotclimate/moist_enthalpy.py','rotclimate/phase_adjustment.py','rotclimate/column_thermodynamics.py','scripts/demo_cell_thermal_wave.py']
    receipt=dict(status='isolated_all_cell_dry_phase_pulse',actual_earth_integrations=0,interactive_moist_feedback=False,
        physics_or_atlas_adoption=False,configuration=dict(levels=nz,shape=[ny,nx],cell_m=dx,depth_m=8000,
            lapse_k_m=.006,isothermal_cap_k=200,source_duration_s=source_duration,duration_s=21600,
            phase_source='One conservative resolved liquid-phase impulse converted to virtual buoyancy tendency and prescribed for one hour; not repeated phase or water transport'),
        column_certificate=column.certificate,time_refinement=refine,runs=runs,phase_certificate=phase.certificate,
        arrays=dict(edges_m=edges.tolist(),cell_mass_kg_m2=m.tolist(),stability_s2=ref.stability_s2.tolist(),
            pressure_pa=p.tolist(),initial_temperature_k=t.tolist(),initial_vapor_kg_m2=vapor.tolist(),
            phase_temperature_k=phase.temperature_k.tolist(),phase_vapor_kg_m2=phase.vapor_kg_m2.tolist(),
            ground_rain_kg_m2=phase.ground_rain_kg_m2.tolist(),ground_rain_enthalpy_j_m2=phase.ground_rain_enthalpy_j_m2.tolist(),
            phase_buoyancy_increment=db.tolist()),sources={name:file_hash(ROOT/name) for name in sources},
        image_sha256=file_hash(out/'cell_thermal_wave.png'),
        scope='Manufactured phase source, linear dry fixed-reference all-cell hydrostatic dynamics; Lorenz computational thermal mode exposed; no interactive moist/ice/radiative/terrain/compressible Earth prediction')
    write_json(out/'verification.json',receipt)
    print(json.dumps(dict(time_refinement=refine,last=history[-1],max_u_ms=float(np.max(abs(last.u_east))),max_v_ms=float(np.max(abs(last.v_south))),phase=phase.certificate),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);run(ap.parse_args().out.resolve())
