"""Resolved native moisture on winds generated from a shared thermal state."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.vertical_state import build_vertical_state,stable_reference
from rotclimate.hydrostatic_wave import HydrostaticWave
from rotclimate.multilevel_transport import solve_multilevel
from scripts.audit_multilevel_adiabatic import audit
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    nz,ny,nx=32,18,24;dx=1e5;edges=np.linspace(0,15000,nz+1);z=.5*(edges[:-1]+edges[1:])
    ref=stable_reference(z);col=build_vertical_state(edges,ref.density_kg_m3,np.full(nz-1,.0001))
    j,i=np.mgrid[:ny,:nx];x=(i+.5)*dx-1200000.;north=900000.-(j+.5)*dx
    phi=150*np.exp(-(x*x+north*north)/(2*400000.**2))
    wave=HydrostaticWave(col,0,(ny,nx),dx,2*7.292e-5*np.sin(np.radians(30)))
    state=wave.from_buoyancy(col.buoyancy_modes[:,0,None,None]*phi)
    for _ in range(24):state=wave.advance(state,900.)
    mass=np.broadcast_to(col.cell_mass_kg_m2[:,None,None],(nz,ny,nx)).copy()
    u=col.pressure_modes[:,0,None,None]*state.u_east
    v=col.pressure_modes[:,0,None,None]*state.v_south
    mixing=.012*np.exp(-z[:,None,None]/2300.)*(1+.3*np.exp(-((x+300000.)**2+north*north)/(2*400000.**2)))
    initial=mass*mixing;water=initial.copy();dt=3*3600.;records=[]
    for step in range(8):
        last_source=water/dt
        result=solve_multilevel(mass,u,v,dx,last_source,1/dt,mixing)
        water=result.amount;relative=float(abs(water.sum()-initial.sum())/initial.sum())
        if relative>1e-12:raise ValueError('Closed multilevel transient vapor budget failed')
        records.append(dict(step=step+1,hours=(step+1)*3,relative_total_water_error=relative,certificate=result.certificate))
    audit_result=audit()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained');slice_y=ny//2
    for ax,value,title in [(axes[0,0],mixing[:,slice_y]*1000,'Initial vertical moisture section'),(axes[0,1],water[:,slice_y]/mass[:,slice_y]*1000,'After24h resolved moisture transport')]:
        im=ax.pcolormesh(np.linspace(-1200,1200,nx+1),edges/1000,value,cmap='YlGnBu',vmin=0,vmax=float(mixing.max()*1000),shading='flat')
        ax.set(title=title,xlabel='Eastward distance km',ylabel='Height km');fig.colorbar(im,ax=ax,shrink=.8,label='Vapor/dry mixing ratio g/kg')
    change=water.sum(0)-initial.sum(0);limit=max(float(np.abs(change).max()),1e-20)
    im=axes[1,0].imshow(change,origin='upper',extent=[-1200,1200,-900,900],cmap='RdBu_r',vmin=-limit,vmax=limit)
    axes[1,0].set(title='Column vapor redistribution, total conserved',xlabel='Eastward distance km',ylabel='Northward distance km');fig.colorbar(im,ax=axes[1,0],shrink=.8,label='kg/m²')
    for key,color in [('ascent','#b96735'),('descent','#357a9c')]:
        rows=audit_result['profiles']['hydrostatic_density'];levels=[int(n) for n in rows]
        axes[1,1].plot(levels,[rows[str(n)]['independent_semidiscrete_ratio'][key] for n in levels],'o-',color=color,label='Stratified '+key)
    axes[1,1].axhline(1,color='#333',ls='--',lw=1);axes[1,1].set(xscale='log',xticks=levels,xticklabels=levels,title='Resolved adiabatic response vs mode',xlabel='Vertical cells',ylabel='Diagnosed / expected response');axes[1,1].legend(fontsize=9);axes[1,1].grid(alpha=.2)
    fig.suptitle('Moisture on the shared32-level hydrostatic geometry\nWind generated from a dry thermal state, then held fixed; passive vapor, no phase or Earth forecast',fontsize=14)
    picture=out/'multilevel_transport.png';fig.savefig(picture,dpi=150,bbox_inches='tight');plt.close(fig)
    sources=['rotclimate/multilevel_transport.py','rotclimate/vertical_state.py','rotclimate/hydrostatic_wave.py','rotclimate/column_thermodynamics.py',
        'tests/test_multilevel_transport.py','scripts/audit_multilevel_adiabatic.py','scripts/demo_multilevel_transport.py','reports/MULTILEVEL_TRANSPORT_20261028.md']
    write_json(out/'verification.json',dict(status='passed_isolated_shared_grid_moisture',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,manufactured_only=True,
        sources={n:file_hash(ROOT/n) for n in sources},image_sha256=file_hash(picture),configuration=dict(levels=nz,shape=[ny,nx],cell_m=dx,dt_s=dt,steps=8,dry_wind_spinup_hours=6),
        final_relative_total_water_error=records[-1]['relative_total_water_error'],records=records,adiabatic_audit=audit_result,
        final_certificate=result.certificate,vertical_certificate=col.certificate,
        arrays=dict(vertical_edges_m=edges.tolist(),layer_mass=mass.tolist(),u_east=u.tolist(),v_south=v.tolist(),initial_vapor=initial.tolist(),final_vapor=water.tolist(),
            east_vapor_flux=result.east_tracer_flux.tolist(),south_vapor_flux=result.south_tracer_flux.tolist(),upward_vapor_flux=result.upward_tracer_flux.tolist(),
            upward_dry_mass_flux=result.upward_dry_mass_flux.tolist(),last_step_source=last_source.tolist()),
        limitations='Sequential dry wind generation and fixed-wind passive moisture; no phase, thermal/momentum feedback, radiation or Earth climate integration.'))
    print(dict(relative_total_water_error=records[-1]['relative_total_water_error'],minimum_water=float(water.min()),vertical_levels=nz,maximum_dry_column_residual=result.certificate['maximum_relative_dry_column_mass_residual']))


if __name__=='__main__':main()
