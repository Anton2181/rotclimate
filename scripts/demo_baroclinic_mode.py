"""Manufactured heating response of the isolated dry baroclinic operator."""
from pathlib import Path
import argparse
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rotclimate.baroclinic_mode import solve_mode
from scripts.local_benchmark_protocol import file_hash,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    j,i=np.mgrid[:40,:48];dx=100000.;x=(i-23.5)*dx;ys=(j-19.5)*dx
    temp=3*np.exp(-(x*x+ys*ys)/(2*650000.**2));temp-=temp.mean()
    rd=287.05;mode_depth=np.log(7/3);rt=1/(20*86400.);r=1/(5*86400.);c=50.;f=2*7.292e-5*np.sin(np.radians(30))
    q=rd*mode_depth*rt*temp
    result=solve_mode(q,dx,f,wave_speed_ms=c,momentum_drag_s=r,thermal_drag_s=rt)
    u,v,phi=result.u_east,result.v_south,result.geopotential
    div=(u-np.roll(u,1,axis=1)+v-np.roll(v,1,axis=0))/dx
    lower_convergence=.75*div;lower_u,lower_v=-.75*u,-.75*v;upper_u,upper_v=.25*u,.25*v
    np.testing.assert_array_equal(.25*lower_u+.75*upper_u,0.)
    np.testing.assert_array_equal(.25*lower_v+.75*upper_v,0.)
    dry_residual=float(np.hypot(.25*lower_u+.75*upper_u,.25*lower_v+.75*upper_v).max())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(13,10),layout='constrained');extent=[x.min()/1000,x.max()/1000,-ys.max()/1000,-ys.min()/1000]
    values=[temp,phi,lower_convergence*1e6];titles=['Prescribed heating pattern','Solved thermal-mode geopotential','Generated lower convergence and inflow'];units=['Equivalent relaxation target K','m²/s²','10⁻⁶ / s']
    for ax,value,title,unit in zip(axes.ravel()[:3],values,titles,units):
        limit=max(float(np.abs(value).max()),1e-30);im=ax.imshow(value,origin='upper',extent=extent,cmap='RdBu_r',vmin=-limit,vmax=limit)
        ax.set(title=title,xlabel='Eastward distance km',ylabel='Northward distance km');fig.colorbar(im,ax=ax,shrink=.8,label=unit)
    stride=(slice(None,None,3),slice(None,None,3))
    uc=.5*(u+np.roll(u,1,axis=1));vc=.5*(v+np.roll(v,1,axis=0))
    upper_u,upper_v=.25*uc,.25*vc;lower_u,lower_v=-.75*uc,-.75*vc
    qu=axes[0,1].quiver(x[stride]/1000,-ys[stride]/1000,upper_u[stride],-upper_v[stride],color='#263745',scale=9,width=.003)
    ql=axes[1,0].quiver(x[stride]/1000,-ys[stride]/1000,lower_u[stride],-lower_v[stride],color='#263745',scale=27,width=.003)
    axes[0,1].quiverkey(qu,.72,.94,.25,'0.25 m/s',coordinates='axes',labelpos='E')
    axes[1,0].quiverkey(ql,.72,.94,.75,'0.75 m/s',coordinates='axes',labelpos='E')
    energy=[float(np.mean(r*(u*u+v*v))),float(np.mean(rt*(phi/c)**2)),float(np.mean(phi*q/c**2))]
    axes[1,1].bar(['Momentum damping','Thermal relaxation','Forcing supply'],energy,color=['#357b92','#96b5bf','#383f48'])
    axes[1,1].set(title='Discrete modal energy balance',ylabel='Energy rate per reference mass m²/s³');axes[1,1].grid(axis='y',alpha=.2)
    fig.suptitle('Heating generates convergence — isolated periodic dry-wave prototype\nFlat plane, Earth rotation at30°N; no terrain, moisture or Earth climate prediction',fontsize=14)
    picture=out/'baroclinic_heating_response.png';fig.savefig(picture,dpi=150);plt.close(fig)
    sources=['rotclimate/baroclinic_mode.py','tests/test_baroclinic_mode.py','scripts/demo_baroclinic_mode.py']
    write_json(out/'verification.json',dict(status='passed_isolated_operator',certificate=result.certificate,
        configuration=dict(cell_m=dx,shape=list(q.shape),coriolis_per_s=f,wave_speed_ms=c,equivalent_depth_m=c*c/9.80665,momentum_drag_days=5,thermal_drag_days=20),
        manufactured_only=True,actual_earth_integrations=0,coupled_climate_connected=False,physics_or_atlas_adoption=False,operator_tests_passed=9,
        lower_convergence_at_heating_peak_per_s=float(lower_convergence[np.unravel_index(q.argmax(),q.shape)]),
        maximum_dry_column_velocity_residual_ms=dry_residual,sources={n:file_hash(ROOT/n) for n in sources},
        image_sha256=file_hash(picture),arrays=dict(heating=q.tolist(),geopotential=phi.tolist(),u_east=u.tolist(),v_south=v.tolist()),
        prerequisites='Open/terrain boundary and donor-exchange treatment, mode forcing in physical energy units, and fixed Earth-like priors before any coupled pilot'))
    print(result.certificate)


if __name__=='__main__':main()
