"""Thermodynamic state drives transient hydrostatic winds on a shared mode."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.column_thermodynamics import G,RD,CP
from rotclimate.vertical_state import stable_reference,build_vertical_state,virtual_potential_buoyancy
from rotclimate.hydrostatic_wave import HydrostaticWave
from scripts.audit_box_mode_coupling import audit
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    edges=np.linspace(0,15000,65);centers=.5*(edges[:-1]+edges[1:]);ref=stable_reference(centers)
    col=build_vertical_state(edges,ref.density_kg_m3,np.full(63,.01**2));ref_i=stable_reference(edges[1:-1])
    ny,nx=40,48;dx=100000.;j,i=np.mgrid[:ny,:nx];x=(i+.5)*dx-2400000.;north=2000000.-(j+.5)*dx
    f=2*7.292e-5*np.sin(np.radians(30+np.degrees(north/6371000.)))
    target_phi=180*np.exp(-((x+100000.)**2+(north-100000.)**2)/(2*550000.**2))
    desired_b=col.buoyancy_modes[:,0,None,None]*target_phi
    theta=ref_i.potential_temperature_k[:,None,None]*(1+desired_b/G)
    initial_t=theta*(ref_i.pressure_pa[:,None,None]/100000.)**(RD/CP)
    actual_b=virtual_potential_buoyancy(initial_t,ref_i.pressure_pa[:,None,None],0.,ref_i.potential_temperature_k[:,None,None])
    runs={};finals={};histories={};snapshots={}
    for label,minutes,damped in [('free60',60.,False),('free30',30.,False),('free15',15.,False),('free7.5',7.5,False),('damped15',15.,True)]:
        solver=HydrostaticWave(col,0,(ny,nx),dx,f,momentum_drag_s=1/(5*86400.) if damped else 0.,buoyancy_drag_s=1/(20*86400.) if damped else 0.)
        state=solver.from_buoyancy(actual_b);initial_e=state.certificate['modal_energy_m2_s2'];dt=minutes*60
        history=[];dissipated=0.;maximum_hydro=0.;maximum_budget=0.;snaps={0:state}
        for step in range(round(86400/dt)):
            state=solver.advance(state,dt);dissipated+=dt*state.certificate['midpoint_damping_m2_s3']
            kinetic=float(.5*(np.sum(state.u_east[:,1:-1]**2)+np.sum(state.v_south[1:-1]**2))/(ny*nx))
            potential=float(.5*np.mean((state.pressure_amplitude/solver.c)**2))
            # Independent actual vertical buoyancy available energy.
            b=solver.buoyancy_interfaces(state)
            actual_ape=float(.5*np.sum(col.interface_energy_weight[:,None,None]*b*b)/(col.total_mass*ny*nx))
            if abs(actual_ape-potential)>1e-10*max(potential,1.):raise ValueError('Vertical modal energy normalization changed')
            hydro=col.buoyancy_from_pressure(solver.pressure_levels(state))-b
            maximum_hydro=max(maximum_hydro,float(np.abs(hydro).max()))
            maximum_budget=max(maximum_budget,state.certificate['relative_energy_budget_error'])
            total=kinetic+actual_ape
            if abs(total+dissipated-initial_e)>1e-10*max(initial_e,1.):raise ValueError('Actual evolving thermal/wind budget changed')
            history.append(dict(hour=(step+1)*dt/3600.,kinetic_m2_s2=kinetic,available_m2_s2=actual_ape,
                cumulative_damping_m2_s2=dissipated,total_plus_damping_m2_s2=total+dissipated))
            if abs((step+1)*dt-21600)<1e-6 or step+1==round(86400/dt):snaps[(step+1)*dt/3600]=state
        runs[label]=dict(timestep_minutes=minutes,steps=len(history),damped=damped,initial_energy_m2_s2=initial_e,
            final_energy_m2_s2=state.certificate['modal_energy_m2_s2'],cumulative_damping_m2_s2=dissipated,
            relative_total_plus_damping_error=float(abs(state.certificate['modal_energy_m2_s2']+dissipated-initial_e)/initial_e),
            maximum_step_energy_error=maximum_budget,maximum_hydrostatic_residual_m_s2=maximum_hydro,
            maximum_final_face_velocity_ms=float(max(np.abs(state.u_east).max(),np.abs(state.v_south).max())))
        finals[label]=state;histories[label]=history;snapshots[label]=snaps
    ref_phi=finals['free7.5'].pressure_amplitude;errors={}
    for label in ['free60','free30','free15']:
        errors[label]=dict(rms_pressure_amplitude_m2_s2=float(np.sqrt(np.mean((finals[label].pressure_amplitude-ref_phi)**2))),
            rms_u_ms=float(np.sqrt(np.mean((finals[label].u_east-finals['free7.5'].u_east)**2))))
    assert errors['free15']['rms_pressure_amplitude_m2_s2']<errors['free30']['rms_pressure_amplitude_m2_s2']<errors['free60']['rms_pressure_amplitude_m2_s2']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained');extent=[-2400,2400,-2000,2000];stride=(slice(None,None,3),slice(None,None,3))
    limit=max(np.abs(s.pressure_amplitude).max() for key in ['free15','damped15'] for s in snapshots[key].values())
    for row,key in enumerate(['free15','damped15']):
        for column,hour in enumerate([0,6,24]):
            ax=axes[row,column];s=snapshots[key][hour]
            im=ax.imshow(s.pressure_amplitude,origin='upper',extent=extent,cmap='RdBu_r',vmin=-limit,vmax=limit)
            uc=.5*(s.u_east[:,:-1]+s.u_east[:,1:]);vc=.5*(s.v_south[:-1]+s.v_south[1:])
            qu=ax.quiver(x[stride]/1000,north[stride]/1000,uc[stride],-vc[stride],scale=45,width=.003,color='#253746')
            ax.quiverkey(qu,.72,.95,2.,'2 m/s mode',coordinates='axes',labelpos='E',fontproperties={'size':8})
            ax.set(title=('Undamped' if row==0 else '5/20-day damping')+f' — {hour}h',xlabel='Eastward distance km',ylabel='Northward distance km')
            fig.colorbar(im,ax=ax,shrink=.8,label='Reduced-pressure mode amplitude m²/s²')
    fig.suptitle('Initial thermal state → hydrostatic pressure → evolving winds and buoyancy\nClosed dry anelastic mode; c from reference stratification; no prescribed initial wind or Earth forecast',fontsize=14)
    fig.savefig(out/'hydrostatic_feedback_maps.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    for key,style in [('free15','-'),('damped15','--')]:
        h=histories[key];hours=[v['hour'] for v in h]
        for field,color,label in [('kinetic_m2_s2','#356d92','Kinetic'),('available_m2_s2','#bf633a','Available'),('total_plus_damping_m2_s2','#30383f','Total + damping')]:
            axes[0].plot(hours,[v[field] for v in h],style,color=color,label=label+(' free' if key=='free15' else ' damped'))
    axes[0].set(title='Actual vertical available energy and face kinetic energy',xlabel='Hours',ylabel='m²/s² per reference mass');axes[0].legend(fontsize=8)
    axes[1].plot([60,30,15],[errors[k]['rms_pressure_amplitude_m2_s2'] for k in ['free60','free30','free15']],'o-')
    axes[1].invert_xaxis();axes[1].set(title='24h time refinement vs7.5-minute steps',xlabel='Timestep minutes',ylabel='RMS pressure-mode difference m²/s²')
    axes[2].plot(col.pressure_modes[:,0],col.centers_m/1000,label='Pressure/velocity mode')
    axes[2].plot(col.buoyancy_modes[:,0]/np.max(np.abs(col.buoyancy_modes[:,0])),edges[1:-1]/1000,label='Buoyancy, rescaled')
    axes[2].set(title=f'Energy-paired64-level mode, c={col.phase_speeds_ms[0]:.2f}m/s',xlabel='Normalized shape',ylabel='Height km');axes[2].legend(fontsize=8)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('Shared hydrostatics and adiabatic pressure work — numerical validation, not climate skill',fontsize=14)
    fig.savefig(out/'hydrostatic_feedback_energy.png',dpi=150);plt.close(fig)
    # Independent vertical-resolution comparisons and old box/mode audit.
    resolution={}
    for n in [8,16,32,64,128]:
        ee=np.linspace(0,15000,n+1);rr=stable_reference(.5*(ee[:-1]+ee[1:]));cc=build_vertical_state(ee,rr.density_kg_m3,np.full(n-1,.01**2))
        resolution[str(n)]=float(cc.phase_speeds_ms[0])
    sources=['rotclimate/column_thermodynamics.py','rotclimate/vertical_state.py','rotclimate/hydrostatic_wave.py','tests/test_vertical_state.py','tests/test_hydrostatic_wave.py',
        'scripts/audit_box_mode_coupling.py','scripts/demo_hydrostatic_feedback.py','reports/VERTICAL_STATE_20261028.md','reports/HYDROSTATIC_FEEDBACK_20261028.md']
    write_json(out/'verification.json',dict(status='passed_isolated_state_pressure_wind_feedback',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,manufactured_only=True,linear_dry_feedback_connected=True,
        sources={n:file_hash(ROOT/n) for n in sources},images_sha256={n:file_hash(out/n) for n in ['hydrostatic_feedback_maps.png','hydrostatic_feedback_energy.png']},
        vertical_certificate=col.certificate,box_coupling_audit=audit(),vertical_resolution_first_speed_ms=resolution,
        configuration=dict(vertical_levels=64,depth_m=15000.,N_per_s=.01,surface_theta_k=300.,surface_pressure_pa=101325.,
                           horizontal_shape=[ny,nx],cell_m=dx,coriolis='Earth latitude30N plus northing',wave_speed_ms=float(col.phase_speeds_ms[0])),
        runs=runs,histories=histories,time_refinement=errors,
        arrays=dict(vertical_edges_m=edges.tolist(),cell_mass_kg_m2=col.cell_mass_kg_m2.tolist(),first_pressure_mode=col.pressure_modes[:,0].tolist(),
            first_buoyancy_mode=col.buoyancy_modes[:,0].tolist(),interface_energy_weight=col.interface_energy_weight.tolist(),
            reference_interface_temperature_k=ref_i.temperature_k.tolist(),reference_interface_pressure_pa=ref_i.pressure_pa.tolist(),
            initial_interface_temperature_k=initial_t.tolist(),initial_buoyancy_m_s2=actual_b.tolist(),
            final_states={key:dict(pressure_amplitude=s.pressure_amplitude.tolist(),u_east=s.u_east.tolist(),v_south=s.v_south.tolist()) for key,s in finals.items()}),
        limits='One dry linear anelastic mode; fixed reference and reflecting walls, no moisture/phase/radiation/terrain feedback. Old moist two-box state not connected.'))
    print(dict(runs=runs,time_refinement=errors,first_speed_ms=float(col.phase_speeds_ms[0])))


if __name__=='__main__':main()
