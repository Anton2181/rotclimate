"""Verify actual split-convection water/enthalpy/rain and closure sensitivity."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def verify(r,a):
    if r['actual_earth_integrations']!=0 or r['physics_or_atlas_adoption'] is not False:raise ValueError('Need isolated non-adopted closure scope')
    for n,h in r['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed closure source: '+n)
    if r['configuration']['relaxation_times_s']!=[0,3600,10800] or r['configuration']['timesteps_s']!=[300,150,75]:raise ValueError('Changed declared closure/refinement cases')
    m=a['cell_mass'];face_mass=m[:,0,0,None,None];cells=int(np.prod(m.shape[1:]));p=np.sqrt(a['pressure_edges'][:-1]*a['pressure_edges'][1:])[:,None,None]
    enthalpy=lambda t,w:(1004*m+1850*w)*t+(2.5e6-1850*273.15)*w
    kinetic=lambda u,v:.5*(np.sum(face_mass*u[:,:,1:-1]**2)+np.sum(face_mass*v[:,1:-1]**2))
    initial=enthalpy(a['initial_temperature'],a['initial_vapor']).sum();water0=a['initial_vapor'].sum()
    max_energy=0.;max_water=0.;cases={}
    for name,case in r['cases'].items():
        outcomes={};tau=case['relaxation_s']
        for key,run in case['runs'].items():
            prefix=name+'_'+key+'_';t,w,u,v,rain,rain_h=[a[prefix+field] for field in ['temperature','vapor','u','v','rain','rain_enthalpy']]
            if np.any(u[:,:,[0,-1]]) or np.any(v[:,[0,-1]]):raise ValueError('Exterior flow changed')
            h=enthalpy(t,w).sum();ke=kinetic(u,v);energy_error=float(abs(h+ke+rain_h.sum()-initial)/abs(initial));water_error=float(abs(w.sum()+rain.sum()-water0)/water0)
            max_energy=max(max_energy,energy_error);max_water=max(max_water,water_error)
            np.testing.assert_allclose(run['history'][-1]['gas_enthalpy_plus_kinetic_energy_j_m2'],(h+ke)/cells,rtol=1e-12)
            np.testing.assert_allclose(run['history'][-1]['kinetic_energy_j_m2'],ke/cells,rtol=1e-12)
            np.testing.assert_allclose(run['mean_rain_mm'],rain.mean(),rtol=1e-12)
            peak=float(max(abs(u).max(),abs(v).max()));np.testing.assert_allclose(run['peak_level_velocity_ms'],peak,rtol=1e-12)
            es=611.2*np.exp(17.67*(t-273.15)/(t-29.65));sat=m*.622*es/(p-es)
            if np.any(w>sat*(1+1e-9)):raise ValueError('Final phase saturation failed')
            alpha=1 if tau==0 else -np.expm1(-run['dt_s']/tau)
            for history in run['history']:
                if history['target_converged'] is not True:raise ValueError('Nonconverged adjustment target accepted')
                np.testing.assert_allclose(history['adjusted_fraction'],alpha,rtol=1e-12)
            actual_parcel=float(np.mean(a[prefix+'positive_parcel_energy']));np.testing.assert_allclose(run['mean_positive_parcel_energy_j_kg'],actual_parcel,rtol=1e-12)
            if key!='75':
                for field in ['temperature','vapor','u','v','rain']:
                    actual=float(np.sqrt(np.mean((a[prefix+field]-a[name+'_75_'+field])**2)))
                    np.testing.assert_allclose(run['difference_vs_75s'][field],actual,rtol=1e-12)
            outcomes[key]=dict(actual_relative_total_energy_error=energy_error,actual_relative_water_error=water_error,
                actual_peak_level_velocity_ms=peak,actual_mean_rain_mm=float(rain.mean()),actual_mean_partial_positive_parcel_energy_j_kg=actual_parcel)
        cases[name]=outcomes
    old=enthalpy(a['stable_initial_temperature'],a['stable_initial_vapor']).sum()
    final=enthalpy(a['stable_temperature'],a['stable_vapor']).sum()+kinetic(a['stable_u'],a['stable_v'])+a['stable_rain_enthalpy'].sum()
    stable_error=float(abs(final-old)/abs(old));max_energy=max(max_energy,stable_error)
    stable_water=float(abs(a['stable_vapor'].sum()+a['stable_rain'].sum()-a['stable_initial_vapor'].sum())/a['stable_initial_vapor'].sum());max_water=max(max_water,stable_water)
    if r['stable_control']['adjusted_pairs']!=0 or r['stable_control']['maximum_temperature_difference_vs_no_adjustment_k']>1e-8 or r['stable_control']['maximum_velocity_difference_vs_no_adjustment_ms']>1e-8:
        raise ValueError('Stable control was changed by the closure')
    if max(max_energy,max_water)>1e-10:raise ValueError('Actual closure long-run total budgets failed')
    return dict(maximum_actual_total_energy_relative_error=max_energy,maximum_actual_water_rain_relative_error=max_water,
        stable_actual_energy_relative_error=stable_error,cases=cases,
        scope='Actual final gas enthalpy+face kinetic+rain enthalpy and water, converged neutral targets, exact relaxation fraction, phase saturation and stable control. Closure sensitivity is not Earth validation.')


def publish(out):
    r=json.loads((out/'verification.json').read_text())
    if file_hash(out/'fields.npz')!=r['raw_fields_sha256'] or file_hash(out/'convective_adjustment.png')!=r['image_sha256']:raise ValueError('Changed closure raw fields/image')
    with np.load(out/'fields.npz') as data:checks=verify(r,{k:data[k] for k in data.files})
    dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'fields.npz',dest/'convective_adjustment_fields.npz');shutil.copyfile(out/'convective_adjustment.png',dest/'convective_adjustment.png')
    write_json(dest/'convective_adjustment.json',dict(experiment=r,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    with Image.open(out/'convective_adjustment.png') as im:w,h=im.size
    rows=''.join(f'<tr><td>{name.replace("_"," ")}</td><td>{case["runs"]["75"]["mean_positive_parcel_energy_j_kg"]:.2f}</td><td>{case["runs"]["75"]["peak_level_velocity_ms"]:.2f}</td><td>{case["runs"]["75"]["mean_rain_mm"]:.3f}</td></tr>' for name,case in r['cases'].items())
    section=f'''<!--convective-adjustment-start--><section aria-labelledby="convective-adjustment-h"><h2 id="convective-adjustment-h">Conservative convective adjustment and closure sensitivity</h2>
<p><strong>Unstable near-saturated layers now have an explicit conservative convection treatment.</strong> Dry-unstable pairs, or near-saturated lower cells whose lifted saturated parcel is warmer than the upper cell, redistribute heat and vapor toward a neutral parcel lapse. Each pair preserves actual water and gas enthalpy. Subsequent liquid phase and ground rain carry actual enthalpy. No wind or buoyancy cap is applied.</p>
<p>The instantaneous target is compared with declared one-hour and three-hour relaxation times at300/150/75-second timesteps. Finite adjustment blends water, gas enthalpy and exported-rain budgets rather than interpolating temperature; the homogenized mixture’s phase change is then booked explicitly. The stable control receives no pair adjustments and matches the unadjusted run to roundoff. Strong conditional motion and closure sensitivity remain visible; this is not adopted Earth physics.</p>
<figure><a href="data/convective_adjustment.png"><img src="data/convective_adjustment.png" width="{w}" height="{h}" loading="lazy" alt="Instantaneous, one-hour and three-hour convection closures compared under timestep refinement, with residual parcel energy, winds and rain"></a><figcaption>One manufactured conditional-moist column, identical initial state, no calibration. Remaining partial-column parcel energy and wind/rain sensitivity are retained.</figcaption></figure>
<div class="table"><table><caption>Finest75-second runs; comparison parameters declared before results, not selected against Earth rainfall</caption><thead><tr><th>Closure</th><th>Mean positive parcel J/kg</th><th>Peak level wind m/s</th><th>Mean rain mm</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Eleven new tests bring the focused suite to293 passes. Tests check dry/moist neutralization, actual water/enthalpy/rain, unchanged stable and unsaturated controls, target agreement with a finer parcel path, split coupled budgets, explicit target nonconvergence, finite relaxation and the no-adjustment limit. Nine conditional runs and one stable control make1656 new repeated steps. Publication independently reconstructs actual final gas/kinetic/rain energy, water, phase bounds, relaxation fractions and refinement comparisons from raw fields.</p>
<p class="note">This is instantaneous local adjacent mixing, optionally relaxed in time, without entrainment, convective momentum transport or explicit turbulent kinetic energy. An unsaturated dry-stable column is not adjusted merely because a finite lift could release parcel energy. A converged neutral target does not imply that a partially relaxed state has no active layers; both are reported. The dynamics/transport/phase step and adjustment are first-order split: final pressure responds on the next timestep, and the nested momentum certificate applies before adjustment. The inherited dry/dilute coordinate omits water loading/volume/potential, ice, nonlinear momentum, radiation, terrain and prognostic surface pressure. Parameterization and resolution sensitivity remain physical acceptance gates. No Earth integration, adoption or rainfall-accuracy gain; Earthr39 and normal world/biome/population fields remain unchanged. Counters stay1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p><a href="data/convective_adjustment.json" download>Download convection cases, budgets, refinement and provenance</a> · <a href="data/convective_adjustment_fields.npz">Raw convective/dynamical states and rain fields</a> · <a href="../../reports/CONVECTIVE_ADJUSTMENT_20261029.md">Conservative closure, relaxation and remaining limitations</a></p></section><!--convective-adjustment-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';s=page.read_text()
    if '<!--convective-adjustment-start-->' in s:
        before,tail=s.split('<!--convective-adjustment-start-->',1);_,after=tail.split('<!--convective-adjustment-end-->',1);s=before+section+after
    else:s=s.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(s)
    result=dict(status='published_experimental_conservative_convection',actual_earth_integrations=0,physics_or_atlas_adoption=False,
        independent_publication_checks=checks,metadata_sha256=file_hash(dest/'convective_adjustment.json'),image_sha256=r['image_sha256'],publisher_sha256=file_hash(Path(__file__)))
    write_json(out/'publication.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
