"""Independently check repeated pressure-coordinate moist runs and controls."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def verify(original,controls,a,b):
    for r in [original,controls]:
        if r['actual_earth_integrations']!=0 or r['interactive_moist_feedback'] is not True or r['physics_or_atlas_adoption'] is not False:
            raise ValueError('Need isolated non-adopted repeated-moist scope')
    for n,h in original['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed coupled source: '+n)
    if file_hash(ROOT/'scripts/audit_pressure_moist_controls.py')!=controls['control_script_sha256']:raise ValueError('Changed controls source')
    mass=a['cell_mass'];mface=mass[:,0,0,None,None];cells=int(np.prod(mass.shape[1:]));max_energy=0.;max_water=0.;checks={}
    def enthalpy(t,w):return (1004*mass+1850*w)*t+(2.5e6-1850*273.15)*w
    def kinetic(u,v):return float(.5*(np.sum(mface*u[:,:,1:-1]**2)+np.sum(mface*v[:,1:-1]**2)))
    for name,data,receipt in [('conditional',a,original),('stable',b,controls)]:
        initial=enthalpy(data['initial_temperature'],data['initial_vapor']).sum();water0=data['initial_vapor'].sum();case={}
        for key,run in receipt['runs'].items():
            t,w,u,v,rain,rain_h=[data[key+'_'+field] for field in ['temperature','vapor','u','v','rain','rain_enthalpy']]
            if np.any(u[:,:,[0,-1]]) or np.any(v[:,[0,-1]]):raise ValueError('Closed walls changed')
            m0=mass[:,0,0]
            for velocity in [u,v]:
                if np.max(abs(np.sum(mface*velocity,axis=0)))/m0.sum()>1e-10:raise ValueError('Depth-mean flow constraint failed')
            h=enthalpy(t,w).sum();ke=kinetic(u,v);total=h+ke+rain_h.sum()
            energy_error=float(abs(total-initial)/abs(initial));water_error=float(abs(w.sum()+rain.sum()-water0)/water0)
            max_energy=max(max_energy,energy_error);max_water=max(max_water,water_error)
            np.testing.assert_allclose(run['history'][-1]['gas_enthalpy_plus_kinetic_energy_j_m2'],(h+ke)/cells,rtol=1e-12)
            np.testing.assert_allclose(run['history'][-1]['kinetic_energy_j_m2'],ke/cells,rtol=1e-12)
            np.testing.assert_allclose(run['history'][-1]['mean_rain_mm'],rain.mean(),rtol=1e-12)
            for history in run['history']:
                if history['maximum_temperature_fixed_point_residual_k']>1e-8:raise ValueError('Unconverged coupled state published')
                scale=max(abs(history['pressure_work_w_m2']),abs(history['compression_work_w_m2']),1.)
                if abs(history['pressure_work_w_m2']+history['compression_work_w_m2'])>1e-10*scale:raise ValueError('Pressure/compression cancellation failed')
            p=np.sqrt(a['pressure_edges'][:-1]*a['pressure_edges'][1:])[:,None,None]
            es=611.2*np.exp(17.67*(t-273.15)/(t-29.65));sat=mass*.622*es/(p-es)
            if np.any(w>sat*(1+1e-9)):raise ValueError('Actual final phase saturation failed')
            case[key]=dict(actual_relative_total_energy_error=energy_error,actual_relative_vapor_plus_rain_error=water_error,
                actual_kinetic_energy_j_m2=ke/cells,actual_peak_level_velocity_ms=float(max(abs(u).max(),abs(v).max())))
            if key!='75':
                for field in ['temperature','vapor','rain','u','v']:
                    actual=float(np.sqrt(np.mean((data[key+'_'+field]-data['75_'+field])**2)))
                    np.testing.assert_allclose(run['difference_vs_75s'][field],actual,rtol=1e-12)
        if not receipt['runs']['75']['history'][-1]['mean_rain_mm']>receipt['runs']['75']['history'][0]['mean_rain_mm']:
            raise ValueError('No repeated rain feedback recorded')
        checks[name]=case
    dry_h0=enthalpy(b['dry_initial_temperature'],np.zeros_like(mass)).sum()
    dry_final=enthalpy(b['dry_temperature'],b['dry_vapor']).sum()+kinetic(b['dry_u'],b['dry_v'])
    dry_error=float(abs(dry_final-dry_h0)/abs(dry_h0));max_energy=max(max_energy,dry_error)
    if max(max_energy,max_water)>1e-11:raise ValueError('Actual long-run conserved quantities failed')
    return dict(maximum_actual_gas_enthalpy_kinetic_rain_relative_error=max_energy,
        maximum_actual_vapor_plus_rain_relative_error=max_water,dry_actual_relative_energy_error=dry_error,
        checked_moist_runs=8,checked_dry_runs=1,cases=checks,
        physics_acceptance='Not adopted: conditional-instability stress case reaches41.8m/s without convection/nonlinear-momentum treatment. Conservation and convergence are necessary, not sufficient.',
        scope='Dry/dilute pressure-coordinate enthalpy+kinetic+rain-enthalpy ledger; no water loading/volume/potential, ice, radiation, terrain or Earth validation')


def publish(out):
    original=json.loads((out/'verification.json').read_text());controls=json.loads((out/'controls_verification.json').read_text())
    pairs=[('verification.json',controls['original_receipt_sha256']),('fields.npz',original['raw_fields_sha256']),
        ('controls_fields.npz',controls['raw_fields_sha256']),('pressure_moist_controls.png',controls['image_sha256'])]
    for n,h in pairs:
        if file_hash(out/n)!=h:raise ValueError('Changed verified artifact: '+n)
    with np.load(out/'fields.npz') as first,np.load(out/'controls_fields.npz') as second:
        checks=verify(original,controls,{k:first[k] for k in first.files},{k:second[k] for k in second.files})
    dest=ROOT/'atlases/climate_accuracy/data'
    for source,target in [('fields.npz','pressure_moist_fields.npz'),('controls_fields.npz','pressure_moist_control_fields.npz'),('pressure_moist_controls.png','pressure_moist_controls.png')]:shutil.copyfile(out/source,dest/target)
    write_json(dest/'pressure_moist.json',dict(experiment=original,controls=controls,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    with Image.open(out/'pressure_moist_controls.png') as im:width,height=im.size
    section=f'''<!--pressure-moist-start--><section aria-labelledby="pressure-moist-h"><h2 id="pressure-moist-h">Repeated moist feedback and a convection acceptance gate</h2>
<p><strong>Temperature, pressure, wind, vapor transport and liquid phase now evolve together.</strong> A new reduced pressure-coordinate model carries gas enthalpy and vapor, predicts hydrostatic pressure from temperature, and updates momentum with the actual pressure gradient. Compression work is the exact hydrostatic energy adjoint and appears once. Drag energy returns as heat, and ground rain exports its actual liquid enthalpy. Each coupled timestep iterates from the same old state; it does not repeatedly inject water or reapply condensation during iteration.</p>
<p>The stable and dry controls stay bounded, but a conditionally unstable moist column produces41.8 m/s peak winds after six hours. This stress response is retained and blocks physics adoption; passing energy and timestep checks is not sufficient to establish realistic convection. The saturated-stable control reaches2.44 m/s, and a dry run starting from the initial phase-adjusted temperature reaches1.17 m/s. These are manufactured mechanism controls, not Earth weather or calibration improvements.</p>
<figure><a href="data/pressure_moist_controls.png"><img src="data/pressure_moist_controls.png" width="{width}" height="{height}" loading="lazy" alt="Repeated moist rain and velocity in stable and conditionally unstable synthetic columns, with a bounded dry control; the unstable case fails physical adoption"></a><figcaption>Both moist cases start motionless, with the same relative-humidity pattern and different declared thermal profiles. The maps use separate color scales. The dry control uses the conditionally unstable case’s phase-adjusted initial temperature, with no latent feedback.</figcaption></figure>
<p>Each moist case runs at600/300/150/75-second timesteps for six hours; a150-second dry control adds144 steps. The total is1224 repeated steps. Stable mean rain is1.053 mm; the conditional stress case produces5.179 mm, versus0.152 mm from its isolated initial phase columns. Continued rain and wind emerge from feedback at every step, not an imposed latent-heating pulse. Both cases converge under timestep refinement; the unstable response remains.</p>
<p>Fourteen new tests bring the focused suite to273 passes. They independently check exact isothermal and log-linear pressure hydrostatics, unequal-grid pressure/compression cancellation, the analytical pressure-coordinate adiabatic limit, motionless equilibrium, actual dry/moist/source/drag/rain budgets, repeat-iteration semantics and rejection of failed coupling. Publication reconstructs final gas enthalpy, kinetic energy, rain enthalpy, water, saturation, wind constraints and refinement errors from saved raw states.</p>
<p class="note">This is a dry/dilute pressure-coordinate prototype with fixed pressure bounds and zero depth-mean flow. Water loading, vapor gas-volume feedback, water gravitational potential/fall heat, ice, stored cloud liquid, nonlinear momentum advection, radiative forcing, terrain and prognostic surface pressure are absent. The enthalpy-only phase budget is different from the fixed-height gas-plus-gz phase model; their terms are not mixed. No observed winds or humidity force the model. Convective stability diagnostics and a physical convection treatment are required before using this branch for an Earth-calibration trial. Earthr39 and all normal climate/biome/population fields remain unchanged. Zero new Earth integrations; counters stay1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p><a href="data/pressure_moist.json" download>Download repeated coupling, controls, provenance and independent checks</a> · <a href="data/pressure_moist_fields.npz">Conditional stress raw fields</a> · <a href="data/pressure_moist_control_fields.npz">Stable/dry control raw fields</a> · <a href="../../reports/PRESSURE_MOIST_20261029.md">Pressure-work derivation, controls and calibration gate</a></p></section><!--pressure-moist-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';s=page.read_text()
    if '<!--pressure-moist-start-->' in s:
        before,tail=s.split('<!--pressure-moist-start-->',1);_,after=tail.split('<!--pressure-moist-end-->',1);s=before+section+after
    else:s=s.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(s)
    receipt=dict(status='published_repeated_pressure_moist_with_controls',actual_earth_integrations=0,interactive_moist_feedback=True,
        physics_or_atlas_adoption=False,independent_publication_checks=checks,metadata_sha256=file_hash(dest/'pressure_moist.json'),
        image_sha256=controls['image_sha256'],publisher_sha256=file_hash(Path(__file__)))
    write_json(out/'publication.json',receipt);print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
