"""Publish the verified fixed-wind transient energy/adiabatic transport test."""
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
    if file_hash(previous)!=receipt['prior_receipt_sha256']:raise ValueError('Changed initial-state receipt')
    for n,h in receipt['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed verified source: '+n)
    image=out/'energy_transport.png'
    if file_hash(image)!=receipt['image_sha256']:raise ValueError('Changed image')
    a={n:np.asarray(v) for n,v in receipt['arrays'].items()}
    m,z=a['layer_mass_kg_m2'],a['height_m'];checks={}
    for state in ['initial','final']:
        t,w=a[state+'_temperature_k'],a[state+'_vapor_kg_m2']
        independent=(1004*m+1850*w)*t+(2.5e6-1850*273.15)*w+9.80665*(m+w)*z
        np.testing.assert_allclose(independent,a[state+'_static_energy_j_m2'],rtol=1e-14,atol=1e-6)
    e0,e1=a['initial_static_energy_j_m2'],a['final_static_energy_j_m2']
    checks['relative_total_energy_error']=float(abs(e1.sum()-e0.sum())/e0.sum())
    checks['relative_total_vapor_error']=float(abs(a['final_vapor_kg_m2'].sum()-a['initial_vapor_kg_m2'].sum())/a['initial_vapor_kg_m2'].sum())
    if max(checks.values())>1e-12:raise ValueError('Closed transient budget failed')
    errors=receipt['refinement_errors']
    if not errors['1.5']['rms_temperature_k']<errors['3.0']['rms_temperature_k']<errors['6.0']['rms_temperature_k']:raise ValueError('Time refinement failed')
    data=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(image,data/image.name)
    write_json(data/'energy_transport.json',dict(receipt=receipt,independent_publication_checks=checks,publisher_sha256=file_hash(Path(__file__))))
    with Image.open(image) as im:w,h=im.size
    rows=''.join(f'<tr><td>{hours}</td><td>{v["rms_temperature_k"]:.6f}</td><td>{v["rms_vapor_kg_m2"]:.6f}</td></tr>' for hours,v in errors.items())
    section=f'''<!--energy-transport-start--><section aria-labelledby="energy-transport-h"><h2 id="energy-transport-h">Prognostic vapor and moist static energy on exact air fluxes</h2>
<p><strong>The new fixed-wind thermodynamic step transports energy and water together.</strong> Including dry/vapor gravitational potential makes rising air cool and descending air warm in the dry hydrostatic limit. The donor fluxes are exactly those solved by the regional circulation. Vapor injection carries its own temperature-dependent enthalpy; external heating and boundary energy are separately accounted.</p>
<p>The native transport equation is advanced with backward Euler: old state/dt plus physical source balances new state/dt plus actual donor transport. The1/dt term is time tendency, not rainfall or heat dissipation. An exact uniform moist-static-energy and mixing-ratio equilibrium is preserved even over varying column mass. Tests also verify independent heated boxes, injected vapor without spurious warming, and dry ascent/descent energy conservation.</p>
<p>The same closed manufactured circulation and phase-adjusted state are transported for24 hours at6/3/1.5/0.75-hour timesteps, with no external heat or water. This adds60 implicit steps and120 native tracer solves, but zero Earth climate integrations. Against the0.75-hour solution, reducing timestep gives the differences below. Relative total energy and water drift remain below1e-12. These are numerical consistency results, not Earth forecast accuracy.</p>
<div class="table"><table><caption>Same24-hour elapsed fixed-wind problem, differences against0.75-hour time steps</caption><thead><tr><th>Timestep h</th><th>RMS temperature difference K</th><th>RMS vapor difference kg/m²</th></tr></thead><tbody>{rows}</tbody></table></div>
<figure><a href="data/{image.name}"><img src="data/{image.name}" width="{w}" height="{h}" loading="lazy" alt="Temperature and vapor redistribution after24-hour closed fixed-wind moist-static-energy transport, plus time-step refinement; no rain or momentum feedback"></a></figure>
<p>Eight new transport tests pass in addition to the preceding156 focused checks. Actual Earth counters remain1934 attempts /1929 strict passes /four historical failures /one historical interruption. Existing Earth r39 and normal world/biome/population climates remain unchanged.</p>
<p class="note">No phase adjustment is performed during this transport test; initially saturated air can become supersaturated. It predicts no rain. Layer heights and winds stay fixed, with no momentum feedback or predicted radiation. The static-energy treatment approximates hydrostatic adiabatic work, not a full compressible mechanical-energy budget. Combining it with phase change must account for falling-water gravitational/mechanical energy. Adding a second adiabatic c²divU temperature tendency from the dry-mode solver would double count ascent cooling. The thermodynamic-state/pressure-mode relation must be resolved before a coupled Earth pilot.</p>
<p><a href="data/energy_transport.json" download>Download transient temperature, vapor, energy and refinement verification</a> · <a href="../../reports/ENERGY_TRANSPORT_20261028.md">Energy equations, time stepping and coupling limits</a></p></section><!--energy-transport-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--energy-transport-start-->' in text:
        before,tail=text.split('<!--energy-transport-start-->',1);_,after=tail.split('<!--energy-transport-end-->',1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_isolated_energy_transport',actual_earth_integrations=0,
        physics_or_atlas_adoption=False,independent_publication_checks=checks,
        metadata_sha256=file_hash(data/'energy_transport.json'),image_sha256=receipt['image_sha256'],publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
