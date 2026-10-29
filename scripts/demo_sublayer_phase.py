"""Fixed-parent phase convergence and its source on an unchanged dry grid."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.column_thermodynamics import G,EPSILON
from rotclimate.lapse_reference import lapse_reference
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.sublayer_phase import restrict_thermal,adjust_sublayer_phase
from rotclimate.cell_thermal_column import build_cell_thermal_column
from rotclimate.cell_thermal_wave import CellThermalWave
from local_benchmark_protocol import file_hash,write_json


def reference(nz,shape=(12,16)):
    edges=np.linspace(0,8000,nz+1);z=.5*(edges[:-1]+edges[1:]);ref=lapse_reference(z)
    mass=np.broadcast_to((-np.diff(lapse_reference(edges).pressure_pa)/G)[:,None,None],(nz,)+shape).copy()
    temperature=np.broadcast_to(ref.temperature_k[:,None,None],mass.shape).copy()
    pressure=np.broadcast_to(ref.pressure_pa[:,None,None],mass.shape).copy()
    return edges,z,mass,temperature,pressure,ref.stability_s2


def run(out):
    out.mkdir(parents=True,exist_ok=True);shape=(12,16);ce,zc,cm,ct,cp,n2=reference(16)
    fine_edges,zfine,mfine,tfine,pfine,_=reference(512)
    y,x=np.mgrid[:shape[0],:shape[1]];pulse=np.exp(-((x-(shape[1]-1)/2)/3)**2-((y-(shape[0]-1)/2)/2.5)**2)
    rh=.8+.28*np.exp(-((zfine-3500)/1800)**2)[:,None,None]*pulse
    wfine=saturation_vapor_mass(tfine,mfine,pfine)*rh
    parent=restrict_thermal(tfine,wfine,mfine,fine_edges,ce)
    column=build_cell_thermal_column(ce,cm[:,0,0]/np.diff(ce),n2)
    tv=lambda t,w,m:t*(1+w/(EPSILON*m))/(1+w/m)
    baseline_tv=tv(parent.temperature_k,parent.vapor_kg_m2,cm)
    arrays=dict(coarse_edges_m=ce,coarse_mass=cm,coarse_pressure=cp,coarse_stability=n2,
        initial_temperature=parent.temperature_k,initial_vapor=parent.vapor_kg_m2)
    cases={};sources={}
    for factor in [1,2,4,8,16,32]:
        fe,z,m,t,p,_=reference(16*factor)
        phase=adjust_sublayer_phase(parent.temperature_k,parent.vapor_kg_m2,cm,ce,fe,m,p)
        db=G*(tv(phase.temperature_k,phase.vapor_kg_m2,cm)-baseline_tv)/ct
        sources[factor]=db
        fields=dict(fine_edges=fe,fine_mass=m,fine_pressure=p,fine_initial_temperature=phase.fine_initial.temperature_k,
            fine_initial_vapor=phase.fine_initial.vapor_kg_m2,fine_temperature=phase.fine_phase.temperature_k,
            fine_vapor=phase.fine_phase.vapor_kg_m2,temperature=phase.temperature_k,vapor=phase.vapor_kg_m2,
            ground_rain=phase.ground_rain_kg_m2,ground_rain_enthalpy=phase.ground_rain_enthalpy_j_m2,buoyancy_increment=db)
        arrays.update({f'f{factor}_{key}':value for key,value in fields.items()})
        cases[str(factor)]=dict(fine_levels=16*factor,certificate=phase.certificate,
            coarse_source_available_energy=column.energy_partition(db),maximum_fine_phase_temperature_change_k=float(np.max(abs(phase.fine_phase.temperature_k-phase.fine_initial.temperature_k))))
    for factor in [1,2,4,8,16]:
        case=cases[str(factor)];ref=cases['32'];case['difference_vs_factor32']=dict(
            rms_coarse_temperature_k=float(np.sqrt(np.mean((arrays[f'f{factor}_temperature']-arrays['f32_temperature'])**2))),
            rms_coarse_vapor_kg_m2=float(np.sqrt(np.mean((arrays[f'f{factor}_vapor']-arrays['f32_vapor'])**2))),
            relative_coarse_source_available_energy_difference=abs(case['coarse_source_available_energy']['total_thermal_available_energy_m2_s2']/ref['coarse_source_available_energy']['total_thermal_available_energy_m2_s2']-1))
    # Identical dry dynamics and timestep for every source comparison.
    wave=CellThermalWave(column,shape,100000.,2*7.2921159e-5*np.sin(np.deg2rad(30)));dt=150.;duration=21600.;pulse_s=3600.
    waves={}
    for factor in [1,8,32]:
        state=wave.initial_state(0.);source_integral=np.zeros_like(sources[factor]);history=[]
        for step in range(int(duration/dt)):
            q=sources[factor]/pulse_s if step*dt<pulse_s else 0.
            old=state;state=wave.advance(old,dt,buoyancy_source_s3=q)
            if step*dt<pulse_s:source_integral+=.5*dt*(old.buoyancy_cells+state.buoyancy_cells)
            history.append(dict(time_s=(step+1)*dt,**state.certificate))
        for key,value in dict(u=state.u_east,v=state.v_south,b=state.buoyancy_cells,pressure=wave.pressure_cells(state),source_integral=source_integral).items():arrays[f'wave{factor}_{key}']=value
        waves[str(factor)]=dict(steps=len(history),history=history)
    for factor in [1,8]:
        waves[str(factor)]['difference_vs_factor32']={key:float(np.sqrt(np.mean((arrays[f'wave{factor}_{key}']-arrays[f'wave32_{key}'])**2))) for key in ['u','v','pressure','b']}
    fig,axes=plt.subplots(2,2,figsize=(12,8));factors=np.array([1,2,4,8,16])
    axes[0,0].loglog(factors,[cases[str(k)]['difference_vs_factor32']['rms_coarse_temperature_k'] for k in factors],'-o',color='#217c95')
    axes[0,0].set_title('Fixed parent column; finer saturation/falling-rain cells');axes[0,0].set_ylabel('RMS coarse temperature difference (K)');axes[0,0].set_xlabel('Phase sublayers per momentum cell')
    axes[0,1].plot([1,2,4,8,16,32],[cases[str(k)]['coarse_source_available_energy']['total_thermal_available_energy_m2_s2'] for k in [1,2,4,8,16,32]],'-o',color='#b56840')
    axes[0,1].set_xscale('log',base=2);axes[0,1].set_title('All source norms measured on the same 16 cells');axes[0,1].set_ylabel('Coarse thermal available energy (m²/s²)');axes[0,1].set_xlabel('Phase sublayers per momentum cell')
    core=(shape[0]//2,shape[1]//2)
    for factor,ls,label in [(1,':','One phase cell'),(8,'--','Eight phase sublayers'),(32,'-','32 sublayers (comparison reference)')]:
        delta=arrays[f'f{factor}_temperature']-parent.temperature_k
        axes[1,0].plot(delta[:,core[0],core[1]],zc/1000,ls=ls,label=label)
    axes[1,0].set_title('Energy-equivalent coarse phase temperature change');axes[1,0].set_xlabel('Temperature change (K)');axes[1,0].set_ylabel('Height (km)');axes[1,0].legend(fontsize=8)
    k=6;field=arrays['wave8_pressure'][k]-arrays['wave32_pressure'][k];lim=max(float(abs(field).max()),1e-10)
    im=axes[1,1].imshow(field,extent=[0,1600,1200,0],cmap='RdBu_r',vmin=-lim,vmax=lim);fig.colorbar(im,ax=axes[1,1],label='Pressure difference (m²/s²)',shrink=.8)
    axes[1,1].set_title('6 h pressure difference: 8 versus 32 phase sublayers');axes[1,1].set_xlabel('East (km)');axes[1,1].set_ylabel('South (km)')
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle('Conservative phase sublayers on an unchanged circulation grid',fontsize=14)
    fig.text(.5,.012,'Fixed 16-cell parent state • retained fine phase state • 512-layer comparison is not truth • dry source pulse, no interactive moist climate',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'sublayer_phase.png',dpi=155);plt.close(fig)
    np.savez_compressed(out/'fields.npz',**arrays)
    files=['rotclimate/sublayer_phase.py','rotclimate/multilevel_phase.py','rotclimate/moist_enthalpy.py',
        'rotclimate/falling_water_energy.py','rotclimate/phase_adjustment.py','rotclimate/lapse_reference.py',
        'rotclimate/cell_thermal_column.py','rotclimate/cell_thermal_wave.py','rotclimate/hydrostatic_wave.py',
        'rotclimate/column_thermodynamics.py','scripts/demo_sublayer_phase.py']
    result=dict(status='isolated_conservative_phase_sublayers',actual_earth_integrations=0,interactive_moist_feedback=False,
        physics_or_atlas_adoption=False,configuration=dict(coarse_levels=16,shape=list(shape),depth_m=8000,
            phase_factors=[1,2,4,8,16,32],wave_factors=[1,8,32],dt_s=dt,duration_s=duration,source_duration_s=pulse_s,
            input='One common water/static-energy parent state from restriction of a manufactured512-layer profile; fixed limited-linear shape reconstruction for all sublayer factors'),
        cases=cases,waves=waves,raw_fields_file='fields.npz',raw_fields_sha256=file_hash(out/'fields.npz'),
        image_sha256=file_hash(out/'sublayer_phase.png'),sources={n:file_hash(ROOT/n) for n in files},
        scope='Nested fixed-pressure liquid phase and prescribed phase-derived dry circulation pulse; coarse means may exceed single-cell saturation. No interactive moisture transport, ice, radiative, terrain or compressible adoption. Native-grid quadratic norms include unresolved variance; compare common coarse observables.')
    write_json(out/'verification.json',result)
    print(json.dumps(dict(cases={k:v.get('difference_vs_factor32') for k,v in cases.items()},waves={k:v.get('difference_vs_factor32') for k,v in waves.items()}),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);run(ap.parse_args().out.resolve())
