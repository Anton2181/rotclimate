"""Resolved donor thermodynamics versus the shared hydrostatic mode adiabat."""
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.column_thermodynamics import CP,G
from rotclimate.vertical_state import build_vertical_state,stable_reference
from rotclimate.multilevel_transport import solve_multilevel


def audit():
    result={}
    for reference in ['uniform_linear','hydrostatic_density']:
        rows={}
        for n in [4,8,16,32,64,128]:
            edges=np.linspace(0,15000,n+1);z=.5*(edges[:-1]+edges[1:]);n2=.0001
            if reference=='uniform_linear':
                density=np.ones(n);temperature=275+(n2*275/G-G/CP)*(z-7500);ti=np.full(n-1,275.)
            else:
                ref=stable_reference(z);density=ref.density_kg_m3;temperature=ref.temperature_k
                ti=stable_reference(edges[1:-1]).temperature_k
            col=build_vertical_state(edges,density,np.full(n-1,n2));mass=col.cell_mass_kg_m2;static=CP*temperature+G*z
            ratios={};actual={}
            for sign,name in [(1,'ascent'),(-1,'descent')]:
                amplitude=sign*1e-6;div=col.pressure_modes[:,0]*amplitude
                vertical=np.r_[0.,-np.cumsum(mass*div)];vertical[-1]=0
                donor=np.where(vertical[1:-1]>=0,static[:-1],static[1:])
                energy_flux=np.r_[0.,vertical[1:-1]*donor,0.]
                tdot=-(mass*static*div+np.diff(energy_flux))/(CP*mass)
                bdot=G/ti*.5*(tdot[:-1]+tdot[1:])
                phidot=col.project_pressure(col.pressure_from_buoyancy(bdot))[0]
                ratios[name]=float(-phidot/(col.phase_speeds_ms[0]**2*amplitude))
            if reference=='uniform_linear':
                expected=np.cos(np.pi/(2*n))**2
                if max(abs(v-expected) for v in ratios.values())>1e-10:raise ValueError('Independent uniform-grid limit changed')
            # Actual backward-Euler matrix versus the independent infinitesimal
            # expression. Closed sine face flow has both ascent/descent columns.
            ny,nx=2,8;dx=1e5;dt=1.
            m=np.broadcast_to(mass[:,None,None],(n,ny,nx)).copy()
            u=np.zeros((n,ny,nx+1));u[:,:,1:-1]=col.pressure_modes[:,0,None,None]*np.sin(np.pi*np.arange(1,nx)/nx)[None,None,:]
            v=np.zeros((n,ny+1,nx));e=np.broadcast_to((mass*static)[:,None,None],m.shape)
            out=solve_multilevel(m,u,v,dx,e/dt,1/dt,static)
            td=(out.amount-e)/(CP*m*dt);bd=G/ti[:,None,None]*.5*(td[:-1]+td[1:])
            pd=col.project_pressure(col.pressure_from_buoyancy(bd))[0]
            amp=np.diff(np.sin(np.pi*np.arange(nx+1)/nx))/dx
            ratio=-pd/(col.phase_speeds_ms[0]**2*amp[None,:])
            actual=dict(ascent=float(np.median(ratio[:,amp>1e-8])),descent=float(np.median(ratio[:,amp<-1e-8])))
            if max(abs(actual[k]-ratios[k]) for k in actual)>2e-4:raise ValueError('Actual N-level thermodynamic matrix disagrees with dry derivative limit')
            rows[str(n)]=dict(first_wave_speed_ms=float(col.phase_speeds_ms[0]),independent_semidiscrete_ratio=ratios,
                             actual_one_second_ratio=actual,dt_s=dt)
        result[reference]=rows
    return dict(actual_earth_integrations=0,profiles=result,
        interpretation='Mode response ratios compare diagnosed interface buoyancy from cell thermodynamics with the shared linear mode adiabat. Uniform-density symmetry cancels directional bias; stratified density retains first-order one-sided error. Refinement reduces both, not a fitted correction or Earth accuracy.')


if __name__=='__main__':
    import argparse
    from scripts.local_benchmark_protocol import write_json
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True);value=audit();write_json(args.out,value)
    print({name:{n:v['independent_semidiscrete_ratio'] for n,v in profile.items()} for name,profile in value['profiles'].items()})
