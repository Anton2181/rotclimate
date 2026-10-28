"""Resolved fixed-wind thermodynamic transient with multi-interface phase/rain."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.column_thermodynamics import G
from rotclimate.vertical_state import build_vertical_state,stable_reference
from rotclimate.hydrostatic_wave import HydrostaticWave
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.regional_energy_step import static_energy
from rotclimate.multilevel_moist import advance_multilevel_moist
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    nz,ny,nx=32,10,14;dx=1e5;edges=np.linspace(0,8000,nz+1);z=.5*(edges[:-1]+edges[1:]);ref=stable_reference(z);ref_e=stable_reference(edges)
    reference_mass=(ref_e.pressure_pa[:-1]-ref_e.pressure_pa[1:])/G
    col=build_vertical_state(edges,reference_mass/np.diff(edges),np.full(nz-1,.0001));ri=stable_reference(edges[1:-1])
    j,i=np.mgrid[:ny,:nx];x=(i+.5)*dx-700000.;north=500000.-(j+.5)*dx;horizontal=np.exp(-(x*x+north*north)/(2*220000.**2))
    warm=.6*np.sin(np.pi*z[:,None,None]/8000.)*horizontal
    t0=ref.temperature_k[:,None,None]+warm
    mass=np.broadcast_to(reference_mass[:,None,None],(nz,ny,nx)).copy();p=np.broadcast_to(ref.pressure_pa[:,None,None],mass.shape).copy()
    height=np.broadcast_to(z[:,None,None],mass.shape).copy()
    b=G*(.6*np.sin(np.pi*edges[1:-1,None,None]/8000.)*horizontal)/ri.temperature_k[:,None,None]
    wave=HydrostaticWave(col,0,(ny,nx),dx,2*7.292e-5*np.sin(np.radians(30)))
    state=wave.from_buoyancy(b)
    for _ in range(24):state=wave.advance(state,900.)
    u=col.pressure_modes[:,0,None,None]*state.u_east;v=col.pressure_modes[:,0,None,None]*state.v_south
    w0=saturation_vapor_mass(t0,mass,p)*(.8+.25*horizontal)[None]
    e0=static_energy(t0,w0,mass,height);runs={};states={}
    for hours in [3.,1.5,.75,.375]:
        dt=hours*3600.;t,w=t0.copy(),w0.copy();rain=np.zeros((ny,nx));rain_h=np.zeros_like(rain);fall_heat=np.zeros_like(mass);checks=[]
        for step in range(round(24/hours)):
            result=advance_multilevel_moist(mass,u,v,dx,t,w,p,edges,dt,t0,w0/mass)
            t,w=result.temperature_k,result.vapor_kg_m2
            rain+=result.ground_rain_kg_m2;rain_h+=result.ground_rain_enthalpy_j_m2;fall_heat+=result.fall_heat_j_m2
            checks.append(dict(hour=(step+1)*hours,energy_error_w_cell_sum=result.certificate['combined_energy_residual_w_m2_cell_sum'],
                               water_error_kg_s_cell_sum=result.certificate['combined_water_residual_kg_m2_s_cell_sum']))
        energy=static_energy(t,w,mass,height)
        er=float(abs(energy.sum()+rain_h.sum()-e0.sum())/e0.sum());wr=float(abs(w.sum()+rain.sum()-w0.sum())/w0.sum())
        if max(er,wr)>1e-12:raise ValueError('Closed resolved atmosphere plus rain budget failed')
        if t.min()<235:raise ValueError('Liquid-only demonstration entered the excluded deeply frozen regime')
        runs[str(hours)]=dict(dt_hours=hours,steps=len(checks),checks=checks,relative_energy_plus_rain_error=er,relative_vapor_plus_rain_error=wr,
            mean_rain_kg_m2=float(rain.mean()),maximum_rain_kg_m2=float(rain.max()),minimum_temperature_k=float(t.min()),maximum_temperature_k=float(t.max()))
        states[hours]=(t,w,rain,rain_h,fall_heat,energy)
    rt,rw,rr,rh,rf,re=states[.375];errors={}
    for h in [3.,1.5,.75]:
        errors[str(h)]=dict(rms_temperature_k=float(np.sqrt(np.mean((states[h][0]-rt)**2))),rms_vapor_kg_m2=float(np.sqrt(np.mean((states[h][1]-rw)**2))),rms_rain_kg_m2=float(np.sqrt(np.mean((states[h][2]-rr)**2))))
    if not errors['0.75']['rms_temperature_k']<errors['1.5']['rms_temperature_k']<errors['3.0']['rms_temperature_k']:raise ValueError('Resolved phase/transport time refinement failed')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained');extent=[-700,700,-500,500]
    delta_t=rt[:,ny//2]-t0[:,ny//2];limit_t=max(float(np.abs(delta_t).max()),1e-20)
    im=axes[0,0].pcolormesh(np.linspace(-700,700,nx+1),edges/1000,delta_t,cmap='RdBu_r',shading='flat',vmin=-limit_t,vmax=limit_t)
    axes[0,0].set(title='Resolved temperature change after24h',xlabel='Eastward distance km',ylabel='Height km');fig.colorbar(im,ax=axes[0,0],shrink=.8,label='K')
    im=axes[0,1].imshow(rr,origin='upper',extent=extent,cmap='YlGnBu',vmin=0)
    axes[0,1].set(title='Accumulated ground rain',xlabel='Eastward distance km',ylabel='Northward distance km');fig.colorbar(im,ax=axes[0,1],shrink=.8,label='kg/m² over24h')
    delta_w=(rw-w0)[:,ny//2];limit_w=max(float(np.abs(delta_w).max()),1e-20)
    im=axes[1,0].pcolormesh(np.linspace(-700,700,nx+1),edges/1000,delta_w,cmap='RdBu_r',shading='flat',vmin=-limit_w,vmax=limit_w)
    axes[1,0].set(title='Resolved vapor change',xlabel='Eastward distance km',ylabel='Height km');fig.colorbar(im,ax=axes[1,0],shrink=.8,label='kg/m² per layer')
    axes[1,1].plot([3,1.5,.75],[errors[str(h)]['rms_temperature_k'] for h in [3.,1.5,.75]],'o-');axes[1,1].invert_xaxis();axes[1,1].grid(alpha=.2)
    axes[1,1].set(title='Fixed24h elapsed, first-order time refinement',xlabel='Timestep hours',ylabel='RMS T difference vs0.375h K')
    fig.suptitle('32-level moist transport and terminal rain phase on shared geometry\nClosed shallow liquid-only8km test, fixed generated winds; not an Earth climate forecast',fontsize=14)
    picture=out/'multilevel_moist.png';fig.savefig(picture,dpi=150,bbox_inches='tight');plt.close(fig)
    sources=['rotclimate/multilevel_moist.py','rotclimate/multilevel_phase.py','rotclimate/multilevel_transport.py','rotclimate/falling_water_energy.py',
        'rotclimate/moist_enthalpy.py','rotclimate/phase_adjustment.py','rotclimate/regional_energy_step.py','rotclimate/hydrostatic_wave.py',
        'rotclimate/vertical_state.py','rotclimate/column_thermodynamics.py','tests/test_multilevel_phase.py','tests/test_multilevel_moist.py',
        'scripts/demo_multilevel_moist.py','reports/MULTILEVEL_MOIST_20261028.md']
    write_json(out/'moist_verification.json',dict(status='passed_isolated_resolved_moist_thermodynamics',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,manufactured_only=True,sources={n:file_hash(ROOT/n) for n in sources},image_sha256=file_hash(picture),
        configuration=dict(levels=nz,shape=[ny,nx],cell_m=dx,depth_m=8000.,N_per_s=.01,generated_wind_spinup_hours=6),runs=runs,time_refinement=errors,
        arrays=dict(vertical_edges_m=edges.tolist(),layer_mass=mass.tolist(),pressure_pa=p.tolist(),height_m=height.tolist(),u_east=u.tolist(),v_south=v.tolist(),
            initial_temperature=t0.tolist(),final_temperature=rt.tolist(),initial_vapor=w0.tolist(),final_vapor=rw.tolist(),initial_static_energy=e0.tolist(),
            final_static_energy=re.tolist(),cumulative_rain=rr.tolist(),cumulative_rain_enthalpy=rh.tolist(),cumulative_fall_heat=rf.tolist()),
        limits='Fixed generated winds, shallow8km warm/supercooled liquid-only column, no ice/radiation/momentum feedback; not a full Earth column.'))
    print({k:v for k,v in runs['0.375'].items() if k!='checks'}|dict(time_refinement=errors))


if __name__=='__main__':main()
