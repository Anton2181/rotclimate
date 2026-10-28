"""Manufactured check: two donor boxes do not equal a smooth first mode."""
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.column_thermodynamics import CP,G
from rotclimate.regional_baroclinic import RegionalMode,mass_divergence
from rotclimate.regional_energy_step import advance_energy
from rotclimate.baroclinic_heating import project_first_mode


def audit():
    ny,nx=3,12;dx=100000.;mass=np.full((ny,nx),9000.);a=.25;depth=15000.;n=.01;tref=275.
    z=np.broadcast_to(np.array([1875.,9375.])[:,None,None],(2,ny,nx))
    lapse=G/CP-n*n*tref/G
    temperature=tref-lapse*(z-depth/2)
    u=np.tile(np.sin(np.pi*np.arange(nx+1)/nx),(ny,1));u[:,[0,-1]]=0.
    v=np.zeros((ny+1,nx));div=mass_divergence(u,v,mass,dx)
    mode=RegionalMode(u,v,np.zeros_like(mass),div,{})
    layer_mass=np.stack([a*mass,(1-a)*mass]);result={}
    scale=np.sin(np.pi*a)/(np.pi*a*(1-a))
    for dt in [1.,.1,.01]:
        moved=advance_energy(mode,mass,dx,temperature,0.,z,dt,temperature,0.)
        tendency=(moved.temperature_k-temperature)/dt
        projected=project_first_mode(CP*layer_mass*tendency,mass,[0.,a,1.],depth_m=depth,buoyancy_frequency_s=n,reference_temperature_k=tref)
        ratio=-projected.forcing_m2_s3/(projected.wave_speed_ms**2*div)
        result[str(dt)]=dict(upward_ratio=float(np.median(ratio[div>1e-8])),downward_ratio=float(np.median(ratio[div<-1e-8])))
    expected=dict(upward_ratio=float(scale*a*(1+np.cos(np.pi*a))),downward_ratio=float(scale*(1-a)*(1-np.cos(np.pi*a))))
    for k,v in expected.items():
        if abs(result['0.01'][k]-v)>1e-5:raise ValueError('Manufactured coarse donor limit was not recovered')
    return dict(actual_earth_integrations=0,closure_matches_continuous_mode=False,
        numerical=result,independent_one_sided_limits=expected,
        continuous_wave_speed_ms=n*depth/np.pi,
        explanation='Donor transport of a discontinuous two-box background adjusts only receiving air. Its projected infinitesimal response is direction-dependent; do not directly couple it to a smooth first mode with an independently imposed c²divU adjustment.')


if __name__=='__main__':
    from scripts.local_benchmark_protocol import write_json
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    result=audit();write_json(args.out,result);print(result)
