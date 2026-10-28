"""Check actual shared-cell hydrostatics, phase and source/work energy ledgers."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def verify(r):
    if r['actual_earth_integrations']!=0 or r['interactive_moist_feedback'] is not False or r['physics_or_atlas_adoption'] is not False:
        raise ValueError('Need isolated non-adopted prescribed-pulse scope')
    for name,h in r['sources'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Changed verified source: '+name)
    a={k:np.array(v) for k,v in r['arrays'].items()};m=a['cell_mass_kg_m2'];edges=a['edges_m'];dz=np.diff(edges);z=.5*(edges[:-1]+edges[1:]);dc=np.diff(z)
    mass=m[:,None,None];e=m/a['stability_s2'];total=m.sum();g=9.80665
    vapor0,vapor1=a['initial_vapor_kg_m2'],a['phase_vapor_kg_m2'];t0,t1=a['initial_temperature_k'],a['phase_temperature_k']
    def static(t,w):return (1004*mass+1850*w)*t+(2.5e6-1850*273.15)*w+g*(mass+w)*z[:,None,None]
    e0,e1=static(t0,vapor0),static(t1,vapor1)
    phase_energy=float(np.max(np.abs(e1.sum(0)+a['ground_rain_enthalpy_j_m2']-e0.sum(0)))/np.max(e0.sum(0)))
    phase_water=float(np.max(np.abs(vapor0.sum(0)-vapor1.sum(0)-a['ground_rain_kg_m2']))/np.max(vapor0.sum(0)))
    if max(phase_energy,phase_water)>1e-12:raise ValueError('Raw resolved phase water/energy budget failed')
    tv=lambda t,w:t*(1+w/(.622*mass))/(1+w/mass)
    db=g*(tv(t1,vapor1)-tv(t0,vapor0))/t0
    np.testing.assert_allclose(a['phase_buoyancy_increment'],db,rtol=1e-12,atol=1e-15)
    # Analytic null of linear cell-to-face interpolation: alternating cell widths.
    null=(-1.)**np.arange(len(m))*dz;null*=np.sqrt(total/np.dot(e,null*null))
    expected_null_amplitude=np.einsum('k,kij->ij',e*null,db)/total
    rhof=((m[:-1]/dz[:-1])*dz[1:]+(m[1:]/dz[1:])*dz[:-1])/(dz[:-1]+dz[1:])
    maximum_balance=0.;maximum_hydrostatic=0.;maximum_mass_mean=0.;energies={}
    for key,run in r['runs'].items():
        b={k:np.array(v) for k,v in run['arrays'].items()};u,v,buoy=b['u_east'],b['v_south'],b['buoyancy_cells']
        if np.any(u[:,:,[0,-1]]) or np.any(v[:,[0,-1]]):raise ValueError('Exterior walls changed')
        shape=buoy.shape;cells=shape[1]*shape[2]
        for velocity in [u,v]:maximum_mass_mean=max(maximum_mass_mean,float(np.max(np.abs(np.sum(mass*velocity,axis=0)))/total))
        face_b=(buoy[:-1]*dz[1:,None,None]+buoy[1:]*dz[:-1,None,None])/(dz[:-1]+dz[1:])[:,None,None]
        pressure=np.concatenate([np.zeros_like(buoy[:1]),np.cumsum(face_b*dc[:,None,None],axis=0)])
        pressure-=np.sum(mass*pressure,axis=0,keepdims=True)/total
        maximum_hydrostatic=max(maximum_hydrostatic,float(np.max(abs(pressure-b['pressure_cells']))))
        np.testing.assert_allclose(pressure,b['pressure_cells'],rtol=1e-10,atol=1e-12)
        div=(np.diff(u,axis=2)+np.diff(v,axis=1))/r['configuration']['cell_m']
        w=-np.cumsum(mass*div,axis=0)[:-1]/rhof[:,None,None]
        np.testing.assert_allclose(w,b['vertical_velocity'],rtol=1e-10,atol=1e-12)
        energy=float(.5*(np.sum(mass*u[:,:,1:-1]**2)+np.sum(mass*v[:,1:-1]**2)+np.sum(e[:,None,None]*buoy**2))/(total*cells))
        source=db/r['configuration']['source_duration_s']
        actual_work=float(np.sum(e[:,None,None]*source*b['source_time_integral_buoyancy'])/(total*cells))
        relative=abs(energy-actual_work)/max(abs(energy),abs(actual_work),1e-30);maximum_balance=max(maximum_balance,relative)
        np.testing.assert_allclose(energy,run['history'][-1]['kinetic_plus_thermal_available_energy_m2_s2'],rtol=1e-12)
        amplitude=np.einsum('k,kij->ij',e*null,buoy)/total
        np.testing.assert_allclose(amplitude,expected_null_amplitude,rtol=1e-10,atol=1e-13)
        null_energy=float(.5*np.mean(amplitude**2))
        np.testing.assert_allclose(null_energy,run['history'][-1]['pressure_invisible_available_energy_m2_s2'],rtol=1e-10)
        energies[key]=dict(actual_final_energy_m2_s2=energy,actual_integrated_source_work_m2_s2=actual_work,
            actual_null_thermal_energy_m2_s2=null_energy,actual_null_fraction_of_final_energy=null_energy/energy)
        if relative>1e-11:raise ValueError('Actual final energy vs actual integrated thermal source work failed')
    if maximum_mass_mean>1e-11:raise ValueError('Column mass-mean flow failed')
    finest=r['runs']['150']['arrays']
    for name in ['buoyancy_cells','u_east','v_south','pressure_cells']:
        errors=[]
        for key in ['1200','600','300']:
            actual=float(np.sqrt(np.mean((np.array(r['runs'][key]['arrays'][name])-finest[name])**2)))
            np.testing.assert_allclose(actual,r['time_refinement'][key][name],rtol=1e-12);errors.append(actual)
        if not errors[2]<errors[1]<errors[0]:raise ValueError('Timestep refinement failed')
    return dict(phase_relative_column_energy_error=phase_energy,phase_relative_column_water_error=phase_water,
        maximum_actual_final_energy_vs_integrated_source_work_relative_error=maximum_balance,
        maximum_actual_hydrostatic_pressure_difference_m2_s2=maximum_hydrostatic,
        maximum_actual_column_mass_mean_velocity_ms=maximum_mass_mean,runs=energies,
        scope='Separate phase water/static energy and dry linear kinetic/available/source-work budgets; not their sum or a complete nonlinear moist energy law')


def publish(out):
    r=json.loads((out/'verification.json').read_text());checks=verify(r)
    if file_hash(out/'cell_thermal_wave.png')!=r['image_sha256']:raise ValueError('Changed verified image')
    data=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'cell_thermal_wave.png',data/'cell_thermal_wave.png')
    write_json(data/'cell_thermal_wave.json',dict(experiment=r,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    with Image.open(out/'cell_thermal_wave.png') as im:width,height=im.size
    rows=''.join(f'<tr><td>{float(key)/60:g}</td><td>{v["pressure_cells"]:.6f}</td><td>{v["u_east"]:.7f}</td><td>{v["v_south"]:.7f}</td></tr>' for key,v in r['time_refinement'].items())
    section=f'''<!--cell-thermal-start--><section aria-labelledby="cell-thermal-h"><h2 id="cell-thermal-h">Shared-cell thermal state, all-level dynamics and a resolved phase pulse</h2>
<p><strong>Cell-centered thermal anomalies now drive pressure and winds without choosing a single vertical mode.</strong> The alternative Lorenz vertical grid shares cell locations with the resolved temperature/moisture code. Hydrostatic pressure is integrated from interpolated cell buoyancy; its exact energy adjoint supplies the adiabatic thermal tendency. On uneven grids the actual pressure work cancels the thermal available-energy tendency. All cell thermal degrees of freedom and all level velocities evolve together.</p>
<p>The discretization exposes one pressure-invisible alternating thermal computational mode. It is retained, measured and tested, rather than filtered or silently assigned to circulating energy. Its energy is about0.89% of the final energy in this particular pulse test; that is not a universal bound. Independent uniform-grid standing-wave dispersion and Crank-Nicolson phase tests check the remaining internal waves.</p>
<figure><a href="data/cell_thermal_wave.png"><img src="data/cell_thermal_wave.png" width="{width}" height="{height}" loading="lazy" alt="A manufactured resolved phase temperature impulse, all-level dry pressure and winds after six hours, vertical velocity and separately tracked computational thermal energy"></a><figcaption>A single liquid-phase pulse supplies one hour of prescribed virtual-buoyancy forcing, then all-cell dry circulation evolves freely. This is a shallow8km manufactured experiment, not interactive moist weather or an Earth forecast.</figcaption></figure>
<p>The16-level reference derives N² from a6 K/km lapse, not an independently fitted circulation speed. One resolved phase adjustment includes vapor/liquid heat capacity, rain reevaporation and fall work. Its temperature and vapor changes supply the actual virtual-buoyancy increment. This pulse is spread over one hour in the dry dynamics, followed by five hours without forcing. Four timestep sequences20/10/5/2.5 minutes make270 coupled dry steps. The finest run reaches peak level velocities around0.68 m/s. A separate raw phase budget and the actual integrated dry thermal-source work both verify; they are different budgets and are not added into a claimed complete atmospheric energy law.</p>
<div class="table"><table><caption>RMS final differences versus2.5-minute steps; numerical refinement, not climate error</caption><thead><tr><th>Step minutes</th><th>Pressure m²/s²</th><th>East wind m/s</th><th>South wind m/s</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Seventeen new tests cover analytic vertical/horizontal dispersion, exact uneven-grid pressure/thermal work, visible null energy, variable rotation, actual forcing work, damping, hydrostatic modes and mass constraints. Direct singular-value mode calculation fixes an ill-conditioned squared-matrix calculation exposed by vertical refinement; independent full-spectrum tests pass through256 levels. Phase-heating vertical refinement remains necessary. The focused suite passes249 tests. Publication reconstructs pressure, continuity, physical source conversion, separate phase water/static energy, final dry energy, integrated source work and null amplitude from saved raw fields.</p>
<p class="note">This is linear dry fixed-reference dynamics with one prescribed phase-derived pulse. The moist state is not transported or repeatedly phase-adjusted during the wave run; density, pressure coordinates and the stable reference are maintained. Velocity is restricted to zero depth-mass-mean baroclinic flow; divergence-free barotropic winds are excluded. No moist-static-energy transport is composed, so no second adiabatic cooling is added. There is no interactive moist circulation, snow/ice, radiation, nonlinear momentum advection, compressible density or terrain. The supercooled liquid-only phase and reflecting walls are test approximations. The pressure-invisible computational mode remains a model-design issue before moist adoption. Earthr39 and normal climate/biome/population fields remain unchanged; zero new Earth integrations or rainfall gain. Counters remain1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p><a href="data/cell_thermal_wave.json" download>Download phase state, shared-cell dynamics, raw source/work integrals and checks</a> · <a href="../../reports/CELL_THERMAL_20261028.md">Shared-cell adjoint derivation and coupling limitations</a></p></section><!--cell-thermal-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--cell-thermal-start-->' in text:
        before,tail=text.split('<!--cell-thermal-start-->',1);_,after=tail.split('<!--cell-thermal-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    result=dict(status='published_isolated_shared_cell_dry_dynamics',actual_earth_integrations=0,
        interactive_moist_feedback=False,physics_or_atlas_adoption=False,independent_publication_checks=checks,
        metadata_sha256=file_hash(data/'cell_thermal_wave.json'),image_sha256=r['image_sha256'],publisher_sha256=file_hash(Path(__file__)))
    write_json(out/'publication.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
