"""Verify/publish fixed-wind prognostic moist transport and falling-water work."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def publish(out):
    receipt=json.loads((out/'verification.json').read_text())
    if (receipt.get('actual_earth_integrations')!=0 or receipt.get('manufactured_only') is not True
            or receipt.get('coupled_climate_connected') is not False or receipt.get('physics_or_atlas_adoption') is not False):raise ValueError('Need isolated scope')
    previous=ROOT/'output/moist_enthalpy_20261028/verification.json'
    if file_hash(previous)!=receipt['prior_receipt_sha256']:raise ValueError('Changed initial state receipt')
    for n,h in receipt['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed source: '+n)
    image=out/'moist_composition.png'
    if file_hash(image)!=receipt['image_sha256']:raise ValueError('Changed image')
    a={n:np.asarray(v) for n,v in receipt['arrays'].items()};m,z=a['layer_mass_kg_m2'],a['height_m']
    for state in ['initial','final']:
        t,w=a[state+'_temperature_k'],a[state+'_vapor_kg_m2']
        energy=(1004*m+1850*w)*t+(2.5e6-1850*273.15)*w+9.80665*(m+w)*z
        np.testing.assert_allclose(energy,a[state+'_static_energy_j_m2'],rtol=1e-14,atol=1e-6)
    e0,e1=a['initial_static_energy_j_m2'],a['final_static_energy_j_m2']
    energy_error=float(abs(e1.sum()+a['rain_enthalpy_j_m2'].sum()-e0.sum())/e0.sum())
    water_error=float(abs(a['final_vapor_kg_m2'].sum()+a['ground_rain_kg_m2'].sum()-a['initial_vapor_kg_m2'].sum())/a['initial_vapor_kg_m2'].sum())
    if max(energy_error,water_error)>1e-12 or np.any(a['ground_rain_kg_m2']<0) or np.any(a['fall_heat_j_m2']<0):raise ValueError('Actual closed moist/precipitation budget failed')
    p=np.asarray(json.loads(previous.read_text())['shared_arrays']['representative_pressure_pa'])
    t=a['final_temperature_k'];es=611.2*np.exp(17.67*(t-273.15)/(t-29.65));sat=m*.622*es/(p-es)
    if np.any(a['final_vapor_kg_m2']>sat*(1+1e-9)):raise ValueError('Final phase saturation failed')
    errors=receipt['refinement_errors']
    if not errors['1.5']['rms_temperature_k']<errors['3.0']['rms_temperature_k']<errors['6.0']['rms_temperature_k']:raise ValueError('Time refinement failed')
    checks=dict(relative_atmosphere_plus_exported_rain_energy_error=energy_error,relative_vapor_plus_ground_rain_water_error=water_error,
                maximum_final_saturation_excess_kg_m2=float(np.maximum(a['final_vapor_kg_m2']-sat,0).max()))
    data=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(image,data/image.name)
    write_json(data/'moist_composition.json',dict(receipt=receipt,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    with Image.open(image) as im:w,h=im.size
    rows=''.join(f'<tr><td>{hours}</td><td>{v["rms_temperature_k"]:.6f}</td><td>{v["rms_vapor_kg_m2"]:.6f}</td><td>{v["rms_rain_kg_m2"]:.6f}</td></tr>' for hours,v in errors.items())
    section=f'''<!--moist-composition-start--><section aria-labelledby="moist-composition-h"><h2 id="moist-composition-h">Prognostic moist transport, phase change and falling-water work</h2>
<p><strong>The thermodynamic operators now run together under fixed winds.</strong> Each step moves vapor and moist static energy on exact dry donor fluxes, then adjusts liquid/vapor phase and lets rain fall. Ground rain carries its actual sensible enthalpy. Lost precipitation potential energy is returned as terminal drag heating along the represented fall path, inside the nonlinear saturation root.</p>
<p>Without that fall-work term, combining the previous transport and phase kernels loses over100kJ/m² in a test column. With it, initial gas static energy equals final gas static energy plus exported rain enthalpy, and initial vapor equals final vapor plus ground rain. The fall model assumes instantaneous terminal motion, uniform drag per distance and no retained precipitation kinetic energy; these are explicit reduced assumptions.</p>
<p>The same closed manufactured wind and phase-adjusted state are integrated for24 hours with6/3/1.5/0.75-hour steps. Geometry matches the maintained15km mode: lower centroid1875m, interface3750m, upper centroid9375m. There is no external heat or water supply. The finest run produces mean0.249 mm and maximum4.030 mm ground rain while its atmosphere-plus-rain energy and vapor-plus-rain water errors are about1.3e-15 relative. These are synthetic fixed-wind results, not Earth rainfall accuracy.</p>
<div class="table"><table><caption>Time refinement of the same24-hour moist problem, differences versus0.75-hour steps</caption><thead><tr><th>Timestep h</th><th>RMS T difference K</th><th>RMS vapor difference kg/m²</th><th>RMS cumulative rain difference kg/m²</th></tr></thead><tbody>{rows}</tbody></table></div>
<figure><a href="data/{image.name}"><img src="data/{image.name}" width="{w}" height="{h}" loading="lazy" alt="Prognostic temperature, vapor and cumulative ground rain over24 hours of closed fixed-wind transport/phase adjustment, including gravitational drag heating and time refinement"></a></figure>
<p>Ten new phase/composition tests pass with the preceding164 focused checks. These four fixed-wind runs use60 composed steps and120 native tracer solves, adding zero Earth climate integrations. Real benchmark counts remain1934 attempts /1929 strict passes /four historical failures /one historical interruption.</p>
<p class="note">This is a closed thermodynamic test under prescribed winds and fixed pressure/heights. It has no momentum feedback, predicted radiation, ice, finite cloud/drop lifetime, precipitation kinetic storage or complete compressible mechanical-energy budget. A consistent evolving thermal-state/pressure-mode relation is still needed for the climate loop. No second adiabatic c²divU cooling is added. Existing Earth r39 and normal world/biome/population climates remain unchanged; no Earth rainfall improvement or global calibration optimum is claimed.</p>
<p><a href="data/moist_composition.json" download>Download moist transient state, cumulative rain and actual energy/water verification</a> · <a href="../../reports/MOIST_COMPOSITION_20261028.md">Composed equations, rain potential work and remaining feedback</a></p></section><!--moist-composition-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--moist-composition-start-->' in text:
        before,tail=text.split('<!--moist-composition-start-->',1);_,after=tail.split('<!--moist-composition-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_isolated_moist_composition',actual_earth_integrations=0,
        physics_or_atlas_adoption=False,metadata_sha256=file_hash(data/'moist_composition.json'),
        image_sha256=receipt['image_sha256'],independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
