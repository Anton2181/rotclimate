"""Verify and publish the conservative phase-to-first-mode forward test."""
from pathlib import Path
import argparse
import json
import shutil
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from rotclimate.column_thermodynamics import CP,G,LV


def verify(out):
    receipt=json.loads((out/'verification.json').read_text())
    if (receipt.get('actual_earth_integrations')!=0 or receipt.get('manufactured_only') is not True
            or receipt.get('coupled_climate_connected') is not False or receipt.get('physics_or_atlas_adoption') is not False):
        raise ValueError('Need explicitly isolated forward demonstration')
    for name,sha in receipt['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed verified source: '+name)
    for name,sha in receipt['images_sha256'].items():
        if file_hash(out/name)!=sha:raise ValueError('Changed verified image: '+name)
    shared={key:np.asarray(value) for key,value in receipt['shared_arrays'].items()}
    mass_layer=shared['layer_mass_kg_m2'];mass=mass_layer.sum(0);total=mass.sum()
    edges=shared['pressure_edges_pa'];dx=receipt['configuration']['cell_m'];dt=86400.
    np.testing.assert_allclose(mass_layer,-np.diff(edges,axis=0)/G,rtol=1e-14)
    a=.25;scale=np.sin(np.pi*a)/(np.pi*a*(1-a));factor=1/(2*scale**2)
    c=.01*15000./np.pi;r=1/(5*86400.);rt=1/(20*86400.)
    verified={}
    for name,case in receipt['cases'].items():
        fields={key:np.asarray(value) for key,value in case['arrays'].items()}
        heat=fields['layer_heat_w_m2'];water_before=fields['initial_vapor'];water_after=fields['final_vapor']
        actual_heat=CP*mass_layer*(fields['final_temperature']-shared['initial_temperature_k'])/dt
        np.testing.assert_allclose(actual_heat,heat,rtol=1e-10,atol=2e-12)
        water_error=water_before.sum(0)-water_after.sum(0)-fields['ground_rain']
        enthalpy_error=np.sum(CP*mass_layer*(fields['final_temperature']-shared['initial_temperature_k'])+LV*(water_after-water_before),axis=0)
        if np.abs(water_error).max()>1e-10 or np.abs(enthalpy_error).max()>1e-5:raise ValueError('Changed actual phase water/enthalpy')
        np.testing.assert_allclose(heat,LV*(fields['condensation']-fields['rain_evaporation'])/dt,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(fields['ground_rain'],fields['condensation'].sum(0)-fields['rain_evaporation'].sum(0),rtol=1e-12,atol=1e-12)
        # Independent exact integrals over the two constant heating intervals.
        buoyancy=G*heat/(CP*275.*mass_layer)
        sine_integral=np.array([(1-np.cos(np.pi*.25))/np.pi,(np.cos(np.pi*.25)+1)/np.pi])[:,None,None]
        first=2*np.sum(sine_integral*buoyancy,axis=0)
        forcing=scale*first/(np.pi/15000.)
        np.testing.assert_allclose(fields['projected_forcing'],forcing,rtol=1e-12,atol=1e-16)
        if abs(case['projection_certificate']['wave_speed_ms']-c)>1e-12:raise ValueError('Changed derived mode speed')
        phi,u,v=fields['geopotential'],fields['u_east'],fields['v_south']
        if np.any(u[:,[0,-1]]) or np.any(v[[0,-1]]):raise ValueError('Closed edges changed')
        mu=np.column_stack((mass[:,0],.5*(mass[:,:-1]+mass[:,1:]),mass[:,-1]))
        mv=np.vstack((mass[0],.5*(mass[:-1]+mass[1:]),mass[-1]))
        div=(np.diff(mu*u,axis=1)+np.diff(mv*v,axis=0))/(mass*dx)
        np.testing.assert_allclose(c*c*div+rt*phi,forcing,rtol=1e-9,atol=1e-13)
        supply=float(factor*np.sum(mass*phi*forcing/c**2)/total)
        drag=float(factor*r*(np.sum(mu[:,1:-1]*u[:,1:-1]**2)+np.sum(mv[1:-1]*v[1:-1]**2))/total)
        cooling=float(factor*rt*np.sum(mass*(phi/c)**2)/total)
        work_error=abs(supply-drag-cooling)/max(abs(supply),1e-30)
        if work_error>1e-10:raise ValueError('Changed continuous first-mode work balance')
        verified[name]=dict(maximum_water_residual_kg_m2=float(np.abs(water_error).max()),
            maximum_dilute_enthalpy_residual_j_m2=float(np.abs(enthalpy_error).max()),
            relative_continuous_first_mode_work_error=work_error,
            independent_input_m2_s3=supply,independent_momentum_damping_m2_s3=drag,
            independent_thermal_damping_m2_s3=cooling)
    return receipt,verified


def publish(out):
    receipt,verified=verify(out)
    data=ROOT/'atlases/climate_accuracy/data';figures=[]
    for name,caption in [
        ('latent_phase_budget.png','The same upper condensation can yield no ground rain or surviving rain, depending on lower humidity, with separately accounted heating and cooling'),
        ('latent_mode_response.png','Accounted latent heat projected on a specified constant-stability first mode, followed by a steady dry circulation response; not an Earth forecast')]:
        shutil.copyfile(out/name,data/name)
        with Image.open(out/name) as picture:w,h=picture.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{caption}"></a><figcaption>{caption}.</figcaption></figure>')
    write_json(data/'latent_circulation.json',dict(receipt=receipt,independent_publication_checks=verified,publisher_sha256=file_hash(Path(__file__))))
    rows=[]
    for name,case in receipt['cases'].items():
        check=case['independent']
        rows.append(f'<tr><td>{name}</td><td>{check["maximum_upper_condensation_kg_m2"]:.3f}</td><td>{check["maximum_lower_rain_evaporation_kg_m2"]:.3f}</td><td>{check["maximum_surface_rain_kg_m2"]:.3f}</td><td>{check["maximum_absolute_net_column_heat_w_m2"]:.2f}</td><td>{1e6*check["continuous_first_mode_input_m2_s3"]:.3f}</td></tr>')
    section=f'''<!--latent-circulation-start--><section aria-labelledby="latent-circulation-h"><h2 id="latent-circulation-h">Conservative phase change and specified vertical-mode heating</h2>
<p><strong>Accounted heating now drives an isolated circulation response; no Earth rainfall improvement is claimed.</strong> Condensation warms its layer, falling rain can evaporate and cool the layer below, and surviving liquid reaches the ground. A bracketed saturation root conserves water and the stated dilute enthalpy cp·Md·T + Lv·Wv. It evaluates saturation at the adjusted temperature. Ground rain and atmospheric condensation are distinct stored quantities.</p>
<p>The same upper moist pulse condenses up to4.157 mm in both cases. Dry lower air reevaporates all of it, producing zero ground rain and zero net column heat while preserving an upper-heating/lower-cooling dipole. Humid lower air passes up to3.931 mm to the ground and cools less. These are maxima at potentially different cells, not a shared-cell arithmetic budget. The fields use kg/m² per one-day manufactured pulse, not observed daily climatology.</p>
<div class="table"><table><caption>Manufactured phase-change maxima and independent continuous first-mode work; work is not total thermodynamic heat</caption><thead><tr><th>Case</th><th>Upper condensation mm</th><th>Lower evaporation mm</th><th>Ground rain mm</th><th>Maximum net heat W/m²</th><th>Mean mode work10⁻⁶m²/s³</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
{figures[0]}
<p>The vertical projection is derived for a maintained constant-stability hydrostatic Boussinesq atmosphere with rigid lids. N=0.01/s and depth15 km imply c=N·H/π=47.75 m/s. Heating in W/m² is converted to layer temperature tendency, then projected onto the sine buoyancy mode. Exact cosine layer averages set the lower/upper wind normalization; the continuous mode’s work includes the corresponding energy factor. Independent vertical integrals verify both. A dry log-pressure thickness diagnostic is also recorded, but is not substituted for this first-mode forcing.</p>
{figures[1]}
<p>Thirty-three new phase/projection tests cover independent saturation roots, full and partial reevaporation, analytic pressure integrals, vertical-mode averages and physical buoyancy work. The wider focused suite passes146 tests. Raw fields, source hashes and independent water/enthalpy/work checks are downloadable. The two new regional responses add zero Earth climate integrations; cumulative counts stay1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p class="note">This is a forward demonstration, not a coupled transient moist atmosphere. A one-day phase pulse supplies a steady dry response; it does not imply that response is reached in one day. No moisture is re-transported or re-condensed afterward. The phase model omits ice, liquid/vapor heat capacities, precipitation enthalpy and gravitational work. The vertical mode assumes uniform reference density and maintained constant N; it is not a compressible Earth eigenmode. Net column heat and unrepresented vertical heating remain in the ledger; captured forcing norm is not captured total heat. Full atmospheric energy transport, radiation, background flow, terrain modes and incoming states remain to be supplied.</p>
<p>Existing Earth r39 and normal world/biome/population climates remain unchanged. The next coupled Earth test must retain location/month rainfall loss, regional tradeoffs, temperature/physical guards and excluded-region checks. Linear-solve uniqueness does not establish a global nonlinear calibration optimum.</p>
<p><a href="data/latent_circulation.json" download>Download phase, heating projection, circulation fields and verification</a> · <a href="../../reports/LATENT_HEATING_20261028.md">Conservative phase change and thickness accounting</a> · <a href="../../reports/FIRST_MODE_HEATING_20261028.md">Vertical-mode derivation, energy normalization and limits</a></p></section><!--latent-circulation-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--latent-circulation-start-->' in text:
        before,tail=text.split('<!--latent-circulation-start-->',1);_,after=tail.split('<!--latent-circulation-end-->',1)
        text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_isolated_latent_forward_demonstration',
        physics_or_atlas_adoption=False,actual_earth_integrations=0,
        metadata_sha256=file_hash(data/'latent_circulation.json'),images_sha256=receipt['images_sha256'],
        independent_publication_checks=verified,publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    publish(parser.parse_args().out.resolve())
