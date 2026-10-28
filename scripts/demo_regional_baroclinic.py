"""Fixed manufactured regional dry-mode comparison; no Earth climate runs."""
from pathlib import Path
import argparse
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate.regional_baroclinic import embed_two_layers, solve_regional_mode
from scripts.local_benchmark_protocol import file_hash, write_json

SCALES = dict(wave_speed_ms=50., momentum_drag_s=1/(5*86400.), thermal_drag_s=1/(20*86400.))
PASSIVE = dict(west='impedance', east='impedance', north='impedance', south='impedance')


def fields(nx):
    ny = 5*nx//6
    dx = 4800000./nx
    y, x = np.mgrid[:ny, :nx]
    x = (x+.5)*dx-2400000.
    north = 2000000.-(y+.5)*dx
    height = 3400*np.exp(-((x-300000.)/370000.)**2-(north/1500000.)**2)
    mass = np.exp(-height/8000.)
    target = 3*np.exp(-((x+200000.)**2+(north-200000.)**2)/(2*650000.**2))
    target -= target.mean()
    q = 287.05*np.log(7/3)*SCALES['thermal_drag_s']*target
    # Beta-plane f is set from Earth latitude at each row, fixed geometric domain.
    f = 2*7.292e-5*np.sin(np.radians(30+np.degrees(north/6371000.)))
    return dx, x, north, height, mass, q, f


