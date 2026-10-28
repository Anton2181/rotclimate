"""Conservative phase heat -> specified vertical mode -> isolated circulation."""
from pathlib import Path
import argparse
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rotclimate.baroclinic_heating import project_first_mode
from rotclimate.column_thermodynamics import CP,G,LV
from rotclimate.heating_projection import pressure_layer_mass,project_layer_heating
from rotclimate.phase_adjustment import falling_rain_column,saturation_vapor_mass
from rotclimate.regional_baroclinic import solve_regional_mode
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    j,i=np.mgrid[:40,:48];dx=100000.;x=(i+.5)*dx-2400000.;north=2000000.-(j+.5)*dx
    ridge=3400*np.exp(-((x-300000.)/370000.)**2-(north/1500000.)**2)
    ps=101325*np.exp(-ridge/8000.)
    edges=np.stack([ps,ps-.25*(ps-10000.),np.full_like(ps,10000.)])
    masses=pressure_layer_mass(edges);mass=masses.sum(0);representative=.5*(edges[:-1]+edges[1:])
    initial_t=np.stack([np.full_like(ps,298.),np.full_like(ps,250.)])
    sat=saturation_vapor_mass(initial_t,masses,representative)
    rh_upper=.75+.85*np.exp(-((x+200000.)**2+(north-200000.)**2)/(2*650000.**2))
    f=2*7.292e-5*np.sin(np.radians(30+np.degrees(north/6371000.)))
    interval=86400.;cases={}
    for key,lower_rh in [('dry-lower',.25),('humid-lower',.98)]:
        initial_w=sat*np.stack([np.full_like(ps,lower_rh),rh_upper])
        phase=falling_rain_column(initial_t,initial_w,masses,representative)
        heat=phase.sensible_heat_j_m2/interval
        projected=project_first_mode(heat,mass,[0.,.25,1.],depth_m=15000.,buoyancy_frequency_s=.01,reference_temperature_k=275.)
        thickness=project_layer_heating(edges,heat)
        mode=solve_regional_mode(projected.forcing_m2_s3,dx,f,column_mass=mass,
            wave_speed_ms=projected.wave_speed_ms,momentum_drag_s=1/(5*86400.),thermal_drag_s=1/(20*86400.))
        water_error=initial_w.sum(0)-phase.vapor_kg_m2.sum(0)-phase.surface_rain_kg_m2
        enthalpy_error=np.sum(CP*masses*(phase.temperature_k-initial_t)+LV*(phase.vapor_kg_m2-initial_w),axis=0)
        heat_error=CP*masses*(phase.temperature_k-initial_t)-phase.sensible_heat_j_m2
        assert np.abs(water_error).max()<1e-10 and np.abs(enthalpy_error).max()<1e-5
        assert np.abs(heat_error).max()<1e-5
        # Independent continuous buoyancy work: exact sin integrals for each
        # layer's physical source; no reuse of projection weights.
        phi_amp=mode.geopotential/projected.velocity_scale;m=np.pi/15000.
        qb=G*heat/(CP*275.*masses)
        from scipy.integrate import quad
        physical_work=np.zeros_like(ps)
        for k,(left,right) in enumerate([(0.,.25),(.25,1.)]):
            sine=quad(lambda s:np.sin(np.pi*s),left,right,epsabs=1e-13)[0]
            physical_work+=m*phi_amp*qb[k]/.01**2*sine
        expected=projected.physical_modal_energy_factor*mode.geopotential*projected.forcing_m2_s3/projected.wave_speed_ms**2
        np.testing.assert_allclose(physical_work,expected,rtol=1e-11,atol=1e-20)
        physical_mean=float(np.sum(mass*physical_work)/mass.sum())
        c=mode.certificate;factor=projected.physical_modal_energy_factor
        dissipated=factor*(c['momentum_dissipation_m2_s3']+c['thermal_dissipation_m2_s3']+c['boundary_energy_export_m2_s3'])
        assert abs(physical_mean-dissipated)<1e-11*max(abs(physical_mean),1e-20)
        cases[key]=dict(phase=phase,projected=projected,mode=mode,initial_w=initial_w,heat=heat,
            thickness=thickness,independent=dict(maximum_water_residual_kg_m2=float(np.abs(water_error).max()),
            maximum_dilute_enthalpy_residual_j_m2=float(np.abs(enthalpy_error).max()),
            maximum_heat_reconstruction_residual_j_m2=float(np.abs(heat_error).max()),
            maximum_work_pairing_residual_m2_s3=float(np.abs(physical_work-expected).max()),
            continuous_first_mode_input_m2_s3=physical_mean,continuous_first_mode_dissipation_m2_s3=dissipated,
            maximum_surface_rain_kg_m2=float(phase.surface_rain_kg_m2.max()),
            maximum_upper_condensation_kg_m2=float(phase.condensation_kg_m2[1].max()),
            maximum_lower_rain_evaporation_kg_m2=float(phase.rain_evaporation_kg_m2[0].max()),
            maximum_absolute_net_column_heat_w_m2=float(np.abs(heat.sum(0)).max())))
    assert np.max(cases['dry-lower']['phase'].surface_rain_kg_m2)<1e-10
    assert cases['humid-lower']['phase'].surface_rain_kg_m2.max()>0
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    extent=[-2400,2400,-2000,2000]
    def panel(ax,value,title,label,*,limit=None,signed=False):
        if limit is None:limit=max(float(np.abs(value).max()),1e-20)
        im=ax.imshow(value,origin='upper',extent=extent,cmap='RdBu_r' if signed else 'YlGnBu',vmin=-limit if signed else 0,vmax=limit)
        ax.set(title=title,xlabel='Eastward distance km',ylabel='Northward distance km')
        plt.colorbar(im,ax=ax,shrink=.8,label=label)
    dry,wet=cases['dry-lower'],cases['humid-lower']
    fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained')
    water_limit=float(dry['phase'].condensation_kg_m2[1].max())
    heat_limit=max(float(np.abs(v['heat']).max()) for v in cases.values())
    panel(axes[0,0],dry['phase'].condensation_kg_m2[1],'Shared upper condensation','kg/m² over the pulse',limit=water_limit)
    panel(axes[0,1],dry['phase'].surface_rain_kg_m2,'Ground rain over dry lower air','kg/m² over the pulse',limit=water_limit)
    panel(axes[0,2],wet['phase'].surface_rain_kg_m2,'Ground rain over humid lower air','kg/m² over the pulse',limit=water_limit)
    panel(axes[1,0],dry['heat'][1],'Shared upper latent heating','W/m² for one-day forcing interval',limit=heat_limit,signed=True)
    panel(axes[1,1],dry['heat'][0],'Lower cooling, dry air','W/m² for one-day forcing interval',limit=heat_limit,signed=True)
    panel(axes[1,2],wet['heat'][0],'Lower cooling, humid air','W/m² for one-day forcing interval',limit=heat_limit,signed=True)
    fig.suptitle('Ground rain does not locate atmospheric latent heating\nConservative liquid-only box adjustment; fixed moist pulse, not an Earth rainfall forecast',fontsize=15)
    fig.savefig(out/'latent_phase_budget.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(16,10),layout='constrained')
    qlim=max(float(np.abs(v['projected'].forcing_m2_s3).max()) for v in cases.values())
    plim=max(float(np.abs(v['mode'].geopotential).max()) for v in cases.values())
    dlim=max(float(np.abs(v['mode'].divergence_per_s).max()*.75*1e6) for v in cases.values())
    stride=(slice(None,None,3),slice(None,None,3))
    for row,(name,case) in enumerate(cases.items()):
        label='Dry lower air' if row==0 else 'Humid lower air';mode=case['mode']
        panel(axes[row,0],case['projected'].forcing_m2_s3,label+'\nProjected first-mode heating','m²/s³',limit=qlim,signed=True)
        panel(axes[row,1],mode.geopotential,label+'\nSteady pressure-mode response','m²/s²',limit=plim,signed=True)
        panel(axes[row,2],.75*mode.divergence_per_s*1e6,label+'\nLower convergence and wind','10⁻⁶ / s',limit=dlim,signed=True)
        u=-.75*.5*(mode.u_east[:,:-1]+mode.u_east[:,1:]);v=-.75*.5*(mode.v_south[:-1]+mode.v_south[1:])
        qu=axes[row,2].quiver(x[stride]/1000,north[stride]/1000,u[stride],-v[stride],scale=25,width=.003,color='#253746')
        axes[row,2].quiverkey(qu,.72,.95,1.,'1 m/s',coordinates='axes',labelpos='E')
    fig.suptitle('Accounted phase heat → specified vertical mode → steady dry response\nConstant N=0.01/s, depth15km, c=47.75m/s; forward demonstration, not a coupled time integration',fontsize=15)
    fig.savefig(out/'latent_mode_response.png',dpi=150);plt.close(fig)
    serial={}
    for name,case in cases.items():
        phase,proj,mode=case['phase'],case['projected'],case['mode']
        serial[name]=dict(phase_certificate=phase.certificate,projection_certificate=proj.certificate,
            mode_certificate=mode.certificate,independent=case['independent'],
            arrays=dict(initial_vapor=case['initial_w'].tolist(),final_temperature=phase.temperature_k.tolist(),
            final_vapor=phase.vapor_kg_m2.tolist(),ground_rain=phase.surface_rain_kg_m2.tolist(),
            condensation=phase.condensation_kg_m2.tolist(),rain_evaporation=phase.rain_evaporation_kg_m2.tolist(),
            layer_heat_w_m2=case['heat'].tolist(),projected_forcing=proj.forcing_m2_s3.tolist(),
            thickness_forcing=case['thickness'].forcing_m2_s3.tolist(),
            captured_buoyancy_forcing_norm_fraction=proj.captured_buoyancy_forcing_norm_fraction.tolist(),
            u_east=mode.u_east.tolist(),v_south=mode.v_south.tolist(),geopotential=mode.geopotential.tolist(),
            divergence_per_s=mode.divergence_per_s.tolist()))
    sources=['rotclimate/phase_adjustment.py','rotclimate/heating_projection.py','rotclimate/baroclinic_heating.py',
        'rotclimate/regional_baroclinic.py','rotclimate/column_thermodynamics.py',
        'tests/test_phase_adjustment.py','tests/test_heating_projection.py','tests/test_baroclinic_heating.py',
        'scripts/demo_latent_circulation.py','reports/LATENT_HEATING_20261028.md','reports/FIRST_MODE_HEATING_20261028.md']
    write_json(out/'verification.json',dict(status='passed_isolated_latent_forward_demonstration',
        actual_earth_integrations=0,isolated_regional_mode_solves=2,phase_column_cases=2,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,manufactured_only=True,
        sources={name:file_hash(ROOT/name) for name in sources},configuration=dict(cell_m=dx,
            shape=list(ps.shape),phase_interval_seconds=interval,depth_m=15000.,N_per_s=.01,Tref_k=275.,
            lower_fraction=.25,momentum_drag_days=5,thermal_drag_days=20,upper_initial_rh=rh_upper.tolist()),
        shared_arrays=dict(pressure_edges_pa=edges.tolist(),representative_pressure_pa=representative.tolist(),
                           layer_mass_kg_m2=masses.tolist(),initial_temperature_k=initial_t.tolist()),
        cases=serial,images_sha256={name:file_hash(out/name) for name in ['latent_phase_budget.png','latent_mode_response.png']},
        limitations='Fixed-pressure liquid-only dilute enthalpy boxes; specified maintained constant-N Boussinesq first mode, no compressible vertical structure/ice/transport/radiation/latent feedback time integration.'))
    print({name:case['independent'] for name,case in cases.items()})


if __name__=='__main__':main()