def audit(mode, mass, q, dx):
    """Independent face work, integrated mass/thermal budgets and embedding."""
    c, r, rt = SCALES.values()
    u, v, p = mode.u_east, mode.v_south, mode.geopotential
    mu = np.column_stack((mass[:,0], .5*(mass[:,:-1]+mass[:,1:]), mass[:,-1]))
    mv = np.vstack((mass[0], .5*(mass[:-1]+mass[1:]), mass[-1]))
    div = (np.diff(mu*u, axis=1)+np.diff(mv*v, axis=0))/(mass*dx)
    boundary_flux = (np.sum(mu[:,-1]*u[:,-1])-np.sum(mu[:,0]*u[:,0])
                     +np.sum(mv[-1]*v[-1])-np.sum(mv[0]*v[0]))/dx
    export = (np.sum(mu[:,-1]*p[:,-1]*u[:,-1])-np.sum(mu[:,0]*p[:,0]*u[:,0])
              +np.sum(mv[-1]*p[-1]*v[-1])-np.sum(mv[0]*p[0]*v[0]))/dx
    drag = r*(np.sum(mu[:,1:-1]*u[:,1:-1]**2)+np.sum(mv[1:-1]*v[1:-1]**2))
    thermal = rt*np.sum(mass*(p/c)**2)
    supply = np.sum(mass*p*q/c**2)
    energy_error = float(abs(supply-drag-thermal-export)/max(abs(supply),1e-30))
    thermal_residual = float(np.abs(c*c*div+rt*p-q).max())
    np.testing.assert_allclose(c*c*div+rt*p,q,rtol=1e-9,atol=1e-13)
    assert energy_error<1e-10 and export>=0
    np.testing.assert_allclose(div,mode.divergence_per_s,atol=1e-20,rtol=1e-12)
    layers = embed_two_layers(mode)
    np.testing.assert_array_equal(.25*layers['lower_u_east']+.75*layers['upper_u_east'],0.)
    np.testing.assert_array_equal(.25*layers['lower_v_south']+.75*layers['upper_v_south'],0.)
    return dict(independent_relative_energy_error=energy_error,
                independent_thermal_residual_m2_s3=thermal_residual,
                independent_integrated_mass_error_per_s=float(abs(np.sum(mass*div)-boundary_flux)/mass.sum()),
                independent_dry_column_face_velocity_residual_ms=float(max(
                    np.abs(.25*layers['lower_u_east']+.75*layers['upper_u_east']).max(),
                    np.abs(.25*layers['lower_v_south']+.75*layers['upper_v_south']).max())),
                rates_m2_s3=dict(forcing=float(supply/mass.sum()),momentum=float(drag/mass.sum()),
                                thermal=float(thermal/mass.sum()),boundary=float(export/mass.sum())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    dx,x,north,height,mass,q,f = fields(48)
    cases = {}
    for key, m, edges in [('flat-wall', np.ones_like(mass), {}),
                          ('mass-wall', mass, {}), ('mass-passive', mass, PASSIVE)]:
        mode = solve_regional_mode(q,dx,f,column_mass=m,boundaries=edges,**SCALES)
        cases[key] = dict(mode=mode, mass=m, independent=audit(mode,m,q,dx))
    # Same physical domain/forcing sampled at 24,48,96 columns, not retuned.
    resolution = {48:cases['mass-passive']['mode']}
    for nx in (24,96):
        d,_,_,_,m,qq,ff = fields(nx)
        result = solve_regional_mode(qq,d,ff,column_mass=m,boundaries=PASSIVE,**SCALES)
        resolution[nx] = result
        audit(result,m,qq,d)
    ref = resolution[96].geopotential
    errors = {}
    for nx in (24,48):
        k = 96//nx
        averaged = ref.reshape(5*nx//6,k,nx,k).mean(axis=(1,3))
        difference = resolution[nx].geopotential-averaged
        errors[str(nx)] = dict(rms_geopotential_difference_m2_s2=float(np.sqrt(np.mean(difference**2))),
                              relative_rms_difference=float(np.sqrt(np.mean(difference**2)/np.mean(averaged**2))))
    assert errors['48']['relative_rms_difference'] < errors['24']['relative_rms_difference']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    extent = [-2400,2400,-2000,2000]
    fig,axes = plt.subplots(2,3,figsize=(16,10),layout='constrained')
    values = [height/1000,cases['mass-wall']['mode'].geopotential,cases['mass-passive']['mode'].geopotential,
              q*86400/(287.05*np.log(7/3)),.75*cases['mass-wall']['mode'].divergence_per_s*1e6,
              .75*cases['mass-passive']['mode'].divergence_per_s*1e6]
    titles = ['Synthetic relief → column mass','Solved mode, closed walls','Solved mode, passive edges',
              'Identical forcing in every case','Lower convergence, closed walls','Lower convergence, passive edges']
    labels = ['Height km','Geopotential m²/s²','Geopotential m²/s²','Equivalent temperature tendency K/day',
              '10⁻⁶ / s','10⁻⁶ / s']
    plim=max(np.abs(values[1]).max(),np.abs(values[2]).max())
    dlim=max(np.abs(values[4]).max(),np.abs(values[5]).max())
    for k,(ax,value,title,label) in enumerate(zip(axes.ravel(),values,titles,labels)):
        limit=[None,plim,plim,np.abs(values[3]).max(),dlim,dlim][k]
        options=dict(cmap='terrain',vmin=0,vmax=3.4) if k==0 else dict(cmap='RdBu_r',vmin=-limit,vmax=limit)
        picture=ax.imshow(value,extent=extent,origin='upper',**options)
        ax.set(title=title,xlabel='Eastward distance km',ylabel='Northward distance km')
        fig.colorbar(picture,ax=ax,shrink=.8,label=label)
    stride=(slice(None,None,3),slice(None,None,3))
    for ax,key in [(axes[1,1],'mass-wall'),(axes[1,2],'mass-passive')]:
        result=cases[key]['mode']
        uc=-.75*.5*(result.u_east[:,:-1]+result.u_east[:,1:])
        vc=-.75*.5*(result.v_south[:-1]+result.v_south[1:])
        arrows=ax.quiver(x[stride]/1000,north[stride]/1000,uc[stride],-vc[stride],color='#253746',scale=12,width=.003)
        ax.quiverkey(arrows,.72,.95,1.,'1 m/s',coordinates='axes',labelpos='E')
    fig.suptitle('Regional circulation with mass weights and passive edges\nManufactured dry-mode test; relief changes column mass only; no rainfall prediction',fontsize=15)
    fig.savefig(out/'regional_baroclinic_response.png',dpi=150)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    delta=cases['mass-wall']['mode'].geopotential-cases['flat-wall']['mode'].geopotential
    limit=np.abs(delta).max()
    picture=axes[0].imshow(delta,extent=extent,origin='upper',cmap='RdBu_r',vmin=-limit,vmax=limit)
    axes[0].set(title='Mass weighting effect, same closed walls',xlabel='Eastward distance km',ylabel='Northward distance km')
    fig.colorbar(picture,ax=axes[0],shrink=.8,label='Change in geopotential m²/s²')
    pos=np.arange(3);bottom=np.zeros(3)
    for term,color in [('momentum','#357b92'),('thermal','#98b8b3'),('boundary','#d3b16a')]:
        vals=np.array([case['independent']['rates_m2_s3'][term] for case in cases.values()])*1e6
        axes[1].bar(pos,vals,bottom=bottom,label=term,color=color)
        bottom+=vals
    axes[1].plot(pos,[case['independent']['rates_m2_s3']['forcing']*1e6 for case in cases.values()],'kx',label='supply')
    axes[1].set(xticks=pos,xticklabels=['Flat/wall','Mass/wall','Mass/passive'],title='Independent modal energy accounting',ylabel='10⁻⁶ m²/s³')
    axes[1].legend()
    axes[2].plot([200,100],[errors[str(nx)]['rms_geopotential_difference_m2_s2'] for nx in (24,48)],'o-')
    axes[2].set(title='Fixed-domain refinement toward 50 km mesh',xlabel='Grid spacing km',ylabel='RMS geopotential difference m²/s²')
    axes[2].invert_xaxis();axes[2].grid(alpha=.2)
    fig.suptitle('Mass and boundary sensitivity — an operator check, not climate skill',fontsize=14)
    fig.savefig(out/'regional_baroclinic_budgets.png',dpi=150)
    plt.close(fig)
    sources=['rotclimate/regional_baroclinic.py','tests/test_regional_baroclinic.py',
             'scripts/demo_regional_baroclinic.py','reports/REGIONAL_BAROCLINIC_20261028.md']
    serial={}
    for key,case in cases.items():
        mode=case['mode']
        serial[key]=dict(certificate=mode.certificate,independent=case['independent'],
                        arrays=dict(geopotential=mode.geopotential.tolist(),u_east=mode.u_east.tolist(),
                                    v_south=mode.v_south.tolist(),mass=case['mass'].tolist(),
                                    divergence_per_s=mode.divergence_per_s.tolist()))
    write_json(out/'verification.json',dict(status='passed_isolated_regional_operator',manufactured_only=True,
        actual_earth_integrations=0,coupled_climate_connected=False,physics_or_atlas_adoption=False,
        regional_tests_passed=17,isolated_operator_solves=5,sources={n:file_hash(ROOT/n) for n in sources},
        configuration=dict(**SCALES,cell_m=dx,shape=list(q.shape),rotation='Earth latitude30N plus northward offset',
                           relief_mass_law='exp(-height/8000m)',maximum_synthetic_height_m=float(height.max())),
        resolution_against_96_columns=errors,cases=serial,
        forcing_m2_s3=q.tolist(),images_sha256={p.name:file_hash(p) for p in out.glob('regional_baroclinic_*.png')},
        limitations='Variable mass only; no terrain metric, mountain blocking, background advection, physical atmospheric heating or moisture coupling. Impedance is first-order and not a transparent rotating boundary.'))
    print({key:case['independent'] for key,case in cases.items()})
    print(errors)


if __name__=='__main__':
    main()
